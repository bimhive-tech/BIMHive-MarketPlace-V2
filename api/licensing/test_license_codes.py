"""
Staff-generated, redeemable license codes — the "upgrade" of the old
installer-generator's manually-issued keys, now connected to the account
system instead of baked into a binary. Covers: code generation/revocation
(admin API), redemption (service + account API), and that a redeemed
time-limited license actually expires and denies activation afterward.
"""
import json
from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone

from catalog.models import Category, Product
from catalog.models.product import ProductStatus
from licensing.models import LicenseCode, LicensedProduct, ProductPurchase
from licensing.services import LicenseCodeError, redeem_license_code

pytestmark = pytest.mark.django_db
User = get_user_model()
PEPPER = "test-pepper"


@pytest.fixture(autouse=True)
def _pepper(settings):
    from django.core.cache import cache

    cache.clear()
    settings.LICENSE_PEPPER = PEPPER


@pytest.fixture
def category():
    return Category.objects.create(name="Revit Plugins")


@pytest.fixture
def sku(category):
    # A nonzero price is deliberate — it's what makes
    # test_redeeming_a_code_creates_a_time_limited_paid_purchase actually
    # exercise the amount-forced-to-zero logic instead of the assertion
    # trivially passing because a free product's price was already 0.
    product = Product.objects.create(
        name="Code Test Plugin", product_code="code-test-plugin", category=category,
        short_description="s", description="d", status=ProductStatus.PUBLISHED,
        price=Decimal("49.00"),
    )
    return LicensedProduct.objects.get(code=product.product_code)


@pytest.fixture
def buyer():
    return User.objects.create_user(username="buyer@x.com", email="buyer@x.com", password="x")


@pytest.fixture
def staff_client():
    staff = User.objects.create_user(username="staff@x.com", email="staff@x.com", password="x", is_staff=True)
    client = Client()
    client.force_login(staff)
    return client


# ── Model ──
def test_code_is_auto_generated(sku):
    code = LicenseCode.objects.create(product=sku)
    assert code.code.startswith("GIFT-")


# ── Redemption service ──
def test_redeeming_a_code_creates_a_time_limited_paid_purchase(sku, buyer):
    code = LicenseCode.objects.create(product=sku, seats=2, duration_days=30)
    purchase = redeem_license_code(code.code, buyer)

    assert purchase.payment_status == ProductPurchase.PaymentStatus.PAID
    assert purchase.seats == 2
    assert purchase.amount == Decimal("0.00")
    assert purchase.expires_at is not None
    assert abs((purchase.expires_at - (timezone.now() + timedelta(days=30))).total_seconds()) < 5

    code.refresh_from_db()
    assert code.status == LicenseCode.Status.REDEEMED
    assert code.redeemed_by_id == buyer.id
    assert code.redeemed_purchase_id == purchase.id


def test_redeeming_a_lifetime_code_leaves_expires_at_null(sku, buyer):
    code = LicenseCode.objects.create(product=sku, seats=1, duration_days=None)
    purchase = redeem_license_code(code.code, buyer)
    assert purchase.expires_at is None
    assert purchase.is_license_active


def test_redeeming_an_unknown_code_fails(buyer):
    with pytest.raises(LicenseCodeError):
        redeem_license_code("NOT-A-REAL-CODE", buyer)


def test_redeeming_an_already_redeemed_code_fails(sku, buyer):
    code = LicenseCode.objects.create(product=sku)
    redeem_license_code(code.code, buyer)
    other = User.objects.create_user(username="other@x.com", email="other@x.com", password="x")
    with pytest.raises(LicenseCodeError):
        redeem_license_code(code.code, other)


def test_redeeming_a_revoked_code_fails(sku, buyer):
    code = LicenseCode.objects.create(product=sku, status=LicenseCode.Status.REVOKED)
    with pytest.raises(LicenseCodeError):
        redeem_license_code(code.code, buyer)


def test_cannot_redeem_a_second_code_while_one_is_already_active(sku, buyer):
    first = LicenseCode.objects.create(product=sku)
    redeem_license_code(first.code, buyer)
    second = LicenseCode.objects.create(product=sku)
    with pytest.raises(LicenseCodeError):
        redeem_license_code(second.code, buyer)


def test_redeeming_a_code_revives_a_lapsed_purchase_with_a_clean_seat_pool(sku, buyer):
    from licensing.models import MachineLicense

    first = LicenseCode.objects.create(product=sku, seats=1, duration_days=1)
    purchase = redeem_license_code(first.code, buyer)
    MachineLicense.objects.create(
        product=sku, user=buyer, purchase=purchase, machine_fingerprint_hash="STALE",
        status="paid", started_at=timezone.now(), expires_at=timezone.now() + timedelta(days=1),
    )
    # Simulate the grant having lapsed.
    purchase.expires_at = timezone.now() - timedelta(days=1)
    purchase.save(update_fields=["expires_at"])
    assert not purchase.is_license_active

    second = LicenseCode.objects.create(product=sku, seats=1, duration_days=30)
    redeem_license_code(second.code, buyer)
    purchase.refresh_from_db()
    assert purchase.is_license_active
    assert purchase.has_seat_for("BRAND-NEW-MACHINE")  # old stale binding no longer eats the fresh seat


# ── Admin API ──
def test_staff_can_generate_a_code(staff_client, sku):
    resp = staff_client.post(
        "/api/admin/license-codes",
        {"product": sku.id, "seats": 3, "duration_days": 90, "note": "for a reviewer"},
    )
    assert resp.status_code == 201, resp.json()
    body = resp.json()
    assert body["seats"] == 3
    assert body["duration_days"] == 90
    assert body["status"] == "unredeemed"
    assert LicenseCode.objects.filter(product=sku).count() == 1


def test_non_staff_cannot_generate_a_code(sku, buyer):
    client = Client()
    client.force_login(buyer)
    resp = client.post("/api/admin/license-codes", {"product": sku.id, "seats": 1})
    assert resp.status_code in (401, 403)


def test_staff_can_revoke_an_unredeemed_code(staff_client, sku):
    code = LicenseCode.objects.create(product=sku)
    resp = staff_client.post(f"/api/admin/license-codes/{code.id}/revoke")
    assert resp.status_code == 200, resp.json()
    code.refresh_from_db()
    assert code.status == LicenseCode.Status.REVOKED


def test_cannot_revoke_an_already_redeemed_code(staff_client, sku, buyer):
    code = LicenseCode.objects.create(product=sku)
    redeem_license_code(code.code, buyer)
    resp = staff_client.post(f"/api/admin/license-codes/{code.id}/revoke")
    assert resp.status_code == 400


# ── Account API ──
def test_customer_can_redeem_a_code_via_the_account_api(sku, buyer):
    code = LicenseCode.objects.create(product=sku, seats=2, duration_days=60)
    client = Client()
    client.force_login(buyer)
    resp = client.post("/api/account/licenses/redeem", {"code": code.code})
    assert resp.status_code == 201, resp.json()
    body = resp.json()
    assert body["seats"] == 2
    assert body["expires_at"] is not None
    assert body["payment_status"] == "paid"


def test_redeeming_an_invalid_code_via_the_account_api_is_a_400(buyer):
    client = Client()
    client.force_login(buyer)
    resp = client.post("/api/account/licenses/redeem", {"code": "BOGUS"})
    assert resp.status_code == 400


def test_anonymous_cannot_redeem(client, sku):
    code = LicenseCode.objects.create(product=sku)
    resp = client.post("/api/account/licenses/redeem", {"code": code.code})
    assert resp.status_code in (401, 403)


# ── Activation respects a redeemed code's expiry ──
def test_activation_is_denied_as_expired_once_a_redeemed_codes_duration_passes(sku, buyer):
    code = LicenseCode.objects.create(product=sku, seats=1, duration_days=30)
    purchase = redeem_license_code(code.code, buyer)
    # Simulate the grant period having elapsed.
    purchase.expires_at = timezone.now() - timedelta(days=1)
    purchase.save(update_fields=["expires_at"])

    resp = Client().post(
        "/api/license/activate",
        data=json.dumps(
            {"productCode": sku.code, "machineFingerprintHash": "SOME-MACHINE", "licenseKey": purchase.license_key}
        ),
        content_type="application/json",
    )
    body = resp.json()
    assert body["authorized"] is False
    assert body["status"] == "expired"


def test_activation_succeeds_within_a_redeemed_codes_duration(sku, buyer):
    code = LicenseCode.objects.create(product=sku, seats=1, duration_days=30)
    purchase = redeem_license_code(code.code, buyer)

    resp = Client().post(
        "/api/license/activate",
        data=json.dumps(
            {"productCode": sku.code, "machineFingerprintHash": "SOME-MACHINE", "licenseKey": purchase.license_key}
        ),
        content_type="application/json",
    )
    body = resp.json()
    assert body["authorized"] is True
    assert body["status"] == "paid"
