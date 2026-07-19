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
        .values("code", "name", "revit_year", "default_trial_days")
    )
    data = [
        {
            "code": item["code"],
            "name": item["name"] or item["code"],
            "revitYear": item["revit_year"] or "",
            "defaultTrialDays": item["default_trial_days"] or 30,
        }
        for item in products
    ]
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
    # SECURITY: the client may *request* a trial length, but the server caps it at the
    # product's configured maximum (default_trial_days). A tampered client asking for a
    # 99999-day trial is clamped; a legitimate request (e.g. 7 days) is unchanged.
    trial_minutes = int(body.get("trialMinutes") or 0)
    trial_days = int(body.get("trialDays") or 0)
    requested_trial_minutes = (
        trial_minutes if trial_minutes > 0 else ((trial_days * 24 * 60) if trial_days > 0 else None)
    )
    server_max_minutes = max(1, product.default_trial_days or 30) * 24 * 60
    if requested_trial_minutes is None or requested_trial_minutes > server_max_minutes:
        effective_trial_minutes = server_max_minutes
    else:
        effective_trial_minutes = requested_trial_minutes

    fingerprint_version = (body.get("fingerprintVersion") or "HWFP-2").strip() or "HWFP-2"
    plugin_version = (body.get("pluginVersion") or "").strip()
    machine_data = body.get("machineData") or {}
    metadata = {
        "pluginVersion": body.get("pluginVersion"),
        "fingerprintVersion": body.get("fingerprintVersion"),
        "trialDays": body.get("trialDays"),
        "trialMinutes": body.get("trialMinutes"),
        "effectiveTrialMinutes": effective_trial_minutes,
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

        paid_expires_at = now + timedelta(days=365 * 100)
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
            machine_license.save()

        _log_event(
            product,
            protected_hash,
            "paid_activation",
            {"licenseKey": paid_purchase.license_key, "userId": paid_purchase.user_id},
            machine_license=machine_license,
            event_time=now,
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

    if machine_license is None:
        expires_at = now + timedelta(minutes=effective_trial_minutes)
        machine_license = MachineLicense.objects.create(
            product=product,
            machine_fingerprint_hash=protected_hash,
            fingerprint_version=fingerprint_version,
            status="active",
            started_at=now,
            expires_at=expires_at,
            first_seen_at=now,
            last_seen_at=now,
            install_count=1,
            plugin_version=plugin_version,
            machine_data=machine_data,
            metadata=metadata,
        )
        _log_event(
            product,
            protected_hash,
            "activate",
            {
                "productCode": product_code,
                "trialDays": trial_days,
                "trialMinutes": trial_minutes,
                "effectiveTrialMinutes": effective_trial_minutes,
            },
            machine_license=machine_license,
            event_time=now,
        )
        remaining = max(0, int((expires_at - now).total_seconds()))
        return _signed_response(
            {
                "authorized": True,
                "status": "active",
                "message": "Trial activated",
                "startedAt": _iso_utc(machine_license.started_at),
                "expiresAt": _iso_utc(machine_license.expires_at),
                "remainingSeconds": remaining,
            }
        )

    machine_license.last_seen_at = now
    machine_license.install_count += 1
    machine_license.plugin_version = plugin_version or machine_license.plugin_version
    machine_license.machine_data = {**(machine_license.machine_data or {}), **machine_data}
    machine_license.metadata = {**(machine_license.metadata or {}), **metadata}
    normalized_expires_at = machine_license.started_at + timedelta(minutes=effective_trial_minutes)
    if machine_license.status != "paid" and normalized_expires_at < machine_license.expires_at:
        machine_license.expires_at = normalized_expires_at
    machine_license.save()

    if now >= machine_license.expires_at:
        machine_license.status = "expired"
        machine_license.last_seen_at = now
        machine_license.save(update_fields=["status", "last_seen_at"])
        _log_event(product, protected_hash, "expired", {"reason": "trial_finished"}, machine_license=machine_license, event_time=now)
        return _signed_response(
            {
                "authorized": False,
                "status": "expired",
                "message": "Access denied. Trial expired. Please contact BIMHive.",
                "startedAt": _iso_utc(machine_license.started_at),
                "expiresAt": _iso_utc(machine_license.expires_at),
                "remainingSeconds": 0,
            }
        )

    _log_event(product, protected_hash, "recheck", {"reason": "still_active"}, machine_license=machine_license, event_time=now)
    remaining = max(0, int((machine_license.expires_at - now).total_seconds()))
    return _signed_response(
        {
            "authorized": True,
            "status": "active",
            "message": "Trial active",
            "startedAt": _iso_utc(machine_license.started_at),
            "expiresAt": _iso_utc(machine_license.expires_at),
            "remainingSeconds": remaining,
        }
    )
