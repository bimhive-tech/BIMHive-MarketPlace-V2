"""
One-time data cleanup for the "an admin became a partner" mistake — see
catalog/migrations/0011_strip_staff_partner_links.py. Tested by calling the
RunPython function directly (its module name starts with a digit, so it can
only be reached via importlib, not a plain import statement) rather than
replaying migration history, since the fix only ever needs to run once
against whatever bad data already exists.
"""
import importlib

import pytest
from django.apps import apps as django_apps
from django.contrib.auth import get_user_model

from catalog.models import Category, Partner, Product

pytestmark = pytest.mark.django_db
User = get_user_model()

migration_module = importlib.import_module("catalog.migrations.0011_strip_staff_partner_links")


@pytest.fixture
def category():
    return Category.objects.create(name="Revit Plugins")


def test_strip_staff_partners_removes_partner_products_and_link(category):
    partner = Partner.objects.create(name="Admin Co", status=Partner.ApplicationStatus.APPROVED)
    staff = User.objects.create_user(
        username="admin2@x.com", email="admin2@x.com", password="x", is_staff=True, partner=partner
    )
    Product.objects.create(
        name="Admin's Tool", short_description="s", description="d", category=category, partner=partner,
    )

    migration_module.strip_staff_partners(django_apps, None)

    staff.refresh_from_db()
    assert staff.partner_id is None
    assert not Partner.objects.filter(id=partner.id).exists()
    assert not Product.objects.filter(name="Admin's Tool").exists()


def test_strip_staff_partners_leaves_non_staff_partners_alone(category):
    partner = Partner.objects.create(name="Real Seller", status=Partner.ApplicationStatus.APPROVED)
    seller = User.objects.create_user(username="seller@x.com", email="seller@x.com", password="x", partner=partner)
    Product.objects.create(
        name="Seller's Tool", short_description="s", description="d", category=category, partner=partner,
    )

    migration_module.strip_staff_partners(django_apps, None)

    seller.refresh_from_db()
    assert seller.partner_id == partner.id
    assert Partner.objects.filter(id=partner.id).exists()
    assert Product.objects.filter(name="Seller's Tool").exists()


def test_strip_staff_partners_is_a_noop_when_nothing_to_clean_up():
    # Should not raise or touch anything when no staff account has a partner.
    migration_module.strip_staff_partners(django_apps, None)
