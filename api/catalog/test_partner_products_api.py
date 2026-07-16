"""
Partner self-service product management: a partner-linked (non-staff) user can
create/edit/upload files on their OWN products only, can never self-publish or
self-reject (only BIMHive staff can), and can never see or touch another
partner's products, files, or media. See catalog/permissions.py (IsStaffOrPartner)
and the partner-branching logic in AdminProductDetailSerializer (admin_api.py).
"""
import pytest
from django.contrib.auth import get_user_model

from catalog.models import Category, Partner, Product, ProductFile

pytestmark = pytest.mark.django_db
User = get_user_model()


@pytest.fixture
def category():
    return Category.objects.create(name="Revit Plugins")


@pytest.fixture
def partner_a():
    return Partner.objects.create(name="Partner A")


@pytest.fixture
def partner_b():
    return Partner.objects.create(name="Partner B")


@pytest.fixture
def partner_a_client(client, partner_a):
    user = User.objects.create_user(
        username="a@partner.com", email="a@partner.com", password="x", partner=partner_a
    )
    client.force_login(user)
    return client


@pytest.fixture
def partner_b_client(client, partner_b):
    user = User.objects.create_user(
        username="b@partner.com", email="b@partner.com", password="x", partner=partner_b
    )
    client.force_login(user)
    return client


@pytest.fixture
def staff_client(client):
    user = User.objects.create_user(username="admin@x.com", email="admin@x.com", password="x", is_staff=True)
    client.force_login(user)
    return client


def _base_payload(category, **overrides):
    payload = {
        "name": "Partner Tool", "short_description": "s", "description": "d",
        "category": category.id, "price": "10.00", "status": "draft",
    }
    payload.update(overrides)
    return payload


# ── Anonymous / plain customer can't reach any of this ──
def test_anonymous_cannot_list_products(client):
    resp = client.get("/api/admin/products")
    assert resp.status_code in (401, 403)


def test_plain_customer_cannot_list_products(client):
    User.objects.create_user(username="c@x.com", email="c@x.com", password="x")
    client.force_login(User.objects.get(email="c@x.com"))
    resp = client.get("/api/admin/products")
    assert resp.status_code == 403


# ── Create: force-scoped to own partner, status locked to draft/pending ──
def test_partner_create_is_force_scoped_to_own_partner(partner_a_client, partner_b, category):
    # Even if the payload tries to claim another partner's id, it's ignored.
    resp = partner_a_client.post(
        "/api/admin/products", _base_payload(category, partner=partner_b.id), content_type="application/json"
    )
    assert resp.status_code == 201, resp.json()
    product = Product.objects.get(pk=resp.json()["id"])
    assert product.partner_id != partner_b.id
    assert product.partner.name == "Partner A"


def test_partner_cannot_create_as_published(partner_a_client, category):
    resp = partner_a_client.post(
        "/api/admin/products", _base_payload(category, status="published"), content_type="application/json"
    )
    assert resp.status_code == 400
    assert "status" in resp.json()


def test_partner_can_create_as_pending(partner_a_client, category):
    resp = partner_a_client.post(
        "/api/admin/products", _base_payload(category, status="pending"), content_type="application/json"
    )
    assert resp.status_code == 201, resp.json()
    assert resp.json()["status"] == "pending"


# ── Update: can't repoint partner, can't self-approve/reject ──
def test_partner_update_cannot_repoint_partner_field(partner_a_client, partner_a, partner_b, category):
    product = Product.objects.create(
        name="Mine", short_description="s", description="d", category=category, partner=partner_a,
    )
    resp = partner_a_client.patch(
        f"/api/admin/products/{product.id}", {"partner": partner_b.id}, content_type="application/json"
    )
    assert resp.status_code == 200, resp.json()
    product.refresh_from_db()
    assert product.partner_id == partner_a.id


def test_partner_update_cannot_set_published(partner_a_client, partner_a, category):
    product = Product.objects.create(
        name="Mine", short_description="s", description="d", category=category, partner=partner_a,
    )
    resp = partner_a_client.patch(
        f"/api/admin/products/{product.id}", {"status": "published"}, content_type="application/json"
    )
    assert resp.status_code == 400


def test_partner_update_cannot_set_rejected(partner_a_client, partner_a, category):
    product = Product.objects.create(
        name="Mine", short_description="s", description="d", category=category, partner=partner_a,
    )
    resp = partner_a_client.patch(
        f"/api/admin/products/{product.id}", {"status": "rejected"}, content_type="application/json"
    )
    assert resp.status_code == 400


def test_partner_can_resave_an_already_published_product_without_touching_status(
    partner_a_client, partner_a, category
):
    # The frontend always resends the currently-loaded status on every save —
    # a partner editing an already-approved product's description must not get
    # rejected just because "published" appears in the payload unchanged.
    product = Product.objects.create(
        name="Mine", short_description="s", description="d", category=category, partner=partner_a,
        status="published",
    )
    resp = partner_a_client.patch(
        f"/api/admin/products/{product.id}",
        {"short_description": "Updated tagline", "status": "published"},
        content_type="application/json",
    )
    assert resp.status_code == 200, resp.json()
    product.refresh_from_db()
    assert product.short_description == "Updated tagline"
    assert product.status == "published"


def test_partner_can_resave_an_already_rejected_product_without_touching_status(
    partner_a_client, partner_a, category
):
    product = Product.objects.create(
        name="Mine", short_description="s", description="d", category=category, partner=partner_a,
        status="rejected", rejection_note="Installer flagged by antivirus.",
    )
    resp = partner_a_client.patch(
        f"/api/admin/products/{product.id}",
        {"description": "Fixed the flagged installer.", "status": "rejected"},
        content_type="application/json",
    )
    assert resp.status_code == 200, resp.json()
    product.refresh_from_db()
    assert product.description == "Fixed the flagged installer."
    # Still can't clear/rewrite the note themselves.
    assert product.rejection_note == "Installer flagged by antivirus."


def test_partner_can_resubmit_a_rejected_product_for_review(partner_a_client, partner_a, category):
    product = Product.objects.create(
        name="Mine", short_description="s", description="d", category=category, partner=partner_a,
        status="rejected", rejection_note="Fix the icon.",
    )
    resp = partner_a_client.patch(
        f"/api/admin/products/{product.id}", {"status": "pending"}, content_type="application/json"
    )
    assert resp.status_code == 200, resp.json()
    product.refresh_from_db()
    assert product.status == "pending"


def test_staff_can_approve_a_partner_product(staff_client, partner_a, category):
    product = Product.objects.create(
        name="Mine", short_description="s", description="d", category=category, partner=partner_a,
        status="pending",
    )
    ProductFile.objects.create(product=product, revit_version="2025", version_label="1.0.0", storage_key="x/y.exe")
    resp = staff_client.patch(
        f"/api/admin/products/{product.id}", {"status": "published"}, content_type="application/json"
    )
    assert resp.status_code == 200, resp.json()
    product.refresh_from_db()
    assert product.status == "published"


# ── Cross-partner isolation: list, detail, files, media ──
def test_partner_list_only_shows_own_products(partner_a_client, partner_a, partner_b, category):
    Product.objects.create(name="Mine", short_description="s", description="d", category=category, partner=partner_a)
    Product.objects.create(
        name="Not mine", short_description="s", description="d", category=category, partner=partner_b
    )
    resp = partner_a_client.get("/api/admin/products")
    names = [row["name"] for row in resp.json()]
    assert names == ["Mine"]


def test_partner_cannot_view_another_partners_product_detail(partner_a_client, partner_b, category):
    other = Product.objects.create(
        name="Not mine", short_description="s", description="d", category=category, partner=partner_b
    )
    resp = partner_a_client.get(f"/api/admin/products/{other.id}")
    assert resp.status_code == 404


def test_partner_cannot_upload_file_to_another_partners_product(partner_a_client, partner_b, category):
    from django.core.files.uploadedfile import SimpleUploadedFile

    other = Product.objects.create(
        name="Not mine", short_description="s", description="d", category=category, partner=partner_b
    )
    upload = SimpleUploadedFile("plugin.exe", b"fake installer bytes", content_type="application/octet-stream")
    resp = partner_a_client.post(
        f"/api/admin/products/{other.id}/files",
        {"revit_version": "2025", "version_label": "1.0.0", "is_current": "true", "file": upload},
    )
    assert resp.status_code == 404


def test_partner_cannot_upload_media_to_another_partners_product(partner_a_client, partner_b, category):
    from django.core.files.uploadedfile import SimpleUploadedFile

    other = Product.objects.create(
        name="Not mine", short_description="s", description="d", category=category, partner=partner_b
    )
    upload = SimpleUploadedFile("cover.png", b"fake png bytes", content_type="image/png")
    resp = partner_a_client.post(f"/api/admin/products/{other.id}/media-upload", data={"file": upload})
    assert resp.status_code == 400  # existence-style 400, matches the endpoint's own not-found style


def test_partner_cannot_delete_another_partners_file(partner_a_client, partner_b, category):
    other = Product.objects.create(
        name="Not mine", short_description="s", description="d", category=category, partner=partner_b
    )
    other_file = ProductFile.objects.create(
        product=other, revit_version="2025", version_label="1.0.0", storage_key="x/y.exe"
    )
    resp = partner_a_client.delete(f"/api/admin/products/files/{other_file.id}")
    assert resp.status_code == 404


# ── AdminOptionsView: partner list is never leaked to a partner caller ──
def test_options_hides_partner_list_from_partner_caller(partner_a_client, partner_a, partner_b):
    resp = partner_a_client.get("/api/admin/options")
    assert resp.status_code == 200
    assert resp.json()["partners"] == []


def test_options_shows_partner_list_to_staff(staff_client, partner_a, partner_b):
    resp = staff_client.get("/api/admin/options")
    assert resp.status_code == 200
    names = {p["name"] for p in resp.json()["partners"]}
    assert {"Partner A", "Partner B"} <= names


# ── Staff behavior stays fully unchanged ──
def test_staff_still_sees_all_partners_products(staff_client, partner_a, partner_b, category):
    Product.objects.create(name="A's", short_description="s", description="d", category=category, partner=partner_a)
    Product.objects.create(name="B's", short_description="s", description="d", category=category, partner=partner_b)
    resp = staff_client.get("/api/admin/products")
    names = {row["name"] for row in resp.json()}
    assert {"A's", "B's"} <= names


def test_staff_can_still_create_without_a_partner(staff_client, category):
    resp = staff_client.post(
        "/api/admin/products", _base_payload(category), content_type="application/json"
    )
    assert resp.status_code == 201, resp.json()
    assert resp.json()["partner"] is None


# ── Partner self-profile (GET/PATCH /api/partner/profile) ──
def test_partner_can_view_and_edit_own_profile(partner_a_client, partner_a):
    resp = partner_a_client.get("/api/partner/profile")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Partner A"

    resp = partner_a_client.patch(
        "/api/partner/profile",
        {"tagline": "Great tools", "bio": "We make things.", "website": "https://example.com"},
        content_type="application/json",
    )
    assert resp.status_code == 200, resp.json()
    partner_a.refresh_from_db()
    assert partner_a.tagline == "Great tools"
    assert partner_a.website == "https://example.com"


def test_partner_cannot_rename_or_self_verify_via_profile(partner_a_client, partner_a):
    resp = partner_a_client.patch(
        "/api/partner/profile", {"name": "Hijacked", "is_verified": True}, content_type="application/json"
    )
    assert resp.status_code == 200, resp.json()
    partner_a.refresh_from_db()
    assert partner_a.name == "Partner A"
    assert partner_a.is_verified is False


def test_plain_customer_cannot_reach_partner_profile(client):
    User.objects.create_user(username="c2@x.com", email="c2@x.com", password="x")
    client.force_login(User.objects.get(email="c2@x.com"))
    resp = client.get("/api/partner/profile")
    assert resp.status_code == 403


def test_staff_without_a_partner_cannot_reach_partner_profile(staff_client):
    resp = staff_client.get("/api/partner/profile")
    assert resp.status_code == 403


# ── Admin issues a partner login (POST /api/admin/partners/{id}/set-login) ──
def test_admin_issues_a_new_partner_login(staff_client, partner_a):
    resp = staff_client.post(
        f"/api/admin/partners/{partner_a.id}/set-login", {"email": "new@partnera.com"},
        content_type="application/json",
    )
    assert resp.status_code == 201, resp.json()
    body = resp.json()
    assert body["email"] == "new@partnera.com"
    assert body["password"]  # auto-generated, returned exactly once

    user = User.objects.get(email="new@partnera.com")
    assert user.partner_id == partner_a.id
    assert user.must_change_password is True
    assert user.check_password(body["password"])


def test_admin_can_relink_an_existing_user_as_a_partner_login(staff_client, partner_a):
    existing = User.objects.create_user(username="already@x.com", email="already@x.com", password="oldpw")
    resp = staff_client.post(
        f"/api/admin/partners/{partner_a.id}/set-login",
        {"email": "already@x.com", "password": "NewPassword!123"},
        content_type="application/json",
    )
    assert resp.status_code == 201, resp.json()
    existing.refresh_from_db()
    assert existing.partner_id == partner_a.id
    assert existing.check_password("NewPassword!123")


def test_partner_admin_form_shows_owner_email_once_issued(staff_client, partner_a):
    staff_client.post(
        f"/api/admin/partners/{partner_a.id}/set-login", {"email": "owner@partnera.com"},
        content_type="application/json",
    )
    resp = staff_client.get(f"/api/admin/partners/{partner_a.id}")
    assert resp.json()["owner_email"] == "owner@partnera.com"


def test_non_staff_cannot_issue_a_partner_login(partner_a_client, partner_a):
    resp = partner_a_client.post(
        f"/api/admin/partners/{partner_a.id}/set-login", {"email": "sneaky@x.com"},
        content_type="application/json",
    )
    assert resp.status_code == 403
