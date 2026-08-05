"""Serializers shared by the public plans list, the account page and admin."""
from rest_framework import serializers

from membership.models import Membership, MembershipPlan


class MembershipPlanSerializer(serializers.ModelSerializer):
    yearly_savings_percent = serializers.IntegerField(read_only=True)
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = MembershipPlan
        fields = [
            "id", "name", "slug", "rank", "tagline", "description",
            "monthly_price", "yearly_price", "currency", "yearly_savings_percent",
            "seats_per_product", "is_featured", "product_count",
        ]

    def get_product_count(self, obj):
        """How many live products this tier unlocks — the number that makes the
        plan's value concrete on the pricing page. Includes everything the lower
        tiers cover, since higher ranks are cumulative."""
        counts = self.context.get("product_counts_by_rank") or {}
        return sum(count for rank, count in counts.items() if rank <= obj.rank)


class AccountMembershipSerializer(serializers.ModelSerializer):
    """The customer's own membership, including the universal key. Never used
    for anyone else's — the key is the credential."""

    plan_name = serializers.CharField(source="plan.name", read_only=True)
    plan_slug = serializers.CharField(source="plan.slug", read_only=True)
    seats_per_product = serializers.IntegerField(source="plan.seats_per_product", read_only=True)
    display_status = serializers.CharField(read_only=True)
    is_usable = serializers.BooleanField(read_only=True)

    class Meta:
        model = Membership
        fields = [
            "id", "plan_name", "plan_slug", "status", "display_status", "is_usable",
            "billing_period", "license_key", "amount", "currency", "seats_per_product",
            "started_at", "expires_at", "cancelled_at",
        ]
