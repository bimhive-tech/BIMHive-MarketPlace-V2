"""
The one place a product's *sale* price is worked out.

Every surface that shows or charges a price goes through here — the storefront
serializers, the cart, and checkout — so a discount can never be real on the
page and missing at the till (or the other way round).
"""
from catalog.models.promotion import Promotion, apply_discount


def live_promotions():
    """Every promotion currently inside its window, best offer first.

    Fetched as a list (not a lazy queryset) because pricing a grid asks the same
    question once per product; `products` is prefetched so a product-scoped
    promotion doesn't cost a query per row.
    """
    return list(Promotion.objects.live().select_related("category").prefetch_related("products"))


def promotion_for(product, promotions=None):
    """The live promotion that covers `product`, or None.

    When several apply, the customer gets the biggest discount — anything else
    would be a worse price than one they were shown somewhere on the site.
    """
    candidates = [p for p in (promotions if promotions is not None else live_promotions()) if p.covers(product)]
    return max(candidates, key=lambda p: p.discount_percent, default=None)


def banner_promotion():
    """The promotion the countdown bar should show, or None. Ordering is the
    model's (priority, then ending soonest)."""
    return Promotion.objects.live().filter(show_countdown=True).first()


def sale_prices(product, promotion):
    """`product`'s prices with `promotion` applied, as a dict matching the
    product's own price fields. Empty dict when nothing is on offer."""
    if promotion is None:
        return {}
    return {
        "price": apply_discount(product.price, promotion.discount_percent),
        "monthly_price": apply_discount(product.monthly_price, promotion.discount_percent),
        "yearly_price": apply_discount(product.yearly_price, promotion.discount_percent),
    }


def unit_price_for(product, billing_period, promotion=None):
    """What one unit of `product` actually costs on `billing_period` right now,
    discount included. Returns None when the product isn't sold that way.

    Checkout calls this instead of reading product.price directly, so the price
    charged is always the one the storefront advertised — and is recomputed
    server-side rather than trusted from the client's cart.
    """
    from licensing.models import ProductPurchase

    if billing_period == ProductPurchase.BillingPeriod.MONTHLY:
        list_price = product.monthly_price
    elif billing_period == ProductPurchase.BillingPeriod.YEARLY:
        list_price = product.yearly_price
    else:
        list_price = product.price
    if list_price is None:
        return None
    if promotion is None:
        promotion = promotion_for(product)
    return apply_discount(list_price, promotion.discount_percent) if promotion else list_price
