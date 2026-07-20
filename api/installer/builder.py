"""
On-demand installer generation: stage this PluginBuild's uploaded files into
a temp directory, generate the .nsi script + branding assets, shell out to
the NSIS compiler (`makensis`), and return the resulting .exe as bytes.
Nothing is written to object storage — the caller (a customer's live
download, or staff/partner testing from the products list) gets the freshly
built file directly and it's discarded once the temp directory closes.
There is deliberately no "build once, cache, reuse" step in this project —
see installer/models.py.
"""
import subprocess
import shutil
import tempfile
from pathlib import Path

from django.conf import settings

from installer.branding import write_branding_assets
from installer.license_shim import (
    SHIM_DLL_NAME,
    SHIM_DLL_PATH,
    AddinRewriteError,
    build_license_config,
    build_real_plugin_hint,
    rewrite_addin_for_shim,
)
from installer.models import PluginBuild
from installer.nsis_generator import OUTPUT_FILENAME, generate_nsis_script, resolve_scope


class BuildError(Exception):
    pass


def _stage_file(storage_key: str, dest: Path) -> None:
    from django.core.files.storage import default_storage

    dest.parent.mkdir(parents=True, exist_ok=True)
    with default_storage.open(storage_key, "rb") as source, open(dest, "wb") as target:
        shutil.copyfileobj(source, target)


def _stage_payload(build: PluginBuild, staging_dir: Path) -> None:
    """Stages the real plugin .dll plus everything LicLoader.dll (the
    license-check shim every installer wraps the plugin with — see
    installer/license_shim.py) needs sitting right next to it: itself, the
    .addin manifest rewritten to load it instead of the real plugin, a hint
    file pointing at the real plugin's filename, and the per-product online
    license config."""
    payload_dir = staging_dir / "payload"
    payload_dir.mkdir(parents=True, exist_ok=True)

    _stage_file(build.dll_storage_key, payload_dir / build.dll_filename)
    shutil.copyfile(SHIM_DLL_PATH, payload_dir / SHIM_DLL_NAME)
    (payload_dir / "_real_plugin.txt").write_bytes(build_real_plugin_hint(build.dll_filename))
    (payload_dir / "_license.bin").write_bytes(build_license_config(build))

    from django.core.files.storage import default_storage

    with default_storage.open(build.addin_storage_key, "rb") as source:
        raw_addin = source.read()
    try:
        wrapped_addin = rewrite_addin_for_shim(raw_addin)
    except AddinRewriteError as exc:
        raise BuildError(f"Could not license-protect this build: {exc}") from exc
    (payload_dir / build.addin_filename).write_bytes(wrapped_addin)

    for index, resource in enumerate(build.resource_files.all()):
        rel = f"resources/{index}_{resource.original_filename}"
        _stage_file(resource.storage_key, payload_dir / rel)


def _run_nsis_build(nsi_path: Path, staging_dir: Path) -> tuple[bool, str]:
    args = [settings.NSIS_EXECUTABLE, "-V2", str(nsi_path.name)]
    try:
        result = subprocess.run(
            args,
            cwd=str(staging_dir),
            capture_output=True,
            text=True,
            timeout=settings.INSTALLER_BUILD_TIMEOUT_SECONDS,
        )
    except FileNotFoundError as exc:
        return False, (
            f"NSIS compiler not found ({settings.NSIS_EXECUTABLE!r}). Install it with "
            f"`apt-get install nsis`, or set NSIS_EXECUTABLE. ({exc})"
        )
    except subprocess.TimeoutExpired:
        return False, f"NSIS build exceeded {settings.INSTALLER_BUILD_TIMEOUT_SECONDS}s and was aborted."

    log = f"$ {' '.join(args)}\n\n--- stdout ---\n{result.stdout}\n\n--- stderr ---\n{result.stderr}"
    return result.returncode == 0, log


def generate_installer_bytes(build: PluginBuild) -> tuple[bool, str, bytes | None, str]:
    """Generates the .exe right now, in memory, and returns
    (success, log, installer_bytes, filename). Never raises, never persists
    anything — every caller (customer download, admin/partner test
    download) gets a fresh build each time. `build.scope` is kept in sync
    by installer/api.py whenever a resource is added/removed, so it doesn't
    need recomputing here for anything other than the .nsi script itself."""
    if not build.is_ready_for_build:
        return False, "Both a .dll and a .addin file are required before building.", None, ""

    resource_files = list(build.resource_files.all())
    resolve_scope(resource_files)  # validated here so a bad destination_path fails loudly, before staging

    with tempfile.TemporaryDirectory(prefix="bimhive-installer-") as tmp:
        staging_dir = Path(tmp)
        try:
            _stage_payload(build, staging_dir)
            write_branding_assets(staging_dir, build.product.name, settings.INSTALLER_MANUFACTURER)
            nsi_source, _ = generate_nsis_script(build, resource_files)
            nsi_path = staging_dir / "installer.nsi"
            nsi_path.write_text(nsi_source, encoding="utf-8")

            success, log = _run_nsis_build(nsi_path, staging_dir)
            output_exe = staging_dir / OUTPUT_FILENAME
        except Exception as exc:  # noqa: BLE001 — any staging/IO failure is a build failure, not a 500
            return False, f"Build failed before invoking NSIS: {exc}", None, ""

        if not success or not output_exe.exists():
            return False, log, None, ""

        slug = build.product.slug or "plugin"
        installer_name = f"{slug}-{build.revit_year}.exe"
        return True, log, output_exe.read_bytes(), installer_name
