"""
Licensing side effects used by the activation API and (later) payment webhooks.
Ported from v1 without the Plugin-sync coupling — activation SKUs are managed via
the admin / legacy import, not synced from a separate Plugin model.
"""
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from licensing.models import LicenseCode, LicenseEvent, LicensedProduct, ProductPurchase


class LicenseCodeError(Exception):
    """Raised with a user-facing message when a code can't be redeemed."""


# How long a subscription purchase's `expires_at` runs for, keyed by
# billing_period. Shared by PaymobWebhookView (a real payment confirming) and
# restore_purchase_access below (staff manually marking a still-PENDING
# subscription order paid, e.g. to test the flow without a live payment) so
# both compute the same expiry the same way. TEMPORARY TEST OVERRIDE for the
# monthly interval — see the comment on MONTHLY below. Revert MONTHLY back to
# timedelta(days=30) once the Paymob payment -> webhook -> license-revocation
# flow has been proven out with the fast interval; nothing else about
# billing_period changes.
def subscription_duration(billing_period: str):
    if billing_period == ProductPurchase.BillingPeriod.MONTHLY:
        # TEMPORARY (test only): really 30 days — shortened to 10 minutes
        # so a real Paymob test payment can be watched through to license
        # revocation without waiting a month. Change back to
        # timedelta(days=30) once that's confirmed working end to end.
        return timedelta(minutes=10)
    if billing_period == ProductPurchase.BillingPeriod.YEARLY:
        return timedelta(days=365)
    return None


def expires_at_for(billing_period, now):
    duration = subscription_duration(billing_period)
    return now + duration if duration else None


def sync_license_sku(product):
    """
    Create or update the activation SKU (licensing.LicensedProduct) for a
    storefront Product, keyed by `product.product_code`. Called automatically
    on every Product save (see catalog/signals.py) so a product added or edited
    anywhere — admin portal, Django admin, shell, seed script — is immediately
    activatable by the desktop plugin. A product without a code yet (shouldn't
    happen since Product.save() always assigns one) is skipped.
    """
    from catalog.models.product import ProductStatus

    if not product.product_code:
        return None
    licensed_product, _ = LicensedProduct.objects.update_or_create(
        code=product.product_code,
        defaults={
            "product": product,
            "name": product.name,
            "default_trial_days": product.default_trial_days,
            "default_trial_hours": product.default_trial_hours,
            "default_trial_minutes": product.default_trial_minutes,
            "price": product.price,
            "currency": product.currency,
            "is_active": product.status == ProductStatus.PUBLISHED,
        },
    )
    return licensed_product


def log_license_event(product, machine_license, event_type, payload=None, event_time=None):
    LicenseEvent.objects.create(
        product=product,
        machine_license=machine_license,
        machine_fingerprint_hash=machine_license.machine_fingerprint_hash,
        event_type=event_type,
        event_time=event_time or timezone.now(),
        payload=payload or {},
    )


def revoke_purchase_access(purchase, status=None, reason=None, event_time=None):
    """Flip a purchase to a non-active state and block its machine licenses."""
    event_time = event_time or timezone.now()
    target_status = status or ProductPurchase.PaymentStatus.REVOKED
    machine_status = (
        "blocked" if target_status == ProductPurchase.PaymentStatus.REVOKED else "cancelled"
    )

    if purchase.payment_status != target_status:
        purchase.payment_status = target_status
        purchase.save(update_fields=["payment_status", "paid_at", "updated_at"])

    for machine_license in purchase.machine_licenses.select_related("product"):
        machine_license.status = machine_status
        machine_license.expires_at = event_time
        machine_license.last_seen_at = event_time
        machine_license.save(update_fields=["status", "expires_at", "last_seen_at"])
        log_license_event(
            machine_license.product,
            machine_license,
            "purchase_revoked",
            {
                "purchaseId": str(purchase.pk),
                "paymentStatus": purchase.payment_status,
                "reason": reason or purchase.payment_status,
            },
            event_time=event_time,
        )
    return purchase


def release_machine_binding(machine_license, event_time=None):
    """Frees one seat of a paid purchase — a staff-only manual override (see
    licensing/admin_api.py::AdminLicenseReleaseView). Licenses are single-use
    per machine with no customer self-service way to move one, by design; the
    next activation call with a different fingerprint can then take that seat
    instead of being denied forever by the old one (active_machine_licenses
    excludes "released" machines — see ProductPurchase.active_machine_licenses
    / has_seat_for)."""
    event_time = event_time or timezone.now()
    machine_license.status = "released"
    machine_license.last_seen_at = event_time
    machine_license.save(update_fields=["status", "last_seen_at"])
    log_license_event(
        machine_license.product,
        machine_license,
        "machine_released",
        {"purchaseId": str(machine_license.purchase_id) if machine_license.purchase_id else None},
        event_time=event_time,
    )
    return machine_license


def restore_purchase_access(purchase, event_time=None):
    """Re-activate a purchase (e.g. after a webhook confirms payment, or a
    staff member manually marking a still-PENDING order paid from the Admin
    Orders page) and its machines."""
    event_time = event_time or timezone.now()
    if purchase.payment_status != ProductPurchase.PaymentStatus.PAID:
        purchase.payment_status = ProductPurchase.PaymentStatus.PAID
        # A subscription purchase's expires_at is deliberately left unset by
        # CheckoutView until payment actually confirms — mirrors what
        # PaymobWebhookView does, so staff clicking "Mark Paid" on a PENDING
        # subscription order (the only way to test the flow while blocked on
        # a real Paymob transaction) correctly starts its billing period
        # instead of leaving it looking perpetual. A purchase that already
        # has an expires_at (already confirmed once before, or a
        # LicenseCode-limited grant) keeps it as-is — see the comment below.
        if purchase.billing_period and purchase.expires_at is None:
            purchase.expires_at = expires_at_for(purchase.billing_period, event_time)
            purchase.save(update_fields=["payment_status", "expires_at", "paid_at", "updated_at"])
        else:
            purchase.save(update_fields=["payment_status", "paid_at", "updated_at"])

    # A time-limited purchase (e.g. from a LicenseCode redemption) keeps its
    # own expiry on restore instead of being reset to "forever" — only an
    # untimed (expires_at=None) purchase gets the effectively-perpetual date.
    paid_expires_at = purchase.expires_at or (event_time + timedelta(days=365 * 100))
    for machine_license in purchase.machine_licenses.select_related("product"):
        machine_license.status = "paid"
        machine_license.user = purchase.user
        machine_license.last_seen_at = event_time
        machine_license.expires_at = paid_expires_at
        machine_license.save(update_fields=["status", "user", "last_seen_at", "expires_at"])
        log_license_event(
            machine_license.product,
            machine_license,
            "purchase_restored",
            {"purchaseId": str(purchase.pk), "paymentStatus": purchase.payment_status},
            event_time=event_time,
        )
    return purchase


def redeem_license_code(code, user, event_time=None):
    """Redeem a staff-issued LicenseCode into a real ProductPurchase for
    `user` — the account-connected upgrade of the old installer-generator's
    manually-issued keys. Raises LicenseCodeError with a user-facing message
    on any invalid state. The resulting purchase goes through the exact same
    activation/seat enforcement as a normal purchase; nothing downstream
    needs to know it came from a redeemed code rather than checkout."""
    event_time = event_time or timezone.now()
    try:
        license_code = LicenseCode.objects.select_related("product").get(code__iexact=code.strip())
    except LicenseCode.DoesNotExist:
        raise LicenseCodeError("That code doesn't exist.")

    if license_code.status != LicenseCode.Status.UNREDEEMED:
        raise LicenseCodeError("That code has already been used or is no longer valid.")

    existing = ProductPurchase.objects.filter(user=user, product=license_code.product).first()
    if existing and existing.is_license_active:
        raise LicenseCodeError("You already have an active license for this product.")

    expires_at = (
        event_time + timedelta(days=license_code.duration_days) if license_code.duration_days else None
    )

    if existing:
        purchase = existing
        # Reset any stale bindings from a previous (expired/cancelled) grant
        # so this redemption starts with its own full, clean seat pool.
        for machine_license in purchase.machine_licenses.exclude(status="released"):
            machine_license.status = "released"
            machine_license.last_seen_at = event_time
            machine_license.save(update_fields=["status", "last_seen_at"])
        purchase.payment_status = ProductPurchase.PaymentStatus.PAID
        purchase.seats = license_code.seats
        purchase.expires_at = expires_at
        purchase.save()
    else:
        purchase = ProductPurchase.objects.create(
            user=user,
            product=license_code.product,
            payment_status=ProductPurchase.PaymentStatus.PAID,
            seats=license_code.seats,
            expires_at=expires_at,
        )

    # A redeemed code is a comp/grant, not a real transaction — force $0
    # regardless of the product's list price. ProductPurchase.save() backfills
    # a zero/falsy amount from product.price on every save (right for a normal
    # purchase, wrong here), and re-runs that backfill even when called with
    # update_fields=["amount"] — update_fields only limits the SQL columns
    # written, not which lines of the overridden save() execute. A queryset
    # .update() bypasses save() entirely, so it's the only way to make this
    # stick. Sales/Orders revenue reporting sums `amount` for paid purchases,
    # so this isn't cosmetic — a stale price would inflate real numbers.
    ProductPurchase.objects.filter(pk=purchase.pk).update(amount=Decimal("0.00"))
    purchase.amount = Decimal("0.00")

    license_code.status = LicenseCode.Status.REDEEMED
    license_code.redeemed_by = user
    license_code.redeemed_purchase = purchase
    license_code.redeemed_at = event_time
    license_code.save(update_fields=["status", "redeemed_by", "redeemed_purchase", "redeemed_at"])

    return purchase
