"""
Real end-to-end build tests — actually invoke the NSIS CLI (`makensis`,
installed via `apt-get install nsis` locally and in the Docker image)
rather than mocking subprocess, because the thing most likely to silently
break here is the generated .nsi no longer being valid NSIS syntax — a mock
would never catch that. Slower than the rest of the suite (each build takes
a couple seconds); that's the right trade for actually proving the
pipeline works.

generate_installer_bytes is on-demand and never touches storage — these
tests assert on the returned bytes directly rather than a saved file.
"""
import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from catalog.models import Category, Product
from installer.builder import generate_installer_bytes
from installer.models import PluginBuild, PluginResourceFile

pytestmark = pytest.mark.django_db

# A real Windows PE executable starts with "MZ" — cheap sanity check that
# makensis actually produced an .exe and not, say, an empty/garbage file.
PE_MAGIC = b"MZ"

# A realistic minimal Revit .addin manifest — the license shim (see
# installer/license_shim.py::rewrite_addin_for_shim) rewrites <Assembly>/
# <FullClassName> to point at LicLoader instead, so it needs something
# that actually parses as a normal add-in manifest, not a bare stub.
SAMPLE_ADDIN_XML = b"""<?xml version="1.0" encoding="utf-8" standalone="no"?>
<RevitAddIns>
  <AddIn Type="Application">
    <Name>Test Plugin</Name>
    <Assembly>Plugin.dll</Assembly>
    <AddInId>ABCDEF12-3456-7890-ABCD-EF1234567890</AddInId>
    <FullClassName>TestPlugin.App</FullClassName>
    <VendorId>TEST</VendorId>
  </AddIn>
</RevitAddIns>"""


@pytest.fixture
def category():
    return Category.objects.create(name="Revit Plugins")


@pytest.fixture
def product(category):
    return Product.objects.create(
        name="Builder Test Plugin", product_code="builder-test", category=category,
        short_description="s", description="d",
    )


def _stage_dll_and_addin(build):
    dll_key = default_storage.save(f"test/{build.product_id}/Plugin.dll", ContentFile(b"fake dll bytes"))
    addin_key = default_storage.save(f"test/{build.product_id}/Plugin.addin", ContentFile(SAMPLE_ADDIN_XML))
    build.dll_storage_key = dll_key
    build.dll_filename = "Plugin.dll"
    build.addin_storage_key = addin_key
    build.addin_filename = "Plugin.addin"
    build.save()


def test_staging_wraps_the_addin_with_the_license_shim(product, tmp_path):
    """Doesn't need makensis at all — just checks _stage_payload put the
    right files in the right place, which is the part that actually
    matters for licensing to work (see installer/license_shim.py)."""
    from installer.builder import _stage_payload
    from installer.license_shim import SHIM_DLL_NAME

    build = PluginBuild.objects.create(product=product, revit_year="2025", plugin_version="1.0.0")
    _stage_dll_and_addin(build)

    _stage_payload(build, tmp_path)
    payload_dir = tmp_path / "payload"

    assert (payload_dir / build.dll_filename).read_bytes() == b"fake dll bytes"
    assert (payload_dir / SHIM_DLL_NAME).exists()
    assert (payload_dir / "_real_plugin.txt").read_text() == build.dll_filename
    license_config = (payload_dir / "_license.bin").read_text()
    assert product.product_code in license_config
    assert "onlineLicense" in license_config

    rewritten_addin = (payload_dir / build.addin_filename).read_text()
    assert "LicLoader.dll" in rewritten_addin
    assert "LicLoader.ExternalApp" in rewritten_addin
    assert "Plugin.dll" not in rewritten_addin  # the real assembly reference is gone, not just supplemented


def test_staging_fails_loudly_on_an_unparseable_addin(product, tmp_path):
    from installer.builder import _stage_payload

    build = PluginBuild.objects.create(product=product, revit_year="2025")
    build.dll_storage_key = default_storage.save(f"test/{product.id}/Plugin.dll", ContentFile(b"fake dll bytes"))
    build.dll_filename = "Plugin.dll"
    build.addin_storage_key = default_storage.save(f"test/{product.id}/broken.addin", ContentFile(b"not xml at all"))
    build.addin_filename = "broken.addin"
    build.save()

    with pytest.raises(Exception, match="license-protect"):
        _stage_payload(build, tmp_path)


def test_build_without_dll_or_addin_fails_cleanly(product):
    build = PluginBuild.objects.create(product=product, revit_year="2025")
    success, log, installer_bytes, installer_name = generate_installer_bytes(build)
    assert success is False
    assert installer_bytes is None
    assert "dll" in log.lower()


def test_peruser_build_produces_a_real_exe(product):
    build = PluginBuild.objects.create(product=product, revit_year="2024", plugin_version="1.0.0")
    _stage_dll_and_addin(build)

    success, log, installer_bytes, installer_name = generate_installer_bytes(build)

    assert success is True, log
    assert installer_bytes and installer_bytes.startswith(PE_MAGIC)
    assert installer_name.endswith(".exe")
    # Nothing gets persisted anywhere — the whole point of on-demand generation.
    assert not default_storage.exists(f"plugin_builds/{build.product_id}/{build.revit_year}/{installer_name}")


def test_permachine_build_with_a_dependency_produces_a_real_exe(product):
    build = PluginBuild.objects.create(product=product, revit_year="2025", plugin_version="1.1.0")
    _stage_dll_and_addin(build)
    dep_key = default_storage.save(f"test/{product.id}/dep.dll", ContentFile(b"fake dependency bytes"))
    PluginResourceFile.objects.create(
        build=build, storage_key=dep_key, original_filename="dep.dll",
        destination_path=r"{INSTALL_DIR}\lib\dep.dll", kind="dependency",
    )

    success, log, installer_bytes, installer_name = generate_installer_bytes(build)

    assert success is True, log
    assert installer_bytes and installer_bytes.startswith(PE_MAGIC)


def test_rebuild_keeps_the_same_upgrade_code(product):
    build = PluginBuild.objects.create(product=product, revit_year="2027", plugin_version="1.0.0")
    _stage_dll_and_addin(build)
    generate_installer_bytes(build)
    original_upgrade_code = build.upgrade_code

    build.plugin_version = "1.0.1"
    build.save()
    success, log, installer_bytes, installer_name = generate_installer_bytes(build)

    assert success is True, log
    build.refresh_from_db()
    assert build.upgrade_code == original_upgrade_code
