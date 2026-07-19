"""
WXS generation logic — string/structure assertions only, no WiX CLI
invocation (see test_builder.py for the real end-to-end build). Verifies
the two things the legacy generator got wrong (stable UpgradeCode, real
Version) and the new scope-selection behavior this rebuild adds.
"""
import pytest

from catalog.models import Category, Product
from installer.models import PluginBuild, PluginResourceFile
from installer.wxs_generator import generate_wxs, resolve_scope

pytestmark = pytest.mark.django_db


@pytest.fixture
def category():
    return Category.objects.create(name="Revit Plugins")


@pytest.fixture
def build(category):
    product = Product.objects.create(
        name="Test Plugin", product_code="wxs-test", category=category,
        short_description="s", description="d", version="2.5.0",
    )
    return PluginBuild.objects.create(
        product=product, revit_year="2025", plugin_version="2.5.0",
        dll_storage_key="x/Plugin.dll", dll_filename="Plugin.dll",
        addin_storage_key="x/Plugin.addin", addin_filename="Plugin.addin",
    )


def test_resolve_scope_defaults_to_peruser_with_no_resources(build):
    assert resolve_scope([]) == "perUser"


def test_resolve_scope_is_permachine_when_any_resource_targets_install_dir(build):
    resource = PluginResourceFile(
        build=build, storage_key="x/dep.dll", original_filename="dep.dll",
        destination_path=r"{INSTALL_DIR}\dep.dll",
    )
    assert resolve_scope([resource]) == "perMachine"


def test_generated_wxs_uses_the_products_real_version_not_a_hardcoded_one(build):
    wxs, _ = generate_wxs(build, [])
    assert 'Version="2.5.0"' in wxs
    assert 'Version="1.0.0"' not in wxs


def test_generated_wxs_upgrade_code_matches_the_persisted_one(build):
    wxs, _ = generate_wxs(build, [])
    assert str(build.upgrade_code).upper() in wxs


def test_rebuilding_with_a_new_version_keeps_the_same_upgrade_code(build):
    first_wxs, _ = generate_wxs(build, [])
    build.plugin_version = "2.6.0"
    build.save()
    second_wxs, _ = generate_wxs(build, [])
    assert str(build.upgrade_code).upper() in first_wxs
    assert str(build.upgrade_code).upper() in second_wxs
    assert 'Version="2.5.0"' in first_wxs
    assert 'Version="2.6.0"' in second_wxs


def test_plugin_name_is_escaped_against_xml_injection(build):
    build.product.name = 'Evil"><Component/>'
    wxs, _ = generate_wxs(build, [])
    assert "<Component/>" not in wxs
    assert "&lt;Component/&gt;" in wxs


def test_resource_under_addin_dir_appears_once_as_a_component(build):
    resource = PluginResourceFile(
        build=build, storage_key="x/icon.png", original_filename="icon.png",
        destination_path=r"{ADDIN_DIR}\Resources\icon.png",
    )
    wxs, payload_paths = generate_wxs(build, [resource])
    assert wxs.count('Name="icon.png"') == 1
    assert wxs.count('Name="Resources"') == 1
    assert any(p.endswith("icon.png") for p in payload_paths)


def test_permachine_build_declares_a_program_files_directory(build):
    resource = PluginResourceFile(
        build=build, storage_key="x/dep.dll", original_filename="dep.dll",
        destination_path=r"{INSTALL_DIR}\dep.dll",
    )
    wxs, _ = generate_wxs(build, [resource])
    assert 'Scope="perMachine"' in wxs
    assert 'Id="ProgramFilesFolder"' in wxs
