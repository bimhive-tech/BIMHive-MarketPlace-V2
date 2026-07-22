"""
catalog/storage.py::refresh_storage_url — the fix for product media/cover/
partner-logo images going permanently broken 7 days after upload. Without
R2_PUBLIC_BASE_URL configured, an uploaded file's URL is a presigned link
capped at 604800 seconds (R2's own SigV4 ceiling, see STORAGES in
config/settings.py) — that string used to get saved straight into the DB
and served back unchanged forever, so every product's gallery went dead a
week after upload, regardless of anything else. This re-derives a fresh
URL from the object key on every read instead.
"""
import pytest
from django.core.files.storage import storages

from catalog.storage import refresh_storage_url

BUCKET = "test-bucket"
EXPIRED_QUERY = "?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Expires=604800&X-Amz-Signature=deadbeef"


@pytest.fixture(autouse=True)
def _r2_settings(settings):
    settings.R2_BUCKET_NAME = BUCKET
    settings.STORAGES = {
        **settings.STORAGES,
        "public_media": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    }


def test_refreshes_a_url_from_its_still_valid_object_key(settings, monkeypatch):
    stored = f"https://acct.r2.cloudflarestorage.com/{BUCKET}/product_media/14/cover.png{EXPIRED_QUERY}"
    fresh = refresh_storage_url(stored)
    # FileSystemStorage.url() just prepends MEDIA_URL to the key — proves the
    # object key (product_media/14/cover.png) was correctly extracted from
    # the stored value, independent of whatever's in the old query string.
    assert fresh == storages["public_media"].url("product_media/14/cover.png")
    assert "X-Amz-Expires" not in fresh


def test_recovers_a_url_whose_signature_has_already_expired():
    # The whole point: an *expired* presigned URL's path segment (the real
    # object key) is still intact and parseable even though its signature
    # query string is now worthless — expiry only invalidates the query
    # string, never the path.
    stored = f"https://acct.r2.cloudflarestorage.com/{BUCKET}/product_media/9/shot.png{EXPIRED_QUERY}"
    assert refresh_storage_url(stored) == storages["public_media"].url("product_media/9/shot.png")


def test_url_encoded_characters_in_the_key_are_decoded():
    stored = f"https://acct.r2.cloudflarestorage.com/{BUCKET}/product_media/1/My%20File.png{EXPIRED_QUERY}"
    assert refresh_storage_url(stored) == storages["public_media"].url("product_media/1/My File.png")


def test_empty_value_passes_through_unchanged():
    assert refresh_storage_url("") == ""


def test_url_not_matching_the_bucket_passes_through_unchanged():
    # A genuinely external URL (or one from a differently-configured bucket)
    # is left alone rather than mangled.
    external = "https://example.com/some/other/image.png"
    assert refresh_storage_url(external) == external


def test_noop_when_r2_bucket_name_isnt_configured(settings):
    settings.R2_BUCKET_NAME = ""
    stored = f"https://acct.r2.cloudflarestorage.com/{BUCKET}/product_media/14/cover.png{EXPIRED_QUERY}"
    assert refresh_storage_url(stored) == stored
