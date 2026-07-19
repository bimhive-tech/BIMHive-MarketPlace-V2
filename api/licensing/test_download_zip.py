"""
Per-download license-key packaging — the installer is generated live at
download time (see installer/builder.py::generate_installer_bytes, called
from licensing/account_api.py::AccountPluginBuildDownloadView) and zipped
with the purchaser's own license key. Nothing is pre-built or cached. A
manually-uploaded file (not a plugin build at all) keeps the old plain
redirect behavior, served by the separate AccountDownloadFileView.
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


# Real WiX invocation, same no-mocking philosophy as test_builder.py.
def test_plugin_build_download_is_a_zip_with_the_license_key(buyer_client):
    client, product, purchase = buyer_client
    build = PluginBuild.objects.create(product=product, revit_year="2025", plugin_version="1.0.0")
    build.dll_storage_key = default_storage.save(f"test/{product.id}/Plugin.dll", ContentFile(b"fake dll"))
    build.dll_filename = "Plugin.dll"
    build.addin_storage_key = default_storage.save(f"test/{product.id}/Plugin.addin", ContentFile(b"<RevitAddIns/>"))
    build.addin_filename = "Plugin.addin"
    build.save()

    resp = client.get(f"/api/account/downloads/plugin-builds/{build.id}/get")

    assert resp.status_code == 200
    assert resp["Content-Type"] == "application/zip"
    archive = zipfile.ZipFile(io.BytesIO(resp.content))
    names = archive.namelist()
    assert any(name.endswith(".msi") for name in names)
    assert "zip-test.key" in names
    assert archive.read("zip-test.key").decode() == purchase.license_key


def test_plugin_build_download_requires_a_paid_purchase(buyer_client):
    client, product, purchase = buyer_client
    purchase.payment_status = ProductPurchase.PaymentStatus.PENDING
    purchase.save()
    build = PluginBuild.objects.create(product=product, revit_year="2025")

    resp = client.get(f"/api/account/downloads/plugin-builds/{build.id}/get")
    assert resp.status_code == 400


def test_plugin_build_download_fails_cleanly_without_dll_or_addin(buyer_client):
    client, product, _ = buyer_client
    build = PluginBuild.objects.create(product=product, revit_year="2025")

    resp = client.get(f"/api/account/downloads/plugin-builds/{build.id}/get")
    assert resp.status_code == 400


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
