"""
The one sellable entity: Product.

A Product may be a Revit plugin, Dynamo script, template, BIM library, or service —
differentiated by `type`, NOT by a separate model. Its licensing/activation records
(per Revit-year build, keyed by product code) live in the `licensing` app and link
back here; that keeps the shipped-plugin activation contract intact without a parallel
"Plugin" model. See ARCHITECTURE §4–5.
"""
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from catalog.models.taxonomy import Category, Partner, Tag, TimeStamped


def _within_days(moment, days):
    """True when `moment` happened inside the last `days`. A window of 0 turns
    the badge off entirely rather than making it permanent."""
    if moment is None or days <= 0:
        return False
    return timezone.now() - moment <= timedelta(days=days)


class ProductType(models.TextChoices):
    PLUGIN = "plugin", "Revit Plugin"
    SCRIPT = "script", "Dynamo Script"
    TEMPLATE = "template", "Template"
    LIBRARY = "library", "BIM Library"
    SERVICE = "service", "Service"
    OTHER = "other", "Other"


class ProductStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PENDING = "pending", "Pending Review"
    PUBLISHED = "published", "Published"
    REJECTED = "rejected", "Rejected"


class ProductVisibility(models.TextChoices):
    PUBLIC = "public", "Public"
    HIDDEN = "hidden", "Hidden"


class PublishedProductQuerySet(models.QuerySet):
    def published(self):
        return self.filter(
            status=ProductStatus.PUBLISHED, visibility=ProductVisibility.PUBLIC
        )

    def featured(self):
        return self.published().filter(is_featured=True)


class Product(TimeStamped):
    # ── Identity ──
    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    # The activation SKU code sent by the desktop plugin (licensing.LicensedProduct.code
    # is kept in sync with this — see catalog/signals.py). Immutable once the product has
    # gone live (enforced in AdminProductWriteSerializer): changing it would break
    # activation for every copy already installed in the field.
    product_code = models.CharField(max_length=120, unique=True, blank=True)
    type = models.CharField(max_length=20, choices=ProductType.choices, default=ProductType.PLUGIN)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    partner = models.ForeignKey(
        Partner, on_delete=models.PROTECT, related_name="products", null=True, blank=True
    )
    tags = models.ManyToManyField(Tag, related_name="products", blank=True)

    # ── Copy ──
    short_description = models.CharField(max_length=220)
    description = models.TextField()

    # ── Pricing ──
    # `price` is the one-time price and stays the default for every product —
    # subscription billing is opt-in: set monthly_price and/or yearly_price
    # (see is_subscription) to sell this product as a recurring plan instead.
    # Both null means "not a subscription," not "$0" — a $0 subscription
    # tier isn't a thing here, only a free one-time product is (see is_free).
    price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    monthly_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    yearly_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=8, default="USD")

    # ── All-Access membership ──
    # The LOWEST membership tier that includes this product; null means it's
    # excluded from All-Access entirely and can only be bought outright. A
    # membership covers this product when its own plan ranks at or above this
    # one (see membership.MembershipPlan.covers_plan).
    membership_plan = models.ForeignKey(
        "membership.MembershipPlan",
        on_delete=models.SET_NULL,
        related_name="products",
        null=True,
        blank=True,
        help_text="Lowest All-Access tier that includes this product. Blank = not in All-Access.",
    )

    # ── Licensing config (activation records live in licensing.LicensedProduct) ──
    # A trial length of 0/0/0 means no trial is offered for this product at all
    # (see has_trial) — the buy box then skips the "Download Trial" option.
    default_trial_days = models.PositiveIntegerField(default=7)
    default_trial_hours = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(23)])
    default_trial_minutes = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(59)])

    @property
    def trial_minutes_total(self):
        return self.default_trial_days * 1440 + self.default_trial_hours * 60 + self.default_trial_minutes

    @property
    def has_trial(self):
        return self.trial_minutes_total > 0

    # ── Media / meta ──
    # Synced from whichever ProductMedia item is marked "cover" (see
    # AdminProductDetailSerializer._sync_nested) — same 1000-char ceiling as
    # ProductMedia.url, for the same reason: presigned R2 URLs run long.
    cover_image_url = models.URLField(max_length=1000, blank=True)
    version = models.CharField(max_length=30, default="1.0.0")
    released_at = models.DateField(null=True, blank=True)
    # When this product last shipped a new version — set automatically whenever
    # `version` changes on a live product (see save()), which is what drives the
    # temporary "Updated" badge in the storefront. Distinct from `updated_at`,
    # which any edit touches (a typo fix in the description is not an update
    # customers should be told about).
    last_release_at = models.DateTimeField(null=True, blank=True)

    # ── Ratings (denormalised aggregate, kept fresh by the reviews app) ──
    rating_average = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal("0.00"))
    rating_count = models.PositiveIntegerField(default=0)
    # Count of ratings per star level, keyed "1".."5". Aggregate source of truth
    # for the ratings-breakdown bars, independent of how many reviews are shown.
    rating_distribution = models.JSONField(default=dict, blank=True)
    download_count = models.PositiveIntegerField(default=0)

    # ── Publishing ──
    status = models.CharField(max_length=20, choices=ProductStatus.choices, default=ProductStatus.DRAFT)
    visibility = models.CharField(
        max_length=20, choices=ProductVisibility.choices, default=ProductVisibility.PUBLIC
    )
    is_featured = models.BooleanField(default=False)
    # Explicit homepage-hero curation — separate from is_featured (which drives
    # the "Featured Products" grid further down the page). When no product has
    # this on, the hero falls back to an automatic pick (discounted, then
    # featured, products — see catalog.views._spotlight_products) rather than
    # showing nothing; staff only need to reach for this to override that.
    is_hero_featured = models.BooleanField(
        default=False, help_text="Show in the homepage hero carousel."
    )
    hero_sort_order = models.PositiveIntegerField(
        default=0, help_text="Lower numbers show first in the hero carousel."
    )
    published_at = models.DateTimeField(null=True, blank=True)
    rejection_note = models.TextField(
        blank=True, help_text="Shown to the submitting partner when status is set to Rejected."
    )

    # ── SEO ──
    seo_title = models.CharField(max_length=180, blank=True)
    seo_description = models.CharField(max_length=300, blank=True)

    objects = PublishedProductQuerySet.as_manager()

    class Meta:
        ordering = ["-is_featured", "-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["status", "visibility"]),
            models.Index(fields=["category"]),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._unique_value("slug", slugify(self.name))
        if not self.product_code:
            self.product_code = self._unique_value("product_code", slugify(self.name) or self.slug)
        if self.status == ProductStatus.PUBLISHED and self.published_at is None:
            self.published_at = timezone.now()
        if self._stamp_release_if_version_changed():
            # An explicit update_fields list limits which columns are written,
            # so the new timestamp would be dropped unless it's added to it.
            update_fields = kwargs.get("update_fields")
            if update_fields is not None:
                kwargs["update_fields"] = {*update_fields, "last_release_at"}
        super().save(*args, **kwargs)

    def _stamp_release_if_version_changed(self):
        """Timestamps a version bump so the storefront can show an "Updated"
        badge for a while afterwards. Only for products already published — the
        edits leading up to a first release aren't updates to anything, and the
        "New" badge covers that period instead. Returns whether it stamped."""
        if not self.pk or self.published_at is None:
            return False
        previous_version = (
            type(self).objects.filter(pk=self.pk).values_list("version", flat=True).first()
        )
        if previous_version is None or previous_version == self.version:
            return False
        self.last_release_at = timezone.now()
        return True

    # ── Storefront freshness badges ──
    @property
    def is_new(self):
        """Published within the "New" window (settings.NEW_PRODUCT_BADGE_DAYS)."""
        return _within_days(self.published_at, settings.NEW_PRODUCT_BADGE_DAYS)

    @property
    def is_updated(self):
        """Shipped a new version within the "Updated" window. A product still
        showing as new isn't also "updated" — one badge per card, and "New" is
        the stronger claim."""
        if self.is_new:
            return False
        return _within_days(self.last_release_at, settings.UPDATED_PRODUCT_BADGE_DAYS)

    def _unique_value(self, field, base):
        """Append -2, -3, ... until `base` doesn't collide with another row's `field`."""
        value = base
        counter = 2
        qs = type(self).objects.exclude(pk=self.pk) if self.pk else type(self).objects.all()
        while qs.filter(**{field: value}).exists():
            value = f"{base}-{counter}"
            counter += 1
        return value

    @property
    def is_subscription(self):
        return bool(self.monthly_price or self.yearly_price)

    @property
    def is_free(self):
        # A subscription product's one-time `price` is unused/irrelevant —
        # it's never actually free just because that field defaults to 0.
        return self.price <= 0 and not self.is_subscription

    @property
    def price_label(self):
        if self.is_subscription:
            if self.monthly_price:
                return f"${self.monthly_price:.2f}/mo"
            return f"${self.yearly_price:.2f}/yr"
        return "Free" if self.is_free else f"${self.price:.2f}"

    @property
    def yearly_savings_percent(self):
        """How much cheaper billing yearly is vs. paying the monthly price
        for 12 months, rounded to a whole percent for display (the
        "Save N%" badge on the billing toggle). None when either price
        isn't set, or when yearly isn't actually cheaper — never shown as a
        misleading 0%/negative "discount"."""
        if not self.monthly_price or not self.yearly_price:
            return None
        yearly_equivalent_of_monthly = self.monthly_price * 12
        if self.yearly_price >= yearly_equivalent_of_monthly:
            return None
        savings = (yearly_equivalent_of_monthly - self.yearly_price) / yearly_equivalent_of_monthly
        return round(savings * 100)


class ProductMedia(TimeStamped):
    """Gallery items (screenshots / video) for the product detail media gallery."""

    class MediaType(models.TextChoices):
        IMAGE = "image", "Image"
        VIDEO = "video", "Video"

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="media")
    media_type = models.CharField(max_length=12, choices=MediaType.choices, default=MediaType.IMAGE)
    # Django's URLField defaults to max_length=200, but a presigned R2 URL (the
    # fallback used whenever R2_PUBLIC_BASE_URL isn't set) runs 350-450+ chars
    # on its own — wide enough to comfortably fit either shape.
    url = models.URLField(max_length=1000)
    caption = models.CharField(max_length=180, blank=True)
    is_cover = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.product.name} media {self.sort_order}"


class KeyFeature(TimeStamped):
    """Repeatable "Key Features" pairs shown on the product page (title + blurb)."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="features")
    title = models.CharField(max_length=140)
    description = models.CharField(max_length=300, blank=True)
    icon = models.CharField(max_length=40, blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.product.name}: {self.title}"


class ChangelogEntry(TimeStamped):
    """"What's New" release history."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="changelog")
    version = models.CharField(max_length=30)
    released_at = models.DateField(null=True, blank=True)
    notes = models.TextField(help_text="One bullet per line.")
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "-released_at", "-id"]
        verbose_name_plural = "changelog entries"

    def __str__(self):
        return f"{self.product.name} v{self.version}"


class CompatibilityEntry(TimeStamped):
    """A supported environment row for the Compatibility tab (e.g. Revit 2024, Windows)."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="compatibility")
    label = models.CharField(max_length=80, help_text="e.g. 'Revit 2024', 'Windows 10+'")
    value = models.CharField(max_length=120, blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name_plural = "compatibility entries"

    def __str__(self):
        return f"{self.product.name}: {self.label}"


class ProductFile(TimeStamped):
    """
    A downloadable build — multi-variant, keyed by Revit version (2024, 2025, ...).
    The download endpoint serves the right file per requested version. Stored in R2;
    `storage_key` is the object key, served via short-lived signed URLs.
    """

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="files")
    revit_version = models.CharField(max_length=16, help_text="e.g. '2024'. Blank = version-agnostic.")
    version_label = models.CharField(max_length=30, help_text="Build version, e.g. '2.1.0'.")
    storage_key = models.CharField(max_length=400, help_text="R2 object key.")
    file_size_bytes = models.PositiveBigIntegerField(default=0)
    is_current = models.BooleanField(default=True)

    class Meta:
        ordering = ["-is_current", "revit_version", "-version_label"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "revit_version", "version_label"],
                name="unique_product_file_variant",
            )
        ]

    def __str__(self):
        return f"{self.product.name} [{self.revit_version or 'any'}] {self.version_label}"
