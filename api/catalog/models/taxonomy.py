"""
Taxonomy: how products are grouped and attributed.

A Category is the primary "kind" of product shown in the storefront sidebar
(Revit Plugins, Automation Tools, Dynamo Scripts, ...). This is where the old
"Plugin" idea now lives — as a category, not a separate model.
"""
from django.db import models
from django.utils.text import slugify


class TimeStamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Category(TimeStamped):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.TextField(blank=True)
    icon = models.CharField(
        max_length=40, blank=True, help_text="Line-icon name (see frontend icon set)."
    )
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, related_name="children", null=True, blank=True
    )
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Collection(TimeStamped):
    """A curated bundle of products (e.g. "Revit Essentials")."""

    name = models.CharField(max_length=140, unique=True)
    slug = models.SlugField(max_length=160, unique=True, blank=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=40, blank=True)
    products = models.ManyToManyField("catalog.Product", related_name="collections", blank=True)
    is_featured = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Tag(TimeStamped):
    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=80, unique=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Partner(TimeStamped):
    """The seller/publisher a product is listed under (shown on the product page).
    Created via the self-service "Become a Seller" application (see
    catalog.partner_api.BecomeSellerView) — `status` gates whether the
    applicant's account actually has partner-portal access yet
    (catalog.permissions.IsStaffOrPartner/IsApprovedPartner)."""

    class ApplicationStatus(models.TextChoices):
        PENDING = "pending", "Pending Review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    name = models.CharField(max_length=160, unique=True)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    tagline = models.CharField(max_length=180, blank=True)
    bio = models.TextField(blank=True)
    # Same 1000-char ceiling as Product.cover_image_url — a presigned R2 URL
    # (the fallback used whenever R2_PUBLIC_BASE_URL isn't set) runs long.
    logo_url = models.URLField(max_length=1000, blank=True)
    website = models.URLField(blank=True)
    # A separate, cosmetic "verified seller" badge BIMHive toggles for public
    # display — unrelated to `status`, which gates portal access itself.
    is_verified = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20, choices=ApplicationStatus.choices, default=ApplicationStatus.PENDING
    )
    rejection_note = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
