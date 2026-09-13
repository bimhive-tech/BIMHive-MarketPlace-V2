"""The display-only "was" price (Product.original_price) and the raised
discount cap. Tools are given away for now with their regular price struck
through, so both have to render honestly and never change what's charged."""
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from catalog.models import Category, Product, Promotion
from catalog.models.product import ProductStatus

pytestmark = pytest.mark.django_db


@pytest.fixture
def category():
    return Category.objects.create(name="Revit Plugins")


def _product(category, **fields):
    defaults = dict(
        name="Priced Tool", short_description="s", description="d",
        category=category, status=ProductStatus.PUBLISHED, price=Decimal("0.00"),
    )
    return Product.objects.create(**{**defaults, **fields})


def test_a_free_product_shows_its_original_price_crossed_out(client, category):
    product = _product(category, original_price=Decimal("29.00"))

    body = client.get(f"/api/products/{product.slug}").json()

    assert body["price_label"] == "Free"
    assert body["original_price_label"] == "$29.00"
    assert body["is_free"] is True


def test_the_card_carries_the_original_price_too(client, category):
    _product(category, original_price=Decimal("29.00"))

    card = client.get("/api/products").json()["results"][0]

    assert card["original_price_label"] == "$29.00"


def test_no_original_price_means_nothing_to_cross_out(category):
    assert _product(category).original_price_label is None


def test_an_original_price_that_isnt_higher_is_not_shown(category):
    """Crossing out $19 next to a $49 price would advertise a price rise."""
    product = _product(category, price=Decimal("49.00"), original_price=Decimal("19.00"))

    assert product.original_price_label is None


def test_a_subscription_product_ignores_the_one_time_original_price(category):
    product = _product(category, monthly_price=Decimal("9.00"), original_price=Decimal("29.00"))

    assert product.original_price_label is None


def _check_discount(percent):
    Promotion._meta.get_field("discount_percent").run_validators(percent)


def test_a_100_percent_promotion_is_allowed():
    _check_discount(100)


def test_a_discount_over_100_percent_is_still_rejected():
    with pytest.raises(ValidationError):
        _check_discount(101)
