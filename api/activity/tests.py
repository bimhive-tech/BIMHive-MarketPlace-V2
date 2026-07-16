"""
Locks in that the actions people actually care about ("who did what, when")
get logged, and that the admin activity list is staff-only and its filters
(actor, verb, date range) actually narrow the results.
"""
import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone

from activity.models import ActivityLog, ActivityVerb
from catalog.models import Category, Product
from catalog.models.product import ProductStatus, ProductVisibility
from licensing.models import LicensedProduct, ProductPurchase

pytestmark = pytest.mark.django_db
User = get_user_model()


@pytest.fixture
def category():
    return Category.objects.create(name="Revit Plugins")


@pytest.fixture
def free_product(category):
    return Product.objects.create(
        name="Free Sample Tool", short_description="s", description="d", category=category,
        price="0.00", status=ProductStatus.PUBLISHED, visibility=ProductVisibility.PUBLIC,
    )


@pytest.fixture
def staff_client():
    user = User.objects.create_user(username="admin@x.com", email="admin@x.com", password="x", is_staff=True)
    client = Client()
    client.force_login(user)
    return client


def _login(email="buyer@example.com"):
    user = User.objects.create_user(username=email, email=email, password="pw12345!")
    client = Client()
    client.force_login(user)
    return user, client


# ── Logging on the actions that matter ──
def test_signup_and_login_are_logged():
    client = Client()
    resp = client.post(
        "/api/auth/register",
        data={"email": "new@example.com", "password": "pw12345!strong", "full_name": "New User"},
        content_type="application/json",
    )
    assert resp.status_code == 201
    assert ActivityLog.objects.filter(verb=ActivityVerb.SIGNED_UP, actor_label="new@example.com").exists()

    client2 = Client()
    resp = client2.post(
        "/api/auth/login",
        data={"email": "new@example.com", "password": "pw12345!strong"},
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert ActivityLog.objects.filter(verb=ActivityVerb.SIGNED_IN, actor_label="new@example.com").exists()


def test_claiming_a_free_product_is_logged(free_product):
    user, client = _login()
    client.post("/api/account/claim-free", data={"slug": free_product.slug}, content_type="application/json")
    entry = ActivityLog.objects.get(verb=ActivityVerb.CLAIMED_FREE_PRODUCT)
    assert entry.actor_id == user.id
    assert entry.target_label == free_product.name


def test_posting_a_review_is_logged(free_product):
    user, client = _login()
    sku = LicensedProduct.objects.get(code=free_product.product_code)
    ProductPurchase.objects.create(user=user, product=sku, payment_status=ProductPurchase.PaymentStatus.PAID)
    client.post(
        f"/api/products/{free_product.slug}/reviews",
        data={"rating": 5, "title": "Great", "body": "Good stuff"},
        content_type="application/json",
    )
    assert ActivityLog.objects.filter(verb=ActivityVerb.POSTED_REVIEW, target_label=free_product.name).exists()


def test_download_logs_and_redirects_only_for_entitled_users(free_product):
    from catalog.models import ProductFile

    owner, owner_client = _login("owner@example.com")
    stranger, stranger_client = _login("stranger@example.com")
    sku = LicensedProduct.objects.get(code=free_product.product_code)
    ProductPurchase.objects.create(user=owner, product=sku, payment_status=ProductPurchase.PaymentStatus.PAID)
    file = ProductFile.objects.create(
        product=free_product, revit_version="2025", version_label="1.0.0", storage_key="product_files/x/y.exe",
    )

    # Not entitled: rejected, nothing logged.
    resp = stranger_client.get(f"/api/account/downloads/{file.id}/get")
    assert resp.status_code == 400
    assert not ActivityLog.objects.filter(verb=ActivityVerb.DOWNLOADED_FILE).exists()

    # Entitled: redirected to the real file, and it's logged.
    resp = owner_client.get(f"/api/account/downloads/{file.id}/get")
    assert resp.status_code == 302
    entry = ActivityLog.objects.get(verb=ActivityVerb.DOWNLOADED_FILE)
    assert entry.actor_id == owner.id
    assert entry.metadata["file_id"] == file.id


def test_admin_product_crud_is_logged(staff_client, category):
    resp = staff_client.post(
        "/api/admin/products",
        data={
            "name": "New Product", "short_description": "s", "description": "d",
            "category": category.id, "price": "10.00",
        },
        content_type="application/json",
    )
    assert resp.status_code == 201
    product_id = resp.json()["id"]
    assert ActivityLog.objects.filter(verb=ActivityVerb.PRODUCT_CREATED, target_label="New Product").exists()

    staff_client.patch(
        f"/api/admin/products/{product_id}", data={"name": "Renamed Product"}, content_type="application/json"
    )
    assert ActivityLog.objects.filter(verb=ActivityVerb.PRODUCT_UPDATED, target_label="Renamed Product").exists()

    staff_client.delete(f"/api/admin/products/{product_id}")
    assert ActivityLog.objects.filter(verb=ActivityVerb.PRODUCT_DELETED, target_label="Renamed Product").exists()


def test_admin_license_actions_are_logged(staff_client, free_product):
    from licensing.models import MachineLicense

    sku = LicensedProduct.objects.get(code=free_product.product_code)
    ml = MachineLicense.objects.create(
        product=sku, machine_fingerprint_hash="ABC123", status="active",
        started_at=timezone.now(), expires_at=timezone.now(),
    )

    staff_client.post(f"/api/admin/licenses/{ml.id}/revoke")
    assert ActivityLog.objects.filter(verb=ActivityVerb.LICENSE_REVOKED).exists()

    staff_client.post(f"/api/admin/licenses/{ml.id}/restore")
    assert ActivityLog.objects.filter(verb=ActivityVerb.LICENSE_RESTORED).exists()

    staff_client.post(f"/api/admin/licenses/{ml.id}/extend", data={"days": 30}, content_type="application/json")
    entry = ActivityLog.objects.get(verb=ActivityVerb.LICENSE_EXTENDED)
    assert entry.metadata["days"] == 30


def test_admin_order_status_change_is_logged(staff_client, free_product):
    owner, _ = _login("owner@example.com")
    sku = LicensedProduct.objects.get(code=free_product.product_code)
    purchase = ProductPurchase.objects.create(
        user=owner, product=sku, payment_status=ProductPurchase.PaymentStatus.PAID
    )

    resp = staff_client.post(
        f"/api/admin/orders/{purchase.id}/status", data={"action": "refund"}, content_type="application/json"
    )
    assert resp.status_code == 200
    entry = ActivityLog.objects.get(verb=ActivityVerb.ORDER_STATUS_CHANGED)
    assert entry.target_label == free_product.name
    assert entry.metadata["action"] == "refund"


# ── The activity list itself: access control + filters ──
def test_activity_list_requires_staff():
    resp = Client().get("/api/admin/activity")
    assert resp.status_code in (401, 403)

    _, client = _login()
    resp = client.get("/api/admin/activity")
    assert resp.status_code == 403


def test_activity_list_filters_by_actor_and_verb(staff_client, free_product):
    user_a, client_a = _login("alice@example.com")
    user_b, client_b = _login("bob@example.com")
    client_a.post("/api/account/claim-free", data={"slug": free_product.slug}, content_type="application/json")
    sku = LicensedProduct.objects.get(code=free_product.product_code)
    ProductPurchase.objects.create(user=user_b, product=sku, payment_status=ProductPurchase.PaymentStatus.PAID)
    client_b.post(
        f"/api/products/{free_product.slug}/reviews",
        data={"rating": 4, "title": "Fine", "body": "It's fine"},
        content_type="application/json",
    )

    resp = staff_client.get("/api/admin/activity?actor=alice")
    rows = resp.json()
    assert all("alice" in r["actor_label"] for r in rows)
    assert any(r["verb"] == "claimed_free_product" for r in rows)

    resp = staff_client.get("/api/admin/activity?verb=posted_review")
    rows = resp.json()
    assert rows and all(r["verb"] == "posted_review" for r in rows)


def test_activity_list_filters_by_date_range(staff_client, free_product):
    _, client = _login()
    client.post("/api/account/claim-free", data={"slug": free_product.slug}, content_type="application/json")

    tomorrow = (timezone.now() + timezone.timedelta(days=1)).date().isoformat()
    resp = staff_client.get(f"/api/admin/activity?date_from={tomorrow}")
    assert resp.json() == []  # nothing happened "tomorrow" yet

    today = timezone.now().date().isoformat()
    resp = staff_client.get(f"/api/admin/activity?date_from={today}")
    assert len(resp.json()) >= 1
