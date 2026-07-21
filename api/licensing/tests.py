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


# ── Trial lifecycle — a trial key is a real ProductPurchase(is_trial=True),
# created by AccountPluginBuildTrialDownloadView, not a client-requested
# length. There's no anonymous/keyless grant anymore — see the "no key at
# all" test below. ──
def _trial_purchase(product, user, *, expires_in=None):
    from datetime import timedelta

    return ProductPurchase.objects.create(
        user=user, product=product, is_trial=True,
        payment_status=ProductPurchase.PaymentStatus.PAID,
        amount=0, expires_at=(timezone.now() + expires_in) if expires_in else None,
    )


def test_no_key_at_all_is_denied(product):
    resp = _activate(Client(), productCode=product.code, machineFingerprintHash=FP)
    body = resp.json()
    assert body["authorized"] is False
    assert body["status"] == "blocked"
    assert not MachineLicense.objects.filter(product=product).exists()


def test_trial_key_authorizes_and_reports_remaining_time(product, django_user_model):
    from datetime import timedelta

    user = django_user_model.objects.create_user(username="u", email="u@x.com", password="x")
    trial = _trial_purchase(product, user, expires_in=timedelta(days=30))

    body = _activate(Client(), productCode=product.code, machineFingerprintHash=FP, licenseKey=trial.license_key).json()
    assert body["authorized"] is True
    assert body["status"] == "trial"
    assert body["message"] == "Trial activated"
    assert body["remainingSeconds"] > 0
    ml = MachineLicense.objects.get(product=product)
    assert ml.machine_fingerprint_hash == _protected_hash(FP)  # peppered + uppercased


def test_repeat_trial_activation_reports_still_active(product, django_user_model):
    from datetime import timedelta

    user = django_user_model.objects.create_user(username="u", email="u@x.com", password="x")
    trial = _trial_purchase(product, user, expires_in=timedelta(days=30))
    _activate(Client(), productCode=product.code, machineFingerprintHash=FP, licenseKey=trial.license_key)

    body = _activate(Client(), productCode=product.code, machineFingerprintHash=FP, licenseKey=trial.license_key).json()
    assert body["authorized"] is True
    assert body["status"] == "trial"
    assert body["message"] == "Trial active"


def test_products_shape_rounds_fractional_days_up(product):
    # 1 day 12 hours = 36h = 1.5 days -> the locked defaultTrialDays field is
    # a whole int, rounded UP so a plugin reading it never sees less trial
    # than actually configured (the real to-the-minute value is enforced by
    # /api/license/activate directly, not this display field).
    product.default_trial_days = 1
    product.default_trial_hours = 12
    product.save()
    data = Client().get("/api/license/products").json()
    assert data[0]["defaultTrialDays"] == 2


def test_expired_trial_denied(product, django_user_model):
    from datetime import timedelta

    user = django_user_model.objects.create_user(username="u", email="u@x.com", password="x")
    trial = _trial_purchase(product, user, expires_in=timedelta(days=-1))  # already expired
    body = _activate(Client(), productCode=product.code, machineFingerprintHash=FP, licenseKey=trial.license_key).json()
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


def test_paid_license_with_seats_allows_that_many_concurrent_machines(product, django_user_model):
    user = django_user_model.objects.create_user(username="u", email="u@x.com", password="x")
    purchase = ProductPurchase.objects.create(
        user=user, product=product, payment_status=ProductPurchase.PaymentStatus.PAID, seats=3
    )
    for fp in ("MACHINE-A", "MACHINE-B", "MACHINE-C"):
        body = _activate(
            Client(), productCode=product.code, machineFingerprintHash=fp, licenseKey=purchase.license_key
        ).json()
        assert body["authorized"] is True and body["status"] == "paid"
    assert MachineLicense.objects.filter(purchase=purchase).count() == 3


def test_paid_license_denies_activation_beyond_its_seat_count(product, django_user_model):
    user = django_user_model.objects.create_user(username="u", email="u@x.com", password="x")
    purchase = ProductPurchase.objects.create(
        user=user, product=product, payment_status=ProductPurchase.PaymentStatus.PAID, seats=2
    )
    for fp in ("MACHINE-A", "MACHINE-B"):
        _activate(Client(), productCode=product.code, machineFingerprintHash=fp, licenseKey=purchase.license_key)
    body = _activate(
        Client(), productCode=product.code, machineFingerprintHash="MACHINE-C", licenseKey=purchase.license_key
    ).json()
    assert body["authorized"] is False and body["status"] == "blocked"


def test_repeat_activation_from_an_already_bound_machine_does_not_need_a_free_seat(product, django_user_model):
    user = django_user_model.objects.create_user(username="u", email="u@x.com", password="x")
    purchase = ProductPurchase.objects.create(
        user=user, product=product, payment_status=ProductPurchase.PaymentStatus.PAID, seats=1
    )
    _activate(Client(), productCode=product.code, machineFingerprintHash=FP, licenseKey=purchase.license_key)
    # Same machine, same single-seat purchase, activating again (e.g. plugin
    # restart) — must succeed, not be treated as a second machine wanting a seat.
    body = _activate(
        Client(), productCode=product.code, machineFingerprintHash=FP, licenseKey=purchase.license_key
    ).json()
    assert body["authorized"] is True and body["status"] == "paid"
    assert MachineLicense.objects.filter(purchase=purchase).count() == 1


def test_manually_blocked_machine_denied(product, django_user_model):
    user = django_user_model.objects.create_user(username="u", email="u@x.com", password="x")
    purchase = ProductPurchase.objects.create(
        user=user, product=product, payment_status=ProductPurchase.PaymentStatus.PAID
    )
    _activate(Client(), productCode=product.code, machineFingerprintHash=FP, licenseKey=purchase.license_key)
    ml = MachineLicense.objects.get(product=product)
    ml.status = "blocked"
    ml.save(update_fields=["status"])
    body = _activate(
        Client(), productCode=product.code, machineFingerprintHash=FP, licenseKey=purchase.license_key
    ).json()
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
    denied_body = _activate(Client(), productCode=product.code, machineFingerprintHash=FP).json()
    bad_request_body = _activate(Client(), machineFingerprintHash=FP).json()  # missing productCode
    assert denied_body["status"] == "blocked"
    assert bad_request_body["status"] == "bad_request"
    assert denied_body["signature"] != bad_request_body["signature"]


def test_no_signature_field_when_signing_key_is_not_configured(product, settings):
    settings.LICENSE_SIGNING_KEY = ""
    body = _activate(Client(), productCode=product.code, machineFingerprintHash=FP).json()
    assert "signature" not in body
