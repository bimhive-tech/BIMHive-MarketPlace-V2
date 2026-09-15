"""AdminProductMediaUploadView — the no-CORS fallback where the file goes
through Django to storage instead of straight from the browser to R2."""
from unittest.mock import MagicMock

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from catalog import admin_api
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
    settings.R2_ACCESS_KEY_ID = "key"
    settings.R2_SECRET_ACCESS_KEY = "secret"
    settings.R2_BUCKET_NAME = "bucket"
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


@pytest.fixture
def r2_client(monkeypatch):
    fake = MagicMock()
    fake.create_multipart_upload.return_value = {"UploadId": "up-1"}
    fake.upload_part.return_value = {"ETag": '"etag-1"'}
    monkeypatch.setattr(admin_api, "_public_media_client", lambda: fake)
    return fake


def _multipart_url(product, action):
    return f"/api/admin/products/{product.id}/media-upload/{action}"


def test_multipart_start_opens_an_r2_upload(staff_client, category, partner, settings, tmp_path, r2_client):
    _use_local_public_media(settings, tmp_path)
    product = _product(category, partner)
    resp = staff_client.post(
        _multipart_url(product, "start"),
        {"filename": "teaser.mp4", "content_type": "video/mp4", "size": 50_000_000},
        content_type="application/json",
    )
    assert resp.status_code == 201, resp.json()
    body = resp.json()
    assert body["upload_id"] == "up-1"
    assert body["media_type"] == "video"
    assert body["key"].startswith(f"product_media/{product.id}/")
    assert body["part_size"] == admin_api.MEDIA_UPLOAD_PART_BYTES


def test_multipart_part_forwards_chunk_to_r2(staff_client, category, partner, settings, tmp_path, r2_client):
    _use_local_public_media(settings, tmp_path)
    product = _product(category, partner)
    chunk = SimpleUploadedFile("teaser.mp4", b"video-bytes", content_type="application/octet-stream")
    resp = staff_client.post(
        _multipart_url(product, "part"),
        {"upload_id": "up-1", "key": f"product_media/{product.id}/teaser.mp4", "part_number": "1", "chunk": chunk},
    )
    assert resp.status_code == 200, resp.json()
    assert resp.json()["etag"] == '"etag-1"'
    kwargs = r2_client.upload_part.call_args.kwargs
    assert kwargs["PartNumber"] == 1
    assert kwargs["Body"] == b"video-bytes"


def test_multipart_rejects_a_key_from_another_product(staff_client, category, partner, settings, tmp_path, r2_client):
    _use_local_public_media(settings, tmp_path)
    product = _product(category, partner)
    chunk = SimpleUploadedFile("teaser.mp4", b"x", content_type="application/octet-stream")
    resp = staff_client.post(
        _multipart_url(product, "part"),
        {"upload_id": "up-1", "key": "product_media/999/teaser.mp4", "part_number": "1", "chunk": chunk},
    )
    assert resp.status_code == 400
    r2_client.upload_part.assert_not_called()


def test_multipart_complete_assembles_parts(staff_client, category, partner, settings, tmp_path, r2_client):
    _use_local_public_media(settings, tmp_path)
    product = _product(category, partner)
    key = f"product_media/{product.id}/teaser.mp4"
    resp = staff_client.post(
        _multipart_url(product, "complete"),
        {"upload_id": "up-1", "key": key, "parts": [{"part_number": 1, "etag": '"etag-1"'}]},
        content_type="application/json",
    )
    assert resp.status_code == 201, resp.json()
    assert key in resp.json()["url"]
    kwargs = r2_client.complete_multipart_upload.call_args.kwargs
    assert kwargs["MultipartUpload"] == {"Parts": [{"PartNumber": 1, "ETag": '"etag-1"'}]}


def test_multipart_unknown_action_is_404(staff_client, category, partner):
    product = _product(category, partner)
    resp = staff_client.post(_multipart_url(product, "nope"), {}, content_type="application/json")
    assert resp.status_code == 404


def test_server_upload_requires_staff(client, category, partner):
    product = _product(category, partner)
    upload = SimpleUploadedFile("cover.png", b"png", content_type="image/png")
    resp = client.post(f"/api/admin/products/{product.id}/media-upload", {"file": upload})
    assert resp.status_code in (401, 403)
