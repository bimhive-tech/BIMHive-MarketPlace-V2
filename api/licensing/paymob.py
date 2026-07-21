"""
Paymob (Egypt) payment gateway client — the "Intention API", Paymob's
current recommended integration path: the backend creates an intention for
an amount, the customer is redirected to Paymob's hosted Unified Checkout
(card data never touches this server), and Paymob confirms the result via
a server-to-server webhook carrying an HMAC signature we verify here.

Reference (fetched live while building this, since the field/endpoint
shapes aren't otherwise documented in this repo):
  https://developers.paymob.com/paymob-docs/developers/intention-apis/create-intention
  https://developers.paymob.com/paymob-docs/developers/webhook-callbacks-and-hmac
"""
import hashlib
import hmac as hmac_lib

import requests
from django.conf import settings


class PaymobError(Exception):
    """Raised for anything that stops a Paymob checkout from proceeding —
    missing config, a non-2xx response, or a response missing the fields
    we need. Callers turn this into a clean 400, never a bare 500."""


def create_intention(
    *,
    amount_cents: int,
    special_reference: str,
    notification_url: str,
    redirection_url: str,
    billing_data: dict,
    items: list[dict],
) -> dict:
    """POSTs to /v1/intention/ and returns the parsed JSON response (which
    includes `client_secret`, used by checkout_url() below). `amount_cents`
    is sent as-is under PAYMOB_CURRENCY — see the currency-mismatch note in
    settings.py, this is a test-mode simplification, not real FX."""
    if not settings.PAYMOB_SECRET_KEY:
        raise PaymobError("Paymob isn't configured (PAYMOB_SECRET_KEY is blank).")
    if not settings.PAYMOB_INTEGRATION_ID:
        raise PaymobError(
            "Paymob isn't fully configured — PAYMOB_INTEGRATION_ID is blank. "
            "Get it from the Paymob dashboard's Payment Integrations page."
        )

    payload = {
        "amount": amount_cents,
        "currency": settings.PAYMOB_CURRENCY,
        "payment_methods": [int(settings.PAYMOB_INTEGRATION_ID)],
        "items": items,
        "billing_data": billing_data,
        "special_reference": special_reference,
        "notification_url": notification_url,
        "redirection_url": redirection_url,
        "expiration": 3600,
    }
    try:
        response = requests.post(
            f"{settings.PAYMOB_BASE_URL}/v1/intention/",
            json=payload,
            headers={"Authorization": f"Token {settings.PAYMOB_SECRET_KEY}"},
            timeout=15,
        )
    except requests.RequestException as exc:
        raise PaymobError(f"Could not reach Paymob: {exc}") from exc

    if not response.ok:
        raise PaymobError(f"Paymob rejected the intention request ({response.status_code}): {response.text[:500]}")

    data = response.json()
    if not data.get("client_secret"):
        raise PaymobError("Paymob's response had no client_secret.")
    return data


def checkout_url(client_secret: str) -> str:
    """The Unified Checkout page to redirect the customer's browser to —
    Paymob-hosted, so this app never sees card details at all."""
    return f"{settings.PAYMOB_BASE_URL}/unifiedcheckout/?publicKey={settings.PAYMOB_PUBLIC_KEY}&clientSecret={client_secret}"


# The exact, fixed field order Paymob's docs specify for a TRANSACTION
# webhook's HMAC — see webhook-callbacks-and-hmac above. Dotted names are
# nested lookups (e.g. "order.id" -> obj["order"]["id"]).
_HMAC_FIELDS = [
    "amount_cents", "created_at", "currency", "error_occured", "has_parent_transaction",
    "id", "integration_id", "is_3d_secure", "is_auth", "is_capture", "is_refunded",
    "is_standalone_payment", "is_voided", "order.id", "owner", "pending",
    "source_data.pan", "source_data.sub_type", "source_data.type", "success",
]


def _field(obj: dict, dotted_path: str) -> str:
    value = obj
    for part in dotted_path.split("."):
        value = (value or {}).get(part) if isinstance(value, dict) else None
    if isinstance(value, bool):
        return "true" if value else "false"
    return "" if value is None else str(value)


def compute_hmac(transaction_obj: dict) -> str:
    concatenated = "".join(_field(transaction_obj, field) for field in _HMAC_FIELDS)
    return hmac_lib.new(
        settings.PAYMOB_HMAC_SECRET.encode("utf-8"), concatenated.encode("utf-8"), hashlib.sha512
    ).hexdigest()


def verify_hmac(transaction_obj: dict, received_hmac: str) -> bool:
    """Constant-time comparison — a webhook is only trusted if this
    passes. Fails closed (False) if either side is empty, never treats a
    missing signature as "no signature required"."""
    if not settings.PAYMOB_HMAC_SECRET or not received_hmac:
        return False
    return hmac_lib.compare_digest(compute_hmac(transaction_obj), received_hmac.strip().lower())
