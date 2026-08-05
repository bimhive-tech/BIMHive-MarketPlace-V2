"""
Staff-only membership administration (mounted under /api/admin/).

Two things staff need: to define the tiers and their prices, and to see or kill
an individual customer's membership. Revoking is the whole promise of the
universal key — one switch and every product it opened closes with it.
"""
from rest_framework import serializers, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from activity.models import ActivityVerb
from activity.services import log_activity
from membership.models import Membership, MembershipPlan
from membership.services import activate_membership, end_membership


class AdminMembershipPlanSerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = MembershipPlan
        fields = [
            "id", "name", "slug", "rank", "tagline", "description",
            "monthly_price", "yearly_price", "currency", "seats_per_product",
            "is_active", "is_featured", "sort_order", "product_count", "member_count",
        ]
        read_only_fields = ["slug"]

    def validate(self, attrs):
        merged = {**(self.instance.__dict__ if self.instance else {}), **attrs}
        if merged.get("monthly_price") is None and merged.get("yearly_price") is None:
            raise ValidationError(
                {"monthly_price": "A plan needs at least one price — monthly, yearly, or both."}
            )
        return attrs

    def get_product_count(self, obj):
        """Products assigned to this exact tier — not the cumulative total the
        storefront shows, since staff are editing one tier at a time here."""
        return obj.products.count()

    def get_member_count(self, obj):
        return obj.memberships.active().count()


class AdminMembershipPlanViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    serializer_class = AdminMembershipPlanSerializer
    queryset = MembershipPlan.objects.all()


class AdminMembershipSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source="user.email", read_only=True)
    plan_name = serializers.CharField(source="plan.name", read_only=True)
    display_status = serializers.CharField(read_only=True)
    granted_count = serializers.SerializerMethodField()

    class Meta:
        model = Membership
        fields = [
            "id", "user_email", "plan", "plan_name", "status", "display_status",
            "billing_period", "license_key", "amount", "currency",
            "started_at", "expires_at", "cancelled_at", "granted_count", "note",
        ]

    def get_granted_count(self, obj):
        """How many products this key has actually been activated on so far —
        the concrete blast radius of revoking it."""
        return obj.granted_purchases.count()


class AdminMembershipViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only by design: status changes go through the explicit
    revoke/reinstate actions below so the covered purchases are always brought
    along, which a bare PATCH on `status` would skip."""

    permission_classes = [IsAdminUser]
    serializer_class = AdminMembershipSerializer

    def get_queryset(self):
        return Membership.objects.select_related("user", "plan").prefetch_related("granted_purchases")


class AdminMembershipRevokeView(APIView):
    """Kills a membership and every license its universal key had opened."""

    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        membership = Membership.objects.select_related("plan", "user").filter(pk=pk).first()
        if membership is None:
            raise ValidationError({"detail": "Membership not found."})

        status = (request.data.get("status") or Membership.Status.REVOKED).strip()
        if status not in {Membership.Status.REVOKED, Membership.Status.REFUNDED, Membership.Status.CANCELLED}:
            raise ValidationError({"status": "Use revoked, refunded, or cancelled."})

        end_membership(membership, status)
        log_activity(
            request.user,
            ActivityVerb.ORDER_REFUND_REQUESTED,
            target_label=f"{membership.user.email} — {membership.plan.name} membership",
            metadata={"membership": True, "status": status},
        )
        membership.refresh_from_db()
        return Response(AdminMembershipSerializer(membership).data)


class AdminMembershipReinstateView(APIView):
    """Turns a membership back on — the manual counterpart to the Paymob
    webhook, and the way to test the whole flow without a live payment (same
    role "Mark Paid" plays for product orders)."""

    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        membership = Membership.objects.select_related("plan", "user").filter(pk=pk).first()
        if membership is None:
            raise ValidationError({"detail": "Membership not found."})

        activate_membership(membership)
        log_activity(
            request.user,
            ActivityVerb.ORDER_PLACED,
            target_label=f"{membership.user.email} — {membership.plan.name} membership",
            metadata={"membership": True, "manual": True},
        )
        membership.refresh_from_db()
        return Response(AdminMembershipSerializer(membership).data)
