"""The three partner-pipeline gaps closed on 2026-09-13.

1. An approved partner could change a LIVE product (details, files, the plugin
   build customers download) and it went live instantly with no review.
2. A rejected seller application was permanent: no way to fix it and resubmit.
3. Nobody was told about a review outcome — there's no email, and the
   notifications feed only showed a user's own actions.
"""
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from activity.models import ActivityLog, ActivityVerb
from catalog.models import Category, Partner, Product, ProductFile
from catalog.models.product import ProductStatus, ProductType

pytestmark = pytest.mark.django_db
User = get_user_model()


@pytest.fixture
def category():
    return Category.objects.create(name="Revit Plugins")


@pytest.fixture
def partner():
    return Partner.objects.create(name="Arch Tools", status=Partner.ApplicationStatus.APPROVED)


@pytest.fixture
def partner_user(partner):
    return User.objects.create_user(username="seller@x.com", email="seller@x.com", password="x", partner=partner)


@pytest.fixture
def partner_client(client, partner_user):
    client.force_login(partner_user)
    return client


@pytest.fixture
def staff_client():
    from django.test import Client

    staff = User.objects.create_user(
        username="admin@x.com", email="admin@x.com", password="x", is_staff=True, is_superuser=True
    )
    c = Client()
    c.force_login(staff)
    return c


@pytest.fixture
def live_product(category, partner):
    return Product.objects.create(
        name="Clash Finder", short_description="Finds clashes.", description="d", category=category,
        partner=partner, status=ProductStatus.PUBLISHED, type=ProductType.PLUGIN, product_code="clash-finder",
    )


def _form_payload(product, **changes):
    """What the product form actually sends: everything, every save."""
    return {
        "name": product.name, "short_description": product.short_description,
        "description": product.description, "category": product.category_id,
        "price": str(product.price), "status": product.status, "type": product.type,
        "features": [], "media": [], "changelog": [], "compatibility": [], "documentation": None,
        **changes,
    }


# ── 1. Live edits go back for review ──
def test_a_partner_changing_a_live_product_sends_it_back_for_review(partner_client, live_product):
    resp = partner_client.patch(
        f"/api/admin/products/{live_product.id}",
        _form_payload(live_product, short_description="Now finds even more clashes."),
        content_type="application/json",
    )

    assert resp.status_code == 200, resp.json()
    live_product.refresh_from_db()
    assert live_product.status == ProductStatus.PENDING
    assert live_product.short_description == "Now finds even more clashes."


def test_an_unchanged_resave_keeps_a_live_product_live(partner_client, live_product):
    """The form resends everything on every save — that alone mustn't unpublish."""
    resp = partner_client.patch(
        f"/api/admin/products/{live_product.id}", _form_payload(live_product), content_type="application/json"
    )

    assert resp.status_code == 200, resp.json()
    live_product.refresh_from_db()
    assert live_product.status == ProductStatus.PUBLISHED


def test_a_freshly_resigned_media_url_is_not_a_change(partner_client, live_product):
    """Media URLs are re-signed on every read and posted back, so only the
    signature differs between two otherwise identical saves."""
    item = {"media_type": "image", "url": "https://r2.example/bucket/cover.png?X-Amz-Signature=aaa",
            "caption": "", "is_cover": True}
    partner_client.patch(
        f"/api/admin/products/{live_product.id}", _form_payload(live_product, media=[item]),
        content_type="application/json",
    )
    Product.objects.filter(pk=live_product.pk).update(status=ProductStatus.PUBLISHED)
    live_product.refresh_from_db()

    resigned = {**item, "url": "https://r2.example/bucket/cover.png?X-Amz-Signature=bbb"}
    partner_client.patch(
        f"/api/admin/products/{live_product.id}", _form_payload(live_product, media=[resigned]),
        content_type="application/json",
    )

    live_product.refresh_from_db()
    assert live_product.status == ProductStatus.PUBLISHED


def test_staff_editing_a_live_product_keeps_it_live(staff_client, live_product):
    resp = staff_client.patch(
        f"/api/admin/products/{live_product.id}",
        _form_payload(live_product, short_description="Copy edit by staff."),
        content_type="application/json",
    )

    assert resp.status_code == 200, resp.json()
    live_product.refresh_from_db()
    assert live_product.status == ProductStatus.PUBLISHED


def test_uploading_a_file_to_a_live_product_sends_it_back_for_review(partner_client, live_product):
    upload = SimpleUploadedFile("plugin.exe", b"new installer", content_type="application/octet-stream")
    with patch("django.core.files.storage.default_storage.save", return_value="product_files/plugin.exe"):
        resp = partner_client.post(
            f"/api/admin/products/{live_product.id}/files",
            {"revit_version": "2025", "version_label": "2.0.0", "is_current": "true", "file": upload},
        )

    assert resp.status_code == 201, resp.json()
    live_product.refresh_from_db()
    assert live_product.status == ProductStatus.PENDING


def test_removing_a_file_from_a_live_product_sends_it_back_for_review(partner_client, live_product):
    product_file = ProductFile.objects.create(
        product=live_product, revit_version="2025", version_label="1.0.0", storage_key="", file_size_bytes=1
    )

    resp = partner_client.delete(f"/api/admin/products/files/{product_file.id}")

    assert resp.status_code == 204
    live_product.refresh_from_db()
    assert live_product.status == ProductStatus.PENDING


def test_adding_a_plugin_build_to_a_live_product_sends_it_back_for_review(partner_client, live_product):
    resp = partner_client.post(f"/api/admin/products/{live_product.id}/plugin-builds", {"revit_year": "2026"})

    assert resp.status_code == 201, resp.json()
    live_product.refresh_from_db()
    assert live_product.status == ProductStatus.PENDING


def test_a_draft_product_is_not_affected(partner_client, live_product):
    Product.objects.filter(pk=live_product.pk).update(status=ProductStatus.DRAFT)
    live_product.refresh_from_db()

    partner_client.patch(
        f"/api/admin/products/{live_product.id}",
        _form_payload(live_product, short_description="Still drafting."),
        content_type="application/json",
    )

    live_product.refresh_from_db()
    assert live_product.status == ProductStatus.DRAFT


# ── 2. A rejected application can be resubmitted ──
def test_a_rejected_seller_can_resubmit_their_application(partner_client, partner):
    Partner.objects.filter(pk=partner.pk).update(
        status=Partner.ApplicationStatus.REJECTED, rejection_note="Add a website."
    )

    resp = partner_client.post("/api/partner/application/resubmit")

    assert resp.status_code == 200, resp.json()
    partner.refresh_from_db()
    assert partner.status == Partner.ApplicationStatus.PENDING
    assert partner.rejection_note == "", "the old reason is cleared so staff don't act on it again"


def test_only_a_rejected_application_can_be_resubmitted(partner_client, partner):
    resp = partner_client.post("/api/partner/application/resubmit")

    assert resp.status_code == 400
    partner.refresh_from_db()
    assert partner.status == Partner.ApplicationStatus.APPROVED


def test_someone_without_an_application_cannot_resubmit(client):
    customer = User.objects.create_user(username="c@x.com", email="c@x.com", password="x")
    client.force_login(customer)

    assert client.post("/api/partner/application/resubmit").status_code == 403


# ── 3. Review outcomes reach the seller's notifications ──
def _feed(client):
    return client.get("/api/account/activity").json()


def test_a_rejected_product_shows_in_the_sellers_notifications_with_the_reason(
    staff_client, partner_client, category, partner
):
    product = Product.objects.create(
        name="Sheet Tool", short_description="s", description="d", category=category,
        partner=partner, status=ProductStatus.PENDING,
    )

    staff_client.patch(
        f"/api/admin/products/{product.id}",
        {"status": "rejected", "rejection_note": "Add screenshots."},
        content_type="application/json",
    )

    rows = [r for r in _feed(partner_client) if r["verb"] == ActivityVerb.PRODUCT_REJECTED]
    assert len(rows) == 1
    assert rows[0]["target_label"] == "Sheet Tool"
    assert rows[0]["note"] == "Add screenshots."


def test_an_application_decision_shows_in_the_applicants_notifications(staff_client, partner_client, partner):
    Partner.objects.filter(pk=partner.pk).update(status=Partner.ApplicationStatus.PENDING)

    staff_client.patch(f"/api/admin/partners/{partner.id}", {"status": "approved"}, content_type="application/json")

    verbs = [r["verb"] for r in _feed(partner_client)]
    assert ActivityVerb.PARTNER_APPROVED in verbs


def test_a_live_edit_sent_back_for_review_is_in_the_feed(partner_client, live_product):
    partner_client.patch(
        f"/api/admin/products/{live_product.id}",
        _form_payload(live_product, short_description="Changed."),
        content_type="application/json",
    )

    assert ActivityVerb.PRODUCT_SUBMITTED_FOR_REVIEW in [r["verb"] for r in _feed(partner_client)]


def test_one_sellers_outcomes_never_reach_another_seller(staff_client, category, partner):
    from django.test import Client

    other_partner = Partner.objects.create(name="Other Co", status=Partner.ApplicationStatus.APPROVED)
    other_user = User.objects.create_user(
        username="other@x.com", email="other@x.com", password="x", partner=other_partner
    )
    other_client = Client()
    other_client.force_login(other_user)
    product = Product.objects.create(
        name="Private", short_description="s", description="d", category=category,
        partner=partner, status=ProductStatus.PENDING,
    )

    staff_client.patch(
        f"/api/admin/products/{product.id}", {"status": "rejected", "rejection_note": "No."},
        content_type="application/json",
    )

    assert _feed(other_client) == []
    assert ActivityLog.objects.filter(verb=ActivityVerb.PRODUCT_REJECTED).count() == 1
