"""
Self-service license reactivation ("I got a new PC") — release a paid
purchase's machine binding so the next activation call, from a different
fingerprint, binds fresh instead of being denied forever by the old one.
See licensing/services.py::release_machine_binding and
licensing/account_api.py::ReactivateLicenseView.
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
        name="Reactivate Test", product_code="reactivate-test", category=category,
        short_description="s", description="d", status=ProductStatus.PUBLISHED,
    )
    return LicensedProduct.objects.get(code=product.product_code)


@pytest.fixture
def buyer_client(sku):
    user = User.objects.create_user(username="buyer@x.com", email="buyer@x.com", password="x")
    purchase = ProductPurchase.objects.create(
        user=user, product=sku, payment_status=ProductPurchase.PaymentStatus.PAID,
    )
    machine = MachineLicense.objects.create(
        product=sku, user=user, purchase=purchase, machine_fingerprint_hash="OLDHASH",
        status="paid", started_at=timezone.now(), expires_at=timezone.now() + timedelta(days=36500),
    )
    client = Client()
    client.force_login(user)
    return client, user, purchase, machine


def test_reactivating_releases_the_machine_binding(buyer_client):
    client, _, purchase, machine = buyer_client
    resp = client.post(f"/api/account/licenses/machines/{machine.id}/reactivate")
    assert resp.status_code == 200, resp.json()
    machine.refresh_from_db()
    assert machine.status == "released"
    assert LicenseEvent.objects.filter(event_type="machine_released").exists()


def test_after_reactivation_a_new_machine_can_activate(buyer_client, settings):
    settings.LICENSE_PEPPER = "test-pepper"
    client, user, purchase, machine = buyer_client
    client.post(f"/api/account/licenses/machines/{machine.id}/reactivate")

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


def test_cannot_reactivate_someone_elses_license(buyer_client):
    _, _, _, machine = buyer_client
    other = User.objects.create_user(username="other@x.com", email="other@x.com", password="x")
    other_client = Client()
    other_client.force_login(other)
    resp = other_client.post(f"/api/account/licenses/machines/{machine.id}/reactivate")
    assert resp.status_code == 400


def test_cannot_reactivate_twice_within_the_cooldown(buyer_client):
    client, _, _, machine = buyer_client
    first = client.post(f"/api/account/licenses/machines/{machine.id}/reactivate")
    assert first.status_code == 200

    # A second machine license appears once the customer activates on the new
    # PC; reactivating THAT one immediately should be blocked by the cooldown
    # tied to the same purchase.
    new_machine = MachineLicense.objects.create(
        product=machine.product, user=machine.user, purchase=machine.purchase,
        machine_fingerprint_hash="NEWHASH", status="paid",
        started_at=timezone.now(), expires_at=timezone.now() + timedelta(days=36500),
    )
    second = client.post(f"/api/account/licenses/machines/{new_machine.id}/reactivate")
    assert second.status_code == 400
    assert "90 days" in second.json()["detail"]


def test_cannot_reactivate_an_unpaid_license(buyer_client):
    client, _, purchase, machine = buyer_client
    purchase.payment_status = ProductPurchase.PaymentStatus.REFUNDED
    purchase.save()
    resp = client.post(f"/api/account/licenses/machines/{machine.id}/reactivate")
    assert resp.status_code == 400


def test_reactivating_an_already_released_machine_is_rejected(buyer_client):
    client, _, _, machine = buyer_client
    client.post(f"/api/account/licenses/machines/{machine.id}/reactivate")
    resp = client.post(f"/api/account/licenses/machines/{machine.id}/reactivate")
    assert resp.status_code == 400


def test_anonymous_cannot_reactivate(client, buyer_client):
    _, _, _, machine = buyer_client
    resp = client.post(f"/api/account/licenses/machines/{machine.id}/reactivate")
    assert resp.status_code in (401, 403)
