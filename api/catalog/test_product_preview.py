"""
Staff product preview (AdminProductPreviewView) — renders an unpublished
product through the real storefront serializer so the admin form can show
"how this will look" without the product being live. The public detail route
can't do this: /api/products/<slug> is published-and-public only.
"""
import pytest
from django.contrib.auth import get_user_model

from accounts.models import Role
from catalog.models import Category, Partner, Product
from catalog.models.product import ProductStatus, ProductVisibility

pytestmark = pytest.mark.django_db
User = get_user_model()


@pytest.fixture
def category():
    return Category.objects.create(name="Revit Plugins")


@pytest.fixture
def partner():
    return Partner.objects.create(name="BIMHIVE", status=Partner.ApplicationStatus.APPROVED)


@pytest.fixture
def draft(category, partner):
    return Product.objects.create(
        name="Unreleased Tool", short_description="s", description="d",
        category=category, partner=partner, status=ProductStatus.DRAFT,
    )


def _staff_client(client, permissions):
    role = Role.objects.create(name="Role", grants_staff_access=True, permissions=permissions)
    user = User.objects.create_user(
        username="s@x.com", email="s@x.com", password="x", is_staff=True, role=role,
    )
    client.force_login(user)
    return client


def test_preview_returns_a_draft_the_public_route_hides(client, draft):
    staff = _staff_client(client, ["products.manage"])

    # The public route genuinely can't serve it...
    assert client.get(f"/api/products/{draft.slug}").status_code == 404
    # ...but the preview can.
    resp = staff.get(f"/api/admin/products/{draft.id}/preview")

    assert resp.status_code == 200, resp.json()
    assert resp.json()["name"] == "Unreleased Tool"


def test_preview_includes_the_server_computed_fields_the_storefront_needs(client, draft):
    staff = _staff_client(client, ["products.manage"])

    body = staff.get(f"/api/admin/products/{draft.id}/preview").json()

    # These are exactly the fields a client-side rebuild would have had to
    # reimplement — the whole reason this is a server endpoint.
    for field in ["price_label", "is_free", "is_subscription", "has_trial", "promotion", "category"]:
        assert field in body, field


def test_preview_also_works_for_a_hidden_product(client, category, partner):
    hidden = Product.objects.create(
        name="Hidden Tool", short_description="s", description="d", category=category,
        partner=partner, status=ProductStatus.PUBLISHED, visibility=ProductVisibility.HIDDEN,
    )
    staff = _staff_client(client, ["products.manage"])

    assert staff.get(f"/api/admin/products/{hidden.id}/preview").status_code == 200


def test_preview_requires_products_manage(client, draft):
    staff = _staff_client(client, ["reviews.moderate"])

    assert staff.get(f"/api/admin/products/{draft.id}/preview").status_code == 403


def test_preview_is_not_public(client, draft):
    assert client.get(f"/api/admin/products/{draft.id}/preview").status_code in (401, 403)


def test_a_partner_cannot_preview_another_partners_product(client, category, draft):
    other_partner = Partner.objects.create(
        name="Someone Else", status=Partner.ApplicationStatus.APPROVED
    )
    user = User.objects.create_user(
        username="p@x.com", email="p@x.com", password="x", partner=other_partner,
    )
    client.force_login(user)

    # 404, not 403 — same as the edit view, so it doesn't confirm the id exists.
    assert client.get(f"/api/admin/products/{draft.id}/preview").status_code == 404
