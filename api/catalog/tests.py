"""
Locks in the Product ↔ licensing.LicensedProduct sync (the "license works"
guarantee) and the admin product API's write behavior. See catalog/signals.py,
licensing/services.py, catalog/admin_api.py.
"""
import pytest
from django.contrib.auth import get_user_model

from catalog.admin_api import AdminProductDetailSerializer
from catalog.models import Category, Partner, Product
from catalog.models.product import ProductStatus
from licensing.models import LicensedProduct

pytestmark = pytest.mark.django_db
User = get_user_model()


@pytest.fixture
def category():
    return Category.objects.create(name="Revit Plugins")


@pytest.fixture
def partner():
    return Partner.objects.create(name="BIMHIVE")


@pytest.fixture
def staff_client(client):
    user = User.objects.create_user(username="admin@x.com", email="admin@x.com", password="x", is_staff=True)
    client.force_login(user)
    return client


# ── Signal-based sync ──
def test_creating_product_creates_activation_sku(category, partner):
    product = Product.objects.create(
        name="Test Plugin", short_description="s", description="d",
        category=category, partner=partner, price="10.00", status=ProductStatus.DRAFT,
    )
    sku = LicensedProduct.objects.get(code=product.product_code)
    assert sku.product_id == product.id
    assert sku.name == "Test Plugin"
    assert sku.is_active is False  # draft products aren't activatable


def test_publishing_product_activates_its_sku(category, partner):
    product = Product.objects.create(
        name="Test Plugin 2", short_description="s", description="d",
        category=category, partner=partner, price="10.00", status=ProductStatus.DRAFT,
    )
    product.status = ProductStatus.PUBLISHED
    product.save()
    sku = LicensedProduct.objects.get(code=product.product_code)
    assert sku.is_active is True


def test_price_and_trial_changes_propagate_to_sku(category, partner):
    product = Product.objects.create(
        name="Test Plugin 3", short_description="s", description="d",
        category=category, partner=partner, price="10.00", default_trial_days=30,
    )
    product.price = "25.00"
    product.default_trial_days = 14
    product.save()
    sku = LicensedProduct.objects.get(code=product.product_code)
    assert str(sku.price) == "25.00"
    assert sku.default_trial_days == 14


def test_product_code_auto_generated_from_name(category, partner):
    product = Product.objects.create(
        name="My Cool Tool!", short_description="s", description="d",
        category=category, partner=partner,
    )
    assert product.product_code == "my-cool-tool"


def test_duplicate_names_get_unique_codes(category, partner):
    p1 = Product.objects.create(name="Dup", short_description="s", description="d", category=category, partner=partner)
    p2 = Product.objects.create(name="Dup", short_description="s", description="d", category=category, partner=partner)
    assert p1.product_code != p2.product_code


# ── Admin write serializer ──
def test_product_code_immutable_once_published(category, partner):
    product = Product.objects.create(
        name="Locked", short_description="s", description="d",
        category=category, partner=partner, status=ProductStatus.PUBLISHED,
    )
    serializer = AdminProductDetailSerializer(product, data={"product_code": "hacked"}, partial=True)
    assert not serializer.is_valid()
    assert "product_code" in serializer.errors


def test_product_code_editable_while_draft(category, partner):
    product = Product.objects.create(
        name="Editable", short_description="s", description="d",
        category=category, partner=partner, status=ProductStatus.DRAFT,
    )
    serializer = AdminProductDetailSerializer(product, data={"product_code": "new-code"}, partial=True)
    assert serializer.is_valid(), serializer.errors
    updated = serializer.save()
    assert updated.product_code == "new-code"
    assert LicensedProduct.objects.filter(code="new-code").exists()


def test_nested_lists_replace_all_on_update(category, partner):
    product = Product.objects.create(
        name="Nested", short_description="s", description="d", category=category, partner=partner,
    )
    serializer = AdminProductDetailSerializer(
        product,
        data={"features": [{"title": "A", "description": "", "sort_order": 0}]},
        partial=True,
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    assert list(product.features.values_list("title", flat=True)) == ["A"]

    # A second update with a different list fully replaces the first.
    serializer2 = AdminProductDetailSerializer(
        product,
        data={"features": [{"title": "B", "description": "", "sort_order": 0}]},
        partial=True,
    )
    serializer2.is_valid(raise_exception=True)
    serializer2.save()
    assert list(product.features.values_list("title", flat=True)) == ["B"]


# ── Admin API endpoints (auth-gated) ──
def test_admin_products_endpoint_requires_staff(client):
    resp = client.get("/api/admin/products")
    assert resp.status_code in (401, 403)


def test_admin_can_list_products(staff_client, category, partner):
    Product.objects.create(name="Listed", short_description="s", description="d", category=category, partner=partner)
    resp = staff_client.get("/api/admin/products")
    assert resp.status_code == 200
    assert any(row["name"] == "Listed" for row in resp.json())
