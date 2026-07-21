"""
Locks in the Product ↔ licensing.LicensedProduct sync (the "license works"
guarantee) and the admin product API's write behavior. See catalog/signals.py,
licensing/services.py, catalog/admin_api.py.
"""
import pytest
from django.contrib.auth import get_user_model

from catalog.admin_api import AdminProductDetailSerializer
from catalog.models import Category, Partner, Product, ProductFile
from catalog.models.product import ProductStatus
from licensing.models import LicensedProduct

pytestmark = pytest.mark.django_db
User = get_user_model()


@pytest.fixture
def category():
    return Category.objects.create(name="Revit Plugins")


@pytest.fixture
def partner():
    return Partner.objects.create(name="BIMHIVE", status=Partner.ApplicationStatus.APPROVED)


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


def test_trial_hours_and_minutes_sync_to_the_activation_sku(category, partner):
    product = Product.objects.create(
        name="Fine Trial", short_description="s", description="d",
        category=category, partner=partner, price="10.00", status=ProductStatus.DRAFT,
        default_trial_days=0, default_trial_hours=3, default_trial_minutes=45,
    )
    sku = LicensedProduct.objects.get(code=product.product_code)
    assert sku.default_trial_hours == 3
    assert sku.default_trial_minutes == 45
    assert sku.trial_minutes_total == 225


def test_new_product_defaults_to_a_seven_day_trial(category, partner):
    product = Product.objects.create(
        name="Default Trial", short_description="s", description="d",
        category=category, partner=partner, price="10.00",
    )
    assert product.default_trial_days == 7
    assert product.default_trial_hours == 0
    assert product.has_trial is True


def test_a_product_with_zero_trial_length_has_no_trial(category, partner):
    product = Product.objects.create(
        name="No Trial", short_description="s", description="d",
        category=category, partner=partner, price="10.00",
        default_trial_days=0, default_trial_hours=0, default_trial_minutes=0,
    )
    assert product.has_trial is False


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


# ── Subscription pricing (Product.monthly_price/yearly_price) ──
# .refresh_from_db() everywhere below: a freshly-.create()'d instance still
# holds the raw string it was assigned (Django only coerces DecimalField to
# a real Decimal on the way back out of the database), and price_label's
# ":.2f" formatting needs a real Decimal — exactly the state every real
# caller is actually in, since they always read from a queryset.
def test_a_plain_product_is_not_a_subscription(category, partner):
    product = Product.objects.create(
        name="Plain", short_description="s", description="d",
        category=category, partner=partner, price="10.00",
    )
    product.refresh_from_db()
    assert product.is_subscription is False
    assert product.price_label == "$10.00"


def test_setting_a_monthly_price_makes_it_a_subscription(category, partner):
    product = Product.objects.create(
        name="Sub", short_description="s", description="d",
        category=category, partner=partner, price="0.00", monthly_price="19.00",
    )
    product.refresh_from_db()
    assert product.is_subscription is True
    # A subscription's $0 one-time price never reads as "free" — the
    # one-time price field is simply unused when subscription pricing is set.
    assert product.is_free is False
    assert product.price_label == "$19.00/mo"


def test_yearly_only_subscription_uses_yearly_label(category, partner):
    product = Product.objects.create(
        name="Yearly Only", short_description="s", description="d",
        category=category, partner=partner, price="0.00", yearly_price="179.00",
    )
    product.refresh_from_db()
    assert product.price_label == "$179.00/yr"


def test_yearly_savings_percent_computed_from_both_prices(category, partner):
    product = Product.objects.create(
        name="Savings", short_description="s", description="d",
        category=category, partner=partner, price="0.00",
        monthly_price="20.00", yearly_price="180.00",  # 240/yr equiv -> 180 = 25% off
    )
    product.refresh_from_db()
    assert product.yearly_savings_percent == 25


def test_yearly_savings_percent_is_none_when_yearly_isnt_actually_cheaper(category, partner):
    product = Product.objects.create(
        name="No Savings", short_description="s", description="d",
        category=category, partner=partner, price="0.00",
        monthly_price="10.00", yearly_price="150.00",  # 120/yr equiv, yearly is worse
    )
    product.refresh_from_db()
    assert product.yearly_savings_percent is None


def test_yearly_savings_percent_is_none_without_both_prices(category, partner):
    product = Product.objects.create(
        name="Monthly Only", short_description="s", description="d",
        category=category, partner=partner, price="0.00", monthly_price="19.00",
    )
    product.refresh_from_db()
    assert product.yearly_savings_percent is None


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
def test_product_code_immutable_once_downloaded(category, partner):
    product = Product.objects.create(
        name="Locked", short_description="s", description="d",
        category=category, partner=partner, status=ProductStatus.PUBLISHED, download_count=1,
    )
    serializer = AdminProductDetailSerializer(product, data={"product_code": "hacked"}, partial=True)
    assert not serializer.is_valid()
    assert "product_code" in serializer.errors


def test_product_code_editable_with_zero_downloads(category, partner):
    # Published but never downloaded: no installed copies exist yet to break.
    product = Product.objects.create(
        name="Editable", short_description="s", description="d",
        category=category, partner=partner, status=ProductStatus.PUBLISHED, download_count=0,
    )
    serializer = AdminProductDetailSerializer(product, data={"product_code": "new-code"}, partial=True)
    assert serializer.is_valid(), serializer.errors
    updated = serializer.save()
    assert updated.product_code == "new-code"
    assert LicensedProduct.objects.filter(code="new-code").exists()


def test_cannot_publish_without_a_file(category, partner):
    product = Product.objects.create(
        name="No Files Yet", short_description="s", description="d",
        category=category, partner=partner, status=ProductStatus.DRAFT,
    )
    serializer = AdminProductDetailSerializer(product, data={"status": "published"}, partial=True)
    assert not serializer.is_valid()
    assert "status" in serializer.errors


def test_can_publish_once_a_file_exists(category, partner):
    product = Product.objects.create(
        name="Has A File", short_description="s", description="d",
        category=category, partner=partner, status=ProductStatus.DRAFT,
    )
    ProductFile.objects.create(product=product, revit_version="2025", version_label="1.0.0", storage_key="x/y.exe")
    serializer = AdminProductDetailSerializer(product, data={"status": "published"}, partial=True)
    assert serializer.is_valid(), serializer.errors
    updated = serializer.save()
    assert updated.status == "published"


def test_can_save_as_draft_without_a_file(category, partner):
    product = Product.objects.create(
        name="Draft No Files", short_description="s", description="d",
        category=category, partner=partner, status=ProductStatus.DRAFT,
    )
    serializer = AdminProductDetailSerializer(product, data={"status": "draft"}, partial=True)
    assert serializer.is_valid(), serializer.errors


def test_media_accepts_a_long_presigned_url(category, partner):
    # R2 presigned URLs (the fallback used whenever R2_PUBLIC_BASE_URL isn't
    # set) run 350-450+ chars — well past Django's URLField default of 200.
    long_url = "https://example.r2.cloudflarestorage.com/bucket/product_media/1/cover.png?" + (
        "X-Amz-Signature=" + "a" * 250
    )
    assert len(long_url) > 200
    product = Product.objects.create(
        name="Long URL", short_description="s", description="d", category=category, partner=partner,
    )
    serializer = AdminProductDetailSerializer(
        product,
        data={"media": [{"media_type": "image", "url": long_url, "caption": "", "is_cover": True, "sort_order": 0}]},
        partial=True,
    )
    assert serializer.is_valid(), serializer.errors
    updated = serializer.save()
    assert updated.media.first().url == long_url


def test_saving_media_syncs_cover_image_url(category, partner):
    # cover_image_url drives ProductCard / the admin product list thumbnail —
    # it isn't admin-editable directly, it's derived from whichever gallery
    # item is marked "cover" so the two can never disagree.
    product = Product.objects.create(
        name="Cover Sync", short_description="s", description="d", category=category, partner=partner,
    )
    serializer = AdminProductDetailSerializer(
        product,
        data={
            "media": [
                {"media_type": "video", "url": "https://example.com/clip.mp4", "caption": "", "is_cover": False, "sort_order": 0},
                {"media_type": "image", "url": "https://example.com/cover.png", "caption": "", "is_cover": True, "sort_order": 1},
            ]
        },
        partial=True,
    )
    serializer.is_valid(raise_exception=True)
    updated = serializer.save()
    assert updated.cover_image_url == "https://example.com/cover.png"

    # Removing the cover item on a later save clears it rather than leaving a
    # stale URL pointing at media that's no longer attached to the product.
    serializer2 = AdminProductDetailSerializer(product, data={"media": []}, partial=True)
    serializer2.is_valid(raise_exception=True)
    updated2 = serializer2.save()
    assert updated2.cover_image_url == ""


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


# ── Media upload (auto-detects image vs video, no manual type picking) ──
def test_media_upload_requires_staff(client, category, partner):
    product = Product.objects.create(name="P", short_description="s", description="d", category=category, partner=partner)
    from django.core.files.uploadedfile import SimpleUploadedFile

    upload = SimpleUploadedFile("cover.png", b"fake png bytes", content_type="image/png")
    resp = client.post(f"/api/admin/products/{product.id}/media-upload", data={"file": upload})
    assert resp.status_code in (401, 403)


def test_media_upload_detects_image(staff_client, category, partner):
    from django.core.files.uploadedfile import SimpleUploadedFile

    product = Product.objects.create(name="P", short_description="s", description="d", category=category, partner=partner)
    upload = SimpleUploadedFile("cover.png", b"fake png bytes", content_type="image/png")
    resp = staff_client.post(f"/api/admin/products/{product.id}/media-upload", data={"file": upload})
    assert resp.status_code == 201
    body = resp.json()
    assert body["media_type"] == "image"
    assert body["url"].startswith("http")


def test_media_upload_detects_video(staff_client, category, partner):
    from django.core.files.uploadedfile import SimpleUploadedFile

    product = Product.objects.create(name="P", short_description="s", description="d", category=category, partner=partner)
    upload = SimpleUploadedFile("teaser.mp4", b"fake mp4 bytes", content_type="video/mp4")
    resp = staff_client.post(f"/api/admin/products/{product.id}/media-upload", data={"file": upload})
    assert resp.status_code == 201
    assert resp.json()["media_type"] == "video"


def test_media_upload_rejects_other_file_types(staff_client, category, partner):
    from django.core.files.uploadedfile import SimpleUploadedFile

    product = Product.objects.create(name="P", short_description="s", description="d", category=category, partner=partner)
    upload = SimpleUploadedFile("installer.exe", b"not media", content_type="application/octet-stream")
    resp = staff_client.post(f"/api/admin/products/{product.id}/media-upload", data={"file": upload})
    assert resp.status_code == 400


@pytest.mark.django_db
def test_media_upload_fails_fast_without_r2_configured(staff_client, category, partner, settings):
    from django.core.files.uploadedfile import SimpleUploadedFile

    settings.R2_ACCESS_KEY_ID = ""
    product = Product.objects.create(name="P", short_description="s", description="d", category=category, partner=partner)
    upload = SimpleUploadedFile("cover.png", b"fake png bytes", content_type="image/png")
    resp = staff_client.post(f"/api/admin/products/{product.id}/media-upload", data={"file": upload})
    assert resp.status_code == 400
    assert "R2" in resp.json()["detail"]


# ── Public search / collection / partner filters ──
def test_search_matches_name_and_short_description(client, category, partner):
    Product.objects.create(
        name="BIM OneClick", short_description="s", description="d", category=category, partner=partner,
        status=ProductStatus.PUBLISHED,
    )
    Product.objects.create(
        name="Sheet Manager", short_description="Automate worksets", description="d",
        category=category, partner=partner, status=ProductStatus.PUBLISHED,
    )
    Product.objects.create(
        name="Unrelated Tool", short_description="s", description="d", category=category, partner=partner,
        status=ProductStatus.PUBLISHED,
    )

    resp = client.get("/api/products?q=OneClick")
    names = [row["name"] for row in resp.json()["results"]]
    assert names == ["BIM OneClick"]

    resp2 = client.get("/api/products?q=worksets")
    assert [row["name"] for row in resp2.json()["results"]] == ["Sheet Manager"]


def test_search_excludes_unpublished_products(client, category, partner):
    Product.objects.create(
        name="Draft OneClick", short_description="s", description="d",
        category=category, partner=partner, status=ProductStatus.DRAFT,
    )
    resp = client.get("/api/products?q=OneClick")
    assert resp.json()["results"] == []


def test_collection_filter_scopes_products(client, category, partner):
    from catalog.models import Collection

    collection = Collection.objects.create(name="Revit Essentials")
    in_collection = Product.objects.create(
        name="In Collection", short_description="s", description="d",
        category=category, partner=partner, status=ProductStatus.PUBLISHED,
    )
    Product.objects.create(
        name="Not In Collection", short_description="s", description="d",
        category=category, partner=partner, status=ProductStatus.PUBLISHED,
    )
    collection.products.add(in_collection)

    resp = client.get(f"/api/products?collection={collection.slug}")
    assert [row["name"] for row in resp.json()["results"]] == ["In Collection"]


def test_partner_endpoint_only_lists_partners_with_live_products(client, category, partner):
    quiet_partner = Partner.objects.create(name="No Products Yet")
    Product.objects.create(
        name="Live Product", short_description="s", description="d",
        category=category, partner=partner, status=ProductStatus.PUBLISHED,
    )

    resp = client.get("/api/partners")
    slugs = [row["slug"] for row in resp.json()]
    assert partner.slug in slugs
    assert quiet_partner.slug not in slugs


def test_partner_filter_scopes_products(client, category, partner):
    other_partner = Partner.objects.create(name="Other Partner")
    Product.objects.create(
        name="This Partner's Product", short_description="s", description="d",
        category=category, partner=partner, status=ProductStatus.PUBLISHED,
    )
    Product.objects.create(
        name="Other Partner's Product", short_description="s", description="d",
        category=category, partner=other_partner, status=ProductStatus.PUBLISHED,
    )

    resp = client.get(f"/api/products?partner={partner.slug}")
    assert [row["name"] for row in resp.json()["results"]] == ["This Partner's Product"]


# ── Admin documentation tab ──
def test_saving_documentation_creates_it_with_sections(category, partner):
    product = Product.objects.create(
        name="Doc Product", short_description="s", description="d", category=category, partner=partner,
    )
    serializer = AdminProductDetailSerializer(
        product,
        data={
            "documentation": {
                "title": "Doc Product Documentation",
                "summary": "Quick summary",
                "overview": "Getting started overview",
                "is_published": True,
                "sections": [
                    {"title": "Installation", "body": "Run the installer.", "image_url": "", "sort_order": 0},
                    {"title": "Usage", "body": "Click the button.", "image_url": "", "sort_order": 1},
                ],
            }
        },
        partial=True,
    )
    serializer.is_valid(raise_exception=True)
    updated = serializer.save()

    doc = updated.documentation
    assert doc.title == "Doc Product Documentation"
    assert doc.is_published is True
    assert list(doc.sections.values_list("title", flat=True)) == ["Installation", "Usage"]


def test_saving_documentation_with_blank_title_deletes_it(category, partner):
    from catalog.models import Documentation

    product = Product.objects.create(
        name="Doc Product 2", short_description="s", description="d", category=category, partner=partner,
    )
    Documentation.objects.create(product=product, title="Existing Doc")
    assert Documentation.objects.filter(product=product).exists()

    serializer = AdminProductDetailSerializer(product, data={"documentation": None}, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    assert not Documentation.objects.filter(product=product).exists()


def test_documentation_updates_replace_all_sections(category, partner):
    product = Product.objects.create(
        name="Doc Product 3", short_description="s", description="d", category=category, partner=partner,
    )
    serializer = AdminProductDetailSerializer(
        product,
        data={"documentation": {"title": "T", "summary": "", "overview": "", "is_published": False,
                                 "sections": [{"title": "A", "body": "x", "image_url": "", "sort_order": 0}]}},
        partial=True,
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()

    serializer2 = AdminProductDetailSerializer(
        product,
        data={"documentation": {"title": "T", "summary": "", "overview": "", "is_published": False,
                                 "sections": [{"title": "B", "body": "y", "image_url": "", "sort_order": 0}]}},
        partial=True,
    )
    serializer2.is_valid(raise_exception=True)
    updated = serializer2.save()
    assert list(updated.documentation.sections.values_list("title", flat=True)) == ["B"]


def test_public_api_hides_unpublished_documentation(client, category, partner):
    from catalog.models import Documentation

    product = Product.objects.create(
        name="Unpublished Doc Product", short_description="s", description="d",
        category=category, partner=partner, status=ProductStatus.PUBLISHED,
    )
    Documentation.objects.create(product=product, title="Draft Doc", is_published=False)

    resp = client.get(f"/api/products/{product.slug}")
    assert resp.json()["documentation"] is None


def test_public_api_shows_published_documentation(client, category, partner):
    from catalog.models import Documentation

    product = Product.objects.create(
        name="Published Doc Product", short_description="s", description="d",
        category=category, partner=partner, status=ProductStatus.PUBLISHED,
    )
    Documentation.objects.create(product=product, title="Live Doc", is_published=True)

    resp = client.get(f"/api/products/{product.slug}")
    assert resp.json()["documentation"]["title"] == "Live Doc"


# ── Standalone /docs library ──
def test_documentation_list_only_shows_published_docs_on_published_products(client, category, partner):
    from catalog.models import Documentation

    live_product = Product.objects.create(
        name="Live Product", short_description="s", description="d",
        category=category, partner=partner, status=ProductStatus.PUBLISHED,
    )
    Documentation.objects.create(product=live_product, title="Live Doc", summary="s", is_published=True)

    draft_doc_product = Product.objects.create(
        name="Draft Doc Product", short_description="s", description="d",
        category=category, partner=partner, status=ProductStatus.PUBLISHED,
    )
    Documentation.objects.create(product=draft_doc_product, title="Draft Doc", is_published=False)

    unpublished_product = Product.objects.create(
        name="Unpublished Product", short_description="s", description="d",
        category=category, partner=partner, status=ProductStatus.DRAFT,
    )
    Documentation.objects.create(product=unpublished_product, title="Doc On Draft Product", is_published=True)

    resp = client.get("/api/documentation")
    titles = [row["title"] for row in resp.json()]
    assert titles == ["Live Doc"]


def test_documentation_detail_includes_sections_and_product_link(client, category, partner):
    from catalog.models import Documentation, DocSection

    product = Product.objects.create(
        name="Doc Detail Product", short_description="s", description="d",
        category=category, partner=partner, status=ProductStatus.PUBLISHED,
    )
    doc = Documentation.objects.create(
        product=product, title="Doc Detail", summary="Short summary", overview="Full overview", is_published=True,
    )
    DocSection.objects.create(documentation=doc, title="Installation", body="Run the installer.", sort_order=0)

    resp = client.get(f"/api/documentation/{doc.slug}")
    body = resp.json()
    assert body["overview"] == "Full overview"
    assert body["product_slug"] == product.slug
    assert [s["title"] for s in body["sections"]] == ["Installation"]


def test_documentation_detail_404s_for_unpublished_doc(client, category, partner):
    from catalog.models import Documentation

    product = Product.objects.create(
        name="Hidden Doc Product", short_description="s", description="d",
        category=category, partner=partner, status=ProductStatus.PUBLISHED,
    )
    doc = Documentation.objects.create(product=product, title="Hidden Doc", is_published=False)

    resp = client.get(f"/api/documentation/{doc.slug}")
    assert resp.status_code == 404


# ── Product listing pagination ──
def test_product_list_is_paginated(client, category, partner):
    for i in range(30):
        Product.objects.create(
            name=f"Paged Product {i}", short_description="s", description="d",
            category=category, partner=partner, status=ProductStatus.PUBLISHED,
        )

    first = client.get("/api/products").json()
    assert first["count"] == 30
    assert len(first["results"]) == 24
    assert first["next"] is not None
    assert first["previous"] is None

    second = client.get("/api/products?page=2").json()
    assert len(second["results"]) == 6
    assert second["next"] is None

    first_names = {p["name"] for p in first["results"]}
    second_names = {p["name"] for p in second["results"]}
    assert first_names.isdisjoint(second_names)


def test_product_list_page_size_is_capped(client, category, partner):
    # bulk_create skips per-instance signals (e.g. activation SKU sync) — fine
    # here since this test only cares about pagination counts.
    Product.objects.bulk_create(
        [
            Product(
                name=f"Paged Product {i}", slug=f"paged-product-{i}", product_code=f"paged-product-{i}",
                short_description="s", description="d",
                category=category, partner=partner, status=ProductStatus.PUBLISHED,
            )
            for i in range(110)
        ]
    )

    resp = client.get("/api/products?page_size=1000").json()
    assert len(resp["results"]) == 100  # max_page_size=100 wins over the requested 1000
