"""
Time-boxed discounts and the countdown banner (catalog/models/promotion.py,
catalog/pricing.py) — including that checkout charges the discounted price
rather than whatever the client's cart claims.
"""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from catalog.models import Category, Product, Promotion
from catalog.models.product import ProductStatus
from catalog.pricing import live_plan_promotion, plan_unit_price_for, promotion_for, unit_price_for
from licensing.models import ProductPurchase
from membership.models import MembershipPlan

pytestmark = pytest.mark.django_db
User = get_user_model()


@pytest.fixture
def root():
    return Category.objects.create(name="Revit Plugins")


@pytest.fixture
def staff_client(client):
    user = User.objects.create_user(username="admin@x.com", email="admin@x.com", password="x", is_staff=True)
    client.force_login(user)
    return client


@pytest.fixture
def product(root):
    return Product.objects.create(
        name="Sheet Machine", short_description="s", description="d",
        category=root, price="100.00", status=ProductStatus.PUBLISHED,
    )


@pytest.fixture
def plan():
    return MembershipPlan.objects.create(
        name="Pro", rank=2, monthly_price="39.00", yearly_price="390.00"
    )


def make_promotion(**overrides):
    now = timezone.now()
    return Promotion.objects.create(
        **{
            "name": "Launch week",
            "headline": "This price won't last long...",
            "discount_percent": 40,
            "starts_at": now - timedelta(hours=1),
            "ends_at": now + timedelta(days=2),
            **overrides,
        }
    )


# ── Window ──
def test_a_promotion_outside_its_window_does_not_apply(product):
    make_promotion(starts_at=timezone.now() + timedelta(days=1), ends_at=timezone.now() + timedelta(days=3))
    assert promotion_for(product) is None


def test_an_expired_promotion_does_not_apply(product):
    make_promotion(starts_at=timezone.now() - timedelta(days=3), ends_at=timezone.now() - timedelta(minutes=1))
    assert promotion_for(product) is None


def test_a_deactivated_promotion_does_not_apply(product):
    make_promotion(is_active=False)
    assert promotion_for(product) is None


# ── Scope ──
def test_category_scope_includes_subcategory_products(root):
    child = Category.objects.create(name="Sheets", parent=root)
    nested = Product.objects.create(
        name="Nested", short_description="s", description="d",
        category=child, price="50.00", status=ProductStatus.PUBLISHED,
    )
    make_promotion(scope=Promotion.Scope.CATEGORY, category=root)

    assert promotion_for(nested) is not None


def test_product_scope_only_covers_the_listed_products(root, product):
    other = Product.objects.create(
        name="Other", short_description="s", description="d",
        category=root, price="20.00", status=ProductStatus.PUBLISHED,
    )
    promo = make_promotion(scope=Promotion.Scope.PRODUCTS)
    promo.products.add(product)

    assert promotion_for(product) is not None
    assert promotion_for(other) is None


def test_the_biggest_discount_wins_when_two_promotions_overlap(product):
    make_promotion(name="Small", discount_percent=10)
    make_promotion(name="Big", discount_percent=55)

    assert promotion_for(product).discount_percent == 55


# ── Pricing ──
def test_sale_price_is_rounded_to_cents(product):
    make_promotion(discount_percent=33)

    assert unit_price_for(product, "") == Decimal("67.00")


def test_subscription_prices_are_discounted_too(root):
    product = Product.objects.create(
        name="Subbed", short_description="s", description="d", category=root,
        price="0.00", monthly_price="10.00", yearly_price="100.00",
        status=ProductStatus.PUBLISHED,
    )
    make_promotion(discount_percent=50)

    assert unit_price_for(product, ProductPurchase.BillingPeriod.MONTHLY) == Decimal("5.00")
    assert unit_price_for(product, ProductPurchase.BillingPeriod.YEARLY) == Decimal("50.00")


# ── Storefront API ──
def test_product_card_reports_the_live_promotion(client, product):
    make_promotion(discount_percent=25, badge_label="SPECIAL OFFER")

    card = client.get("/api/products").json()["results"][0]

    assert card["price"] == "100.00", "list price stays intact for the struck-through display"
    assert card["promotion"]["price"] == "75.00"
    assert card["promotion"]["discount_percent"] == 25
    assert card["promotion"]["label"] == "SPECIAL OFFER"


def test_product_without_a_promotion_reports_none(client, product):
    card = client.get("/api/products").json()["results"][0]
    assert card["promotion"] is None


def test_banner_endpoint_returns_the_live_plan_promotion(client, plan):
    make_promotion(headline="Ends soon", scope=Promotion.Scope.PLAN, plan=plan)

    body = client.get("/api/promotions/banner").json()["promotion"]
    assert body["headline"] == "Ends soon"
    assert body["plan_name"] == "Pro"


def test_banner_endpoint_is_null_when_nothing_is_running(client, plan):
    make_promotion(scope=Promotion.Scope.PLAN, plan=plan, show_countdown=False)

    assert client.get("/api/promotions/banner").json()["promotion"] is None


def test_banner_endpoint_ignores_a_product_scoped_promotion_even_with_show_countdown(client, product):
    """The banner is plan-only, full stop — a sitewide product discount
    (however it was flagged) must never surface there."""
    make_promotion(scope=Promotion.Scope.ALL, show_countdown=True)

    assert client.get("/api/promotions/banner").json()["promotion"] is None


# ── Plan-scoped promotions ──
def test_a_plan_promotion_discounts_the_plan_not_any_product(client, product, plan):
    make_promotion(scope=Promotion.Scope.PLAN, plan=plan, discount_percent=20)

    assert promotion_for(product) is None
    assert live_plan_promotion(plan) is not None


def test_plan_promotion_discounts_both_billing_intervals(plan):
    from membership.models import Membership

    make_promotion(scope=Promotion.Scope.PLAN, plan=plan, discount_percent=50)

    assert plan_unit_price_for(plan, Membership.BillingPeriod.MONTHLY) == Decimal("19.50")
    assert plan_unit_price_for(plan, Membership.BillingPeriod.YEARLY) == Decimal("195.00")


def test_a_promotion_on_one_plan_does_not_discount_another(plan):
    from membership.models import Membership

    other_plan = MembershipPlan.objects.create(name="Standard", rank=1, monthly_price="19.00")
    make_promotion(scope=Promotion.Scope.PLAN, plan=plan, discount_percent=50)

    assert live_plan_promotion(other_plan) is None
    assert Decimal(plan_unit_price_for(other_plan, Membership.BillingPeriod.MONTHLY)) == Decimal("19.00")


def test_membership_plans_endpoint_reports_the_live_discount(client, plan):
    make_promotion(scope=Promotion.Scope.PLAN, plan=plan, discount_percent=25)

    body = client.get("/api/membership/plans").json()["plans"][0]

    assert body["promotion"]["discount_percent"] == 25
    assert body["promotion"]["monthly_price"] == "29.25"


def test_membership_checkout_charges_the_discounted_price(client, plan, monkeypatch):
    make_promotion(scope=Promotion.Scope.PLAN, plan=plan, discount_percent=50)
    user = User.objects.create_user(username="m@x.com", email="m@x.com", password="x")
    client.force_login(user)
    monkeypatch.setattr("licensing.paymob.create_intention", lambda **kwargs: {"client_secret": "secret"})
    monkeypatch.setattr("licensing.paymob.checkout_url", lambda secret: "https://pay.test/x")

    resp = client.post(
        "/api/account/membership/checkout",
        {"plan": plan.slug, "billingPeriod": "monthly"},
        content_type="application/json",
    )

    assert resp.status_code == 201, resp.json()
    from membership.models import Membership

    membership = Membership.objects.get(user=user)
    assert membership.amount == Decimal("19.50")


# ── Admin validation ──
def test_admin_promotion_requires_a_plan_for_plan_scope(staff_client):
    now = timezone.now()
    resp = staff_client.post(
        "/api/admin/promotions",
        {
            "name": "No plan", "headline": "x", "discount_percent": 10, "scope": "plan",
            "starts_at": now.isoformat(), "ends_at": (now + timedelta(days=1)).isoformat(),
        },
        content_type="application/json",
    )

    assert resp.status_code == 400
    assert "plan" in resp.json()


def test_admin_promotion_rejects_countdown_on_a_non_plan_scope(staff_client, product):
    now = timezone.now()
    resp = staff_client.post(
        "/api/admin/promotions",
        {
            "name": "Not allowed", "headline": "x", "discount_percent": 10, "scope": "all",
            "show_countdown": True,
            "starts_at": now.isoformat(), "ends_at": (now + timedelta(days=1)).isoformat(),
        },
        content_type="application/json",
    )

    assert resp.status_code == 400
    assert "show_countdown" in resp.json()


def test_admin_can_create_a_plan_scoped_promotion(staff_client, plan):
    now = timezone.now()
    resp = staff_client.post(
        "/api/admin/promotions",
        {
            "name": "Pro launch", "headline": "x", "discount_percent": 20, "scope": "plan",
            "plan": plan.id, "show_countdown": True,
            "starts_at": now.isoformat(), "ends_at": (now + timedelta(days=1)).isoformat(),
        },
        content_type="application/json",
    )

    assert resp.status_code == 201, resp.json()
    assert resp.json()["plan_name"] == "Pro"


# ── Cart re-quoting ──
def test_cart_quote_returns_the_current_discounted_price(client, product):
    make_promotion(discount_percent=30)

    body = client.post(
        "/api/cart/quote",
        {"items": [{"slug": product.slug, "billingPeriod": ""}]},
        content_type="application/json",
    ).json()

    assert body["items"] == [
        {
            "slug": product.slug,
            "billing_period": "",
            "unit_price": "70.00",
            "discount_percent": 30,
            "monthly_price": None,
            "yearly_price": None,
        }
    ]


def test_cart_quote_drops_a_line_the_customer_can_no_longer_buy(client, product):
    product.status = ProductStatus.DRAFT
    product.save()

    body = client.post(
        "/api/cart/quote",
        {"items": [{"slug": product.slug, "billingPeriod": ""}]},
        content_type="application/json",
    ).json()

    assert body["items"] == []


def test_cart_quote_reports_list_price_once_the_promotion_has_ended(client, product):
    make_promotion(
        discount_percent=30,
        starts_at=timezone.now() - timedelta(days=2),
        ends_at=timezone.now() - timedelta(seconds=1),
    )

    body = client.post(
        "/api/cart/quote",
        {"items": [{"slug": product.slug, "billingPeriod": ""}]},
        content_type="application/json",
    ).json()

    assert body["items"][0]["unit_price"] == "100.00"
    assert body["items"][0]["discount_percent"] == 0


# ── Admin API ──
def test_admin_can_create_an_all_scope_promotion(staff_client, product):
    now = timezone.now()
    resp = staff_client.post(
        "/api/admin/promotions",
        {
            "name": "Launch",
            "badge_label": "SPECIAL OFFER",
            "headline": "This price won't last long...",
            "discount_percent": 25,
            "scope": "all",
            "starts_at": now.isoformat(),
            "ends_at": (now + timedelta(days=3)).isoformat(),
        },
        content_type="application/json",
    )

    assert resp.status_code == 201, resp.json()
    assert resp.json()["is_live"] is True


def test_admin_promotion_rejects_an_end_before_the_start(staff_client):
    now = timezone.now()
    resp = staff_client.post(
        "/api/admin/promotions",
        {
            "name": "Broken",
            "headline": "x",
            "discount_percent": 10,
            "scope": "all",
            "starts_at": now.isoformat(),
            "ends_at": (now - timedelta(days=1)).isoformat(),
        },
        content_type="application/json",
    )

    assert resp.status_code == 400
    assert "ends_at" in resp.json()


def test_admin_promotion_requires_a_category_for_category_scope(staff_client):
    now = timezone.now()
    resp = staff_client.post(
        "/api/admin/promotions",
        {
            "name": "No category",
            "headline": "x",
            "discount_percent": 10,
            "scope": "category",
            "starts_at": now.isoformat(),
            "ends_at": (now + timedelta(days=1)).isoformat(),
        },
        content_type="application/json",
    )

    assert resp.status_code == 400
    assert "category" in resp.json()


def test_admin_promotion_requires_products_for_product_scope(staff_client):
    now = timezone.now()
    resp = staff_client.post(
        "/api/admin/promotions",
        {
            "name": "No products",
            "headline": "x",
            "discount_percent": 10,
            "scope": "products",
            "starts_at": now.isoformat(),
            "ends_at": (now + timedelta(days=1)).isoformat(),
        },
        content_type="application/json",
    )

    assert resp.status_code == 400
    assert "products" in resp.json()


def test_non_staff_cannot_create_a_promotion(client):
    now = timezone.now()
    resp = client.post(
        "/api/admin/promotions",
        {
            "name": "Nope", "headline": "x", "discount_percent": 10, "scope": "all",
            "starts_at": now.isoformat(), "ends_at": (now + timedelta(days=1)).isoformat(),
        },
        content_type="application/json",
    )

    assert resp.status_code in (401, 403)


# ── Checkout is priced server-side ──
def test_checkout_charges_the_discounted_price_not_the_clients(client, product, settings, monkeypatch):
    make_promotion(discount_percent=60)
    user = User.objects.create_user(username="b@x.com", email="b@x.com", password="x")
    client.force_login(user)
    monkeypatch.setattr(
        "licensing.paymob.create_intention", lambda **kwargs: {"client_secret": "secret"}
    )
    monkeypatch.setattr("licensing.paymob.checkout_url", lambda secret: "https://pay.test/x")

    resp = client.post(
        "/api/account/checkout",
        {"items": [{"slug": product.slug, "qty": 1, "billingPeriod": "", "price": "1.00"}]},
        content_type="application/json",
    )

    assert resp.status_code == 201, resp.json()
    purchase = ProductPurchase.objects.get(user=user)
    assert purchase.amount == Decimal("40.00")
