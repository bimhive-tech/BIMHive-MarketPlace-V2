"""
Staff-only admin API for the Licenses section — look up / extend / revoke / re-issue
a license and see its fingerprint + trial state. This was only possible by hand-editing
the DB in v1 (see REBUILD_PROMPT admin requirements); here it's a real, first-class
admin surface backed by the same models the activation API writes to.
"""
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from rest_framework import generics, serializers
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from activity.models import ActivityVerb
from activity.services import log_activity
from licensing.models import LicensedProduct, MachineLicense, ProductPurchase
from licensing.services import restore_purchase_access, revoke_purchase_access


# ─────────────────────────────────────────────────────────────
# Licenses (machine activations)
# ─────────────────────────────────────────────────────────────
class AdminMachineLicenseSerializer(serializers.ModelSerializer):
    product_code = serializers.CharField(source="product.code", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True, default="")
    license_key = serializers.CharField(source="purchase.license_key", read_only=True, default="")
    fingerprint_preview = serializers.SerializerMethodField()

    class Meta:
        model = MachineLicense
        fields = [
            "id", "product_code", "product_name", "user_email", "license_key",
            "fingerprint_preview", "fingerprint_version", "status", "started_at",
            "expires_at", "first_seen_at", "last_seen_at", "install_count", "plugin_version",
        ]

    def get_fingerprint_preview(self, obj):
        h = obj.machine_fingerprint_hash or ""
        return f"{h[:12]}…" if h else ""


class AdminLicenseListView(generics.ListAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = AdminMachineLicenseSerializer

    def get_queryset(self):
        qs = MachineLicense.objects.select_related("product", "user", "purchase").order_by("-last_seen_at")
        params = self.request.query_params
        if search := params.get("search"):
            qs = qs.filter(
                Q(product__code__icontains=search)
                | Q(product__name__icontains=search)
                | Q(user__email__icontains=search)
                | Q(purchase__license_key__icontains=search)
            )
        if status := params.get("status"):
            if status != "all":
                qs = qs.filter(status=status)
        return qs


class AdminLicenseRevokeView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        license_obj = MachineLicense.objects.select_related("purchase").get(pk=pk)
        now = timezone.now()
        if license_obj.purchase_id:
            revoke_purchase_access(license_obj.purchase, reason="admin_revoke", event_time=now)
        else:
            license_obj.status = "blocked"
            license_obj.last_seen_at = now
            license_obj.save(update_fields=["status", "last_seen_at"])
        license_obj.refresh_from_db()
        log_activity(request.user, ActivityVerb.LICENSE_REVOKED, target_label=license_obj.product.name)
        return Response(AdminMachineLicenseSerializer(license_obj).data)


class AdminLicenseRestoreView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        license_obj = MachineLicense.objects.select_related("purchase").get(pk=pk)
        now = timezone.now()
        if license_obj.purchase_id:
            restore_purchase_access(license_obj.purchase, event_time=now)
        else:
            license_obj.status = "active"
            license_obj.last_seen_at = now
            license_obj.save(update_fields=["status", "last_seen_at"])
        license_obj.refresh_from_db()
        log_activity(request.user, ActivityVerb.LICENSE_RESTORED, target_label=license_obj.product.name)
        return Response(AdminMachineLicenseSerializer(license_obj).data)


class AdminLicenseExtendView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        days = request.data.get("days")
        try:
            days = int(days)
        except (TypeError, ValueError):
            raise ValidationError({"days": "A whole number of days is required."})
        if days <= 0:
            raise ValidationError({"days": "Must be a positive number of days."})
        license_obj = MachineLicense.objects.get(pk=pk)
        license_obj.expires_at = license_obj.expires_at + timedelta(days=days)
        license_obj.last_seen_at = timezone.now()
        license_obj.save(update_fields=["expires_at", "last_seen_at"])
        log_activity(
            request.user,
            ActivityVerb.LICENSE_EXTENDED,
            target_label=license_obj.product.name,
            metadata={"days": days},
        )
        return Response(AdminMachineLicenseSerializer(license_obj).data)


# ─────────────────────────────────────────────────────────────
# Orders (product purchases)
# ─────────────────────────────────────────────────────────────
class AdminOrderSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_code = serializers.CharField(source="product.code", read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True)

    class Meta:
        model = ProductPurchase
        fields = [
            "id", "product_name", "product_code", "user_email", "license_key", "amount",
            "currency", "payment_status", "company_name", "contact_email", "requested_at",
            "paid_at",
        ]


class AdminOrderListView(generics.ListAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = AdminOrderSerializer

    def get_queryset(self):
        qs = ProductPurchase.objects.select_related("product", "user").order_by("-requested_at")
        status = self.request.query_params.get("status")
        if status and status != "all":
            qs = qs.filter(payment_status=status)
        return qs


class AdminOrderStatusView(APIView):
    """Move a purchase between payment states, granting/revoking activation as needed."""

    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        purchase = ProductPurchase.objects.select_related("product", "user").get(pk=pk)
        action = request.data.get("action")
        if action == "restore":
            restore_purchase_access(purchase)
        elif action == "revoke":
            revoke_purchase_access(purchase, status=ProductPurchase.PaymentStatus.REVOKED)
        elif action == "refund":
            revoke_purchase_access(purchase, status=ProductPurchase.PaymentStatus.REFUNDED)
        else:
            raise ValidationError({"action": "Must be one of: restore, revoke, refund."})
        purchase.refresh_from_db()
        log_activity(
            request.user,
            ActivityVerb.ORDER_STATUS_CHANGED,
            target_label=purchase.product.name,
            metadata={"action": action, "new_status": purchase.payment_status},
        )
        return Response(AdminOrderSerializer(purchase).data)


class AdminLicenseOptionsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        return Response(
            {
                "products": list(
                    LicensedProduct.objects.values("id", "code", "name", "is_active")
                ),
            }
        )
