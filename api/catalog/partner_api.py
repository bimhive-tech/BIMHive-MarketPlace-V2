"""Self-service API for partner-linked users (the partner portal), distinct from
the staff-only admin API in admin_api.py — product CRUD is shared with staff via
admin_api.py's IsStaffOrPartner-gated views, but a partner's own profile/
application/sales have no staff equivalent, so they live here instead."""
from django.db.models import Sum
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import Partner
from catalog.permissions import IsApprovedPartner, IsPartnerUser
from licensing.models import ProductPurchase


class PartnerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Partner
        fields = [
            "id", "name", "slug", "tagline", "bio", "logo_url", "website", "is_verified",
            "status", "rejection_note",
        ]
        # Name/slug affect URLs and public listings elsewhere — admin-only via the
        # existing AdminPartnerViewSet. is_verified is BIMHive's call, not the
        # partner's own. status/rejection_note are staff-set outcomes of the
        # application review, read-only here for the same reason.
        read_only_fields = ["id", "name", "slug", "is_verified", "status", "rejection_note"]


class PartnerProfileView(APIView):
    """GET/PATCH the caller's own Partner record (tagline/bio/logo/website only) —
    reachable regardless of application status, so a pending/rejected applicant
    can still see why and fix their info."""

    permission_classes = [IsPartnerUser]

    def get(self, request):
        return Response(PartnerProfileSerializer(request.user.partner).data)

    def patch(self, request):
        serializer = PartnerProfileSerializer(request.user.partner, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class BecomeSellerView(APIView):
    """The "Become a Seller" application — a plain authenticated customer (not
    yet partner-linked) submits a company name + optional logo, creating a
    Partner record in "pending" status. BIMHive staff approve or reject it via
    the existing AdminPartnerViewSet (same PATCH mechanism already used for
    reviewing products) — this view only ever creates a pending application,
    never grants access itself."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        if request.user.partner_id is not None:
            raise ValidationError({"detail": "You've already applied to become a seller."})

        company_name = (request.data.get("company_name") or "").strip()
        if not company_name:
            raise ValidationError({"company_name": "A company name is required."})
        if Partner.objects.filter(name__iexact=company_name).exists():
            raise ValidationError({"company_name": "A partner with this name already exists."})

        logo_url = ""
        uploaded = request.FILES.get("logo")
        if uploaded:
            from django.conf import settings
            from django.core.files.storage import storages

            if not (settings.R2_ACCESS_KEY_ID and settings.R2_SECRET_ACCESS_KEY and settings.R2_BUCKET_NAME):
                raise ValidationError(
                    {"detail": "Logo uploads need Cloudflare R2 storage configured on the server first."}
                )
            content_type = uploaded.content_type or ""
            if not content_type.startswith("image/"):
                raise ValidationError({"logo": "Only image files are supported."})
            public_storage = storages["public_media"]
            key = public_storage.save(f"partner_logos/{request.user.id}/{uploaded.name}", uploaded)
            logo_url = public_storage.url(key)

        partner = Partner.objects.create(name=company_name, logo_url=logo_url)
        request.user.partner = partner
        request.user.save(update_fields=["partner"])

        return Response(PartnerProfileSerializer(partner).data, status=201)


class PartnerSaleSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = ProductPurchase
        # No customer PII (user_email/company_name/contact_email) — BIMHive is
        # merchant of record, this isn't the partner's data to see.
        fields = ["id", "product_name", "amount", "currency", "payment_status", "requested_at", "paid_at"]


class PartnerSalesView(APIView):
    """The partner's own order/revenue history — scoped to purchases of their
    own products only. ProductPurchase -> LicensedProduct -> catalog.Product
    -> Partner is the FK chain (LicensedProduct.product is nullable, hence the
    isnull=False exclusion)."""

    permission_classes = [IsApprovedPartner]

    def get(self, request):
        purchases = (
            ProductPurchase.objects.filter(
                product__product__partner=request.user.partner, product__product__isnull=False
            )
            .select_related("product")
            .order_by("-requested_at")
        )
        paid = purchases.filter(payment_status=ProductPurchase.PaymentStatus.PAID)
        total_revenue = paid.aggregate(total=Sum("amount"))["total"] or 0
        return Response(
            {
                "total_revenue": str(total_revenue),
                "order_count": purchases.count(),
                "orders": PartnerSaleSerializer(purchases[:50], many=True).data,
            }
        )
