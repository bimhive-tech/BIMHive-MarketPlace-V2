"""Applies the R2 bucket CORS rule that direct browser uploads depend on.

Product media is PUT straight from the browser to a presigned R2 URL (see
AdminProductMediaUploadUrlView). Without a CORS rule on the bucket, R2 rejects
the browser's preflight with "CORS not configured for this bucket" and every
image/video upload fails. Running this on every boot (scripts/start.sh) keeps
the rule in place instead of relying on a one-off dashboard step that can be
missed or wiped. Origins come from TRUSTED_ORIGINS, the same list CSRF uses.
"""
from django.conf import settings
from django.core.files.storage import storages
from django.core.management.base import BaseCommand

CORS_MAX_AGE_SECONDS = 3600


def build_cors_rules(origins):
    return [
        {
            "AllowedOrigins": list(origins),
            "AllowedMethods": ["PUT", "GET", "HEAD"],
            "AllowedHeaders": ["Content-Type"],
            "ExposeHeaders": ["ETag"],
            "MaxAgeSeconds": CORS_MAX_AGE_SECONDS,
        }
    ]


class Command(BaseCommand):
    help = "Set the R2 bucket CORS policy so browsers can upload to presigned URLs."

    def handle(self, *args, **options):
        if not (settings.R2_ACCESS_KEY_ID and settings.R2_SECRET_ACCESS_KEY and settings.R2_BUCKET_NAME):
            self.stdout.write("R2 not configured; skipping CORS setup.")
            return

        origins = settings.CSRF_TRUSTED_ORIGINS
        client = storages["public_media"].connection.meta.client
        client.put_bucket_cors(
            Bucket=settings.R2_BUCKET_NAME,
            CORSConfiguration={"CORSRules": build_cors_rules(origins)},
        )
        self.stdout.write(f"R2 CORS set for: {', '.join(origins)}")
