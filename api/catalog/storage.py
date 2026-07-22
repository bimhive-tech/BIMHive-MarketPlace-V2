"""
Shared helper for the "public_media" storage alias (product gallery images/
video, partner logos — see STORAGES in config/settings.py). These render in
plain <img>/<video> tags across the storefront and need to stay loadable
indefinitely, but without R2_PUBLIC_BASE_URL configured, the URL an upload
endpoint hands back is a presigned link that hard-expires after 7 days (R2's
own SigV4 ceiling) — and that string was being saved straight into the DB
and served back unchanged forever after, so every product's media quietly
went dead a week after upload.

refresh_storage_url() re-derives a live URL from the *object key* embedded
in whatever's stored, on every read, instead of trusting the stored value.
A presigned URL's signature only lives in its query string — the path
segment holding the real key stays intact and parseable even once that
signature has expired, so this recovers already-broken links with no
backfill needed, and prevents it from ever recurring (once
R2_PUBLIC_BASE_URL is set, this transparently returns a real permanent URL
instead, and becomes a no-op).
"""
from urllib.parse import unquote

from django.conf import settings


def refresh_storage_url(value: str) -> str:
    if not value or not settings.R2_BUCKET_NAME:
        return value
    marker = f"/{settings.R2_BUCKET_NAME}/"
    if marker not in value:
        return value
    key = unquote(value.split(marker, 1)[1].split("?", 1)[0])
    if not key:
        return value
    from django.core.files.storage import storages

    return storages["public_media"].url(key)
