"""Self-service API for partner-linked users (the partner portal), distinct from
the staff-only admin API in admin_api.py — product CRUD is shared with staff via
admin_api.py's IsStaffOrPartner-gated views, but a partner's own profile has no
staff equivalent, so it lives here instead."""
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import Partner
from catalog.permissions import IsPartnerUser


class PartnerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Partner
        fields = ["id", "name", "slug", "tagline", "bio", "logo_url", "website", "is_verified"]
        # Name/slug affect URLs and public listings elsewhere — admin-only via the
        # existing AdminPartnerViewSet. is_verified is BIMHive's call, not the
        # partner's own.
        read_only_fields = ["id", "name", "slug", "is_verified"]


class PartnerProfileView(APIView):
    """GET/PATCH the caller's own Partner record (tagline/bio/logo/website only)."""

    permission_classes = [IsPartnerUser]

    def get(self, request):
        return Response(PartnerProfileSerializer(request.user.partner).data)

    def patch(self, request):
        serializer = PartnerProfileSerializer(request.user.partner, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
