"""
Deploy-safety migration: promoting every pre-existing is_staff=True account to
Admin (is_superuser=True) at the same moment granular permission checks ship —
see accounts/migrations/0006_role_permissions.py. Tested by calling the
RunPython function directly (its module name starts with a digit, so it can
only be reached via importlib, not a plain import statement), same pattern as
catalog/test_strip_staff_partners_migration.py.
"""
import importlib

import pytest
from django.apps import apps as django_apps
from django.contrib.auth import get_user_model

pytestmark = pytest.mark.django_db
User = get_user_model()

migration_module = importlib.import_module("accounts.migrations.0006_role_permissions")


def test_promote_existing_staff_to_admin_flips_superuser():
    staff = User.objects.create_user(username="staff@x.com", email="staff@x.com", password="x", is_staff=True)

    migration_module.promote_existing_staff_to_admin(django_apps, None)

    staff.refresh_from_db()
    assert staff.is_superuser is True


def test_promote_existing_staff_to_admin_leaves_a_plain_customer_alone():
    customer = User.objects.create_user(username="cust@x.com", email="cust@x.com", password="x")

    migration_module.promote_existing_staff_to_admin(django_apps, None)

    customer.refresh_from_db()
    assert customer.is_staff is False
    assert customer.is_superuser is False


def test_promote_existing_staff_to_admin_is_idempotent_for_an_already_promoted_account():
    admin = User.objects.create_user(
        username="admin@x.com", email="admin@x.com", password="x", is_staff=True, is_superuser=True
    )

    migration_module.promote_existing_staff_to_admin(django_apps, None)

    admin.refresh_from_db()
    assert admin.is_superuser is True
