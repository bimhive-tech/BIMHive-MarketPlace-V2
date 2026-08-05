"""
The two-level taxonomy: one top-level category with subcategories under it
(see migration 0014 and catalog/views.py).
"""
import pytest
from django.contrib.auth import get_user_model

from catalog.models import Category, Product
from catalog.models.product import ProductStatus

pytestmark = pytest.mark.django_db
User = get_user_model()


@pytest.fixture
def root():
    return Category.objects.create(name="Revit Plugins")


@pytest.fixture
def staff_client(client):
    user = User.objects.create_user(username="admin@x.com", email="admin@x.com", password="x", is_staff=True)
    client.force_login(user)
    return client


def make_product(name, category):
    return Product.objects.create(
        name=name, short_description="s", description="d",
        category=category, price="10.00", status=ProductStatus.PUBLISHED,
    )


# ── Public API ──
def test_category_list_nests_subcategories_under_their_root(client, root):
    Category.objects.create(name="Model Cleanup", parent=root)
    Category.objects.create(name="Sheet Automation", parent=root)

    body = client.get("/api/categories").json()

    assert [c["slug"] for c in body] == ["revit-plugins"]
    assert [c["name"] for c in body[0]["children"]] == ["Model Cleanup", "Sheet Automation"]
    assert body[0]["children"][0]["parent_slug"] == "revit-plugins"


def test_root_product_count_includes_its_subcategories(client, root):
    child = Category.objects.create(name="Model Cleanup", parent=root)
    make_product("Direct", root)
    make_product("Nested", child)

    body = client.get("/api/categories").json()

    assert body[0]["product_count"] == 2
    assert body[0]["children"][0]["product_count"] == 1


def test_filtering_by_the_root_returns_subcategory_products_too(client, root):
    child = Category.objects.create(name="Model Cleanup", parent=root)
    make_product("Direct", root)
    make_product("Nested", child)

    body = client.get("/api/products?category=revit-plugins").json()

    assert {p["name"] for p in body["results"]} == {"Direct", "Nested"}


def test_filtering_by_a_subcategory_narrows_to_just_it(client, root):
    child = Category.objects.create(name="Model Cleanup", parent=root)
    make_product("Direct", root)
    make_product("Nested", child)

    body = client.get("/api/products?category=model-cleanup").json()

    assert [p["name"] for p in body["results"]] == ["Nested"]


def test_subcategory_detail_resolves_by_slug(client, root):
    Category.objects.create(name="Model Cleanup", parent=root)

    body = client.get("/api/categories/model-cleanup").json()

    assert body["name"] == "Model Cleanup"
    assert body["parent_slug"] == "revit-plugins"


# ── Admin API guardrails ──
def test_admin_can_create_a_subcategory(staff_client, root):
    resp = staff_client.post(
        "/api/admin/categories",
        {"name": "Model Cleanup", "parent": root.id},
        content_type="application/json",
    )

    assert resp.status_code == 201, resp.json()
    assert resp.json()["parent_name"] == "Revit Plugins"


def test_admin_cannot_nest_a_subcategory_under_another_subcategory(staff_client, root):
    child = Category.objects.create(name="Model Cleanup", parent=root)

    resp = staff_client.post(
        "/api/admin/categories",
        {"name": "Too Deep", "parent": child.id},
        content_type="application/json",
    )

    assert resp.status_code == 400
    assert "nested" in str(resp.json()["parent"]).lower()


def test_admin_cannot_make_a_category_its_own_parent(staff_client, root):
    resp = staff_client.patch(
        f"/api/admin/categories/{root.id}",
        {"parent": root.id},
        content_type="application/json",
    )

    assert resp.status_code == 400


def test_admin_cannot_demote_a_category_that_has_children(staff_client, root):
    Category.objects.create(name="Model Cleanup", parent=root)
    other_root = Category.objects.create(name="Services")

    resp = staff_client.patch(
        f"/api/admin/categories/{root.id}",
        {"parent": other_root.id},
        content_type="application/json",
    )

    assert resp.status_code == 400
    assert "subcategories of its own" in str(resp.json()["parent"])
