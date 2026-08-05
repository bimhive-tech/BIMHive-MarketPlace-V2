"""
The homepage hero's product selection (catalog.views._spotlight_products) —
staff curation via Product.is_hero_featured/hero_sort_order always wins over
the automatic discounted/featured fallback.
"""
from datetime import timedelta

import pytest
from django.utils import timezone

from catalog.models import Category, Product, Promotion
from catalog.models.product import ProductStatus

pytestmark = pytest.mark.django_db


@pytest.fixture
def root():
    return Category.objects.create(name="Revit Plugins")


def make_product(name, root, **overrides):
    fields = {
        "name": name, "short_description": "s", "description": "d", "category": root,
        "price": "10.00", "status": ProductStatus.PUBLISHED,
    }
    fields.update(overrides)
    return Product.objects.create(**fields)


def test_curated_products_win_over_the_automatic_pick(client, root):
    make_product("Featured", root, is_featured=True)
    curated = make_product("Curated", root, is_hero_featured=True, hero_sort_order=0)

    body = client.get("/api/home").json()

    assert [p["name"] for p in body["spotlight_products"]] == [curated.name]


def test_curated_products_are_ordered_by_hero_sort_order(client, root):
    make_product("Second", root, is_hero_featured=True, hero_sort_order=2)
    make_product("First", root, is_hero_featured=True, hero_sort_order=1)

    body = client.get("/api/home").json()

    assert [p["name"] for p in body["spotlight_products"]] == ["First", "Second"]


def test_falls_back_to_discounted_then_featured_when_nothing_is_curated(client, root):
    now = timezone.now()
    discounted = make_product("On Sale", root, is_featured=False)
    Promotion.objects.create(
        name="Promo", headline="x", discount_percent=10, scope=Promotion.Scope.PRODUCTS,
        starts_at=now - timedelta(hours=1), ends_at=now + timedelta(days=1),
    ).products.add(discounted)
    featured = make_product("Featured", root, is_featured=True)

    body = client.get("/api/home").json()

    assert [p["name"] for p in body["spotlight_products"]] == ["On Sale", "Featured"]


def test_an_unpublished_product_is_never_curated_into_the_hero(client, root):
    make_product("Draft", root, is_hero_featured=True, status=ProductStatus.DRAFT)

    body = client.get("/api/home").json()

    assert body["spotlight_products"] == []
