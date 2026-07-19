"""
Licensing side effects used by the activation API and (later) payment webhooks.
Ported from v1 without the Plugin-sync coupling — activation SKUs are managed via
the admin / legacy import, not synced from a separate Plugin model.
"""
from datetime import timedelta

from django.utils import timezone

from licensing.models import LicenseEvent, LicensedProduct, ProductPurchase


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
    """Frees a paid purchase's machine binding — self-service "I got a new
    PC" reactivation (see licensing/account_api.py::ReactivateLicenseView).
    The next activation call with a different fingerprint then binds fresh
    instead of being denied forever by the old one (bound_machine_license
    excludes "released" machines — see ProductPurchase.bound_machine_license)."""
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
    """Re-activate a purchase (e.g. after a webhook confirms payment) and its machines."""
    event_time = event_time or timezone.now()
    if purchase.payment_status != ProductPurchase.PaymentStatus.PAID:
        purchase.payment_status = ProductPurchase.PaymentStatus.PAID
        purchase.save(update_fields=["payment_status", "paid_at", "updated_at"])

    paid_expires_at = event_time + timedelta(days=365 * 100)
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
