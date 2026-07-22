"""
Trial installer download — gated on Product.has_trial and being published,
no checkout involved, but (see licensing/account_api.py::
AccountPluginBuildTrialDownloadView) it DOES create a real, account-bound
trial ProductPurchase with its own key: a key is required to actually
activate the plugin now, trial or paid — see licensing/tests.py and
licensing/api_views.py::license_activate_api. Real NSIS invocation, same
no-mocking philosophy as test_builder.py for the .exe streaming assertions.
"""
import pytest
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.test import Client

from catalog.models import Category, Product
from catalog.models.product import ProductStatus
from installer.models import PluginBuild
from licensing.models import LicensedProduct, ProductPurchase

pytestmark = pytest.mark.django_db
User = get_user_model()

PE_MAGIC = b"MZ"

# A realistic minimal Revit .addin manifest — the license shim (see
# installer/license_shim.py::rewrite_addin_for_shim) rewrites <Assembly>/
# <FullClassName> to point at LicLoader instead, so it needs something
# that actually parses as a normal add-in manifest, not a bare stub.
SAMPLE_ADDIN_XML = b"""<?xml version="1.0" encoding="utf-8" standalone="no"?>
<RevitAddIns>
  <AddIn Type="Application">
    <Name>Test Plugin</Name>
    <Assembly>Plugin.dll</Assembly>
    <AddInId>ABCDEF12-3456-7890-ABCD-EF1234567890</AddInId>
    <FullClassName>TestPlugin.App</FullClassName>
    <VendorId>TEST</VendorId>
  </AddIn>
</RevitAddIns>"""


@pytest.fixture
def category():
    return Category.objects.create(name="Revit Plugins")


@pytest.fixture
def buyer_client():
    user = User.objects.create_user(username="trial@x.com", email="trial@x.com", password="x")
    client = Client()
    client.force_login(user)
    return client, user


def _staged_build(product):
    build = PluginBuild.objects.create(product=product, revit_year="2025", plugin_version="1.0.0")
    build.dll_storage_key = default_storage.save(f"test/{product.id}/Plugin.dll", ContentFile(b"fake dll"))
    build.dll_filename = "Plugin.dll"
    build.addin_storage_key = default_storage.save(f"test/{product.id}/Plugin.addin", ContentFile(SAMPLE_ADDIN_XML))
    build.addin_filename = "Plugin.addin"
    build.save()
    return build


def test_trial_download_streams_a_real_exe_and_issues_a_trial_key(buyer_client, category):
    client, user = buyer_client
    product = Product.objects.create(
        name="Trial Test", product_code="trial-test", category=category,
        short_description="s", description="d", status=ProductStatus.PUBLISHED,
        default_trial_days=7,
    )
    build = _staged_build(product)

    resp = client.get(f"/api/account/downloads/plugin-builds/{build.id}/trial")

    assert resp.status_code == 200
    assert resp["Content-Type"] == "application/vnd.microsoft.portable-executable"
    assert resp.content.startswith(PE_MAGIC)

    sku = LicensedProduct.objects.get(code=product.product_code)
    trial = ProductPurchase.objects.get(user=user, product=sku)
    assert trial.is_trial is True
    assert trial.payment_status == ProductPurchase.PaymentStatus.PAID
    assert trial.license_key  # a real key was issued, not left blank
    assert trial.expires_at is not None
    # No key is embedded in the .exe itself — same as the paid download; the
    # customer copies this key from /account/licenses and types it in.
    assert trial.license_key.encode() not in resp.content


def test_redownloading_the_trial_reuses_the_same_key_and_never_resets_the_clock(buyer_client, category):
    client, user = buyer_client
    product = Product.objects.create(
        name="Trial Test", product_code="trial-test-redownload", category=category,
        short_description="s", description="d", status=ProductStatus.PUBLISHED,
        default_trial_days=7,
    )
    build = _staged_build(product)

    client.get(f"/api/account/downloads/plugin-builds/{build.id}/trial")
    sku = LicensedProduct.objects.get(code=product.product_code)
    first = ProductPurchase.objects.get(user=user, product=sku)

    client.get(f"/api/account/downloads/plugin-builds/{build.id}/trial")
    assert ProductPurchase.objects.filter(user=user, product=sku).count() == 1
    second = ProductPurchase.objects.get(user=user, product=sku)
    assert second.pk == first.pk
    assert second.license_key == first.license_key
    assert second.expires_at == first.expires_at


def test_db_rejects_a_second_trial_purchase_for_the_same_user_and_product(buyer_client, category):
    # The actual race-safety mechanism behind get_or_create() in
    # AccountPluginBuildTrialDownloadView — without this DB-level partial
    # unique index, two near-simultaneous requests could each pass the "no
    # trial yet" check before either committed and both insert, minting two
    # trial keys for one account. Exercised directly against the model here
    # since simulating a real race in a single-threaded test isn't feasible.
    from django.db import IntegrityError

    _, user = buyer_client
    product = Product.objects.create(
        name="Race Test", product_code="race-test", category=category,
        short_description="s", description="d", status=ProductStatus.PUBLISHED,
        default_trial_days=7,
    )
    sku = LicensedProduct.objects.filter(product=product).first() or LicensedProduct.objects.create(
        code=product.product_code, name=product.name, price=product.price, currency=product.currency,
    )
    ProductPurchase.objects.create(user=user, product=sku, is_trial=True, payment_status=ProductPurchase.PaymentStatus.PAID)
    with pytest.raises(IntegrityError):
        ProductPurchase.objects.create(user=user, product=sku, is_trial=True, payment_status=ProductPurchase.PaymentStatus.PAID)


def test_trial_download_requires_login(category):
    product = Product.objects.create(
        name="Trial Test", product_code="trial-test-anon", category=category,
        short_description="s", description="d", status=ProductStatus.PUBLISHED,
        default_trial_days=7,
    )
    build = _staged_build(product)
    resp = Client().get(f"/api/account/downloads/plugin-builds/{build.id}/trial")
    assert resp.status_code in (401, 403)


def test_trial_download_rejected_when_product_has_no_trial(buyer_client, category):
    client, _ = buyer_client
    product = Product.objects.create(
        name="No Trial", product_code="no-trial-test", category=category,
        short_description="s", description="d", status=ProductStatus.PUBLISHED,
        default_trial_days=0, default_trial_hours=0, default_trial_minutes=0,
    )
    build = _staged_build(product)
    resp = client.get(f"/api/account/downloads/plugin-builds/{build.id}/trial")
    assert resp.status_code == 400


def test_trial_download_rejected_for_an_unpublished_product(buyer_client, category):
    client, _ = buyer_client
    product = Product.objects.create(
        name="Draft Trial", product_code="draft-trial-test", category=category,
        short_description="s", description="d", status=ProductStatus.DRAFT,
        default_trial_days=7,
    )
    build = _staged_build(product)
    resp = client.get(f"/api/account/downloads/plugin-builds/{build.id}/trial")
    assert resp.status_code == 400


def test_trial_download_fails_cleanly_without_dll_or_addin(buyer_client, category):
    client, _ = buyer_client
    product = Product.objects.create(
        name="Incomplete Trial", product_code="incomplete-trial-test", category=category,
        short_description="s", description="d", status=ProductStatus.PUBLISHED,
        default_trial_days=7,
    )
    build = PluginBuild.objects.create(product=product, revit_year="2025")
    resp = client.get(f"/api/account/downloads/plugin-builds/{build.id}/trial")
    assert resp.status_code == 400
