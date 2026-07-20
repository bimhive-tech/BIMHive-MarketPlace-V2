"""
HTTP-layer concerns for the plugin-build API: ownership scoping (mirrors
catalog.admin_api._effective_partner_id, reused rather than re-derived),
upload validation, and the destination-path guard rejecting unsafe paths
at the API boundary too (not just in the model's .clean()). NSIS build
mechanics themselves are covered in test_builder.py.
"""
import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from catalog.models import Category, Partner, Product
from catalog.models.product import ProductType
from installer.models import PluginBuild, PluginResourceFile

pytestmark = pytest.mark.django_db
User = get_user_model()


@pytest.fixture
def category():
    return Category.objects.create(name="Revit Plugins")


@pytest.fixture
def partner_a():
    return Partner.objects.create(name="Partner A", status=Partner.ApplicationStatus.APPROVED)


@pytest.fixture
def partner_b():
    return Partner.objects.create(name="Partner B", status=Partner.ApplicationStatus.APPROVED)


@pytest.fixture
def product_a(category, partner_a):
    return Product.objects.create(
        name="A's Plugin", product_code="a-plugin", category=category, partner=partner_a,
        short_description="s", description="d",
    )


@pytest.fixture
def product_b(category, partner_b):
    return Product.objects.create(
        name="B's Plugin", product_code="b-plugin", category=category, partner=partner_b,
        short_description="s", description="d",
    )


@pytest.fixture
def script_product(category, partner_a):
    return Product.objects.create(
        name="A's Script", product_code="a-script", category=category, partner=partner_a,
        type=ProductType.SCRIPT, short_description="s", description="d",
    )


@pytest.fixture
def partner_a_client(client, partner_a):
    user = User.objects.create_user(username="a@x.com", email="a@x.com", password="x", partner=partner_a)
    client.force_login(user)
    return client


@pytest.fixture
def staff_client(client):
    user = User.objects.create_user(username="staff@x.com", email="staff@x.com", password="x", is_staff=True)
    client.force_login(user)
    return client


# ── Ownership scoping ──
def test_partner_can_create_a_build_for_their_own_product(partner_a_client, product_a):
    resp = partner_a_client.post(f"/api/admin/products/{product_a.id}/plugin-builds", {"revit_year": "2025"})
    assert resp.status_code == 201, resp.json()
    assert resp.json()["revit_year"] == "2025"


def test_partner_cannot_create_a_build_for_another_partners_product(partner_a_client, product_b):
    resp = partner_a_client.post(f"/api/admin/products/{product_b.id}/plugin-builds", {"revit_year": "2025"})
    assert resp.status_code == 404


def test_partner_cannot_list_another_partners_builds(partner_a_client, product_b):
    PluginBuild.objects.create(product=product_b, revit_year="2025")
    resp = partner_a_client.get(f"/api/admin/products/{product_b.id}/plugin-builds")
    assert resp.status_code == 404


def test_staff_can_create_builds_for_any_product(staff_client, product_a, product_b):
    resp_a = staff_client.post(f"/api/admin/products/{product_a.id}/plugin-builds", {"revit_year": "2025"})
    resp_b = staff_client.post(f"/api/admin/products/{product_b.id}/plugin-builds", {"revit_year": "2025"})
    assert resp_a.status_code == 201
    assert resp_b.status_code == 201


def test_cannot_create_a_duplicate_revit_year_for_the_same_product(partner_a_client, product_a):
    PluginBuild.objects.create(product=product_a, revit_year="2025")
    resp = partner_a_client.post(f"/api/admin/products/{product_a.id}/plugin-builds", {"revit_year": "2025"})
    assert resp.status_code == 400


def test_anonymous_cannot_reach_the_plugin_build_api(client, product_a):
    resp = client.get(f"/api/admin/products/{product_a.id}/plugin-builds")
    assert resp.status_code in (401, 403)


def test_cannot_create_a_build_for_a_non_plugin_product(partner_a_client, script_product):
    resp = partner_a_client.post(f"/api/admin/products/{script_product.id}/plugin-builds", {"revit_year": "2025"})
    assert resp.status_code == 400
    assert "product" in resp.json()


# ── Uploads ──
def test_uploading_a_dll_updates_the_build(partner_a_client, product_a):
    build = PluginBuild.objects.create(product=product_a, revit_year="2025")
    upload = SimpleUploadedFile("Plugin.dll", b"fake dll bytes", content_type="application/octet-stream")
    resp = partner_a_client.post(f"/api/admin/plugin-builds/{build.id}/dll", {"file": upload})
    assert resp.status_code == 200, resp.json()
    assert resp.json()["dll_filename"] == "Plugin.dll"


def test_uploading_a_non_dll_file_as_the_dll_is_rejected(partner_a_client, product_a):
    build = PluginBuild.objects.create(product=product_a, revit_year="2025")
    upload = SimpleUploadedFile("Plugin.exe", b"not a dll", content_type="application/octet-stream")
    resp = partner_a_client.post(f"/api/admin/plugin-builds/{build.id}/dll", {"file": upload})
    assert resp.status_code == 400


def test_uploading_a_resource_with_a_valid_destination_succeeds(partner_a_client, product_a):
    build = PluginBuild.objects.create(product=product_a, revit_year="2025")
    upload = SimpleUploadedFile("config.json", b"{}", content_type="application/json")
    resp = partner_a_client.post(
        f"/api/admin/plugin-builds/{build.id}/resources",
        {"file": upload, "destination_path": r"{ADDIN_DIR}\extra\config.json", "kind": "resource"},
    )
    assert resp.status_code == 201, resp.json()
    assert PluginResourceFile.objects.filter(build=build).count() == 1


def test_uploading_a_resource_with_a_path_traversal_destination_is_rejected(partner_a_client, product_a):
    build = PluginBuild.objects.create(product=product_a, revit_year="2025")
    upload = SimpleUploadedFile("evil.dll", b"x", content_type="application/octet-stream")
    resp = partner_a_client.post(
        f"/api/admin/plugin-builds/{build.id}/resources",
        {"file": upload, "destination_path": r"{ADDIN_DIR}\..\..\evil.dll", "kind": "resource"},
    )
    assert resp.status_code == 400
    assert PluginResourceFile.objects.filter(build=build).count() == 0


def test_deleting_a_resource_is_scoped_to_its_owner(partner_a_client, staff_client, product_a):
    build = PluginBuild.objects.create(product=product_a, revit_year="2025")
    resource = PluginResourceFile.objects.create(
        build=build, storage_key="x/y.json", original_filename="y.json",
        destination_path=r"{ADDIN_DIR}\y.json",
    )
    resp = staff_client.delete(f"/api/admin/plugin-builds/{build.id}/resources/{resource.id}")
    assert resp.status_code == 204
    assert not PluginResourceFile.objects.filter(pk=resource.id).exists()


def test_destination_options_lists_both_tokens(partner_a_client):
    resp = partner_a_client.get("/api/admin/plugin-builds/destination-options")
    assert resp.status_code == 200
    tokens = {row["token"] for row in resp.json()}
    assert tokens == {"{ADDIN_DIR}", "{INSTALL_DIR}"}


# ── Direct download (staff/partner testing a build, no purchase needed) ──
# Real NSIS invocation, same philosophy as test_builder.py — no mocking.
def test_owner_downloading_generates_and_streams_a_fresh_exe(partner_a_client, product_a):
    from django.core.files.base import ContentFile
    from django.core.files.storage import default_storage

    build = PluginBuild.objects.create(product=product_a, revit_year="2025")
    build.dll_storage_key = default_storage.save(f"test/{product_a.id}/Plugin.dll", ContentFile(b"fake dll"))
    build.dll_filename = "Plugin.dll"
    build.addin_storage_key = default_storage.save(f"test/{product_a.id}/Plugin.addin", ContentFile(b"<RevitAddIns/>"))
    build.addin_filename = "Plugin.addin"
    build.save()

    resp = partner_a_client.get(f"/api/admin/plugin-builds/{build.id}/download")
    assert resp.status_code == 200
    assert resp["Content-Type"] == "application/vnd.microsoft.portable-executable"
    assert resp.content.startswith(b"MZ")


def test_cannot_download_a_build_missing_dll_or_addin(partner_a_client, product_a):
    build = PluginBuild.objects.create(product=product_a, revit_year="2025")
    resp = partner_a_client.get(f"/api/admin/plugin-builds/{build.id}/download")
    assert resp.status_code == 400


def test_another_partners_build_is_not_downloadable(partner_a_client, product_b):
    build = PluginBuild.objects.create(product=product_b, revit_year="2025")
    resp = partner_a_client.get(f"/api/admin/plugin-builds/{build.id}/download")
    assert resp.status_code == 404
