"""
Self-service cancel/refund (see licensing/account_api.py::AccountOrderRefundView)
gives the buy box's existing "30-Day Money Back Guarantee" copy an actual
mechanism. The test worth taking seriously here isn't the refund itself —
it's proving a refunded purchase's machine can never come back for a
second free trial or quietly reactivate. That guarantee isn't new code;
it falls out of MachineLicense rows never being deleted (only their status
changes) and /api/license/activate only ever issuing a trial when no such
row exists yet — see licensing/tests.py for the activation contract itself.
"""
import json
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone

from catalog.models import Category, Product
from catalog.models.product import ProductStatus
from licensing.models import LicenseEvent, LicensedProduct, MachineLicense, ProductPurchase

pytestmark = pytest.mark.django_db
User = get_user_model()

PEPPER = "test-pepper"
FP = "MACHINE-FINGERPRINT-RAW"


@pytest.fixture(autouse=True)
def _pepper(settings):
    from django.core.cache import cache

    cache.clear()
    settings.LICENSE_PEPPER = PEPPER


@pytest.fixture
def category():
    return Category.objects.create(name="Revit Plugins")


@pytest.fixture
def buyer_and_purchase(category):
    product = Product.objects.create(
        name="Refund Test", product_code="refund-test", category=category,
        short_description="s", description="d", status=ProductStatus.PUBLISHED, price="49.00",
    )
    sku = LicensedProduct.objects.get(code=product.product_code)
    user = User.objects.create_user(username="buyer@x.com", email="buyer@x.com", password="x")
    purchase = ProductPurchase.objects.create(
        user=user, product=sku, payment_status=ProductPurchase.PaymentStatus.PAID,
    )
    return user, product, purchase


def _refund(client, purchase_id):
    return client.post(f"/api/account/orders/{purchase_id}/refund")


def _activate(**body):
    return Client().post("/api/license/activate", data=json.dumps(body), content_type="application/json")


def test_refund_marks_the_purchase_refunded(buyer_and_purchase):
    user, _, purchase = buyer_and_purchase
    client = Client()
    client.force_login(user)

    resp = _refund(client, purchase.pk)
    assert resp.status_code == 200, resp.json()

    purchase.refresh_from_db()
    assert purchase.payment_status == ProductPurchase.PaymentStatus.REFUNDED


def test_refund_requires_login(buyer_and_purchase):
    _, _, purchase = buyer_and_purchase
    resp = _refund(Client(), purchase.pk)
    assert resp.status_code in (401, 403)


def test_cannot_refund_someone_elses_order(buyer_and_purchase):
    _, _, purchase = buyer_and_purchase
    other = User.objects.create_user(username="other@x.com", email="other@x.com", password="x")
    client = Client()
    client.force_login(other)

    resp = _refund(client, purchase.pk)
    assert resp.status_code == 400


def test_cannot_refund_an_already_refunded_order(buyer_and_purchase):
    user, _, purchase = buyer_and_purchase
    client = Client()
    client.force_login(user)
    _refund(client, purchase.pk)

    resp = _refund(client, purchase.pk)
    assert resp.status_code == 400


def test_cannot_refund_outside_the_30_day_window(buyer_and_purchase):
    user, _, purchase = buyer_and_purchase
    purchase.paid_at = timezone.now() - timedelta(days=31)
    purchase.save(update_fields=["paid_at"])
    client = Client()
    client.force_login(user)

    resp = _refund(client, purchase.pk)
    assert resp.status_code == 400
    assert "30-day" in resp.json()["detail"]


def test_refunding_a_purchase_denies_the_machine_that_had_it(buyer_and_purchase):
    user, product, purchase = buyer_and_purchase
    activate_resp = _activate(productCode=product.product_code, machineFingerprintHash=FP, licenseKey=purchase.license_key)
    assert activate_resp.json()["authorized"] is True

    client = Client()
    client.force_login(user)
    _refund(client, purchase.pk)

    denied = _activate(productCode=product.product_code, machineFingerprintHash=FP, licenseKey=purchase.license_key)
    body = denied.json()
    assert body["authorized"] is False
    assert body["status"] == "cancelled"  # ProductPurchase.denial_status collapses refunded -> "cancelled"
    assert "refunded" in body["message"].lower()


def test_refunding_does_not_hand_the_same_machine_a_fresh_trial(buyer_and_purchase):
    """The abuse case: activate with a real key, refund, then try activating
    again with NO key at all (as if hoping for a brand-new trial). Must
    still be denied — never a fresh 'Trial activated' response."""
    user, product, purchase = buyer_and_purchase
    _activate(productCode=product.product_code, machineFingerprintHash=FP, licenseKey=purchase.license_key)

    client = Client()
    client.force_login(user)
    _refund(client, purchase.pk)

    retried_without_key = _activate(productCode=product.product_code, machineFingerprintHash=FP)
    body = retried_without_key.json()
    assert body["authorized"] is False
    assert body["status"] != "active"  # "active" is the trial-issued status — must never see it again
    assert MachineLicense.objects.filter(product__code=product.product_code).count() == 1  # no new row created


def test_a_different_machine_is_unaffected_by_someone_elses_refund(buyer_and_purchase):
    user, product, purchase = buyer_and_purchase
    _activate(productCode=product.product_code, machineFingerprintHash=FP, licenseKey=purchase.license_key)

    client = Client()
    client.force_login(user)
    _refund(client, purchase.pk)

    fresh_machine = _activate(productCode=product.product_code, machineFingerprintHash="A-DIFFERENT-MACHINE")
    body = fresh_machine.json()
    assert body["authorized"] is True
    assert body["status"] == "active"  # a genuinely new machine still gets its own trial


def test_refund_logs_a_license_event_for_the_bound_machine(buyer_and_purchase):
    user, product, purchase = buyer_and_purchase
    _activate(productCode=product.product_code, machineFingerprintHash=FP, licenseKey=purchase.license_key)

    client = Client()
    client.force_login(user)
    _refund(client, purchase.pk)

    assert LicenseEvent.objects.filter(product__code=product.product_code, event_type="purchase_revoked").exists()
