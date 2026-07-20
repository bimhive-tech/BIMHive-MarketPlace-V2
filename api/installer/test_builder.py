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
    addin_key = default_storage.save(f"test/{build.product_id}/Plugin.addin", ContentFile(b"<RevitAddIns/>"))
    build.dll_storage_key = dll_key
    build.dll_filename = "Plugin.dll"
    build.addin_storage_key = addin_key
    build.addin_filename = "Plugin.addin"
    build.save()


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
