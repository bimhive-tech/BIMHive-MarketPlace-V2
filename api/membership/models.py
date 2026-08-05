"""
All-Access membership — one subscription that unlocks many products.

Alongside buying products one at a time, a customer can subscribe to a plan and
get everything that plan covers. Two ideas carry the whole feature:

**Tiers.** Plans are ranked (`MembershipPlan.rank`). Each product names the
*lowest* plan that includes it (`Product.membership_plan`), so a Pro-only
product is simply one pointing at the Pro plan. A product pointing at no plan is
excluded from All-Access entirely and stays buy-only.

**One universal key.** A membership carries a single license key that activates
every covered product, rather than a key per product. The desktop plugins are
unchanged: when that key arrives at /api/license/activate, the server resolves it
to a normal, membership-owned ProductPurchase for whichever product asked (see
membership/services.py). Cancel, refund or expire the membership and every
purchase it minted goes with it — one switch, not a cleanup job.
"""
import secrets
import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


def generate_membership_key():
    """Visibly distinct from a per-product key (licensing.generate_license_key's
    "BH-…") so a customer looking at their account can tell at a glance which
    key is the All-Access one."""
    return "-".join(["BHX"] + [secrets.token_hex(2).upper() for _ in range(4)])


class MembershipPlan(models.Model):
    """A purchasable tier. `rank` is what decides coverage: a membership on a
    plan includes every product whose own plan ranks at or below it, so adding a
    higher tier later never removes anything from an existing one."""

    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    rank = models.PositiveSmallIntegerField(
        default=1,
        help_text="Higher tiers include everything the lower ones do. Standard=1, Pro=2, ...",
    )
    tagline = models.CharField(max_length=180, blank=True)
    description = models.TextField(blank=True)

    monthly_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    yearly_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=8, default="USD")

    # How many machines a member may run any ONE covered product on. Copied onto
    # each purchase the membership mints, so it goes through the same seat
    # enforcement as a bought license (see ProductPurchase.has_seat_for).
    seats_per_product = models.PositiveSmallIntegerField(default=2)

    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(
        default=False, help_text="Highlighted as the recommended plan on the pricing page."
    )
    sort_order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["rank", "sort_order", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def yearly_savings_percent(self):
        """How much cheaper the yearly price is than 12 monthly payments, for
        the "Save N%" badge. None when either price is missing or yearly isn't
        actually cheaper — never a misleading 0%."""
        if not self.monthly_price or not self.yearly_price:
            return None
        twelve_months = self.monthly_price * 12
        if self.yearly_price >= twelve_months:
            return None
        return round((twelve_months - self.yearly_price) / twelve_months * 100)

    def covers_plan(self, other):
        """Whether a membership on this plan includes products assigned to
        `other`. A product with no plan is covered by nothing."""
        return other is not None and other.rank <= self.rank


class MembershipQuerySet(models.QuerySet):
    def active(self, now=None):
        now = now or timezone.now()
        return self.filter(status=Membership.Status.ACTIVE).filter(
            models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=now)
        )


class Membership(models.Model):
    """One customer's subscription to a plan, and the universal key it grants."""

    class Status(models.TextChoices):
        PENDING = "pending", "Awaiting payment"
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"
        REFUNDED = "refunded", "Refunded"
        REVOKED = "revoked", "Revoked"

    class BillingPeriod(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        YEARLY = "yearly", "Yearly"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships")
    plan = models.ForeignKey(MembershipPlan, on_delete=models.PROTECT, related_name="memberships")

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    billing_period = models.CharField(max_length=10, choices=BillingPeriod.choices)
    # The one key that opens everything this plan covers. Unique across all
    # memberships — /api/license/activate looks a presented key up here after
    # failing to find a per-product purchase for it.
    license_key = models.CharField(max_length=64, unique=True, blank=True)

    amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=8, default="USD")

    started_at = models.DateTimeField(null=True, blank=True)
    # Null while PENDING; set when payment confirms and on every renewal. Null
    # on an ACTIVE membership means perpetual (a staff comp), not "expired".
    expires_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    payment_reference = models.CharField(max_length=120, blank=True, db_index=True)
    card_brand = models.CharField(max_length=40, blank=True)
    card_last4 = models.CharField(max_length=4, blank=True)
    note = models.TextField(blank=True, help_text="Staff-only note.")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = MembershipQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} — {self.plan.name} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.license_key:
            self.license_key = generate_membership_key()
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return bool(self.expires_at and self.expires_at <= timezone.now())

    @property
    def is_usable(self):
        """The single question everything else asks: may this key open a
        product right now?"""
        return self.status == self.Status.ACTIVE and not self.is_expired

    @property
    def display_status(self):
        """What the customer sees. A lapsed membership still marked ACTIVE in
        the database reads as expired, not active — the row is only flipped when
        something next touches it (see services.sync_membership_purchases)."""
        if self.status == self.Status.ACTIVE and self.is_expired:
            return self.Status.EXPIRED
        return self.status

    def covers(self, product):
        """Whether this membership's plan includes `product` — and whether the
        membership is in a state to grant anything at all."""
        return self.is_usable and self.plan.covers_plan(product.membership_plan)
