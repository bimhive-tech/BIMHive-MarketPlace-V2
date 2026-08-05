"""
All-Access membership: tiered coverage, the universal key at
/api/license/activate, and revocation pulling every granted license with it.
"""
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from catalog.models import Category, Product
from catalog.models.product import ProductStatus
from licensing.models import LicensedProduct, ProductPurchase
from membership.models import Membership, MembershipPlan
from membership.services import (
    activate_membership,
    end_membership,
    has_entitlement,
    resolve_membership_purchase,
)

pytestmark = pytest.mark.django_db
User = get_user_model()

FINGERPRINT = "MACHINE-ABC"


@pytest.fixture
def plans():
    standard = MembershipPlan.objects.create(
        name="Standard", rank=1, monthly_price="19.00", yearly_price="190.00", seats_per_product=2
    )
    pro = MembershipPlan.objects.create(
        name="Pro", rank=2, monthly_price="39.00", yearly_price="390.00", seats_per_product=3
    )
    return standard, pro


@pytest.fixture
def category():
    return Category.objects.create(name="Revit Plugins")


@pytest.fixture
def user():
    return User.objects.create_user(username="m@x.com", email="m@x.com", password="x")


@pytest.fixture
def staff_client(client):
    staff = User.objects.create_user(username="admin@x.com", email="admin@x.com", password="x", is_staff=True)
    client.force_login(staff)
    return client


def make_product(name, category, plan=None):
    return Product.objects.create(
        name=name, short_description="s", description="d", category=category,
        price="49.00", status=ProductStatus.PUBLISHED, membership_plan=plan,
    )


def make_membership(user, plan, **overrides):
    membership = Membership.objects.create(
        user=user, plan=plan, billing_period=Membership.BillingPeriod.MONTHLY,
        status=Membership.Status.ACTIVE, expires_at=timezone.now() + timedelta(days=30),
        **overrides,
    )
    return membership


def activate(client, product_code, license_key, settings):
    settings.LICENSE_PEPPER = "test-pepper"
    return client.post(
        "/api/license/activate",
        {
            "productCode": product_code,
            "licenseKey": license_key,
            "machineFingerprintHash": FINGERPRINT,
        },
        content_type="application/json",
    ).json()


# ── Tier coverage ──
def test_a_plan_covers_its_own_tier_and_everything_below(plans, category, user):
    standard, pro = plans
    standard_product = make_product("Standard Tool", category, standard)
    pro_product = make_product("Pro Tool", category, pro)
    excluded = make_product("Buy-only Tool", category, None)

    pro_member = make_membership(user, pro)

    assert pro_member.covers(standard_product) is True
    assert pro_member.covers(pro_product) is True
    assert pro_member.covers(excluded) is False, "no plan means not in All-Access at all"


def test_a_lower_tier_does_not_reach_a_higher_one(plans, category, user):
    standard, pro = plans
    pro_product = make_product("Pro Tool", category, pro)

    assert make_membership(user, standard).covers(pro_product) is False


def test_an_expired_membership_covers_nothing(plans, category, user):
    standard, _ = plans
    product = make_product("Standard Tool", category, standard)
    membership = make_membership(user, standard, )
    membership.expires_at = timezone.now() - timedelta(minutes=1)
    membership.save()

    assert membership.covers(product) is False


# ── The universal key at /api/license/activate ──
def test_the_universal_key_activates_a_covered_product(client, plans, category, user, settings):
    standard, _ = plans
    product = make_product("Standard Tool", category, standard)
    membership = make_membership(user, standard)

    body = activate(client, product.product_code, membership.license_key, settings)

    assert body["authorized"] is True
    assert body["status"] == "paid"


def test_the_universal_key_mints_one_purchase_owned_by_the_membership(
    client, plans, category, user, settings
):
    standard, _ = plans
    product = make_product("Standard Tool", category, standard)
    membership = make_membership(user, standard)

    activate(client, product.product_code, membership.license_key, settings)
    activate(client, product.product_code, membership.license_key, settings)

    purchases = ProductPurchase.objects.filter(source_membership=membership)
    assert purchases.count() == 1, "re-activating must not mint a second grant"
    assert purchases.first().seats == standard.seats_per_product


def test_the_universal_key_is_refused_for_an_uncovered_product(client, plans, category, user, settings):
    standard, pro = plans
    pro_product = make_product("Pro Tool", category, pro)
    membership = make_membership(user, standard)

    body = activate(client, pro_product.product_code, membership.license_key, settings)

    assert body["authorized"] is False
    assert ProductPurchase.objects.filter(source_membership=membership).exists() is False


def test_an_unknown_key_is_still_refused(client, plans, category, user, settings):
    standard, _ = plans
    product = make_product("Standard Tool", category, standard)
    make_membership(user, standard)

    body = activate(client, product.product_code, "BHX-NOPE-NOPE-NOPE-NOPE", settings)

    assert body["authorized"] is False


# ── Revocation ──
def test_ending_a_membership_revokes_every_license_it_granted(client, plans, category, user, settings):
    standard, _ = plans
    first = make_product("Tool One", category, standard)
    second = make_product("Tool Two", category, standard)
    membership = make_membership(user, standard)
    activate(client, first.product_code, membership.license_key, settings)
    activate(client, second.product_code, membership.license_key, settings)
    assert ProductPurchase.objects.filter(source_membership=membership).count() == 2

    end_membership(membership, Membership.Status.REFUNDED)

    statuses = set(
        ProductPurchase.objects.filter(source_membership=membership).values_list("payment_status", flat=True)
    )
    assert statuses == {ProductPurchase.PaymentStatus.REFUNDED}


def test_a_revoked_key_stops_activating(client, plans, category, user, settings):
    standard, _ = plans
    product = make_product("Standard Tool", category, standard)
    membership = make_membership(user, standard)
    activate(client, product.product_code, membership.license_key, settings)

    end_membership(membership, Membership.Status.CANCELLED)
    body = activate(client, product.product_code, membership.license_key, settings)

    assert body["authorized"] is False
    assert body["status"] == "cancelled"


def test_a_dead_membership_never_mints_a_new_grant(plans, category, user):
    standard, _ = plans
    product = make_product("Standard Tool", category, standard)
    membership = make_membership(user, standard)
    end_membership(membership, Membership.Status.CANCELLED)
    sku = LicensedProduct.objects.get(code=product.product_code)

    assert resolve_membership_purchase(membership, sku) is None


# ── Renewal ──
def test_renewing_extends_from_the_current_expiry_not_from_today(plans, user):
    standard, _ = plans
    membership = make_membership(user, standard)
    original_expiry = membership.expires_at

    activate_membership(membership)

    assert membership.expires_at > original_expiry + timedelta(days=29)


def test_activating_reopens_previously_revoked_grants(client, plans, category, user, settings):
    standard, _ = plans
    product = make_product("Standard Tool", category, standard)
    membership = make_membership(user, standard)
    activate(client, product.product_code, membership.license_key, settings)
    end_membership(membership, Membership.Status.CANCELLED)

    activate_membership(membership)

    purchase = ProductPurchase.objects.get(source_membership=membership)
    assert purchase.payment_status == ProductPurchase.PaymentStatus.PAID


# ── Downloads ──
def test_a_member_can_download_a_covered_product_before_ever_activating(plans, category, user):
    standard, _ = plans
    product = make_product("Standard Tool", category, standard)
    make_membership(user, standard)

    assert has_entitlement(user, product) is True


def test_a_member_cannot_download_a_product_outside_their_tier(plans, category, user):
    standard, pro = plans
    pro_product = make_product("Pro Tool", category, pro)
    make_membership(user, standard)

    assert has_entitlement(user, pro_product) is False


def test_downloads_list_flags_which_products_came_from_the_membership(client, plans, category, user):
    standard, _ = plans
    make_product("Standard Tool", category, standard)
    make_membership(user, standard)
    client.force_login(user)

    rows = client.get("/api/account/downloads").json()

    assert [r["product_name"] for r in rows] == ["Standard Tool"]
    assert rows[0]["via_membership"] is True


# ── Public API ──
def test_plans_endpoint_counts_products_cumulatively(client, plans, category):
    standard, pro = plans
    make_product("Standard Tool", category, standard)
    make_product("Pro Tool", category, pro)

    body = client.get("/api/membership/plans").json()
    by_name = {plan["name"]: plan for plan in body["plans"]}

    assert by_name["Standard"]["product_count"] == 1
    assert by_name["Pro"]["product_count"] == 2, "a higher tier includes the lower tiers' products"


def test_yearly_savings_are_reported_for_the_pricing_toggle(client, plans):
    body = client.get("/api/membership/plans").json()

    # 190 vs 12x19 (228) is a 17% saving.
    assert body["plans"][0]["yearly_savings_percent"] == 17


def test_account_membership_exposes_the_universal_key(client, plans, category, user):
    standard, _ = plans
    make_product("Standard Tool", category, standard)
    membership = make_membership(user, standard)
    client.force_login(user)

    body = client.get("/api/account/membership").json()

    assert body["membership"]["license_key"] == membership.license_key
    assert [p["name"] for p in body["products"]] == ["Standard Tool"]


def test_cancelling_from_the_account_ends_the_membership(client, plans, user):
    standard, _ = plans
    make_membership(user, standard)
    client.force_login(user)

    resp = client.post("/api/account/membership/cancel")

    assert resp.status_code == 200
    assert resp.json()["status"] == Membership.Status.CANCELLED


# ── Admin API ──
def test_admin_can_create_a_plan(staff_client):
    resp = staff_client.post(
        "/api/admin/membership-plans",
        {"name": "Enterprise", "rank": 3, "monthly_price": "99.00"},
        content_type="application/json",
    )

    assert resp.status_code == 201, resp.json()
    assert resp.json()["slug"] == "enterprise"


def test_admin_plan_requires_at_least_one_price(staff_client):
    resp = staff_client.post(
        "/api/admin/membership-plans",
        {"name": "Priceless", "rank": 1},
        content_type="application/json",
    )

    assert resp.status_code == 400


def test_admin_can_revoke_a_membership_and_it_pulls_every_grant(client, staff_client, plans, category, user, settings):
    standard, _ = plans
    product = make_product("Standard Tool", category, standard)
    membership = make_membership(user, standard)
    activate(client, product.product_code, membership.license_key, settings)

    resp = staff_client.post(f"/api/admin/memberships/{membership.id}/revoke", {"status": "revoked"}, content_type="application/json")

    assert resp.status_code == 200
    assert resp.json()["display_status"] == Membership.Status.REVOKED
    purchase = ProductPurchase.objects.get(source_membership=membership)
    assert purchase.payment_status == ProductPurchase.PaymentStatus.REVOKED


def test_admin_can_reinstate_a_revoked_membership(staff_client, plans, user):
    standard, _ = plans
    membership = make_membership(user, standard)
    end_membership(membership, Membership.Status.CANCELLED)

    resp = staff_client.post(f"/api/admin/memberships/{membership.id}/reinstate")

    assert resp.status_code == 200
    assert resp.json()["display_status"] == Membership.Status.ACTIVE


def test_non_staff_cannot_revoke_a_membership(client, plans, user):
    standard, _ = plans
    membership = make_membership(user, standard)
    client.force_login(user)

    resp = client.post(f"/api/admin/memberships/{membership.id}/revoke", {}, content_type="application/json")

    assert resp.status_code in (401, 403)
