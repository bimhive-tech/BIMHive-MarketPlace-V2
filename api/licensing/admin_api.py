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
from licensing.models import LicenseCode, LicensedProduct, MachineLicense, ProductPurchase
from licensing.services import release_machine_binding, restore_purchase_access, revoke_purchase_access


# ─────────────────────────────────────────────────────────────
# Licenses (machine activations)
# ─────────────────────────────────────────────────────────────
class AdminMachineLicenseSerializer(serializers.ModelSerializer):
    product_code = serializers.CharField(source="product.code", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True, default="")
    license_key = serializers.CharField(source="purchase.license_key", read_only=True, default="")
    seats = serializers.IntegerField(source="purchase.seats", read_only=True, default=1)
    fingerprint_preview = serializers.SerializerMethodField()

    class Meta:
        model = MachineLicense
        fields = [
            "id", "product_code", "product_name", "user_email", "license_key", "seats",
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


class AdminLicenseReleaseView(APIView):
    """Staff-only equivalent of the old customer self-service reactivation:
    frees this one machine's seat so a different machine can claim it. Each
    seat is otherwise single-use forever (see ProductPurchase.has_seat_for)
    — this is the deliberate manual override for "customer's PC died,"
    an alternative to issuing them a brand-new license code from scratch."""

    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        license_obj = MachineLicense.objects.select_related("purchase", "product").get(pk=pk)
        if license_obj.status == "released":
            raise ValidationError({"detail": "This machine binding is already released."})
        release_machine_binding(license_obj)
        license_obj.refresh_from_db()
        log_activity(request.user, ActivityVerb.LICENSE_RELEASED, target_label=license_obj.product.name)
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
        license_obj = MachineLicense.objects.select_related("purchase").get(pk=pk)
        now = timezone.now()
        if license_obj.purchase_id and license_obj.purchase.expires_at:
            # A time-limited purchase (LicenseCode redemption) re-stamps every
            # machine's expires_at to purchase.expires_at on each activation
            # (see api_views.py) — extending the raw machine date alone would
            # get silently overwritten on the next activation call. Extend the
            # purchase-level date instead, which is what's actually enforced.
            purchase = license_obj.purchase
            purchase.expires_at = purchase.expires_at + timedelta(days=days)
            purchase.save(update_fields=["expires_at", "updated_at"])
            license_obj.expires_at = purchase.expires_at
        else:
            license_obj.expires_at = license_obj.expires_at + timedelta(days=days)
        license_obj.last_seen_at = now
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
            "id", "product_name", "product_code", "user_email", "license_key", "seats", "amount",
            "currency", "payment_status", "company_name", "contact_email", "requested_at",
            "paid_at",
        ]
        read_only_fields = ["seats"]  # set via AdminOrderSeatsView, not a plain field update


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


class AdminOrderSeatsView(APIView):
    """Set how many machines a purchase may have bound at once. There's no
    checkout flow yet (see AdminOrdersPage's empty-state copy), so this is
    currently the only way a "buy N licenses" purchase gets more than 1 seat."""

    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        seats = request.data.get("seats")
        try:
            seats = int(seats)
        except (TypeError, ValueError):
            raise ValidationError({"seats": "A whole number of seats is required."})
        if seats < 1:
            raise ValidationError({"seats": "Must be at least 1."})
        purchase = ProductPurchase.objects.select_related("product", "user").get(pk=pk)
        purchase.seats = seats
        purchase.save(update_fields=["seats", "updated_at"])
        log_activity(
            request.user,
            ActivityVerb.ORDER_SEATS_CHANGED,
            target_label=purchase.product.name,
            metadata={"seats": seats},
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


# ─────────────────────────────────────────────────────────────
# License codes — staff-generated, redeemable, single-product codes
# ─────────────────────────────────────────────────────────────
class AdminLicenseCodeSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_code = serializers.CharField(source="product.code", read_only=True)
    redeemed_by_email = serializers.CharField(source="redeemed_by.email", read_only=True, default="")

    class Meta:
        model = LicenseCode
        fields = [
            "id", "code", "product", "product_name", "product_code", "seats", "duration_days",
            "status", "note", "redeemed_by_email", "created_at", "redeemed_at",
        ]
        read_only_fields = ["id", "code", "status", "created_at", "redeemed_at"]


class AdminLicenseCodeListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = AdminLicenseCodeSerializer

    def get_queryset(self):
        qs = LicenseCode.objects.select_related("product", "redeemed_by").order_by("-created_at")
        if product_id := self.request.query_params.get("product"):
            qs = qs.filter(product_id=product_id)
        if status := self.request.query_params.get("status"):
            if status != "all":
                qs = qs.filter(status=status)
        return qs

    def perform_create(self, serializer):
        code = serializer.save(created_by=self.request.user)
        log_activity(
            self.request.user,
            ActivityVerb.LICENSE_CODE_CREATED,
            target_label=code.product.name,
            metadata={"seats": code.seats, "duration_days": code.duration_days},
        )


class AdminLicenseCodeRevokeView(APIView):
    """Invalidate an unredeemed code so it can no longer be used — does not
    touch anything already redeemed (revoke the resulting order instead)."""

    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        code = LicenseCode.objects.select_related("product").get(pk=pk)
        if code.status != LicenseCode.Status.UNREDEEMED:
            raise ValidationError({"detail": "Only an unredeemed code can be revoked."})
        code.status = LicenseCode.Status.REVOKED
        code.save(update_fields=["status"])
        log_activity(request.user, ActivityVerb.LICENSE_CODE_REVOKED, target_label=code.product.name)
        return Response(AdminLicenseCodeSerializer(code).data)
