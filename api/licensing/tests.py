"""
Golden-master tests for the license activation contract. These assert the EXACT JSON
shape/values installed Revit plugins depend on. If any of these change, field installs
may break — treat a failure here as a compatibility regression, not a test to "fix".
See ARCHITECTURE §5.
"""
import hashlib
import json

import pytest
from django.test import Client
from django.utils import timezone

from licensing.models import LicensedProduct, MachineLicense, ProductPurchase

pytestmark = pytest.mark.django_db

PEPPER = "test-pepper"
FP = "MACHINE-FINGERPRINT-RAW"


def _protected_hash(raw):
    return hashlib.sha256(f"{raw}|{PEPPER}".encode()).hexdigest().upper()


@pytest.fixture(autouse=True)
def _pepper(settings):
    from django.core.cache import cache

    cache.clear()  # rate-limit counter is process-wide; isolate each test
    settings.LICENSE_PEPPER = PEPPER


@pytest.fixture
def product():
    return LicensedProduct.objects.create(
        code="bim-oneclick-2024-online", name="BIM OneClick", revit_year="2024",
        default_trial_days=30, is_active=True,
    )


def _activate(client, **body):
    return client.post(
        "/api/license/activate", data=json.dumps(body), content_type="application/json"
    )


# ── GET /api/license/products ──
def test_products_shape(product):
    resp = Client().get("/api/license/products")
    assert resp.status_code == 200
    data = resp.json()
    assert data == [
        {
            "code": "bim-oneclick-2024-online",
            "name": "BIM OneClick",
            "revitYear": "2024",
            "defaultTrialDays": 30,
        }
    ]


def test_products_excludes_inactive(product):
    LicensedProduct.objects.create(code="hidden-online", name="Hidden", is_active=False)
    codes = [p["code"] for p in Client().get("/api/license/products").json()]
    assert codes == ["bim-oneclick-2024-online"]


# ── POST /api/license/activate: validation ──
def test_activate_requires_product_code():
    resp = _activate(Client(), machineFingerprintHash=FP)
    assert resp.status_code == 400
    assert resp.json()["status"] == "bad_request"


def test_activate_requires_fingerprint(product):
    resp = _activate(Client(), productCode=product.code)
    assert resp.status_code == 400
    assert resp.json()["status"] == "bad_request"


def test_activate_unknown_product_is_blocked():
    resp = _activate(Client(), productCode="nope", machineFingerprintHash=FP)
    body = resp.json()
    assert body["authorized"] is False and body["status"] == "blocked"


# ── Trial lifecycle ──
def test_first_activation_starts_trial(product):
    resp = _activate(Client(), productCode=product.code, machineFingerprintHash=FP)
    body = resp.json()
    assert body["authorized"] is True
    assert body["status"] == "active"
    assert body["message"] == "Trial activated"
    assert body["remainingSeconds"] > 0
    ml = MachineLicense.objects.get(product=product)
    assert ml.machine_fingerprint_hash == _protected_hash(FP)  # peppered + uppercased


def test_trial_days_clamped_to_server_max(product):
    # Client asks for 99999 days; server caps at product.default_trial_days (30).
    _activate(Client(), productCode=product.code, machineFingerprintHash=FP, trialDays=99999)
    ml = MachineLicense.objects.get(product=product)
    span_days = (ml.expires_at - ml.started_at).days
    assert span_days == 30


def test_expired_trial_denied(product):
    _activate(Client(), productCode=product.code, machineFingerprintHash=FP)
    ml = MachineLicense.objects.get(product=product)
    ml.started_at = timezone.now() - timezone.timedelta(days=40)
    ml.expires_at = timezone.now() - timezone.timedelta(days=10)
    ml.save()
    body = _activate(Client(), productCode=product.code, machineFingerprintHash=FP).json()
    assert body["authorized"] is False and body["status"] == "expired"


# ── Paid licenses ──
def test_paid_license_key_authorizes(product, django_user_model):
    user = django_user_model.objects.create_user(username="u", email="u@x.com", password="x")
    purchase = ProductPurchase.objects.create(
        user=user, product=product, payment_status=ProductPurchase.PaymentStatus.PAID
    )
    body = _activate(
        Client(), productCode=product.code, machineFingerprintHash=FP, licenseKey=purchase.license_key
    ).json()
    assert body["authorized"] is True
    assert body["status"] == "paid"
    assert body["remainingSeconds"] == 3153600000


def test_paid_license_bound_to_other_machine_is_blocked(product, django_user_model):
    user = django_user_model.objects.create_user(username="u", email="u@x.com", password="x")
    purchase = ProductPurchase.objects.create(
        user=user, product=product, payment_status=ProductPurchase.PaymentStatus.PAID
    )
    # First machine binds the key.
    _activate(Client(), productCode=product.code, machineFingerprintHash="MACHINE-A", licenseKey=purchase.license_key)
    # A different machine using the same key is refused.
    body = _activate(
        Client(), productCode=product.code, machineFingerprintHash="MACHINE-B", licenseKey=purchase.license_key
    ).json()
    assert body["authorized"] is False and body["status"] == "blocked"


def test_manually_blocked_machine_denied(product):
    _activate(Client(), productCode=product.code, machineFingerprintHash=FP)
    ml = MachineLicense.objects.get(product=product)
    ml.status = "blocked"
    ml.save(update_fields=["status"])
    body = _activate(Client(), productCode=product.code, machineFingerprintHash=FP).json()
    assert body["authorized"] is False and body["status"] == "blocked"


def test_missing_pepper_is_500(product, settings):
    settings.LICENSE_PEPPER = ""
    resp = _activate(Client(), productCode=product.code, machineFingerprintHash=FP)
    assert resp.status_code == 500


# ── Rate limiting ──
def test_activate_rate_limited(product):
    client = Client()
    last = None
    for _ in range(35):  # limit is 30/min
        last = _activate(client, productCode=product.code, machineFingerprintHash=FP)
    assert last.status_code == 429
    assert last.json()["status"] == "rate_limited"


def test_response_has_exact_top_level_keys(product):
    # "signature" is a deliberate, additive extension (see
    # licensing.api_views._signed_response / LICENSE_SIGNING_KEY) — an
    # HMAC over the decision fields so a network-level tamper of a genuine
    # response can't just flip "authorized" without also forging a
    # signature it has no key for. Old, already-shipped clients ignore
    # unknown JSON fields, so this stays additive to the byte-compatible
    # contract rather than breaking it.
    body = _activate(Client(), productCode=product.code, machineFingerprintHash=FP).json()
    required = {"authorized", "status", "message", "startedAt", "expiresAt", "remainingSeconds"}
    assert required <= body.keys()
    assert body.keys() - required <= {"signature"}


# ── Response signing (Phase 4 — see licensing/api_views.py::_signed_response) ──
SIGNING_KEY = "test-signing-key"


@pytest.fixture
def _signing(settings):
    settings.LICENSE_SIGNING_KEY = SIGNING_KEY


def _expected_signature(body):
    import hmac

    canonical = "|".join(
        str(body.get(f, "")) for f in ("authorized", "status", "startedAt", "expiresAt", "remainingSeconds")
    )
    return hmac.new(SIGNING_KEY.encode(), canonical.encode(), hashlib.sha256).hexdigest()


def test_response_includes_a_valid_signature_when_signing_key_is_configured(product, _signing):
    body = _activate(Client(), productCode=product.code, machineFingerprintHash=FP).json()
    assert "signature" in body
    assert body["signature"] == _expected_signature(body)


def test_signature_reflects_the_actual_decision_not_a_constant(product, _signing):
    active_body = _activate(Client(), productCode=product.code, machineFingerprintHash=FP).json()
    bad_request_body = _activate(Client(), machineFingerprintHash=FP).json()  # missing productCode
    assert active_body["status"] == "active"
    assert bad_request_body["status"] == "bad_request"
    assert active_body["signature"] != bad_request_body["signature"]


def test_no_signature_field_when_signing_key_is_not_configured(product, settings):
    settings.LICENSE_SIGNING_KEY = ""
    body = _activate(Client(), productCode=product.code, machineFingerprintHash=FP).json()
    assert "signature" not in body
