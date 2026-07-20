"""
Trial installer download — no purchase required, gated purely on
Product.has_trial and being published. Real NSIS invocation, same
no-mocking philosophy as test_builder.py — see
licensing/account_api.py::AccountPluginBuildTrialDownloadView.
"""
import pytest
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.test import Client

from catalog.models import Category, Product
from catalog.models.product import ProductStatus
from installer.models import PluginBuild

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
    return client


def _staged_build(product):
    build = PluginBuild.objects.create(product=product, revit_year="2025", plugin_version="1.0.0")
    build.dll_storage_key = default_storage.save(f"test/{product.id}/Plugin.dll", ContentFile(b"fake dll"))
    build.dll_filename = "Plugin.dll"
    build.addin_storage_key = default_storage.save(f"test/{product.id}/Plugin.addin", ContentFile(SAMPLE_ADDIN_XML))
    build.addin_filename = "Plugin.addin"
    build.save()
    return build


def test_trial_download_streams_a_real_exe_with_no_purchase(buyer_client, category):
    product = Product.objects.create(
        name="Trial Test", product_code="trial-test", category=category,
        short_description="s", description="d", status=ProductStatus.PUBLISHED,
        default_trial_days=7,
    )
    build = _staged_build(product)

    resp = buyer_client.get(f"/api/account/downloads/plugin-builds/{build.id}/trial")

    assert resp.status_code == 200
    assert resp["Content-Type"] == "application/vnd.microsoft.portable-executable"
    assert resp.content.startswith(PE_MAGIC)


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
    product = Product.objects.create(
        name="No Trial", product_code="no-trial-test", category=category,
        short_description="s", description="d", status=ProductStatus.PUBLISHED,
        default_trial_days=0, default_trial_hours=0, default_trial_minutes=0,
    )
    build = _staged_build(product)
    resp = buyer_client.get(f"/api/account/downloads/plugin-builds/{build.id}/trial")
    assert resp.status_code == 400


def test_trial_download_rejected_for_an_unpublished_product(buyer_client, category):
    product = Product.objects.create(
        name="Draft Trial", product_code="draft-trial-test", category=category,
        short_description="s", description="d", status=ProductStatus.DRAFT,
        default_trial_days=7,
    )
    build = _staged_build(product)
    resp = buyer_client.get(f"/api/account/downloads/plugin-builds/{build.id}/trial")
    assert resp.status_code == 400


def test_trial_download_fails_cleanly_without_dll_or_addin(buyer_client, category):
    product = Product.objects.create(
        name="Incomplete Trial", product_code="incomplete-trial-test", category=category,
        short_description="s", description="d", status=ProductStatus.PUBLISHED,
        default_trial_days=7,
    )
    build = PluginBuild.objects.create(product=product, revit_year="2025")
    resp = buyer_client.get(f"/api/account/downloads/plugin-builds/{build.id}/trial")
    assert resp.status_code == 400
