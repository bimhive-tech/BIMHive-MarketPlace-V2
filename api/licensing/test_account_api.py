"""
Customer account API (/api/account/*) — mainly guarding the entitlement gate:
a signed-in customer must only ever see their own orders/licenses/downloads, and
downloads must only appear for purchases that actually cleared payment.
"""
import pytest
from django.test import Client

from catalog.models import Category, Product
from catalog.models.product import ProductStatus, ProductVisibility
from licensing.models import LicensedProduct, MachineLicense, ProductPurchase

pytestmark = pytest.mark.django_db


@pytest.fixture
def sku():
    return LicensedProduct.objects.create(
        code="bim-oneclick-2024-online", name="BIM OneClick", revit_year="2024",
        default_trial_days=30, is_active=True, price="49.00",
    )


@pytest.fixture
def category():
    return Category.objects.create(name="Revit Plugins")


@pytest.fixture
def free_product(category):
    return Product.objects.create(
        name="Free Sample Tool", short_description="s", description="d", category=category,
        price="0.00", status=ProductStatus.PUBLISHED, visibility=ProductVisibility.PUBLIC,
    )


@pytest.fixture
def paid_product(category):
    return Product.objects.create(
        name="Paid Tool", short_description="s", description="d", category=category,
        price="49.00", status=ProductStatus.PUBLISHED, visibility=ProductVisibility.PUBLIC,
    )


def _login(django_user_model, email="buyer@example.com"):
    user = django_user_model.objects.create_user(username=email, email=email, password="pw12345!")
    client = Client()
    client.force_login(user)
    return user, client


def test_orders_requires_auth(sku):
    resp = Client().get("/api/account/orders")
    assert resp.status_code in (401, 403)


def test_orders_scoped_to_current_user(django_user_model, sku):
    owner, owner_client = _login(django_user_model, "owner@example.com")
    other, _ = _login(django_user_model, "other@example.com")
    ProductPurchase.objects.create(user=owner, product=sku, payment_status=ProductPurchase.PaymentStatus.PAID)
    ProductPurchase.objects.create(user=other, product=sku, payment_status=ProductPurchase.PaymentStatus.PAID)

    resp = owner_client.get("/api/account/orders")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["product_code"] == "bim-oneclick-2024-online"


def test_downloads_excludes_unpaid_purchases(django_user_model, sku):
    user, client = _login(django_user_model)
    ProductPurchase.objects.create(user=user, product=sku, payment_status=ProductPurchase.PaymentStatus.PENDING)

    resp = client.get("/api/account/downloads")
    assert resp.status_code == 200
    assert resp.json() == []


def test_downloads_included_after_payment(django_user_model, sku):
    user, client = _login(django_user_model)
    ProductPurchase.objects.create(user=user, product=sku, payment_status=ProductPurchase.PaymentStatus.PAID)

    resp = client.get("/api/account/downloads")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["product_name"] == "BIM OneClick"
    # sku isn't linked to a catalog.Product in this fixture, so there's no file list to serve
    assert rows[0]["files"] == []


def test_licenses_reports_bound_machines(django_user_model, sku):
    user, client = _login(django_user_model)
    purchase = ProductPurchase.objects.create(
        user=user, product=sku, payment_status=ProductPurchase.PaymentStatus.PAID
    )
    MachineLicense.objects.create(
        product=sku, user=user, purchase=purchase,
        machine_fingerprint_hash="ABCDEF0123456789", status="active",
        started_at="2026-01-01T00:00:00Z", expires_at="2027-01-01T00:00:00Z",
    )

    resp = client.get("/api/account/licenses")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 1
    assert len(rows[0]["machines"]) == 1
    assert rows[0]["machines"][0]["fingerprint_preview"] == "ABCDEF012345…"
    assert rows[0]["machines"][0]["started_at"] == "2026-01-01T00:00:00Z"


# ── Subscriptions (the recurring-priced slice of a customer's purchases) ──
def test_subscriptions_requires_auth(sku):
    resp = Client().get("/api/account/subscriptions")
    assert resp.status_code in (401, 403)


def test_subscriptions_excludes_one_time_purchases(django_user_model, sku):
    user, client = _login(django_user_model)
    ProductPurchase.objects.create(user=user, product=sku, payment_status=ProductPurchase.PaymentStatus.PAID)

    resp = client.get("/api/account/subscriptions")
    assert resp.status_code == 200
    assert resp.json() == []


def test_subscriptions_includes_billing_period_purchases(django_user_model, sku):
    from datetime import timedelta

    from django.utils import timezone

    user, client = _login(django_user_model)
    ProductPurchase.objects.create(
        user=user, product=sku, payment_status=ProductPurchase.PaymentStatus.PAID,
        billing_period=ProductPurchase.BillingPeriod.MONTHLY,
        expires_at=timezone.now() + timedelta(days=20),
    )

    resp = client.get("/api/account/subscriptions")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["billing_period"] == "monthly"
    assert rows[0]["license_status"] == "active"
    assert rows[0]["is_expiring_soon"] is False


def test_subscriptions_flags_one_expiring_within_three_days(django_user_model, sku):
    from datetime import timedelta

    from django.utils import timezone

    user, client = _login(django_user_model)
    ProductPurchase.objects.create(
        user=user, product=sku, payment_status=ProductPurchase.PaymentStatus.PAID,
        billing_period=ProductPurchase.BillingPeriod.YEARLY,
        expires_at=timezone.now() + timedelta(days=1),
    )

    resp = client.get("/api/account/subscriptions")
    assert resp.json()[0]["is_expiring_soon"] is True


def test_subscriptions_scoped_to_current_user(django_user_model, sku):
    owner, owner_client = _login(django_user_model, "owner@example.com")
    other, _ = _login(django_user_model, "other@example.com")
    ProductPurchase.objects.create(
        user=owner, product=sku, payment_status=ProductPurchase.PaymentStatus.PAID,
        billing_period=ProductPurchase.BillingPeriod.MONTHLY,
    )
    ProductPurchase.objects.create(
        user=other, product=sku, payment_status=ProductPurchase.PaymentStatus.PAID,
        billing_period=ProductPurchase.BillingPeriod.MONTHLY,
    )

    resp = owner_client.get("/api/account/subscriptions")
    assert len(resp.json()) == 1


# ── Payment methods (real usage history, not saved cards) ──
def test_payment_methods_requires_auth(sku):
    resp = Client().get("/api/account/payment-methods")
    assert resp.status_code in (401, 403)


def test_payment_methods_excludes_purchases_with_no_captured_card(django_user_model, sku):
    user, client = _login(django_user_model)
    ProductPurchase.objects.create(user=user, product=sku, payment_status=ProductPurchase.PaymentStatus.PAID)

    resp = client.get("/api/account/payment-methods")
    assert resp.status_code == 200
    assert resp.json() == []


def test_payment_methods_groups_by_brand_and_last4(django_user_model, sku):
    user, client = _login(django_user_model)
    ProductPurchase.objects.create(
        user=user, product=sku, payment_status=ProductPurchase.PaymentStatus.PAID,
        card_brand="MasterCard", card_last4="1234",
    )
    ProductPurchase.objects.create(
        user=user, product=sku, payment_status=ProductPurchase.PaymentStatus.PAID,
        card_brand="MasterCard", card_last4="1234",
    )
    ProductPurchase.objects.create(
        user=user, product=sku, payment_status=ProductPurchase.PaymentStatus.PAID,
        card_brand="Visa", card_last4="9999",
    )

    resp = client.get("/api/account/payment-methods")
    rows = resp.json()
    assert len(rows) == 2
    mastercard = next(r for r in rows if r["card_brand"] == "MasterCard")
    assert mastercard["times_used"] == 2


def test_payment_methods_scoped_to_current_user(django_user_model, sku):
    owner, owner_client = _login(django_user_model, "owner@example.com")
    other, _ = _login(django_user_model, "other@example.com")
    ProductPurchase.objects.create(
        user=owner, product=sku, payment_status=ProductPurchase.PaymentStatus.PAID,
        card_brand="Visa", card_last4="1111",
    )
    ProductPurchase.objects.create(
        user=other, product=sku, payment_status=ProductPurchase.PaymentStatus.PAID,
        card_brand="Visa", card_last4="2222",
    )

    resp = owner_client.get("/api/account/payment-methods")
    assert len(resp.json()) == 1


# ── Claiming a free product (the no-checkout acquisition path) ──
def _claim(client, slug):
    return client.post("/api/account/claim-free", data={"slug": slug}, content_type="application/json")


def test_claim_free_requires_auth(free_product):
    resp = _claim(Client(), free_product.slug)
    assert resp.status_code in (401, 403)


def test_claim_free_grants_a_paid_zero_amount_purchase(django_user_model, free_product):
    user, client = _login(django_user_model)
    resp = _claim(client, free_product.slug)
    assert resp.status_code == 201

    purchase = ProductPurchase.objects.get(user=user)
    assert purchase.payment_status == ProductPurchase.PaymentStatus.PAID
    assert purchase.amount == 0
    assert purchase.product.code == free_product.product_code

    # And it actually shows up as a real download, same as a paid purchase would.
    downloads = client.get("/api/account/downloads").json()
    assert len(downloads) == 1
    assert downloads[0]["product_name"] == free_product.name


def test_claim_free_is_idempotent(django_user_model, free_product):
    user, client = _login(django_user_model)
    first = _claim(client, free_product.slug)
    second = _claim(client, free_product.slug)
    assert first.status_code == 201
    assert second.status_code == 200
    assert ProductPurchase.objects.filter(user=user).count() == 1


def test_claim_free_rejects_a_paid_product(django_user_model, paid_product):
    _, client = _login(django_user_model)
    resp = _claim(client, paid_product.slug)
    assert resp.status_code == 400
    assert not ProductPurchase.objects.exists()


def test_claim_free_rejects_unpublished_product(django_user_model, category):
    _, client = _login(django_user_model)
    draft = Product.objects.create(
        name="Draft Free Tool", short_description="s", description="d", category=category,
        price="0.00", status=ProductStatus.DRAFT,
    )
    resp = _claim(client, draft.slug)
    assert resp.status_code == 400
    assert not ProductPurchase.objects.exists()
