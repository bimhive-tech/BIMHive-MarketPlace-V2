"""
The temporary "New" / "Updated" badges (catalog.models.Product.is_new/is_updated)
— including that they expire on their own once the window passes.
"""
from datetime import timedelta

import pytest
from django.utils import timezone

from catalog.models import Category, Product
from catalog.models.product import ProductStatus

pytestmark = pytest.mark.django_db


@pytest.fixture
def root():
    return Category.objects.create(name="Revit Plugins")


@pytest.fixture
def product(root):
    return Product.objects.create(
        name="Sheet Machine", short_description="s", description="d",
        category=root, price="10.00", status=ProductStatus.PUBLISHED,
    )


def backdate(product, **fields):
    """Writes timestamps straight to the row — Product.save() would overwrite
    them with "now" via its own publishing/versioning logic."""
    Product.objects.filter(pk=product.pk).update(**fields)
    product.refresh_from_db()


def test_a_freshly_published_product_is_new(product):
    assert product.is_new is True
    assert product.is_updated is False


def test_the_new_badge_expires_after_its_window(product, settings):
    backdate(product, published_at=timezone.now() - timedelta(days=settings.NEW_PRODUCT_BADGE_DAYS + 1))

    assert product.is_new is False


def test_bumping_the_version_stamps_a_release_and_shows_updated(product, settings):
    backdate(product, published_at=timezone.now() - timedelta(days=settings.NEW_PRODUCT_BADGE_DAYS + 1))

    product.version = "2.0.0"
    product.save()

    assert product.last_release_at is not None
    assert product.is_updated is True


def test_editing_without_a_version_change_does_not_mark_it_updated(product, settings):
    backdate(product, published_at=timezone.now() - timedelta(days=settings.NEW_PRODUCT_BADGE_DAYS + 1))

    product.short_description = "reworded"
    product.save()

    assert product.last_release_at is None
    assert product.is_updated is False


def test_the_updated_badge_expires_after_its_window(product, settings):
    backdate(
        product,
        published_at=timezone.now() - timedelta(days=365),
        last_release_at=timezone.now() - timedelta(days=settings.UPDATED_PRODUCT_BADGE_DAYS + 1),
    )

    assert product.is_updated is False


def test_a_new_product_is_not_also_labelled_updated(product):
    product.version = "1.1.0"
    product.save()

    assert product.is_new is True
    assert product.is_updated is False, "one badge per card — New outranks Updated"


def test_a_zero_day_window_turns_the_badge_off(product, settings):
    settings.NEW_PRODUCT_BADGE_DAYS = 0

    assert product.is_new is False


def test_the_storefront_api_exposes_both_flags(client, product):
    card = client.get("/api/products").json()["results"][0]

    assert card["is_new"] is True
    assert card["is_updated"] is False
