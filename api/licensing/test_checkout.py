"""
Test checkout — no payment processor connected yet, so this is the honest
interim way to turn a cart into real ProductPurchase rows (see
licensing/account_api.py::CheckoutView). The main behavior worth locking in:
one purchase per unit bought — buying qty=3 of the same product creates
three independent purchases, each its own license_key, seats=1. One key
per seat, deliberately, so each copy activates its own machine.
"""
import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from catalog.models import Category, Product
from catalog.models.product import ProductStatus
from licensing.models import ProductPurchase

pytestmark = pytest.mark.django_db
User = get_user_model()


@pytest.fixture
def category():
    return Category.objects.create(name="Revit Plugins")


@pytest.fixture
def product(category):
    return Product.objects.create(
        name="Checkout Test", product_code="checkout-test", category=category,
        short_description="s", description="d", status=ProductStatus.PUBLISHED,
        price="49.00",
    )


@pytest.fixture
def second_product(category):
    return Product.objects.create(
        name="Second Checkout Test", product_code="checkout-test-2", category=category,
        short_description="s", description="d", status=ProductStatus.PUBLISHED,
        price="19.00",
    )


@pytest.fixture
def buyer_client():
    user = User.objects.create_user(username="buyer@x.com", email="buyer@x.com", password="x")
    client = Client()
    client.force_login(user)
    return client, user


def _checkout(client, items):
    return client.post("/api/account/checkout", data={"items": items}, content_type="application/json")


def test_buying_three_of_the_same_product_creates_three_separate_keys(buyer_client, product):
    client, user = buyer_client
    resp = _checkout(client, [{"slug": product.slug, "qty": 3}])
    assert resp.status_code == 201, resp.json()

    purchases = list(ProductPurchase.objects.filter(user=user, product__product=product))
    assert len(purchases) == 3
    assert len({p.license_key for p in purchases}) == 3  # every key is distinct
    for purchase in purchases:
        assert purchase.seats == 1
        assert purchase.payment_status == ProductPurchase.PaymentStatus.PAID
        assert str(purchase.amount) == "49.00"  # unit price, not qty * price


def test_checkout_creates_one_purchase_per_unit_across_distinct_products(buyer_client, product, second_product):
    client, user = buyer_client
    resp = _checkout(client, [{"slug": product.slug, "qty": 1}, {"slug": second_product.slug, "qty": 2}])
    assert resp.status_code == 201, resp.json()
    assert ProductPurchase.objects.filter(user=user, product__product=product).count() == 1
    assert ProductPurchase.objects.filter(user=user, product__product=second_product).count() == 2


def test_checking_out_again_adds_more_separate_purchases(buyer_client, product):
    client, user = buyer_client
    _checkout(client, [{"slug": product.slug, "qty": 1}])
    resp = _checkout(client, [{"slug": product.slug, "qty": 2}])
    assert resp.status_code == 201, resp.json()

    purchases = list(ProductPurchase.objects.filter(user=user, product__product=product))
    assert len(purchases) == 3  # 1 from the first checkout + 2 from the second
    assert len({p.license_key for p in purchases}) == 3


def test_checkout_requires_login(product):
    resp = _checkout(Client(), [{"slug": product.slug, "qty": 1}])
    assert resp.status_code in (401, 403)


def test_checkout_rejects_an_empty_cart(buyer_client):
    client, _ = buyer_client
    resp = _checkout(client, [])
    assert resp.status_code == 400


def test_checkout_rejects_an_unknown_slug(buyer_client):
    client, _ = buyer_client
    resp = _checkout(client, [{"slug": "does-not-exist", "qty": 1}])
    assert resp.status_code == 400


def test_checkout_rejects_an_unpublished_product(buyer_client, category):
    draft = Product.objects.create(
        name="Draft Checkout Test", product_code="draft-checkout-test", category=category,
        short_description="s", description="d", status=ProductStatus.DRAFT, price="10.00",
    )
    client, _ = buyer_client
    resp = _checkout(client, [{"slug": draft.slug, "qty": 1}])
    assert resp.status_code == 400


def test_checkout_works_for_a_free_product_too(buyer_client, category):
    free_product = Product.objects.create(
        name="Free Checkout Test", product_code="free-checkout-test", category=category,
        short_description="s", description="d", status=ProductStatus.PUBLISHED, price="0.00",
    )
    client, user = buyer_client
    resp = _checkout(client, [{"slug": free_product.slug, "qty": 1}])
    assert resp.status_code == 201, resp.json()
    purchase = ProductPurchase.objects.get(user=user, product__product=free_product)
    assert purchase.payment_status == ProductPurchase.PaymentStatus.PAID
    assert str(purchase.amount) == "0.00"


# ── Subscription (monthly/yearly) checkout ──
@pytest.fixture
def subscription_product(category):
    return Product.objects.create(
        name="Subscription Test", product_code="subscription-test", category=category,
        short_description="s", description="d", status=ProductStatus.PUBLISHED,
        price="0.00", monthly_price="19.00", yearly_price="179.00",
    )


def test_monthly_checkout_uses_monthly_price_and_expires_in_30_days(buyer_client, subscription_product):
    from datetime import timedelta

    from django.utils import timezone

    client, user = buyer_client
    resp = _checkout(client, [{"slug": subscription_product.slug, "qty": 1, "billingPeriod": "monthly"}])
    assert resp.status_code == 201, resp.json()

    purchase = ProductPurchase.objects.get(user=user, product__product=subscription_product)
    assert str(purchase.amount) == "19.00"
    assert purchase.billing_period == "monthly"
    assert purchase.expires_at is not None
    assert abs((purchase.expires_at - timezone.now()) - timedelta(days=30)) < timedelta(minutes=1)


def test_yearly_checkout_uses_yearly_price_and_expires_in_365_days(buyer_client, subscription_product):
    from datetime import timedelta

    from django.utils import timezone

    client, user = buyer_client
    resp = _checkout(client, [{"slug": subscription_product.slug, "qty": 1, "billingPeriod": "yearly"}])
    assert resp.status_code == 201, resp.json()

    purchase = ProductPurchase.objects.get(user=user, product__product=subscription_product)
    assert str(purchase.amount) == "179.00"
    assert purchase.billing_period == "yearly"
    assert abs((purchase.expires_at - timezone.now()) - timedelta(days=365)) < timedelta(minutes=1)


def test_checkout_rejects_a_billing_period_for_a_non_subscription_product(buyer_client, product):
    client, _ = buyer_client
    resp = _checkout(client, [{"slug": product.slug, "qty": 1, "billingPeriod": "monthly"}])
    assert resp.status_code == 400


def test_checkout_rejects_an_invalid_billing_period(buyer_client, subscription_product):
    client, _ = buyer_client
    resp = _checkout(client, [{"slug": subscription_product.slug, "qty": 1, "billingPeriod": "weekly"}])
    assert resp.status_code == 400


def test_one_time_checkout_of_a_subscription_product_falls_back_to_the_one_time_price(buyer_client, category):
    # A subscription product can still list a one-time price too — omitting
    # billingPeriod entirely just buys it outright, perpetual, same as any
    # other product.
    hybrid = Product.objects.create(
        name="Hybrid Pricing Test", product_code="hybrid-pricing-test", category=category,
        short_description="s", description="d", status=ProductStatus.PUBLISHED,
        price="99.00", monthly_price="9.00", yearly_price="89.00",
    )
    client, user = buyer_client
    resp = _checkout(client, [{"slug": hybrid.slug, "qty": 1}])
    assert resp.status_code == 201, resp.json()
    purchase = ProductPurchase.objects.get(user=user, product__product=hybrid)
    assert str(purchase.amount) == "99.00"
    assert purchase.billing_period == ""
    assert purchase.expires_at is None
