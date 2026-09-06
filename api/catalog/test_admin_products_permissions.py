"""
Proves the trickiest composition in the granular-permission rollout: product
management is shared between staff-with-products.manage and approved partners
(IsApprovedPartner | (IsAuthenticated & HasAdminPermission), see
catalog/admin_api.py and catalog/permissions.py) — the old blanket "any
is_staff" grant (IsStaffOrPartner) is gone, but the partner branch must still
work unchanged.
"""
import pytest
from django.contrib.auth import get_user_model

from accounts.models import Role
from catalog.models import Category, Partner

pytestmark = pytest.mark.django_db
User = get_user_model()


@pytest.fixture
def category():
    return Category.objects.create(name="Revit Plugins")


def test_staff_without_products_manage_is_denied(client, category):
    role = Role.objects.create(name="Support Only", grants_staff_access=True, permissions=["reviews.moderate"])
    user = User.objects.create_user(
        username="s@x.com", email="s@x.com", password="x", is_staff=True, role=role,
    )
    client.force_login(user)
    resp = client.get("/api/admin/products")
    assert resp.status_code == 403


def test_staff_with_products_manage_is_allowed(client, category):
    role = Role.objects.create(name="Catalog Editor", grants_staff_access=True, permissions=["products.manage"])
    user = User.objects.create_user(
        username="s2@x.com", email="s2@x.com", password="x", is_staff=True, role=role,
    )
    client.force_login(user)
    resp = client.get("/api/admin/products")
    assert resp.status_code == 200


def test_admin_is_always_allowed_regardless_of_role(client, category):
    admin = User.objects.create_user(
        username="a@x.com", email="a@x.com", password="x", is_staff=True, is_superuser=True,
    )
    client.force_login(admin)
    resp = client.get("/api/admin/products")
    assert resp.status_code == 200


def test_approved_partner_is_still_allowed_with_no_staff_status_at_all(client, category):
    partner = Partner.objects.create(name="Real Seller", status=Partner.ApplicationStatus.APPROVED)
    user = User.objects.create_user(username="p@x.com", email="p@x.com", password="x", partner=partner)
    client.force_login(user)
    resp = client.get("/api/admin/products")
    assert resp.status_code == 200


def test_pending_partner_is_still_denied(client, category):
    partner = Partner.objects.create(name="New Seller")  # defaults to pending
    user = User.objects.create_user(username="p2@x.com", email="p2@x.com", password="x", partner=partner)
    client.force_login(user)
    resp = client.get("/api/admin/products")
    assert resp.status_code == 403
