"""
Staff-only machine-binding release — the replacement for the old customer
self-service "I got a new PC" reactivation, removed when licenses became
single-use-per-machine (see licensing/services.py::release_machine_binding,
licensing/admin_api.py::AdminLicenseReleaseView). A customer can no longer
free their own seat; only staff can, as a manual override.
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


@pytest.fixture
def category():
    return Category.objects.create(name="Revit Plugins")


@pytest.fixture
def sku(category):
    product = Product.objects.create(
        name="Release Test", product_code="release-test", category=category,
        short_description="s", description="d", status=ProductStatus.PUBLISHED,
    )
    return LicensedProduct.objects.get(code=product.product_code)


@pytest.fixture
def buyer_and_machine(sku):
    user = User.objects.create_user(username="buyer@x.com", email="buyer@x.com", password="x")
    purchase = ProductPurchase.objects.create(
        user=user, product=sku, payment_status=ProductPurchase.PaymentStatus.PAID,
    )
    machine = MachineLicense.objects.create(
        product=sku, user=user, purchase=purchase, machine_fingerprint_hash="OLDHASH",
        status="paid", started_at=timezone.now(), expires_at=timezone.now() + timedelta(days=36500),
    )
    return user, purchase, machine


@pytest.fixture
def staff_client(client):
    user = User.objects.create_user(username="staff@x.com", email="staff@x.com", password="x", is_staff=True)
    client.force_login(user)
    return client


def test_customer_has_no_self_service_way_to_release_their_own_machine(buyer_and_machine):
    user, _, machine = buyer_and_machine
    client = Client()
    client.force_login(user)
    resp = client.post(f"/api/account/licenses/machines/{machine.id}/reactivate")
    assert resp.status_code == 404


def test_staff_can_release_a_machine_binding(staff_client, buyer_and_machine):
    _, _, machine = buyer_and_machine
    resp = staff_client.post(f"/api/admin/licenses/{machine.id}/release")
    assert resp.status_code == 200, resp.json()
    machine.refresh_from_db()
    assert machine.status == "released"
    assert LicenseEvent.objects.filter(event_type="machine_released").exists()


def test_a_new_machine_can_activate_after_staff_releases_the_old_one(staff_client, buyer_and_machine, settings):
    settings.LICENSE_PEPPER = "test-pepper"
    _, purchase, machine = buyer_and_machine
    staff_client.post(f"/api/admin/licenses/{machine.id}/release")

    activate_client = Client()
    resp = activate_client.post(
        "/api/license/activate",
        data=json.dumps(
            {"productCode": purchase.product.code, "machineFingerprintHash": "NEWHASH", "licenseKey": purchase.license_key}
        ),
        content_type="application/json",
    )
    body = resp.json()
    assert body["authorized"] is True, body
    assert body["status"] == "paid"

    new_machine = MachineLicense.objects.exclude(pk=machine.pk).get(product=purchase.product)
    assert new_machine.status == "paid"


def test_releasing_one_seat_of_a_multi_seat_purchase_only_frees_that_one(staff_client, sku):
    user = User.objects.create_user(username="buyer2@x.com", email="buyer2@x.com", password="x")
    purchase = ProductPurchase.objects.create(
        user=user, product=sku, payment_status=ProductPurchase.PaymentStatus.PAID, seats=2,
    )
    machine_a = MachineLicense.objects.create(
        product=sku, user=user, purchase=purchase, machine_fingerprint_hash="HASH-A",
        status="paid", started_at=timezone.now(), expires_at=timezone.now() + timedelta(days=36500),
    )
    machine_b = MachineLicense.objects.create(
        product=sku, user=user, purchase=purchase, machine_fingerprint_hash="HASH-B",
        status="paid", started_at=timezone.now(), expires_at=timezone.now() + timedelta(days=36500),
    )

    resp = staff_client.post(f"/api/admin/licenses/{machine_a.id}/release")
    assert resp.status_code == 200, resp.json()

    machine_a.refresh_from_db()
    machine_b.refresh_from_db()
    assert machine_a.status == "released"
    assert machine_b.status == "paid"  # untouched — releasing one seat doesn't touch the other


def test_releasing_an_already_released_machine_is_rejected(staff_client, buyer_and_machine):
    _, _, machine = buyer_and_machine
    staff_client.post(f"/api/admin/licenses/{machine.id}/release")
    resp = staff_client.post(f"/api/admin/licenses/{machine.id}/release")
    assert resp.status_code == 400


def test_non_staff_cannot_release_a_machine_binding(buyer_and_machine):
    user, _, machine = buyer_and_machine
    client = Client()
    client.force_login(user)
    resp = client.post(f"/api/admin/licenses/{machine.id}/release")
    assert resp.status_code in (401, 403)


def test_anonymous_cannot_release_a_machine_binding(client, buyer_and_machine):
    _, _, machine = buyer_and_machine
    resp = client.post(f"/api/admin/licenses/{machine.id}/release")
    assert resp.status_code in (401, 403)
