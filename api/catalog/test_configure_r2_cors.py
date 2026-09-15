"""configure_r2_cors — without a bucket CORS rule, every browser upload to a
presigned R2 URL is blocked at the preflight."""
from unittest.mock import MagicMock

from django.core.management import call_command

from catalog.management.commands import configure_r2_cors


def _configure_r2(settings):
    settings.R2_ACCESS_KEY_ID = "key"
    settings.R2_SECRET_ACCESS_KEY = "secret"
    settings.R2_BUCKET_NAME = "bucket"
    settings.CSRF_TRUSTED_ORIGINS = ["https://hub.example.com"]


def test_puts_cors_rule_for_trusted_origins(settings, monkeypatch):
    _configure_r2(settings)
    storage = MagicMock()
    monkeypatch.setattr(configure_r2_cors, "storages", {"public_media": storage})

    call_command("configure_r2_cors")

    client = storage.connection.meta.client
    client.put_bucket_cors.assert_called_once()
    kwargs = client.put_bucket_cors.call_args.kwargs
    assert kwargs["Bucket"] == "bucket"
    rule = kwargs["CORSConfiguration"]["CORSRules"][0]
    assert rule["AllowedOrigins"] == ["https://hub.example.com"]
    assert "PUT" in rule["AllowedMethods"]
    assert rule["AllowedHeaders"] == ["Content-Type"]


def test_skips_when_r2_not_configured(settings, monkeypatch):
    settings.R2_BUCKET_NAME = ""
    storage = MagicMock()
    monkeypatch.setattr(configure_r2_cors, "storages", {"public_media": storage})

    call_command("configure_r2_cors")

    storage.connection.meta.client.put_bucket_cors.assert_not_called()
