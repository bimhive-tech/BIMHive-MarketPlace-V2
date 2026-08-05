"""
Public + customer-facing membership API.

  GET  /api/membership/plans          — the pricing page
  GET  /api/account/membership        — my membership, my universal key
  POST /api/account/membership/checkout — start a Paymob payment for a plan
  POST /api/account/membership/cancel   — end my own membership
"""
from django.conf import settings
from django.db.models import Count
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from activity.models import ActivityVerb
from activity.services import log_activity
from catalog.models import Product
from catalog.serializers import ProductCardSerializer
from licensing import paymob
from membership.models import Membership, MembershipPlan
from membership.serializers import AccountMembershipSerializer, MembershipPlanSerializer
from membership.services import active_membership_for, covered_products, end_membership


def _plan_context():
    """One grouped COUNT for the whole plans list, rather than a query per
    plan (see MembershipPlanSerializer.get_product_count)."""
    rows = (
        Product.objects.published()
        .filter(membership_plan__isnull=False)
        .values("membership_plan__rank")
        .annotate(total=Count("id"))
    )
    return {"product_counts_by_rank": {row["membership_plan__rank"]: row["total"] for row in rows}}


class MembershipPlanListView(APIView):
    """The /membership pricing page. Public — this is marketing copy."""

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        plans = MembershipPlan.objects.filter(is_active=True)
        return Response(
            {"plans": MembershipPlanSerializer(plans, many=True, context=_plan_context()).data}
        )


class AccountMembershipView(APIView):
    """Everything /account/membership renders: the membership itself, the
    universal key, and what that key opens."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        membership = active_membership_for(request.user)
        if membership is None:
            # Fall back to the most recent lapsed one so the page can say
            # "your membership ended on ..." instead of pretending there was
            # never one.
            membership = (
                Membership.objects.filter(user=request.user)
                .exclude(status=Membership.Status.PENDING)
                .select_related("plan")
                .first()
            )
        if membership is None:
            return Response({"membership": None, "products": []})

        products = covered_products(membership.plan) if membership.is_usable else Product.objects.none()
        return Response(
            {
                "membership": AccountMembershipSerializer(membership).data,
                "products": ProductCardSerializer(products, many=True).data,
            }
        )


class MembershipCheckoutView(APIView):
    """Starts a Paymob payment for a plan.

    Creates the membership PENDING and hands back a checkout URL — exactly like
    CheckoutView does for products. Nothing is granted here; only the
    HMAC-verified webhook activates a membership (see PaymobWebhookView),
    because trusting the browser redirect would let anyone unlock the whole
    catalogue by visiting a URL.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        import uuid

        plan = MembershipPlan.objects.filter(
            slug=(request.data.get("plan") or "").strip(), is_active=True
        ).first()
        if plan is None:
            raise ValidationError({"plan": "That plan isn't available."})

        billing_period = (request.data.get("billingPeriod") or "").strip()
        if billing_period not in {choice for choice, _ in Membership.BillingPeriod.choices}:
            raise ValidationError({"billingPeriod": "Pick monthly or yearly."})

        amount = plan.monthly_price if billing_period == Membership.BillingPeriod.MONTHLY else plan.yearly_price
        if amount is None:
            raise ValidationError({"billingPeriod": f"{plan.name} isn't sold on that interval."})

        existing = active_membership_for(request.user)
        if existing and existing.plan_id == plan.id and existing.billing_period == billing_period:
            raise ValidationError({"detail": "You're already on this plan. It renews automatically."})

        reference = f"bimhive-membership-{uuid.uuid4()}"
        # Supersedes any abandoned attempt, the same way CheckoutView does for
        # products — otherwise a failed card leaves PENDING memberships piling
        # up with unusable keys.
        Membership.objects.filter(user=request.user, status=Membership.Status.PENDING).update(
            status=Membership.Status.CANCELLED
        )
        membership = Membership.objects.create(
            user=request.user,
            plan=plan,
            billing_period=billing_period,
            status=Membership.Status.PENDING,
            amount=amount,
            currency=plan.currency,
            payment_reference=reference,
        )

        billing_data = {
            "first_name": request.user.first_name or request.user.username,
            "last_name": request.user.last_name or "N/A",
            "email": request.user.email,
            "phone_number": "+20000000000",
            "apartment": "NA", "floor": "NA", "street": "NA",
            "building": "NA", "city": "NA", "state": "NA", "country": "NA",
        }
        try:
            intention = paymob.create_intention(
                amount_cents=int(amount * 100),
                special_reference=reference,
                notification_url=f"{settings.SITE_URL}/api/webhooks/paymob",
                redirection_url=f"{settings.SITE_URL}/checkout/confirmation?reference={reference}",
                billing_data=billing_data,
                items=[
                    {
                        "name": f"{plan.name} membership"[:100],
                        "amount": int(amount * 100),
                        "description": f"BIMHive All-Access — {plan.name} ({billing_period})"[:200],
                        "quantity": 1,
                    }
                ],
            )
        except paymob.PaymobError as exc:
            membership.status = Membership.Status.CANCELLED
            membership.save(update_fields=["status", "updated_at"])
            raise ValidationError({"detail": f"Could not start payment: {exc}"}) from exc

        return Response(
            {"checkoutUrl": paymob.checkout_url(intention["client_secret"]), "reference": reference},
            status=201,
        )


class AccountMembershipCancelView(APIView):
    """Self-service cancellation. Immediate: the universal key stops working
    and every product it opened is revoked in the same call (see
    membership.services.end_membership)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        membership = active_membership_for(request.user)
        if membership is None:
            raise ValidationError({"detail": "You don't have an active membership."})

        end_membership(membership, Membership.Status.CANCELLED)
        log_activity(
            request.user,
            ActivityVerb.ORDER_REFUND_REQUESTED,
            target_label=f"{membership.plan.name} membership",
            metadata={"self_service": True, "membership": True},
        )
        membership.refresh_from_db()
        return Response(AccountMembershipSerializer(membership).data)
