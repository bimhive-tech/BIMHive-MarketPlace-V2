"""
The self-service "Become a Seller" application flow: apply -> pending Partner
linked to the applicant's User -> staff approve/reject via the existing
AdminPartnerViewSet PATCH -> approval unlocks product management + the sales
view. See catalog/partner_api.py (BecomeSellerView, PartnerSalesView) and
catalog/permissions.py (IsStaffOrPartner/IsApprovedPartner now gate on
Partner.status, not just User.partner_id).
"""
import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from catalog.models import Category, Partner, Product
from catalog.models.product import ProductStatus, ProductVisibility
from licensing.models import LicensedProduct, ProductPurchase

pytestmark = pytest.mark.django_db
User = get_user_model()


@pytest.fixture
def category():
    return Category.objects.create(name="Revit Plugins")


@pytest.fixture
def customer_client():
    # A dedicated Client() instance (not the shared `client` fixture) — several
    # tests here need a customer AND staff logged in simultaneously, which two
    # fixtures both force_login-ing the same shared client would silently
    # clobber (the second login overwrites the first's session).
    user = User.objects.create_user(username="c@x.com", email="c@x.com", password="x")
    client = Client()
    client.force_login(user)
    return client, user


@pytest.fixture
def staff_client():
    user = User.objects.create_user(username="admin@x.com", email="admin@x.com", password="x", is_staff=True)
    client = Client()
    client.force_login(user)
    return client


# ── Applying ──
def test_applying_creates_a_pending_partner_linked_to_the_user(customer_client):
    client, user = customer_client
    resp = client.post("/api/partner/apply", {"company_name": "Acme Tools"})
    assert resp.status_code == 201, resp.json()
    body = resp.json()
    assert body["status"] == "pending"

    user.refresh_from_db()
    assert user.partner is not None
    assert user.partner.name == "Acme Tools"
    assert user.partner.status == Partner.ApplicationStatus.PENDING


def test_cannot_apply_without_a_company_name(customer_client):
    client, _ = customer_client
    resp = client.post("/api/partner/apply", {"company_name": ""})
    assert resp.status_code == 400


def test_cannot_apply_twice(customer_client):
    client, _ = customer_client
    client.post("/api/partner/apply", {"company_name": "Acme Tools"})
    resp = client.post("/api/partner/apply", {"company_name": "Acme Tools 2"})
    assert resp.status_code == 400


def test_cannot_apply_with_a_duplicate_company_name(customer_client):
    Partner.objects.create(name="Existing Co")
    client, _ = customer_client
    resp = client.post("/api/partner/apply", {"company_name": "Existing Co"})
    assert resp.status_code == 400


def test_anonymous_cannot_apply(client):
    resp = client.post("/api/partner/apply", {"company_name": "Acme Tools"})
    assert resp.status_code in (401, 403)


def test_staff_cannot_apply(staff_client):
    # Staff already have unrestricted access via the admin portal and must
    # never also be a partner — see catalog.partner_api.BecomeSellerView.
    resp = staff_client.post("/api/partner/apply", {"company_name": "Acme Tools"})
    assert resp.status_code == 400
    assert "detail" in resp.json()


# ── Access before approval ──
def test_pending_partner_can_see_and_edit_own_profile(customer_client):
    client, _ = customer_client
    client.post("/api/partner/apply", {"company_name": "Acme Tools"})
    resp = client.get("/api/partner/profile")
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"

    resp = client.patch("/api/partner/profile", {"tagline": "New tagline"}, content_type="application/json")
    assert resp.status_code == 200, resp.json()
    assert resp.json()["tagline"] == "New tagline"


def test_pending_partner_cannot_create_products(customer_client, category):
    client, _ = customer_client
    client.post("/api/partner/apply", {"company_name": "Acme Tools"})
    resp = client.post(
        "/api/admin/products",
        {
            "name": "Tool", "short_description": "s", "description": "d",
            "category": category.id, "price": "10.00", "status": "draft",
        },
        content_type="application/json",
    )
    assert resp.status_code == 403


def test_rejected_partner_cannot_create_products(customer_client, staff_client, category):
    client, user = customer_client
    client.post("/api/partner/apply", {"company_name": "Acme Tools"})
    user.refresh_from_db()
    staff_client.patch(
        f"/api/admin/partners/{user.partner_id}",
        {"status": "rejected", "rejection_note": "Not a real business."},
        content_type="application/json",
    )
    resp = client.post(
        "/api/admin/products",
        {
            "name": "Tool", "short_description": "s", "description": "d",
            "category": category.id, "price": "10.00", "status": "draft",
        },
        content_type="application/json",
    )
    assert resp.status_code == 403


def test_rejected_partner_sees_the_rejection_note_on_their_profile(customer_client, staff_client):
    client, user = customer_client
    client.post("/api/partner/apply", {"company_name": "Acme Tools"})
    user.refresh_from_db()
    staff_client.patch(
        f"/api/admin/partners/{user.partner_id}",
        {"status": "rejected", "rejection_note": "Not a real business."},
        content_type="application/json",
    )
    resp = client.get("/api/partner/profile")
    body = resp.json()
    assert body["status"] == "rejected"
    assert body["rejection_note"] == "Not a real business."


def test_pending_partner_cannot_access_sales(customer_client):
    client, _ = customer_client
    client.post("/api/partner/apply", {"company_name": "Acme Tools"})
    resp = client.get("/api/partner/sales")
    assert resp.status_code == 403


# ── Staff approval unlocks access ──
def test_staff_approving_unlocks_product_access(customer_client, staff_client, category):
    client, user = customer_client
    client.post("/api/partner/apply", {"company_name": "Acme Tools"})
    user.refresh_from_db()
    resp = staff_client.patch(
        f"/api/admin/partners/{user.partner_id}", {"status": "approved"}, content_type="application/json"
    )
    assert resp.status_code == 200, resp.json()

    resp = client.post(
        "/api/admin/products",
        {
            "name": "Tool", "short_description": "s", "description": "d",
            "category": category.id, "price": "10.00", "status": "draft",
        },
        content_type="application/json",
    )
    assert resp.status_code == 201, resp.json()


# ── Public exposure ──
def test_pending_partner_not_in_public_partner_list(customer_client, staff_client, category):
    client, user = customer_client
    client.post("/api/partner/apply", {"company_name": "Acme Tools"})
    user.refresh_from_db()
    Product.objects.create(
        name="Tool", short_description="s", description="d", category=category, partner=user.partner,
        status=ProductStatus.PUBLISHED, visibility=ProductVisibility.PUBLIC, price="10.00",
    )
    resp = client.get("/api/partners")
    names = [p["name"] for p in resp.json()]
    assert "Acme Tools" not in names


def test_approved_partner_with_a_published_product_is_public(customer_client, staff_client, category):
    client, user = customer_client
    client.post("/api/partner/apply", {"company_name": "Acme Tools"})
    user.refresh_from_db()
    staff_client.patch(
        f"/api/admin/partners/{user.partner_id}", {"status": "approved"}, content_type="application/json"
    )
    Product.objects.create(
        name="Tool", short_description="s", description="d", category=category, partner=user.partner,
        status=ProductStatus.PUBLISHED, visibility=ProductVisibility.PUBLIC, price="10.00",
    )
    resp = client.get("/api/partners")
    names = [p["name"] for p in resp.json()]
    assert "Acme Tools" in names


# ── Sales ──
def test_sales_sums_only_paid_purchases_of_the_partners_own_products(customer_client, staff_client, category):
    client, user = customer_client
    client.post("/api/partner/apply", {"company_name": "Acme Tools"})
    user.refresh_from_db()
    staff_client.patch(
        f"/api/admin/partners/{user.partner_id}", {"status": "approved"}, content_type="application/json"
    )
    product = Product.objects.create(
        name="Tool", short_description="s", description="d", category=category, partner=user.partner,
        price="25.00",
    )
    other_product = Product.objects.create(
        name="Other's Tool", short_description="s", description="d", category=category, price="99.00",
    )
    sku = LicensedProduct.objects.get(code=product.product_code)
    other_sku = LicensedProduct.objects.get(code=other_product.product_code)

    buyer = User.objects.create_user(username="buyer@x.com", email="buyer@x.com", password="x")
    ProductPurchase.objects.create(
        user=buyer, product=sku, amount="25.00", payment_status=ProductPurchase.PaymentStatus.PAID
    )
    # A pending purchase for the same partner's product shouldn't count toward revenue.
    buyer2 = User.objects.create_user(username="buyer2@x.com", email="buyer2@x.com", password="x")
    ProductPurchase.objects.create(
        user=buyer2, product=sku, amount="25.00", payment_status=ProductPurchase.PaymentStatus.PENDING
    )
    # A purchase of someone else's product must never count.
    buyer3 = User.objects.create_user(username="buyer3@x.com", email="buyer3@x.com", password="x")
    ProductPurchase.objects.create(
        user=buyer3, product=other_sku, amount="99.00", payment_status=ProductPurchase.PaymentStatus.PAID
    )

    resp = client.get("/api/partner/sales")
    assert resp.status_code == 200, resp.json()
    body = resp.json()
    assert body["total_revenue"] == "25.00"
    assert body["order_count"] == 2  # paid + pending, both theirs
    for row in body["orders"]:
        assert "user_email" not in row and "contact_email" not in row and "company_name" not in row
        assert "buyer@x.com" not in str(row)
