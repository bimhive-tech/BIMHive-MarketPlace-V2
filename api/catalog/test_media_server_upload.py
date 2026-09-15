"""AdminProductMediaUploadView — the no-CORS fallback where the file goes
through Django to storage instead of straight from the browser to R2."""
import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from catalog.admin_api import AdminProductMediaUploadUrlView
from catalog.models import Category, Partner, Product

pytestmark = pytest.mark.django_db
User = get_user_model()


@pytest.fixture
def category():
    return Category.objects.create(name="Revit Plugins")


@pytest.fixture
def partner():
    return Partner.objects.create(name="BIMHIVE", status=Partner.ApplicationStatus.APPROVED)


@pytest.fixture
def staff_client(client):
    user = User.objects.create_user(
        username="admin@x.com", email="admin@x.com", password="x", is_staff=True, is_superuser=True,
    )
    client.force_login(user)
    return client


def _use_local_public_media(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    settings.STORAGES = {
        **settings.STORAGES,
        "public_media": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    }


def _product(category, partner):
    return Product.objects.create(name="P", short_description="s", description="d", category=category, partner=partner)


def test_server_upload_stores_image(staff_client, category, partner, settings, tmp_path):
    _use_local_public_media(settings, tmp_path)
    product = _product(category, partner)
    upload = SimpleUploadedFile("cover.png", b"png-bytes", content_type="image/png")
    resp = staff_client.post(f"/api/admin/products/{product.id}/media-upload", {"file": upload})
    assert resp.status_code == 201, resp.json()
    body = resp.json()
    assert body["media_type"] == "image"
    assert f"product_media/{product.id}/cover" in body["url"]


def test_server_upload_rejects_other_file_types(staff_client, category, partner, settings, tmp_path):
    _use_local_public_media(settings, tmp_path)
    product = _product(category, partner)
    upload = SimpleUploadedFile("setup.exe", b"x", content_type="application/octet-stream")
    resp = staff_client.post(f"/api/admin/products/{product.id}/media-upload", {"file": upload})
    assert resp.status_code == 400


def test_server_upload_rejects_oversized_image(staff_client, category, partner, settings, tmp_path, monkeypatch):
    _use_local_public_media(settings, tmp_path)
    monkeypatch.setattr(AdminProductMediaUploadUrlView, "MAX_IMAGE_BYTES", 3)
    product = _product(category, partner)
    upload = SimpleUploadedFile("cover.png", b"too-big", content_type="image/png")
    resp = staff_client.post(f"/api/admin/products/{product.id}/media-upload", {"file": upload})
    assert resp.status_code == 400
    assert "MB" in resp.json()["file"]


def test_server_upload_requires_staff(client, category, partner):
    product = _product(category, partner)
    upload = SimpleUploadedFile("cover.png", b"png", content_type="image/png")
    resp = client.post(f"/api/admin/products/{product.id}/media-upload", {"file": upload})
    assert resp.status_code in (401, 403)
