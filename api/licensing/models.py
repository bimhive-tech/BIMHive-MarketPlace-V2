"""
Licensing models — the activation backend shipped Revit plugins depend on.

Kept structurally compatible with v1 so the legacy installer-generator data
(products, machine_licenses, license_events) can be imported and the activation
contract behaves identically. Table names match v1 (`machine_licenses`,
`license_events`) for that import. See ARCHITECTURE §5 and licensing/api_views.py.

`LicensedProduct` is an *activation SKU* (one per product code / Revit-year build),
NOT a storefront listing. It links to the single storefront `catalog.Product`; this
preserves the "one Product" rule while keeping per-code activation intact.
"""
import secrets
import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


def generate_license_key():
    return "-".join(["BH"] + [secrets.token_hex(2).upper() for _ in range(4)])


class LicensedProduct(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.SET_NULL,
        related_name="license_skus",
        null=True,
        blank=True,
    )
    code = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=160, unique=True, blank=True)
    name = models.CharField(max_length=180)
    revit_year = models.CharField(max_length=16, blank=True)
    default_trial_days = models.PositiveIntegerField(default=30)
    is_active = models.BooleanField(default=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=8, default="USD")
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        db_table = "license_products"
        ordering = ["name", "code"]

    def __str__(self):
        return f"{self.name} [{self.code}]"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name or self.code) or slugify(self.code)
            slug, counter = base, 2
            qs = LicensedProduct.objects.all()
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            while qs.filter(slug=slug).exists():
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


class ProductPurchase(models.Model):
    class PaymentStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"
        CANCELLED = "cancelled", "Cancelled"
        REVOKED = "revoked", "Revoked"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="product_purchases"
    )
    product = models.ForeignKey(LicensedProduct, on_delete=models.CASCADE, related_name="purchases")
    payment_status = models.CharField(
        max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING, db_index=True
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=8, default="USD")
    license_key = models.CharField(max_length=64, unique=True, blank=True)
    company_name = models.CharField(max_length=180, blank=True)
    contact_email = models.EmailField(blank=True)
    payment_reference = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "license_purchases"
        ordering = ["-requested_at", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "product"], name="unique_product_purchase_per_user"
            )
        ]

    def __str__(self):
        return f"{self.user} -> {self.product.code} ({self.payment_status})"

    @property
    def is_license_active(self):
        return self.payment_status == self.PaymentStatus.PAID

    @property
    def denial_status(self):
        if self.payment_status in {
            self.PaymentStatus.CANCELLED,
            self.PaymentStatus.REFUNDED,
        }:
            return "cancelled"
        return "blocked"

    @property
    def denial_message(self):
        if self.payment_status == self.PaymentStatus.REFUNDED:
            return "Access denied. This license has been refunded."
        if self.payment_status in {self.PaymentStatus.REVOKED, self.PaymentStatus.CANCELLED}:
            return "Access denied. This license has been cancelled."
        return "Access denied. This license is not active."

    @property
    def bound_machine_license(self):
        # "released" machines (see services.release_machine_binding) are
        # deliberately excluded — that status exists specifically so a freed
        # binding stops blocking the next activation attempt from a new PC.
        return self.machine_licenses.exclude(status="released").order_by("first_seen_at", "id").first()

    def save(self, *args, **kwargs):
        if not self.license_key:
            self.license_key = generate_license_key()
        if not self.amount:
            self.amount = self.product.price
        if not self.currency:
            self.currency = self.product.currency
        if self.payment_status == self.PaymentStatus.PAID and self.paid_at is None:
            self.paid_at = timezone.now()
        if self.payment_status not in {self.PaymentStatus.PAID, self.PaymentStatus.REFUNDED}:
            self.paid_at = None
        super().save(*args, **kwargs)


class MachineLicense(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        LicensedProduct, on_delete=models.CASCADE, related_name="machine_licenses"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="machine_licenses",
        null=True,
        blank=True,
    )
    purchase = models.ForeignKey(
        ProductPurchase,
        on_delete=models.SET_NULL,
        related_name="machine_licenses",
        null=True,
        blank=True,
    )
    machine_fingerprint_hash = models.TextField()
    fingerprint_version = models.TextField(default="HWFP-2")
    status = models.TextField(default="active", db_index=True)
    started_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    first_seen_at = models.DateTimeField(default=timezone.now)
    last_seen_at = models.DateTimeField(default=timezone.now)
    install_count = models.IntegerField(default=1)
    plugin_version = models.TextField(blank=True)
    machine_data = models.JSONField(default=dict)
    metadata = models.JSONField(default=dict)

    class Meta:
        db_table = "machine_licenses"
        constraints = [
            models.UniqueConstraint(
                fields=["product", "machine_fingerprint_hash"],
                name="unique_machine_license_per_product",
            )
        ]

    def __str__(self):
        return f"{self.product.code} [{self.status}]"


class LicenseEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(LicensedProduct, on_delete=models.CASCADE, related_name="events")
    machine_license = models.ForeignKey(
        MachineLicense,
        on_delete=models.SET_NULL,
        related_name="events",
        null=True,
        blank=True,
    )
    machine_fingerprint_hash = models.TextField()
    event_type = models.TextField()
    event_time = models.DateTimeField(default=timezone.now)
    payload = models.JSONField(default=dict)

    class Meta:
        db_table = "license_events"
        ordering = ["-event_time", "-id"]

    def __str__(self):
        return f"{self.product.code} {self.event_type}"
