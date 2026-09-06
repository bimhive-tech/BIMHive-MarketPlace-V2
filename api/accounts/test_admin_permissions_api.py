"""
Endpoint-level proof that Staff can never touch Users, Roles & Permissions, or
Settings — the core requirement behind the granular permission system (see
accounts/permissions.py and accounts/test_permissions.py for the underlying
logic these endpoints compose). Also covers the Users/Customers split.
"""
import pytest
from django.contrib.auth import get_user_model

from accounts.models import Role

pytestmark = pytest.mark.django_db
User = get_user_model()


def _admin_client(client):
    user = User.objects.create_user(
        username="admin@x.com", email="admin@x.com", password="x", is_staff=True, is_superuser=True,
    )
    client.force_login(user)
    return client


def _staff_client(client, permissions=None):
    role = Role.objects.create(
        name="Some Role", grants_staff_access=True, permissions=permissions or [],
    )
    user = User.objects.create_user(
        username="staff@x.com", email="staff@x.com", password="x", is_staff=True, role=role,
    )
    client.force_login(user)
    return user, client


# ── Users & Roles: Admin-only, no exceptions ──
def test_staff_cannot_list_users(client):
    _staff_client(client)
    assert client.get("/api/admin/users").status_code == 403


def test_staff_cannot_update_a_user(client):
    _, staff = _staff_client(client)
    target = User.objects.create_user(username="t@x.com", email="t@x.com", password="x")
    resp = staff.patch(f"/api/admin/users/{target.id}", {"is_active": False}, content_type="application/json")
    assert resp.status_code == 403


def test_staff_cannot_list_roles(client):
    _staff_client(client)
    assert client.get("/api/admin/roles").status_code == 403


def test_staff_cannot_create_a_role(client):
    _, staff = _staff_client(client)
    resp = staff.post(
        "/api/admin/roles", {"name": "Self-Granted", "permissions": []}, content_type="application/json"
    )
    assert resp.status_code == 403


def test_admin_can_list_and_update_users(client):
    admin = _admin_client(client)
    target = User.objects.create_user(username="t2@x.com", email="t2@x.com", password="x")
    assert admin.get("/api/admin/users").status_code == 200
    resp = admin.patch(f"/api/admin/users/{target.id}", {"is_active": False}, content_type="application/json")
    assert resp.status_code == 200
    target.refresh_from_db()
    assert target.is_active is False


def test_admin_can_create_a_role_with_permissions(client):
    admin = _admin_client(client)
    resp = admin.post(
        "/api/admin/roles",
        {"name": "Catalog Editor", "grants_staff_access": True, "permissions": ["products.manage"]},
        content_type="application/json",
    )
    assert resp.status_code == 201, resp.json()
    assert resp.json()["permissions"] == ["products.manage"]


def test_role_rejects_an_unknown_permission_key(client):
    admin = _admin_client(client)
    resp = admin.post(
        "/api/admin/roles",
        {"name": "Bad Role", "permissions": ["not.a.real.key"]},
        content_type="application/json",
    )
    assert resp.status_code == 400


# ── Self-demotion lockout guard ──
def test_admin_cannot_demote_the_last_remaining_admin(client):
    admin = User.objects.create_user(
        username="only@x.com", email="only@x.com", password="x", is_staff=True, is_superuser=True,
    )
    client.force_login(admin)
    resp = client.patch(f"/api/admin/users/{admin.id}", {"is_superuser": False}, content_type="application/json")
    assert resp.status_code == 400
    admin.refresh_from_db()
    assert admin.is_superuser is True


def test_admin_can_demote_a_different_admin_when_another_remains(client):
    admin = _admin_client(client)
    other_admin = User.objects.create_user(
        username="other@x.com", email="other@x.com", password="x", is_staff=True, is_superuser=True,
    )
    resp = admin.patch(
        f"/api/admin/users/{other_admin.id}", {"is_superuser": False}, content_type="application/json"
    )
    assert resp.status_code == 200
    other_admin.refresh_from_db()
    assert other_admin.is_superuser is False


# ── Customers: genuinely separate from Users, permission-gated, no sensitive fields ──
def test_customers_requires_the_customers_view_permission(client):
    _staff_client(client, permissions=["products.manage"])
    assert client.get("/api/admin/customers").status_code == 403


def test_customers_reachable_with_the_grant_and_excludes_sensitive_fields(client):
    _, staff = _staff_client(client, permissions=["customers.view"])
    User.objects.create_user(username="cust@x.com", email="cust@x.com", password="x")
    resp = staff.get("/api/admin/customers")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) >= 1
    assert "is_staff" not in body[0]
    assert "role" not in body[0]
