"""
licensing/paymob.py — the parts that don't need a real network call: HMAC
computation/verification (the security-critical piece — an attacker who
could forge this could grant themselves a license for free) and the
Unified Checkout URL format. create_intention() itself is exercised via
mocking in test_checkout.py, not here — it's a thin wrapper around one
`requests.post` call with no logic of its own worth unit-testing in
isolation from a real or mocked HTTP response.
"""
import pytest

from licensing import paymob

pytestmark = pytest.mark.django_db

HMAC_SECRET = "test-paymob-hmac-secret"


@pytest.fixture(autouse=True)
def _paymob_settings(settings):
    settings.PAYMOB_HMAC_SECRET = HMAC_SECRET
    settings.PAYMOB_PUBLIC_KEY = "egy_pk_test_fake"
    settings.PAYMOB_BASE_URL = "https://accept.paymob.com"


SAMPLE_TRANSACTION = {
    "amount_cents": 10000,
    "created_at": "2026-01-01T00:00:00Z",
    "currency": "EGP",
    "error_occured": False,
    "has_parent_transaction": False,
    "id": 12345,
    "integration_id": 5083949,
    "is_3d_secure": True,
    "is_auth": False,
    "is_capture": False,
    "is_refunded": False,
    "is_standalone_payment": True,
    "is_voided": False,
    "order": {"id": 98765},
    "owner": 555,
    "pending": False,
    "source_data": {"pan": "1234", "sub_type": "MasterCard", "type": "card"},
    "success": True,
}


def test_compute_hmac_is_deterministic():
    assert paymob.compute_hmac(SAMPLE_TRANSACTION) == paymob.compute_hmac(SAMPLE_TRANSACTION)


def test_compute_hmac_changes_if_any_field_changes():
    mutated = {**SAMPLE_TRANSACTION, "success": False}
    assert paymob.compute_hmac(SAMPLE_TRANSACTION) != paymob.compute_hmac(mutated)


def test_verify_hmac_accepts_a_correctly_computed_signature():
    signature = paymob.compute_hmac(SAMPLE_TRANSACTION)
    assert paymob.verify_hmac(SAMPLE_TRANSACTION, signature) is True


def test_verify_hmac_is_case_insensitive_on_the_received_value():
    signature = paymob.compute_hmac(SAMPLE_TRANSACTION)
    assert paymob.verify_hmac(SAMPLE_TRANSACTION, signature.upper()) is True


def test_verify_hmac_rejects_a_tampered_transaction():
    signature = paymob.compute_hmac(SAMPLE_TRANSACTION)
    tampered = {**SAMPLE_TRANSACTION, "amount_cents": 1}  # attacker lowers the charged amount
    assert paymob.verify_hmac(tampered, signature) is False


def test_verify_hmac_rejects_a_wrong_signature():
    assert paymob.verify_hmac(SAMPLE_TRANSACTION, "0" * 128) is False


def test_verify_hmac_fails_closed_with_no_received_signature():
    assert paymob.verify_hmac(SAMPLE_TRANSACTION, "") is False


def test_verify_hmac_fails_closed_when_secret_isnt_configured(settings):
    settings.PAYMOB_HMAC_SECRET = ""
    signature = "anything"
    assert paymob.verify_hmac(SAMPLE_TRANSACTION, signature) is False


def test_hmac_field_extraction_handles_nested_and_missing_fields():
    # order.id and source_data.pan are nested; a field genuinely absent
    # from the payload must not blow up, just contribute an empty string.
    sparse = {"order": {"id": 1}, "source_data": {"pan": "9999"}}
    assert paymob._field(sparse, "order.id") == "1"
    assert paymob._field(sparse, "source_data.pan") == "9999"
    assert paymob._field(sparse, "does_not_exist") == ""
    assert paymob._field(sparse, "source_data.also_missing") == ""


def test_hmac_field_extraction_stringifies_booleans_lowercase():
    assert paymob._field({"success": True}, "success") == "true"
    assert paymob._field({"success": False}, "success") == "false"


def test_checkout_url_includes_public_key_and_client_secret():
    url = paymob.checkout_url("cs_test_abc123")
    assert url == "https://accept.paymob.com/unifiedcheckout/?publicKey=egy_pk_test_fake&clientSecret=cs_test_abc123"


def test_create_intention_raises_cleanly_when_not_configured(settings):
    settings.PAYMOB_SECRET_KEY = ""
    with pytest.raises(paymob.PaymobError):
        paymob.create_intention(
            amount_cents=1000, special_reference="x", notification_url="https://x/",
            redirection_url="https://x/", billing_data={}, items=[],
        )


def test_create_intention_raises_cleanly_without_an_integration_id(settings):
    settings.PAYMOB_SECRET_KEY = "sk_test_x"
    settings.PAYMOB_INTEGRATION_ID = ""
    with pytest.raises(paymob.PaymobError):
        paymob.create_intention(
            amount_cents=1000, special_reference="x", notification_url="https://x/",
            redirection_url="https://x/", billing_data={}, items=[],
        )
