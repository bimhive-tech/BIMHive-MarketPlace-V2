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
    # How many machines this one purchase may have bound at once (a "buy 3
    # licenses" checkout sets this to 3 instead of creating 3 separate
    # purchase rows — see ProductPurchase.available_seats and
    # licensing/api_views.py's activation seat check).
    seats = models.PositiveIntegerField(default=1)
    # Null = perpetual (the default for a normal purchase). Set when this
    # purchase came from a time-limited LicenseCode redemption — the whole
    # purchase expires at this instant, not just one machine's binding.
    expires_at = models.DateTimeField(null=True, blank=True)
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
    def is_expired(self):
        return bool(self.expires_at and self.expires_at <= timezone.now())

    @property
    def is_license_active(self):
        return self.payment_status == self.PaymentStatus.PAID and not self.is_expired

    @property
    def license_status(self):
        """Simplified active/inactive/expired label for customer-facing UI —
        `payment_status` has more states than a buyer needs to reason about
        (pending/failed/refunded/cancelled/revoked all just mean "not usable
        right now"). Checked in this order since a lapsed expires_at should
        read as "expired" even on an otherwise-paid purchase."""
        if self.is_expired:
            return "expired"
        if self.payment_status == self.PaymentStatus.PAID:
            return "active"
        return "inactive"

    @property
    def denial_status(self):
        if self.is_expired:
            return "expired"
        if self.payment_status in {
            self.PaymentStatus.CANCELLED,
            self.PaymentStatus.REFUNDED,
        }:
            return "cancelled"
        return "blocked"

    @property
    def denial_message(self):
        if self.is_expired:
            return "Access denied. This license has expired."
        if self.payment_status == self.PaymentStatus.REFUNDED:
            return "Access denied. This license has been refunded."
        if self.payment_status in {self.PaymentStatus.REVOKED, self.PaymentStatus.CANCELLED}:
            return "Access denied. This license has been cancelled."
        return "Access denied. This license is not active."

    @property
    def active_machine_licenses(self):
        # "released" machines (see services.release_machine_binding, now a
        # staff-only override — see licensing/admin_api.py::AdminLicenseReleaseView)
        # are deliberately excluded — that status exists specifically so a
        # freed binding frees up a seat for a new machine to take.
        return self.machine_licenses.exclude(status="released").order_by("first_seen_at", "id")

    def has_seat_for(self, machine_fingerprint_hash):
        """True if `machine_fingerprint_hash` already holds one of this
        purchase's seats, or if an unused seat is available for it to take.
        Each seat is single-use for the machine that first claims it — there
        is no customer self-service way to move a claimed seat to a
        different machine (only a staff override, see AdminLicenseReleaseView);
        `seats` just controls how many distinct machines may each claim one
        seat, once, ever."""
        active = list(self.active_machine_licenses)
        if any(m.machine_fingerprint_hash == machine_fingerprint_hash for m in active):
            return True
        return len(active) < self.seats

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


def generate_redeem_code():
    return "-".join(["GIFT"] + [secrets.token_hex(2).upper() for _ in range(3)])


class LicenseCode(models.Model):
    """A staff-generated, single-use code for one specific product that
    grants a real (non-trial) license to whichever account redeems it —
    the "upgrade" of the old installer-generator's manually-issued keys:
    still admin-controlled per-product and per-duration, but now redeemed
    through the account system instead of baked into a specific binary.
    Redeeming one creates/activates the redeemer's normal ProductPurchase
    for that product, so it goes through the exact same seat/activation
    enforcement as anything bought through checkout."""

    class Status(models.TextChoices):
        UNREDEEMED = "unredeemed", "Unredeemed"
        REDEEMED = "redeemed", "Redeemed"
        REVOKED = "revoked", "Revoked"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=64, unique=True, blank=True)
    product = models.ForeignKey(LicensedProduct, on_delete=models.CASCADE, related_name="license_codes")
    seats = models.PositiveIntegerField(default=1)
    # Null = lifetime — mirrors ProductPurchase.expires_at, copied onto the
    # purchase at redemption time (duration counts from redemption, not
    # from when the code was generated).
    duration_days = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UNREDEEMED, db_index=True)
    note = models.CharField(max_length=200, blank=True, help_text="Staff-only note, e.g. who this was issued to and why.")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name="license_codes_created",
        null=True, blank=True,
    )
    redeemed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name="license_codes_redeemed",
        null=True, blank=True,
    )
    redeemed_purchase = models.ForeignKey(
        ProductPurchase, on_delete=models.SET_NULL, related_name="source_license_code",
        null=True, blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    redeemed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "license_codes"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.code} [{self.status}]"

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = generate_redeem_code()
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
