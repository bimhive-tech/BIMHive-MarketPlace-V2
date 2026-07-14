"""
Django settings for BIM Hive Marketplace V2.

Environment-driven (see repo-root .env / .env.example). Security defaults are safe:
DEBUG is False unless explicitly enabled, and HSTS + secure cookies are enforced in code
when DEBUG is off so a stray env var can't weaken them in production.
"""
import sys
from pathlib import Path
from urllib.parse import urlparse

import dj_database_url
import environ

# BASE_DIR = /api ; REPO_ROOT = repo root (holds .env, /web, /infra)
BASE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BASE_DIR.parent

env = environ.Env()
environ.Env.read_env(REPO_ROOT / ".env")


def _clean_hosts(raw):
    """Drop blank entries. Host vars are commonly templated from a platform-
    provided domain (e.g. Railway's ${{RAILWAY_PUBLIC_DOMAIN}}) that may not be
    assigned yet on a service's first deploy, leaving an empty string in the list
    instead of a real host — better to drop it than let it silently match nothing
    (or, for origins below, hard-crash the whole app on every boot)."""
    return [h for h in raw if h.strip()]


def _clean_origins(raw):
    """Same idea as _clean_hosts, but for full origins (scheme://netloc) — Django
    hard-crashes via a SystemCheckError if any entry lacks a scheme or netloc, so
    an unresolved template variable here takes the whole app down on every boot
    until someone notices and fixes the env var. Drop what's invalid instead."""
    kept = []
    for origin in raw:
        parsed = urlparse(origin)
        if parsed.scheme and parsed.netloc:
            kept.append(origin)
        else:
            print(f"Ignoring invalid origin in env config: {origin!r}", file=sys.stderr)
    return kept


# ─────────────────────────────────────────────────────────────
# Core
# ─────────────────────────────────────────────────────────────
SECRET_KEY = env("DJANGO_SECRET_KEY", default="insecure-dev-key")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
# 127.0.0.1/localhost are always allowed regardless of DJANGO_ALLOWED_HOSTS: in
# this single-container topology (see scripts/start.sh), Next.js's server-side
# fetches always reach Django over that loopback address, no matter what public
# domain is (or isn't yet) configured — it's a fact of the container's internal
# wiring, not deployment config.
ALLOWED_HOSTS = list(
    {"localhost", "127.0.0.1", *_clean_hosts(env.list("DJANGO_ALLOWED_HOSTS", default=[]))}
)
CSRF_TRUSTED_ORIGINS = _clean_origins(
    env.list(
        "DJANGO_CSRF_TRUSTED_ORIGINS",
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
    )
)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "corsheaders",
    # Local
    "accounts",
    "catalog",
    "reviews",
    "licensing",
    "activity",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ─────────────────────────────────────────────────────────────
# Database
# ─────────────────────────────────────────────────────────────
DATABASES = {
    "default": dj_database_url.parse(
        env("DATABASE_URL", default="postgres://bimhive:bimhive@localhost:5432/bimhive"),
        conn_max_age=600,
    )
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ─────────────────────────────────────────────────────────────
# i18n / tz
# ─────────────────────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ─────────────────────────────────────────────────────────────
# Static / media
# ─────────────────────────────────────────────────────────────
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ─────────────────────────────────────────────────────────────
# DRF — same-origin session auth (see ARCHITECTURE §7)
# ─────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.ScopedRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {
        # Blunts credential stuffing / signup abuse on the auth endpoints.
        "auth": "10/min",
    },
}

# CORS — only needed in dev when Next.js (:3000) calls Django (:8000) directly.
CORS_ALLOWED_ORIGINS = _clean_origins(
    env.list(
        "DJANGO_CSRF_TRUSTED_ORIGINS",
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
    )
)
CORS_ALLOW_CREDENTIALS = True

# ─────────────────────────────────────────────────────────────
# Licensing (see licensing/ and ARCHITECTURE §5)
# ─────────────────────────────────────────────────────────────
LICENSE_PEPPER = env("LICENSE_PEPPER", default="")
LEGACY_LICENSE_DATABASE_URL = env("LEGACY_LICENSE_DATABASE_URL", default="")

# ─────────────────────────────────────────────────────────────
# Object storage (Cloudflare R2 / MinIO). Wired in a later task.
# ─────────────────────────────────────────────────────────────
R2_BUCKET_NAME = env("R2_BUCKET_NAME", default="")
R2_ACCESS_KEY_ID = env("R2_ACCESS_KEY_ID", default="")
R2_SECRET_ACCESS_KEY = env("R2_SECRET_ACCESS_KEY", default="")
R2_ENDPOINT_URL = env("R2_ENDPOINT_URL", default="")
R2_PUBLIC_BASE_URL = env("R2_PUBLIC_BASE_URL", default="")
R2_REGION = env("R2_REGION", default="auto")
R2_SIGNED_URL_TTL = env.int("R2_SIGNED_URL_TTL", default=300)

# Default file storage: R2 (prod) or the MinIO instance docker-compose starts for
# local dev — both are S3-compatible, so the same backend covers either one. Files
# only ever land on local disk if neither is configured at all. This matters beyond
# local dev convenience: Railway's filesystem is ephemeral, so ProductFile uploads
# (the actual plugin installers customers download) must live in object storage or
# they vanish on the next deploy.
if R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY and R2_BUCKET_NAME:
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
            "OPTIONS": {
                "bucket_name": R2_BUCKET_NAME,
                "region_name": R2_REGION,
                "endpoint_url": R2_ENDPOINT_URL,
                "access_key": R2_ACCESS_KEY_ID,
                "secret_key": R2_SECRET_ACCESS_KEY,
                "signature_version": "s3v4",
                "addressing_style": "path",
                "default_acl": None,
                "file_overwrite": False,
                # Every download link is presigned + short-lived; nothing is public
                # by default, since entitlement is checked in the account API, not
                # by hiding the bucket.
                "querystring_auth": True,
                "querystring_expire": R2_SIGNED_URL_TTL,
            },
        },
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }
else:
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }

# ─────────────────────────────────────────────────────────────
# Payments
# ─────────────────────────────────────────────────────────────
STRIPE_SECRET_KEY = env("STRIPE_SECRET_KEY", default="")
STRIPE_PUBLISHABLE_KEY = env("STRIPE_PUBLISHABLE_KEY", default="")
STRIPE_WEBHOOK_SECRET = env("STRIPE_WEBHOOK_SECRET", default="")

# ─────────────────────────────────────────────────────────────
# Cache — used by the license rate limiter (fail-open). Local-memory by default.
# ─────────────────────────────────────────────────────────────
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "bimhive-cache",
    }
}

# ─────────────────────────────────────────────────────────────
# Transport security — enforced in code when not in DEBUG so it can't be
# weakened by env. Local dev stays http-friendly.
# ─────────────────────────────────────────────────────────────
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

if not DEBUG:
    # No SECURE_SSL_REDIRECT here on purpose: gunicorn binds to 127.0.0.1 only
    # (see scripts/start.sh) and is never reachable from outside the container —
    # every request it sees is Next.js's internal loopback fetch, which is always
    # plain HTTP and never carries X-Forwarded-Proto. Redirecting those to https
    # would just break every server-side API call. TLS termination and enforcement
    # happen at Railway's edge and in Next.js, the only public-facing process.
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
