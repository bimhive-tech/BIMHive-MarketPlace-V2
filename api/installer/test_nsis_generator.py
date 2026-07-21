"""
NSI script generation logic — string/structure assertions only, no NSIS CLI
invocation (see test_builder.py for the real end-to-end build). Verifies
the two things that matter across a version (stable upgrade key via a
persisted UUID, real Version) and the scope-selection behavior, same as the
WiX generator this replaced.
"""
import pytest

from catalog.models import Category, Product
from installer.models import PluginBuild, PluginResourceFile
from installer.nsis_generator import generate_nsis_script, resolve_scope

pytestmark = pytest.mark.django_db


@pytest.fixture
def category():
    return Category.objects.create(name="Revit Plugins")


@pytest.fixture
def build(category):
    product = Product.objects.create(
        name="Test Plugin", product_code="nsi-test", category=category,
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


def test_generated_script_uses_the_products_real_version_not_a_hardcoded_one(build):
    script, _ = generate_nsis_script(build, [])
    assert 'VIAddVersionKey "ProductVersion" "2.5.0"' in script
    assert 'VIAddVersionKey "ProductVersion" "1.0.0"' not in script


def test_generated_script_uninstall_key_matches_the_persisted_upgrade_code(build):
    script, _ = generate_nsis_script(build, [])
    assert str(build.upgrade_code) in script


def test_rebuilding_with_a_new_version_keeps_the_same_upgrade_code(build):
    first_script, _ = generate_nsis_script(build, [])
    build.plugin_version = "2.6.0"
    build.save()
    second_script, _ = generate_nsis_script(build, [])
    assert str(build.upgrade_code) in first_script
    assert str(build.upgrade_code) in second_script
    assert 'VIAddVersionKey "ProductVersion" "2.5.0"' in first_script
    assert 'VIAddVersionKey "ProductVersion" "2.6.0"' in second_script


def test_plugin_name_with_a_quote_cannot_break_out_of_the_nsis_string(build):
    build.product.name = 'Evil" WriteRegStr HKLM "Software\\Pwn" "x" "y'
    script, _ = generate_nsis_script(build, [])
    assert 'Name "Evil" WriteRegStr' not in script
    assert '$\\"' in script


def test_resource_under_addin_dir_appears_once_as_a_file_entry(build):
    resource = PluginResourceFile(
        build=build, storage_key="x/icon.png", original_filename="icon.png",
        destination_path=r"{ADDIN_DIR}\Resources\icon.png",
    )
    script, payload_paths = generate_nsis_script(build, [resource])
    assert script.count("/oname=icon.png") == 1
    # Once in Install (SetOutPath stages it) and once in Uninstall (RMDir
    # cleans up that subdirectory) — a real second mention, not a duplicate.
    assert script.count("Addins\\2025\\Resources") == 2
    assert any(p.endswith("icon.png") for p in payload_paths)


def test_resource_with_a_blank_subpath_keeps_its_own_original_filename(build):
    resource = PluginResourceFile(
        build=build, storage_key="x/readme.txt", original_filename="readme.txt",
        destination_path=r"{ADDIN_DIR}",
    )
    script, _ = generate_nsis_script(build, [resource])
    assert "/oname=readme.txt" in script


def test_permachine_build_declares_a_program_files_directory(build):
    resource = PluginResourceFile(
        build=build, storage_key="x/dep.dll", original_filename="dep.dll",
        destination_path=r"{INSTALL_DIR}\dep.dll",
    )
    script, _ = generate_nsis_script(build, [resource])
    assert "RequestExecutionLevel admin" in script
    assert "$PROGRAMFILES64" in script


def test_peruser_build_requests_user_execution_level(build):
    script, _ = generate_nsis_script(build, [])
    assert "RequestExecutionLevel user" in script
