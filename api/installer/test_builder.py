"""
Real end-to-end build tests — actually invoke the WiX CLI (installed via
`dotnet tool install --global wix` + `wix extension add -g
WixToolset.UI.wixext`, same as local dev) rather than mocking subprocess,
because the thing most likely to silently break here is the generated .wxs
no longer being valid WiX syntax — a mock would never catch that. Slower
than the rest of the suite (each build takes several seconds); that's the
right trade for actually proving the pipeline works.
"""
import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from catalog.models import Category, Product
from installer.builder import build_plugin_installer
from installer.models import PluginBuild, PluginResourceFile

pytestmark = pytest.mark.django_db


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
    result = build_plugin_installer(build)
    assert result.status == PluginBuild.Status.FAILED
    assert "dll" in result.build_log.lower()


def test_peruser_build_produces_a_real_msi(product):
    build = PluginBuild.objects.create(product=product, revit_year="2024", plugin_version="1.0.0")
    _stage_dll_and_addin(build)

    result = build_plugin_installer(build)

    assert result.status == PluginBuild.Status.READY, result.build_log
    assert result.scope == "perUser"
    assert result.built_msi_storage_key
    assert default_storage.exists(result.built_msi_storage_key)


def test_permachine_build_with_a_dependency_produces_a_real_msi(product):
    build = PluginBuild.objects.create(product=product, revit_year="2025", plugin_version="1.1.0")
    _stage_dll_and_addin(build)
    dep_key = default_storage.save(f"test/{product.id}/dep.dll", ContentFile(b"fake dependency bytes"))
    PluginResourceFile.objects.create(
        build=build, storage_key=dep_key, original_filename="dep.dll",
        destination_path=r"{INSTALL_DIR}\lib\dep.dll", kind="dependency",
    )

    result = build_plugin_installer(build)

    assert result.status == PluginBuild.Status.READY, result.build_log
    assert result.scope == "perMachine"
    assert default_storage.exists(result.built_msi_storage_key)


def test_successful_build_syncs_a_product_file(product):
    build = PluginBuild.objects.create(product=product, revit_year="2026", plugin_version="3.0.0")
    _stage_dll_and_addin(build)

    build_plugin_installer(build)

    from catalog.models import ProductFile

    product_file = ProductFile.objects.get(product=product, revit_version="2026")
    assert product_file.version_label == "3.0.0"
    assert product_file.storage_key == build.built_msi_storage_key
    assert product_file.is_current is True


def test_rebuild_keeps_the_same_upgrade_code(product):
    build = PluginBuild.objects.create(product=product, revit_year="2027", plugin_version="1.0.0")
    _stage_dll_and_addin(build)
    build_plugin_installer(build)
    original_upgrade_code = build.upgrade_code

    build.plugin_version = "1.0.1"
    build.save()
    result = build_plugin_installer(build)

    assert result.status == PluginBuild.Status.READY, result.build_log
    assert result.upgrade_code == original_upgrade_code
