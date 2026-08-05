"""
Time-boxed price promotions.

One model drives both halves of the same campaign: the percentage taken off the
products it covers, and the countdown banner above the storefront nav that says
how long that price lasts. A promotion is only ever live inside its own
[starts_at, ends_at) window, so the discount and the countdown can never
disagree — when the clock hits zero, prices are back to list on the next request
with no scheduled job to run.
"""
from decimal import ROUND_HALF_UP, Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from catalog.models.taxonomy import TimeStamped

# A promotion is a discount, not a giveaway: 90% is already extreme, and the
# cap stops a mistyped "100" from silently making the whole catalog free.
MAX_DISCOUNT_PERCENT = 90
CENTS = Decimal("0.01")


def apply_discount(amount, percent):
    """`amount` reduced by `percent`, rounded to cents. None in, None out — a
    product with no monthly/yearly price doesn't gain one by being on sale."""
    if amount is None:
        return None
    discounted = Decimal(amount) * (Decimal(100 - percent) / Decimal(100))
    return discounted.quantize(CENTS, rounding=ROUND_HALF_UP)


class LivePromotionQuerySet(models.QuerySet):
    def live(self, now=None):
        now = now or timezone.now()
        return self.filter(is_active=True, starts_at__lte=now, ends_at__gt=now)


class Promotion(TimeStamped):
    class Scope(models.TextChoices):
        ALL = "all", "Every product"
        CATEGORY = "category", "One category (and its subcategories)"
        PRODUCTS = "products", "Selected products only"

    # ── Staff-facing identity ──
    name = models.CharField(max_length=140, help_text="Internal name, e.g. 'Back to school 2026'.")

    # ── Storefront copy ──
    badge_label = models.CharField(
        max_length=40, default="SPECIAL OFFER", help_text="Short label on the countdown bar."
    )
    headline = models.CharField(
        max_length=160, help_text="The line customers read, e.g. \"This price won't last long...\""
    )
    cta_label = models.CharField(max_length=40, blank=True)
    cta_url = models.CharField(
        max_length=200, blank=True, help_text="Where the banner's button goes, e.g. /catalog."
    )

    # ── What it discounts ──
    discount_percent = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(MAX_DISCOUNT_PERCENT)]
    )
    scope = models.CharField(max_length=20, choices=Scope.choices, default=Scope.ALL)
    category = models.ForeignKey(
        "catalog.Category",
        on_delete=models.CASCADE,
        related_name="promotions",
        null=True,
        blank=True,
        help_text="Required when scope is 'category'. Subcategories are included.",
    )
    products = models.ManyToManyField(
        "catalog.Product",
        related_name="promotions",
        blank=True,
        help_text="Required when scope is 'products'.",
    )

    # ── When ──
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    is_active = models.BooleanField(
        default=True, help_text="Switches the promotion off without changing its dates."
    )

    # ── Banner ──
    show_countdown = models.BooleanField(
        default=True, help_text="Show this promotion in the countdown bar above the nav."
    )
    priority = models.IntegerField(
        default=0,
        help_text="Higher wins when two live promotions cover the same product or want the banner.",
    )

    objects = LivePromotionQuerySet.as_manager()

    class Meta:
        # Highest priority first, then the one ending soonest — the more urgent
        # of two equally-ranked offers is the one worth showing.
        ordering = ["-priority", "ends_at"]
        indexes = [models.Index(fields=["is_active", "starts_at", "ends_at"])]

    def __str__(self):
        return f"{self.name} (-{self.discount_percent}%)"

    @property
    def is_live(self):
        return self.is_active and self.starts_at <= timezone.now() < self.ends_at

    def covers(self, product):
        """Whether this promotion discounts `product`. Reads only prefetched
        relations so pricing a whole product grid stays query-free."""
        if self.scope == self.Scope.ALL:
            return True
        if self.scope == self.Scope.CATEGORY:
            if not self.category_id:
                return False
            return product.category_id == self.category_id or (
                product.category and product.category.parent_id == self.category_id
            )
        return any(p.pk == product.pk for p in self.products.all())
