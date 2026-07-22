"""
License activation API — BYTE-COMPATIBLE with v1. Installed Revit plugins call these
endpoints; the request/response JSON, status vocabulary, fingerprint hashing, trial
clamping and rate limiting must not change. Covered by golden-master tests in
licensing/tests.py. See ARCHITECTURE §5.

Endpoints (registered in config/urls.py, no trailing slash):
  GET  /api/license/products
  POST /api/license/activate
"""
import hashlib
import hmac
import json
import math
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from licensing.models import LicenseEvent, LicensedProduct, MachineLicense, ProductPurchase
from licensing.services import revoke_purchase_access


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────
def _client_ip(request):
    xff = (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip()
    return xff or request.META.get("REMOTE_ADDR") or "unknown"


def _rate_limited(request, bucket, limit=30, window=60):
    """Per-IP fixed-window throttle. Fails open on cache errors so a cache outage
    never blocks legitimate plugin activations."""
    key = f"licrl:{bucket}:{_client_ip(request)}"
    try:
        if cache.add(key, 1, timeout=window):
            return False
        try:
            count = cache.incr(key)
        except ValueError:
            cache.set(key, 1, timeout=window)
            count = 1
        return count > limit
    except Exception:
        return False


def _too_many_requests():
    return _signed_response(
        {
            "authorized": False,
            "status": "rate_limited",
            "message": "Too many requests. Please try again shortly.",
            "remainingSeconds": 0,
        },
        status=429,
    )


def _iso_utc(value):
    if value is None:
        return None
    return value.astimezone().isoformat()


def _hash_hex(value):
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest().upper()


# ─────────────────────────────────────────────────────────────
# Response signing (additive — see installer-generator-reference project
# notes, phase 4). A tampered/patched loader can still fabricate its own
# "authorized: true" locally without ever calling the server, so this isn't
# a silver bullet — but it means a network-level tamper of a genuine
# response (or a naive replay against a different request) requires forging
# an HMAC it doesn't have the key for, not just editing a JSON boolean.
# Purely additive: existing fields/shape are untouched, so an already-shipped
# plugin that doesn't know about "signature" keeps working unmodified.
# ─────────────────────────────────────────────────────────────
_SIGNED_FIELDS = ("authorized", "status", "startedAt", "expiresAt", "remainingSeconds")


def _sign_payload(payload: dict) -> str:
    # Deliberately NOT json.dumps(payload) — JSON key ordering/whitespace
    # isn't guaranteed identical across languages, which would make
    # independent re-implementations of verification fragile. A fixed,
    # pipe-delimited field order avoids that ambiguity.
    canonical = "|".join(str(payload.get(field, "")) for field in _SIGNED_FIELDS)
    return hmac.new(
        settings.LICENSE_SIGNING_KEY.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def _signed_response(payload: dict, status: int = 200) -> JsonResponse:
    if settings.LICENSE_SIGNING_KEY:
        payload = {**payload, "signature": _sign_payload(payload)}
    return JsonResponse(payload, status=status)


def _json_body(request):
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def _log_event(product, machine_hash, event_type, payload, machine_license=None, event_time=None):
    LicenseEvent.objects.create(
        product=product,
        machine_license=machine_license,
        machine_fingerprint_hash=machine_hash,
        event_type=event_type,
        event_time=event_time or timezone.now(),
        payload=payload or {},
    )


def _denied_purchase_response(machine_license, purchase):
    return _signed_response(
        {
            "authorized": False,
            "status": purchase.denial_status,
            "message": purchase.denial_message,
            "startedAt": _iso_utc(machine_license.started_at) if machine_license else None,
            "expiresAt": _iso_utc(machine_license.expires_at) if machine_license else None,
            "remainingSeconds": 0,
        }
    )


def _no_seats_denied_response(machine_license):
    return _signed_response(
        {
            "authorized": False,
            "status": "blocked",
            "message": "This license key has no available seats left. Free up a machine from your account, or buy another seat.",
            "startedAt": _iso_utc(machine_license.started_at) if machine_license else None,
            "expiresAt": _iso_utc(machine_license.expires_at) if machine_license else None,
            "remainingSeconds": 0,
        }
    )


def _trial_already_used_response(machine_license):
    return _signed_response(
        {
            "authorized": False,
            "status": "trial_used",
            "message": "This device has already used its free trial for this product. Enter a purchased license key to continue.",
            "startedAt": _iso_utc(machine_license.started_at) if machine_license else None,
            "expiresAt": _iso_utc(machine_license.expires_at) if machine_license else None,
            "remainingSeconds": 0,
        }
    )


# ─────────────────────────────────────────────────────────────
# GET /api/license/products
# ─────────────────────────────────────────────────────────────
@require_GET
def license_products_api(request):
    if _rate_limited(request, "products", limit=60):
        return _too_many_requests()
    products = (
        LicensedProduct.objects.filter(is_active=True)
        .order_by("code")
        .values("code", "name", "revit_year", "default_trial_days", "default_trial_hours", "default_trial_minutes")
    )
    data = []
    for item in products:
        total_minutes = (
            (item["default_trial_days"] or 0) * 1440
            + (item["default_trial_hours"] or 0) * 60
            + (item["default_trial_minutes"] or 0)
        )
        data.append(
            {
                "code": item["code"],
                "name": item["name"] or item["code"],
                "revitYear": item["revit_year"] or "",
                # Whole days, rounded UP so a plugin reading this as a plain
                # int never sees a shorter trial than actually configured —
                # the real to-the-minute value is what /api/license/activate
                # enforces (see the trial clamp below); this field is
                # display-only and was always whole days in the locked
                # response shape.
                "defaultTrialDays": math.ceil(total_minutes / 1440) or 30,
            }
        )
    return JsonResponse(data, safe=False)


# ─────────────────────────────────────────────────────────────
# POST /api/license/activate
# ─────────────────────────────────────────────────────────────
@csrf_exempt
@require_POST
def license_activate_api(request):
    if _rate_limited(request, "activate", limit=30):
        return _too_many_requests()
    body = _json_body(request)
    if body is None:
        return _signed_response(
            {"authorized": False, "status": "bad_request", "message": "Invalid request.", "remainingSeconds": 0},
            status=400,
        )

    product_code = (body.get("productCode") or "").strip()
    machine_fingerprint_hash = (body.get("machineFingerprintHash") or "").strip()
    if not product_code:
        return _signed_response(
            {"authorized": False, "status": "bad_request", "message": "Product code is required.", "remainingSeconds": 0},
            status=400,
        )
    if not machine_fingerprint_hash:
        return _signed_response(
            {"authorized": False, "status": "bad_request", "message": "Machine fingerprint hash is required.", "remainingSeconds": 0},
            status=400,
        )
    if not settings.LICENSE_PEPPER:
        return JsonResponse({"detail": "LICENSE_PEPPER is not configured."}, status=500)

    try:
        product = LicensedProduct.objects.get(code=product_code, is_active=True)
    except LicensedProduct.DoesNotExist:
        return _signed_response(
            {"authorized": False, "status": "blocked", "message": "Access denied. Product is inactive.", "remainingSeconds": 0}
        )

    now = timezone.now()
    fingerprint_version = (body.get("fingerprintVersion") or "HWFP-2").strip() or "HWFP-2"
    plugin_version = (body.get("pluginVersion") or "").strip()
    machine_data = body.get("machineData") or {}
    metadata = {
        "pluginVersion": body.get("pluginVersion"),
        "fingerprintVersion": body.get("fingerprintVersion"),
        "ipAddress": body.get("ipAddress"),
    }
    license_key = (body.get("licenseKey") or "").strip()
    protected_hash = _hash_hex(f"{machine_fingerprint_hash}|{settings.LICENSE_PEPPER}")

    machine_license = (
        MachineLicense.objects.filter(product=product, machine_fingerprint_hash=protected_hash)
        .select_related("purchase", "user")
        .first()
    )
    paid_purchase = None
    matched_purchase = None
    if license_key:
        matched_purchase = (
            ProductPurchase.objects.filter(product=product, license_key__iexact=license_key)
            .select_related("user")
            .first()
        )
        if matched_purchase and matched_purchase.payment_status == ProductPurchase.PaymentStatus.PAID:
            paid_purchase = matched_purchase
    elif machine_license and machine_license.purchase_id:
        matched_purchase = (
            ProductPurchase.objects.filter(pk=machine_license.purchase_id)
            .select_related("user")
            .first()
        )
        if matched_purchase and matched_purchase.payment_status == ProductPurchase.PaymentStatus.PAID:
            paid_purchase = matched_purchase

    purchase_backed_block = (
        machine_license
        and machine_license.status == "blocked"
        and machine_license.purchase_id
        and machine_license.purchase
        and not machine_license.purchase.is_license_active
    )

    if machine_license and machine_license.status == "blocked" and not purchase_backed_block:
        _log_event(product, protected_hash, "blocked", {"reason": "manually_blocked"}, machine_license=machine_license, event_time=now)
        return _signed_response(
            {
                "authorized": False,
                "status": "blocked",
                "message": "Access denied. Please contact BIMHive.",
                "startedAt": _iso_utc(machine_license.started_at),
                "expiresAt": _iso_utc(machine_license.expires_at),
                "remainingSeconds": 0,
            }
        )

    invalid_purchase = None
    if matched_purchase and not matched_purchase.is_license_active:
        invalid_purchase = matched_purchase
    elif machine_license and machine_license.purchase_id:
        linked_purchase = matched_purchase or machine_license.purchase
        if linked_purchase and not linked_purchase.is_license_active:
            invalid_purchase = linked_purchase

    if invalid_purchase:
        if machine_license and machine_license.purchase_id == invalid_purchase.pk:
            revoke_purchase_access(invalid_purchase, status=invalid_purchase.payment_status, reason="startup_recheck", event_time=now)
            machine_license.refresh_from_db()
        _log_event(
            product,
            protected_hash,
            "purchase_denied",
            {"reason": invalid_purchase.payment_status, "purchaseId": str(invalid_purchase.pk)},
            machine_license=machine_license,
            event_time=now,
        )
        return _denied_purchase_response(machine_license, invalid_purchase)

    if paid_purchase:
        # A machine that has ever consumed a trial for this product (see
        # MachineLicense.used_trial) stays locked out of any *other* trial
        # purchase forever, regardless of which account/key presents it —
        # without this, a machine's binding just gets silently reassigned to
        # whichever new valid key shows up (see the block below), which is
        # exactly how a new account + the same PC could mint itself an
        # unlimited string of fresh trials. Re-activating the SAME trial
        # purchase it already used (a reinstall, e.g.) is unaffected — that's
        # not a new trial, and its own expiry is enforced separately via
        # invalid_purchase above once it lapses.
        if (
            paid_purchase.is_trial
            and machine_license is not None
            and machine_license.used_trial
            and machine_license.purchase_id != paid_purchase.pk
        ):
            _log_event(
                product,
                protected_hash,
                "trial_denied_device_already_used",
                {"licenseKey": paid_purchase.license_key, "purchaseId": str(paid_purchase.pk)},
                machine_license=machine_license,
                event_time=now,
            )
            return _trial_already_used_response(machine_license)

        # `has_seat_for` is True either because this exact machine already
        # holds one of the purchase's seats (a repeat/heartbeat activation —
        # doesn't consume a new one) or because a seat is still free. A
        # purchase with seats=1 behaves exactly like the old single-machine
        # rule; seats>1 lets that many distinct machines stay bound at once.
        if not paid_purchase.has_seat_for(protected_hash):
            if machine_license and machine_license.purchase_id == paid_purchase.pk:
                machine_license.status = "blocked"
                machine_license.last_seen_at = now
                machine_license.save(update_fields=["status", "last_seen_at"])
            reference_machine = machine_license or paid_purchase.active_machine_licenses.first()
            _log_event(
                product,
                protected_hash,
                "paid_activation_denied_no_seats_available",
                {
                    "licenseKey": paid_purchase.license_key,
                    "purchaseId": str(paid_purchase.pk),
                    "seats": paid_purchase.seats,
                },
                machine_license=machine_license,
                event_time=now,
            )
            return _no_seats_denied_response(reference_machine)

        # A LicenseCode-redeemed or trial purchase carries its own expiry; a
        # normal (perpetual) purchase has expires_at=None and gets the
        # effectively-forever date, same as before this field existed.
        paid_expires_at = paid_purchase.expires_at or (now + timedelta(days=365 * 100))
        was_first_activation = machine_license is None
        if machine_license is None:
            machine_license = MachineLicense.objects.create(
                product=product,
                user=paid_purchase.user,
                purchase=paid_purchase,
                machine_fingerprint_hash=protected_hash,
                fingerprint_version=fingerprint_version,
                status="paid",
                started_at=now,
                expires_at=paid_expires_at,
                first_seen_at=now,
                last_seen_at=now,
                install_count=1,
                plugin_version=plugin_version,
                machine_data=machine_data,
                metadata=metadata,
                used_trial=paid_purchase.is_trial,
            )
        else:
            machine_license.user = paid_purchase.user
            machine_license.purchase = paid_purchase
            machine_license.status = "paid"
            machine_license.expires_at = paid_expires_at
            machine_license.last_seen_at = now
            machine_license.install_count += 1
            machine_license.plugin_version = plugin_version or machine_license.plugin_version
            machine_license.machine_data = {**(machine_license.machine_data or {}), **machine_data}
            machine_license.metadata = {**(machine_license.metadata or {}), **metadata}
            if paid_purchase.is_trial:
                machine_license.used_trial = True
            machine_license.save()

        _log_event(
            product,
            protected_hash,
            "trial_activation" if paid_purchase.is_trial else "paid_activation",
            {"licenseKey": paid_purchase.license_key, "userId": paid_purchase.user_id},
            machine_license=machine_license,
            event_time=now,
        )
        # A trial purchase still expires (see AccountPluginBuildTrialDownloadView),
        # so — unlike a real paid purchase, which reports the fixed "forever"
        # shape below — it needs its actual startedAt/expiresAt/remainingSeconds
        # so LicLoader can tell the customer how much trial time is left, and so
        # a lapsed trial denies via the invalid_purchase branch above with a real
        # "expired" status instead of looking indistinguishable from "paid."
        if paid_purchase.is_trial:
            remaining = max(0, int((paid_expires_at - now).total_seconds()))
            return _signed_response(
                {
                    "authorized": True,
                    "status": "trial",
                    "message": "Trial activated" if was_first_activation else "Trial active",
                    "startedAt": _iso_utc(machine_license.started_at),
                    "expiresAt": _iso_utc(paid_expires_at),
                    "remainingSeconds": remaining,
                }
            )
        return _signed_response(
            {
                "authorized": True,
                "status": "paid",
                "message": "Paid license active",
                "startedAt": None,
                "expiresAt": None,
                "remainingSeconds": 3153600000,
            }
        )

    # No key at all, or a key that doesn't resolve to an active purchase (a
    # trial purchase counts here too — see AccountPluginBuildTrialDownloadView,
    # which is the only way to acquire a trial key). A key is always required
    # to activate, trial or paid — there's deliberately no anonymous/keyless
    # grant here anymore.
    _log_event(product, protected_hash, "denied", {"reason": "no_active_purchase"}, machine_license=machine_license, event_time=now)
    return _signed_response(
        {
            "authorized": False,
            "status": "blocked",
            "message": "Enter a valid BIM Hive license key — including a free trial key from your account — to activate this plugin.",
            "startedAt": _iso_utc(machine_license.started_at) if machine_license else None,
            "expiresAt": _iso_utc(machine_license.expires_at) if machine_license else None,
            "remainingSeconds": 0,
        }
    )
