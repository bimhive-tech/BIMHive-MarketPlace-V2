"""
Customer account API (/api/account/*) — mainly guarding the entitlement gate:
a signed-in customer must only ever see their own orders/licenses/downloads, and
downloads must only appear for purchases that actually cleared payment.
"""
import pytest
from django.test import Client

from licensing.models import LicensedProduct, MachineLicense, ProductPurchase

pytestmark = pytest.mark.django_db


@pytest.fixture
def sku():
    return LicensedProduct.objects.create(
        code="bim-oneclick-2024-online", name="BIM OneClick", revit_year="2024",
        default_trial_days=30, is_active=True, price="49.00",
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
