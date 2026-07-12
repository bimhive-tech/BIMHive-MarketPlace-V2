"""
Licensing side effects used by the activation API and (later) payment webhooks.
Ported from v1 without the Plugin-sync coupling — activation SKUs are managed via
the admin / legacy import, not synced from a separate Plugin model.
"""
from datetime import timedelta

from django.utils import timezone

from licensing.models import LicenseEvent, ProductPurchase


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
