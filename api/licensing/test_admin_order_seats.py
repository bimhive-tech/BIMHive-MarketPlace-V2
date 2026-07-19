"""
Staff-only endpoint for setting how many machines a purchase may bind at
once (see licensing/admin_api.py::AdminOrderSeatsView) — the only way a
purchase gets more than 1 seat today, since there's no checkout flow yet.
"""
import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from licensing.models import LicensedProduct, ProductPurchase

pytestmark = pytest.mark.django_db
User = get_user_model()


@pytest.fixture
def product():
    return LicensedProduct.objects.create(code="seat-test-online", name="Seat Test", is_active=True)


@pytest.fixture
def purchase(product):
    user = User.objects.create_user(username="buyer@x.com", email="buyer@x.com", password="x")
    return ProductPurchase.objects.create(
        user=user, product=product, payment_status=ProductPurchase.PaymentStatus.PAID
    )


@pytest.fixture
def staff_client():
    staff = User.objects.create_user(username="staff@x.com", email="staff@x.com", password="x", is_staff=True)
    client = Client()
    client.force_login(staff)
    return client


def test_staff_can_set_seats(staff_client, purchase):
    resp = staff_client.post(f"/api/admin/orders/{purchase.id}/seats", {"seats": 5})
    assert resp.status_code == 200, resp.json()
    assert resp.json()["seats"] == 5
    purchase.refresh_from_db()
    assert purchase.seats == 5


def test_seats_must_be_at_least_one(staff_client, purchase):
    resp = staff_client.post(f"/api/admin/orders/{purchase.id}/seats", {"seats": 0})
    assert resp.status_code == 400


def test_seats_must_be_a_number(staff_client, purchase):
    resp = staff_client.post(f"/api/admin/orders/{purchase.id}/seats", {"seats": "many"})
    assert resp.status_code == 400


def test_non_staff_cannot_set_seats(purchase):
    client = Client()
    client.force_login(purchase.user)
    resp = client.post(f"/api/admin/orders/{purchase.id}/seats", {"seats": 3})
    assert resp.status_code in (401, 403)
