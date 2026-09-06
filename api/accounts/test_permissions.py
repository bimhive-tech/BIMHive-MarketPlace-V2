"""
Unit tests for the core staff/admin permission logic (accounts/permissions.py).
Deliberately tests the two permission classes directly against a minimal dummy
view rather than every real admin endpoint — every real endpoint just sets
`permission_classes`/`required_permission`, a one-line, easily-reviewed diff;
get the shared logic exactly right here and every endpoint composing it
correctly follows.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory

from accounts.models import Role
from accounts.permissions import HasAdminPermission, IsSuperAdmin

pytestmark = pytest.mark.django_db
User = get_user_model()
factory = APIRequestFactory()


class _DummyView:
    required_permission = "products.manage"


def _request(user):
    request = factory.get("/")
    request.user = user
    return request


class _Anonymous:
    is_authenticated = False


def test_has_admin_permission_denies_anonymous():
    assert not HasAdminPermission().has_permission(_request(_Anonymous()), _DummyView())


def test_has_admin_permission_denies_authenticated_non_staff():
    user = User.objects.create_user(username="u@x.com", email="u@x.com", password="x")
    assert not HasAdminPermission().has_permission(_request(user), _DummyView())


def test_has_admin_permission_denies_staff_with_no_role():
    user = User.objects.create_user(username="s@x.com", email="s@x.com", password="x", is_staff=True)
    assert not HasAdminPermission().has_permission(_request(user), _DummyView())


def test_has_admin_permission_denies_staff_with_role_lacking_the_key():
    role = Role.objects.create(name="Support", grants_staff_access=True, permissions=["reviews.moderate"])
    user = User.objects.create_user(username="s2@x.com", email="s2@x.com", password="x", is_staff=True, role=role)
    assert not HasAdminPermission().has_permission(_request(user), _DummyView())


def test_has_admin_permission_allows_staff_with_role_granting_the_key():
    role = Role.objects.create(name="Catalog Editor", grants_staff_access=True, permissions=["products.manage"])
    user = User.objects.create_user(username="s3@x.com", email="s3@x.com", password="x", is_staff=True, role=role)
    assert HasAdminPermission().has_permission(_request(user), _DummyView())


def test_has_admin_permission_allows_superuser_with_no_role():
    admin = User.objects.create_user(
        username="a@x.com", email="a@x.com", password="x", is_staff=True, is_superuser=True
    )
    assert HasAdminPermission().has_permission(_request(admin), _DummyView())


def test_has_admin_permission_allows_superuser_even_with_role_lacking_the_key():
    # Admin always bypasses granular checks, regardless of whatever role
    # happens to also be assigned.
    role = Role.objects.create(name="Support", grants_staff_access=True, permissions=["reviews.moderate"])
    admin = User.objects.create_user(
        username="a2@x.com", email="a2@x.com", password="x", is_staff=True, is_superuser=True, role=role
    )
    assert HasAdminPermission().has_permission(_request(admin), _DummyView())


def test_is_super_admin_denies_plain_staff():
    user = User.objects.create_user(username="s4@x.com", email="s4@x.com", password="x", is_staff=True)
    assert not IsSuperAdmin().has_permission(_request(user), _DummyView())


def test_is_super_admin_allows_superuser():
    admin = User.objects.create_user(
        username="a3@x.com", email="a3@x.com", password="x", is_staff=True, is_superuser=True
    )
    assert IsSuperAdmin().has_permission(_request(admin), _DummyView())
