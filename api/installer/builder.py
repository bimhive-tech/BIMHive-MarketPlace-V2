"""
Top-level build orchestration: stage this PluginBuild's files into a temp
directory, generate the .wxs + branding assets, shell out to the WiX CLI,
and — on success — upload the resulting .msi to object storage and sync it
into catalog.ProductFile so the existing storefront download flow (already
entitlement-gated, already logged — see licensing/account_api.py) picks it
up with zero changes on that side.
"""
import shutil
import subprocess
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone

from installer.branding import write_branding_assets
from installer.models import PluginBuild
from installer.wxs_generator import generate_wxs


class BuildError(Exception):
    pass


def _stage_file(storage_key: str, dest: Path) -> None:
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


def build_plugin_installer(build: PluginBuild) -> PluginBuild:
    """Runs synchronously — this project has no background task queue, and a
    plugin installer build (well under the configured timeout in practice)
    is short enough to run inline on the triggering request. Always leaves
    the build in a terminal status (ready/failed) with a log, never raises,
    so the caller can render the outcome directly."""
    if not build.is_ready_for_build:
        build.status = PluginBuild.Status.FAILED
        build.build_log = "Both a .dll and a .addin file are required before building."
        build.save(update_fields=["status", "build_log", "updated_at"])
        return build

    build.status = PluginBuild.Status.BUILDING
    build.save(update_fields=["status", "updated_at"])

    resource_files = list(build.resource_files.all())
    from installer.wxs_generator import resolve_scope

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
            output_msi = staging_dir / f"{slug}-{build.revit_year}.msi"
            success, log = _run_wix_build(wxs_path, output_msi, staging_dir)
        except Exception as exc:  # noqa: BLE001 — any staging/IO failure is a build failure, not a 500
            build.status = PluginBuild.Status.FAILED
            build.scope = scope
            build.build_log = f"Build failed before invoking WiX: {exc}"
            build.save(update_fields=["status", "scope", "build_log", "updated_at"])
            return build

        build.scope = scope
        build.build_log = log

        if not success or not output_msi.exists():
            build.status = PluginBuild.Status.FAILED
            build.save(update_fields=["status", "scope", "build_log", "updated_at"])
            return build

        storage_key = f"plugin_builds/{build.product_id}/{build.revit_year}/{output_msi.name}"
        with open(output_msi, "rb") as fh:
            saved_key = default_storage.save(storage_key, ContentFile(fh.read()))

        build.status = PluginBuild.Status.READY
        build.built_msi_storage_key = saved_key
        build.built_at = timezone.now()
        build.save(
            update_fields=["status", "scope", "build_log", "built_msi_storage_key", "built_at", "updated_at"]
        )
        _sync_product_file(build, output_msi.stat().st_size)
        return build


def _sync_product_file(build: PluginBuild, file_size_bytes: int) -> None:
    """Mirrors licensing.services.sync_license_sku's update_or_create
    pattern — a successful auto-build becomes the ProductFile the existing,
    already-entitlement-gated download flow serves, keyed the same way a
    manually-uploaded file variant would be."""
    from catalog.models import ProductFile

    ProductFile.objects.update_or_create(
        product=build.product,
        revit_version=build.revit_year,
        version_label=build.plugin_version,
        defaults={
            "storage_key": build.built_msi_storage_key,
            "file_size_bytes": file_size_bytes,
            "is_current": True,
        },
    )
