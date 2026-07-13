"""
Read-only system configuration status for the admin Settings > General page.
Reports whether each integration is actually configured (via env), never the
secret values themselves — this is real, live status, not an editable form
backed by nothing (see CLAUDE.md: no placeholders).
"""
from django.conf import settings
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView


class AdminSystemStatusView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        return Response(
            {
                "debug_mode": settings.DEBUG,
                "database": "PostgreSQL",
                "licensing": {
                    "pepper_configured": bool(settings.LICENSE_PEPPER),
                },
                "storage": {
                    "bucket": settings.R2_BUCKET_NAME or "(not set)",
                    "configured": bool(settings.R2_BUCKET_NAME and settings.R2_ACCESS_KEY_ID),
                },
                "payments": {
                    "stripe_configured": bool(settings.STRIPE_SECRET_KEY)
                    and not settings.STRIPE_SECRET_KEY.endswith("_xxx"),
                    "paypal_configured": bool(getattr(settings, "PAYPAL_CLIENT_ID", "")),
                },
            }
        )
