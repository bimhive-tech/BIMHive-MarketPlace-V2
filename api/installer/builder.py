"""
On-demand installer generation: stage this PluginBuild's uploaded files into
a temp directory, generate the .wxs + branding assets, shell out to the WiX
CLI, and return the resulting .msi as bytes. Nothing is written to object
storage — the caller (a customer's live download, or staff/partner testing
from the products list) gets the freshly-built file directly and it's
discarded once the temp directory closes. There is deliberately no "build
once, cache, reuse" step in this project — see installer/models.py.
"""
import subprocess
import shutil
import tempfile
from pathlib import Path

from django.conf import settings

from installer.branding import write_branding_assets
from installer.models import PluginBuild
from installer.wxs_generator import generate_wxs, resolve_scope


class BuildError(Exception):
    pass


def _stage_file(storage_key: str, dest: Path) -> None:
    from django.core.files.storage import default_storage

    dest.parent.mkdir(parents=True, exist_ok=True)
    with default_storage.open(storage_key, "rb") as source, open(dest, "wb") as target:
        shutil.copyfileobj(source, target)


def _stage_payload(build: PluginBuild, staging_dir: Path) -> None:
    payload_dir = staging_dir / "payload"
    _stage_file(build.dll_storage_key, payload_dir / build.dll_filename)
    _stage_file(build.addin_storage_key, payload_dir / build.addin_filename)
    for index, resource in enumerate(build.resource_files.all()):
        rel = f"resources/{index}_{resource.original_filename}"
        _stage_file(resource.storage_key, payload_dir / rel)


def _run_wix_build(wxs_path: Path, output_msi: Path, staging_dir: Path) -> tuple[bool, str]:
    args = [
        settings.WIX_EXECUTABLE,
        "build",
        str(wxs_path),
        "-ext",
        "WixToolset.UI.wixext",
        "-o",
        str(output_msi),
    ]
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
            f"WiX CLI not found ({settings.WIX_EXECUTABLE!r}). Install it with "
            "`dotnet tool install --global wix` and `wix extension add -g "
            f"WixToolset.UI.wixext`, or set WIX_EXECUTABLE. ({exc})"
        )
    except subprocess.TimeoutExpired:
        return False, f"WiX build exceeded {settings.INSTALLER_BUILD_TIMEOUT_SECONDS}s and was aborted."

    log = f"$ {' '.join(args)}\n\n--- stdout ---\n{result.stdout}\n\n--- stderr ---\n{result.stderr}"
    return result.returncode == 0, log


def generate_installer_bytes(build: PluginBuild) -> tuple[bool, str, bytes | None, str]:
    """Generates the .msi right now, in memory, and returns
    (success, log, msi_bytes, filename). Never raises, never persists
    anything — every caller (customer download, admin/partner test
    download) gets a fresh build each time. `build.scope` is kept in sync
    by installer/api.py whenever a resource is added/removed, so it doesn't
    need recomputing here for anything other than the .wxs itself."""
    if not build.is_ready_for_build:
        return False, "Both a .dll and a .addin file are required before building.", None, ""

    resource_files = list(build.resource_files.all())
    scope = resolve_scope(resource_files)

    with tempfile.TemporaryDirectory(prefix="bimhive-installer-") as tmp:
        staging_dir = Path(tmp)
        try:
            _stage_payload(build, staging_dir)
            write_branding_assets(staging_dir, build.product.name, settings.INSTALLER_MANUFACTURER)
            wxs_source, _ = generate_wxs(build, resource_files)
            wxs_path = staging_dir / "installer.wxs"
            wxs_path.write_text(wxs_source, encoding="utf-8")

            slug = build.product.slug or "plugin"
            msi_name = f"{slug}-{build.revit_year}.msi"
            output_msi = staging_dir / msi_name
            success, log = _run_wix_build(wxs_path, output_msi, staging_dir)
        except Exception as exc:  # noqa: BLE001 — any staging/IO failure is a build failure, not a 500
            return False, f"Build failed before invoking WiX: {exc}", None, ""

        if not success or not output_msi.exists():
            return False, log, None, ""

        return True, log, output_msi.read_bytes(), msi_name
