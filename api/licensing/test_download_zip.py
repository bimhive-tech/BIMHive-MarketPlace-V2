"""
Per-download license-key packaging — a file the auto-installer pipeline
built gets zipped with the purchaser's own license key instead of a bare
redirect (see licensing/account_api.py::AccountDownloadFileView). A
manually-uploaded file (no matching PluginBuild) keeps the old redirect
behavior untouched.
"""
import io
import zipfile

import pytest
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.test import Client

from catalog.models import Category, Product, ProductFile
from catalog.models.product import ProductStatus
from installer.models import PluginBuild
from licensing.models import LicensedProduct, ProductPurchase

pytestmark = pytest.mark.django_db
User = get_user_model()


@pytest.fixture
def category():
    return Category.objects.create(name="Revit Plugins")


@pytest.fixture
def buyer_client(category):
    product = Product.objects.create(
        name="Zip Test", product_code="zip-test", category=category,
        short_description="s", description="d", status=ProductStatus.PUBLISHED,
    )
    sku = LicensedProduct.objects.get(code=product.product_code)
    user = User.objects.create_user(username="zipbuyer@x.com", email="zipbuyer@x.com", password="x")
    purchase = ProductPurchase.objects.create(user=user, product=sku, payment_status=ProductPurchase.PaymentStatus.PAID)
    client = Client()
    client.force_login(user)
    return client, product, purchase


def test_auto_built_file_download_is_a_zip_with_the_license_key(buyer_client):
    client, product, purchase = buyer_client
    msi_key = default_storage.save(f"test/{product.id}/plugin.msi", ContentFile(b"fake msi bytes"))
    build = PluginBuild.objects.create(
        product=product, revit_year="2025", plugin_version="1.0.0",
        status=PluginBuild.Status.READY, built_msi_storage_key=msi_key,
    )
    file = ProductFile.objects.create(
        product=product, revit_version="2025", version_label="1.0.0", storage_key=msi_key,
    )

    resp = client.get(f"/api/account/downloads/{file.id}/get")

    assert resp.status_code == 200
    assert resp["Content-Type"] == "application/zip"
    archive = zipfile.ZipFile(io.BytesIO(resp.content))
    names = archive.namelist()
    assert any(name.endswith(".msi") for name in names)
    assert "zip-test.key" in names
    assert archive.read("zip-test.key").decode() == purchase.license_key
    assert build.id  # sanity: fixture wired correctly


def test_manually_uploaded_file_still_redirects(buyer_client):
    client, product, _ = buyer_client
    manual_key = default_storage.save(f"test/{product.id}/manual.msi", ContentFile(b"manual bytes"))
    file = ProductFile.objects.create(
        product=product, revit_version="2024", version_label="1.0.0", storage_key=manual_key,
    )

    resp = client.get(f"/api/account/downloads/{file.id}/get")

    assert resp.status_code == 302
    assert resp["Content-Type"] != "application/zip"


def test_download_still_requires_a_paid_purchase(buyer_client):
    client, product, purchase = buyer_client
    purchase.payment_status = ProductPurchase.PaymentStatus.PENDING
    purchase.save()
    key = default_storage.save(f"test/{product.id}/gated.msi", ContentFile(b"x"))
    file = ProductFile.objects.create(product=product, revit_version="2025", version_label="1.0.0", storage_key=key)

    resp = client.get(f"/api/account/downloads/{file.id}/get")
    assert resp.status_code == 400
