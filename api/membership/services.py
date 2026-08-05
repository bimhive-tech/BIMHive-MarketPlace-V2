"""
Where a membership turns into an actual license.

The desktop plugins know nothing about memberships — they send a product code
and a key to /api/license/activate exactly as they always have. This module is
the translation layer: when the key presented is a membership's universal key,
it mints (or refreshes) an ordinary ProductPurchase owned by that membership for
the product being activated, and hands it back. Everything downstream —
seats, machine binding, blocking, downloads — then behaves identically to a
purchase made through checkout, because it *is* one.

That also makes revocation trivial: killing the membership walks the purchases
it created and revokes each one through the same
licensing.services.revoke_purchase_access staff already use.
"""
from datetime import timedelta
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from licensing.models import LicensedProduct, ProductPurchase
from licensing.services import revoke_purchase_access
from membership.models import Membership

# How long a paid billing period runs for. Mirrors licensing.services
# .subscription_duration, but kept separate on purpose: that one still carries a
# TEMPORARY 10-minute monthly override for payment testing, which must not
# silently apply to memberships.
BILLING_DURATIONS = {
    Membership.BillingPeriod.MONTHLY: timedelta(days=30),
    Membership.BillingPeriod.YEARLY: timedelta(days=365),
}


def membership_expiry(billing_period, start):
    duration = BILLING_DURATIONS.get(billing_period)
    return start + duration if duration else None


def active_membership_for(user):
    """The membership currently granting `user` access, or None. The best plan
    wins if somehow more than one is active (e.g. a mid-cycle upgrade)."""
    if not user or not user.is_authenticated:
        return None
    return (
        Membership.objects.active().filter(user=user).select_related("plan").order_by("-plan__rank").first()
    )


def membership_for_key(license_key):
    """The membership a presented key belongs to, usable or not.

    Returns even an inactive one so the activation endpoint can answer
    "expired"/"cancelled" rather than the misleading "unknown key".
    """
    if not license_key:
        return None
    return (
        Membership.objects.select_related("plan", "user").filter(license_key__iexact=license_key.strip()).first()
    )


def resolve_membership_purchase(membership, licensed_product):
    """The ProductPurchase that lets `membership` activate `licensed_product`.

    None when the plan simply doesn't include that product — a wrong-tier key is
    no more valid than a stranger's. Otherwise the purchase is returned even if
    the membership has since lapsed, so activation can deny with a truthful
    "expired"/"cancelled" instead of a generic "unknown key". What a dead
    membership never does is mint a *new* grant.

    Idempotent and self-healing: called on every activation, it re-stamps the
    purchase's expiry and status from the membership, so a renewal or a
    cancellation takes effect the next time the plugin phones home, with no
    separate reconciliation pass.
    """
    catalog_product = licensed_product.product
    if catalog_product is None or not membership.plan.covers_plan(catalog_product.membership_plan):
        return None

    existing = ProductPurchase.objects.filter(
        user=membership.user, product=licensed_product, source_membership=membership
    ).first()
    if existing is None:
        if not membership.is_usable:
            return None
        existing = _get_or_create_membership_purchase(membership, licensed_product)

    _sync_purchase_to_membership(existing, membership)
    return existing


def _get_or_create_membership_purchase(membership, licensed_product):
    try:
        with transaction.atomic():
            purchase, _ = ProductPurchase.objects.get_or_create(
                user=membership.user,
                product=licensed_product,
                source_membership=membership,
                defaults={
                    "payment_status": ProductPurchase.PaymentStatus.PAID,
                    # The membership was paid for, not this product — pricing
                    # it at the product's list price would inflate revenue
                    # reporting, which sums `amount` over paid purchases.
                    "amount": Decimal("0.00"),
                    "currency": membership.currency,
                    "seats": membership.plan.seats_per_product,
                    "expires_at": membership.expires_at,
                },
            )
            return purchase
    except IntegrityError:
        # Two activations for the same product landed at once; the loser reads
        # back the row the winner committed.
        return ProductPurchase.objects.get(
            user=membership.user, product=licensed_product, source_membership=membership
        )


def _sync_purchase_to_membership(purchase, membership):
    """Drags one membership-owned purchase back in line with its membership."""
    if membership.is_usable:
        changed = (
            purchase.expires_at != membership.expires_at
            or purchase.payment_status != ProductPurchase.PaymentStatus.PAID
            or purchase.seats != membership.plan.seats_per_product
        )
        if changed:
            purchase.expires_at = membership.expires_at
            purchase.payment_status = ProductPurchase.PaymentStatus.PAID
            purchase.seats = membership.plan.seats_per_product
            purchase.save()
    elif purchase.payment_status == ProductPurchase.PaymentStatus.PAID:
        revoke_purchase_access(
            purchase,
            status=_purchase_status_for(membership.status),
            reason=f"membership_{membership.status}",
        )


def _purchase_status_for(membership_status):
    """A membership's end state, expressed in ProductPurchase's vocabulary, so
    the customer sees a matching reason on the license rather than a generic
    "revoked" for every case."""
    return {
        Membership.Status.REFUNDED: ProductPurchase.PaymentStatus.REFUNDED,
        Membership.Status.CANCELLED: ProductPurchase.PaymentStatus.CANCELLED,
        Membership.Status.EXPIRED: ProductPurchase.PaymentStatus.CANCELLED,
    }.get(membership_status, ProductPurchase.PaymentStatus.REVOKED)


def sync_membership_purchases(membership):
    """Push the membership's current state onto every purchase it minted.

    Called whenever the membership itself changes — payment confirmed, renewed,
    cancelled, refunded, revoked by staff — so access is gained or lost right
    away rather than at the next activation.
    """
    for purchase in membership.granted_purchases.select_related("product"):
        _sync_purchase_to_membership(purchase, membership)
    return membership


def activate_membership(membership, event_time=None, card_brand="", card_last4=""):
    """Confirm payment: start the clock and open up every covered product.

    Renewing an already-active membership extends from its current expiry
    rather than from now, so paying early never costs the customer days.
    """
    event_time = event_time or timezone.now()
    extend_from = (
        membership.expires_at
        if membership.expires_at and membership.expires_at > event_time
        else event_time
    )

    membership.status = Membership.Status.ACTIVE
    membership.started_at = membership.started_at or event_time
    membership.expires_at = membership_expiry(membership.billing_period, extend_from)
    if card_brand or card_last4:
        membership.card_brand = card_brand
        membership.card_last4 = card_last4
    membership.save()

    return sync_membership_purchases(membership)


def end_membership(membership, status, event_time=None):
    """Stop a membership (cancel / refund / staff revoke) and pull access to
    every product it was opening. One switch — that's the point of the universal
    key."""
    membership.status = status
    membership.cancelled_at = event_time or timezone.now()
    membership.save()
    return sync_membership_purchases(membership)


def has_entitlement(user, catalog_product):
    """Whether `user` may download `catalog_product` right now.

    Two independent routes: a paid purchase of the product itself, or an active
    All-Access membership whose plan covers it. The membership route matters
    before any activation has happened — a member should find their products on
    /account/downloads immediately, not only after a plugin has phoned home and
    minted the backing purchase.
    """
    if not user or not user.is_authenticated:
        return False
    owned = ProductPurchase.objects.filter(
        user=user,
        product__product=catalog_product,
        payment_status=ProductPurchase.PaymentStatus.PAID,
    ).exists()
    if owned:
        return True
    membership = active_membership_for(user)
    return bool(membership and membership.covers(catalog_product))


def entitled_products(user):
    """Every published product `user` can download, from both routes above."""
    from catalog.models import Product

    if not user or not user.is_authenticated:
        return Product.objects.none()

    purchased = Product.objects.published().filter(
        license_skus__purchases__user=user,
        license_skus__purchases__payment_status=ProductPurchase.PaymentStatus.PAID,
    )
    membership = active_membership_for(user)
    included = covered_products(membership.plan) if membership else Product.objects.none()
    return (purchased | included).distinct().select_related("membership_plan").prefetch_related("files")


def covered_products(plan):
    """The published products a given plan includes, best-known ordering."""
    from catalog.models import Product

    if plan is None:
        return Product.objects.none()
    return (
        Product.objects.published()
        .filter(membership_plan__isnull=False, membership_plan__rank__lte=plan.rank)
        .select_related("category", "partner", "membership_plan")
    )


def sync_licensed_products_for(membership):
    """Every activation SKU the membership's plan covers — used by the account
    page to show what the universal key actually opens."""
    return LicensedProduct.objects.filter(
        is_active=True, product__in=covered_products(membership.plan)
    ).select_related("product")
