"""
Customer-facing review submission (POST /api/products/<slug>/reviews). Reviews
are read-only elsewhere (embedded in ProductDetailSerializer, moderated via the
admin API) — this is the only place a customer can create one, so what matters
most here is that author/is_verified_purchase can never be spoofed by the client.
"""
import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from catalog.models import Category, Product
from catalog.models.product import ProductStatus, ProductVisibility
from licensing.models import LicensedProduct, ProductPurchase
from reviews.models import Review

pytestmark = pytest.mark.django_db
User = get_user_model()


@pytest.fixture
def category():
    return Category.objects.create(name="Revit Plugins")


@pytest.fixture
def product(category):
    return Product.objects.create(
        name="Reviewable Tool", short_description="s", description="d", category=category,
        price="19.00", status=ProductStatus.PUBLISHED, visibility=ProductVisibility.PUBLIC,
    )


def _login(email="reviewer@example.com"):
    user = User.objects.create_user(username=email, email=email, password="pw12345!", first_name="Rae")
    client = Client()
    client.force_login(user)
    return user, client


def _post_review(client, slug, **body):
    return client.post(
        f"/api/products/{slug}/reviews", data={"rating": 5, "title": "Great", "body": "Works well.", **body},
        content_type="application/json",
    )


def test_review_requires_auth(product):
    resp = _post_review(Client(), product.slug)
    assert resp.status_code in (401, 403)


def test_review_created_and_visible_on_product_detail(product):
    user, client = _login()
    resp = _post_review(client, product.slug)
    assert resp.status_code == 201
    # Full shape, not just the input fields — the client renders this response
    # directly instead of waiting on the product page's fetch cache to catch up.
    body = resp.json()
    assert body["author_name"] == "Rae"
    assert body["is_verified_purchase"] is False

    review = Review.objects.get(product=product)
    assert review.author_id == user.id
    assert review.author_name == "Rae"
    assert review.is_verified_purchase is False  # no purchase yet

    detail = client.get(f"/api/products/{product.slug}").json()
    assert len(detail["reviews"]) == 1
    assert detail["reviews"][0]["title"] == "Great"


def test_review_marks_verified_purchase(product):
    user, client = _login()
    sku = LicensedProduct.objects.get(code=product.product_code)
    ProductPurchase.objects.create(user=user, product=sku, payment_status=ProductPurchase.PaymentStatus.PAID)

    resp = _post_review(client, product.slug)
    assert resp.status_code == 201
    assert Review.objects.get(product=product).is_verified_purchase is True


def test_review_rejects_out_of_range_rating(product):
    _, client = _login()
    resp = _post_review(client, product.slug, rating=9)
    assert resp.status_code == 400
    assert not Review.objects.exists()


def test_review_refreshes_product_rating_aggregate(product):
    _, client = _login()
    _post_review(client, product.slug, rating=4)
    product.refresh_from_db()
    assert product.rating_count == 1
    assert float(product.rating_average) == 4.0


def test_review_author_name_cannot_be_spoofed(product):
    _, client = _login()
    resp = _post_review(client, product.slug, author_name="Not Rae", is_verified_purchase=True)
    assert resp.status_code == 201
    review = Review.objects.get(product=product)
    assert review.author_name == "Rae"  # from the account, not the request body
    assert review.is_verified_purchase is False  # no purchase — request body value ignored
