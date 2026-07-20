"""
Customer downloads — the installer is generated live at download time (see
installer/builder.py::generate_installer_bytes, called from
licensing/account_api.py::AccountPluginBuildDownloadView) and streamed back
as a bare .exe. Nothing is pre-built or cached, and no license key is
attached: the customer types their key into the plugin themselves, copied
from /account/licenses — the plugin's own first activation call with that
key is what actually binds it to a machine. A manually-uploaded file (not a
plugin build at all) keeps the old plain redirect behavior, served by the
separate AccountDownloadFileView.
"""
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

PE_MAGIC = b"MZ"


@pytest.fixture
def category():
    return Category.objects.create(name="Revit Plugins")


@pytest.fixture
def buyer_client(category):
    product = Product.objects.create(
        name="Download Test", product_code="download-test", category=category,
        short_description="s", description="d", status=ProductStatus.PUBLISHED,
    )
    sku = LicensedProduct.objects.get(code=product.product_code)
    user = User.objects.create_user(username="buyer@x.com", email="buyer@x.com", password="x")
    purchase = ProductPurchase.objects.create(user=user, product=sku, payment_status=ProductPurchase.PaymentStatus.PAID)
    client = Client()
    client.force_login(user)
    return client, product, purchase


# Real NSIS invocation, same no-mocking philosophy as test_builder.py.
def test_plugin_build_download_streams_a_bare_exe_with_no_key_attached(buyer_client):
    client, product, purchase = buyer_client
    build = PluginBuild.objects.create(product=product, revit_year="2025", plugin_version="1.0.0")
    build.dll_storage_key = default_storage.save(f"test/{product.id}/Plugin.dll", ContentFile(b"fake dll"))
    build.dll_filename = "Plugin.dll"
    build.addin_storage_key = default_storage.save(f"test/{product.id}/Plugin.addin", ContentFile(b"<RevitAddIns/>"))
    build.addin_filename = "Plugin.addin"
    build.save()

    resp = client.get(f"/api/account/downloads/plugin-builds/{build.id}/get")

    assert resp.status_code == 200
    assert resp["Content-Type"] == "application/vnd.microsoft.portable-executable"
    assert resp.content.startswith(PE_MAGIC)
    # No license key anywhere in the response — it's a bare installer.
    assert purchase.license_key.encode() not in resp.content
    assert "attachment;" in resp["Content-Disposition"]
    assert resp["Content-Disposition"].endswith('.exe"')


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
