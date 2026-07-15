"""
Customer-facing review submission (POST /api/products/<slug>/reviews) and
management (GET/PATCH/DELETE /api/account/reviews). Reviews are read-only
elsewhere (embedded in ProductDetailSerializer, moderated via the admin API) —
this covers the only places a customer can create/edit/delete one, so what
matters most is that ownership can't be bypassed and author/is_verified_purchase
can never be spoofed by the client.
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


def _give_purchase(user, product):
    sku = LicensedProduct.objects.get(code=product.product_code)
    return ProductPurchase.objects.create(user=user, product=sku, payment_status=ProductPurchase.PaymentStatus.PAID)


def _post_review(client, slug, **body):
    return client.post(
        f"/api/products/{slug}/reviews", data={"rating": 5, "title": "Great", "body": "Works well.", **body},
        content_type="application/json",
    )


def test_review_requires_auth(product):
    resp = _post_review(Client(), product.slug)
    assert resp.status_code in (401, 403)


def test_review_requires_owning_the_product(product):
    _, client = _login()
    resp = _post_review(client, product.slug)
    assert resp.status_code == 403
    assert not Review.objects.exists()


def test_review_created_and_visible_on_product_detail(product):
    user, client = _login()
    _give_purchase(user, product)
    resp = _post_review(client, product.slug)
    assert resp.status_code == 201
    # Full shape, not just the input fields — the client renders this response
    # directly instead of waiting on the product page's fetch cache to catch up.
    body = resp.json()
    assert body["author_name"] == "Rae"
    assert body["is_verified_purchase"] is True

    review = Review.objects.get(product=product)
    assert review.author_id == user.id
    assert review.author_name == "Rae"

    detail = client.get(f"/api/products/{product.slug}").json()
    assert len(detail["reviews"]) == 1
    assert detail["reviews"][0]["title"] == "Great"


def test_review_rejects_second_review_for_the_same_product(product):
    user, client = _login()
    _give_purchase(user, product)
    assert _post_review(client, product.slug).status_code == 201
    resp = _post_review(client, product.slug, title="Second attempt")
    assert resp.status_code == 400
    assert Review.objects.filter(product=product).count() == 1


def test_review_rejects_out_of_range_rating(product):
    user, client = _login()
    _give_purchase(user, product)
    resp = _post_review(client, product.slug, rating=9)
    assert resp.status_code == 400
    assert not Review.objects.exists()


def test_review_refreshes_product_rating_aggregate(product):
    user, client = _login()
    _give_purchase(user, product)
    _post_review(client, product.slug, rating=4)
    product.refresh_from_db()
    assert product.rating_count == 1
    assert float(product.rating_average) == 4.0


def test_review_author_name_and_verified_status_cannot_be_spoofed(product):
    user, client = _login()
    _give_purchase(user, product)
    # Attempts to fake a *different* name and to force verified=False despite a
    # real purchase — both should be silently overridden by the server-computed
    # values, not whatever the client sent.
    resp = _post_review(client, product.slug, author_name="Not Rae", is_verified_purchase=False)
    assert resp.status_code == 201
    review = Review.objects.get(product=product)
    assert review.author_name == "Rae"
    assert review.is_verified_purchase is True


# ── Account: my reviews (list / edit / delete) ──
def test_account_reviews_lists_only_my_own_reviews(product, category):
    user, client = _login("me@example.com")
    _give_purchase(user, product)
    _post_review(client, product.slug)

    other_product = Product.objects.create(
        name="Someone Else's Product", short_description="s", description="d", category=category,
        status=ProductStatus.PUBLISHED, visibility=ProductVisibility.PUBLIC,
    )
    other_user, other_client = _login("other@example.com")
    _give_purchase(other_user, other_product)
    _post_review(other_client, other_product.slug)

    resp = client.get("/api/account/reviews")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["product_slug"] == product.slug


def test_account_review_edit_updates_rating_and_aggregate(product):
    user, client = _login()
    _give_purchase(user, product)
    review_id = _post_review(client, product.slug, rating=3).json()["id"]

    resp = client.patch(
        f"/api/account/reviews/{review_id}", data={"rating": 5, "title": "Updated"}, content_type="application/json"
    )
    assert resp.status_code == 200
    assert resp.json()["rating"] == 5

    product.refresh_from_db()
    assert float(product.rating_average) == 5.0


def test_account_review_delete_removes_it_and_refreshes_aggregate(product):
    user, client = _login()
    _give_purchase(user, product)
    review_id = _post_review(client, product.slug).json()["id"]

    resp = client.delete(f"/api/account/reviews/{review_id}")
    assert resp.status_code == 204
    assert not Review.objects.filter(id=review_id).exists()

    product.refresh_from_db()
    assert product.rating_count == 0


def test_account_review_cannot_edit_someone_elses_review(product):
    owner, owner_client = _login("owner@example.com")
    _give_purchase(owner, product)
    review_id = _post_review(owner_client, product.slug).json()["id"]

    _, other_client = _login("intruder@example.com")
    resp = other_client.patch(
        f"/api/account/reviews/{review_id}", data={"rating": 1}, content_type="application/json"
    )
    assert resp.status_code == 404
