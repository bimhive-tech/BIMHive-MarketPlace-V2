"""
Read-only system configuration status for the admin Settings > General page.
Reports whether each integration is actually configured (via env), never the
secret values themselves — this is real, live status, not an editable form
backed by nothing (see CLAUDE.md: no placeholders).
"""
from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsSuperAdmin


class AdminSystemStatusView(APIView):
    # Settings (General/Payments) is hard Admin-only, like Users/Roles — never
    # a grantable Staff permission (see accounts.permissions).
    permission_classes = [IsSuperAdmin]

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
