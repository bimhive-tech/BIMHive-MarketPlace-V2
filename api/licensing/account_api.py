"""
Customer-facing account API — "my orders / my licenses / my downloads"
(mounted under /api/account/). Everything here is scoped to request.user; this is
the read side of the same ProductPurchase/MachineLicense data the admin API manages.
"""
from django.conf import settings
from django.utils import timezone
from rest_framework import generics, serializers
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from activity.models import ActivityVerb
from activity.services import log_activity
from licensing import paymob
from licensing.models import LicensedProduct, MachineLicense, ProductPurchase
from licensing.services import (
    LicenseCodeError,
    expires_at_for,
    redeem_license_code,
    revoke_purchase_access,
    subscription_duration,
)

# Matches the "30-Day Money Back Guarantee" copy already shown on every buy
# box (web/features/product/BuyBox/BuyBox.tsx) — self-service refund gives
# that promise an actual mechanism instead of just being marketing copy.
REFUND_WINDOW_DAYS = 30


class AccountOrderSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_code = serializers.CharField(source="product.code", read_only=True)

    class Meta:
        model = ProductPurchase
        fields = [
            "id", "product_name", "product_code", "amount", "currency", "payment_status",
            "license_key", "seats", "is_trial", "billing_period", "requested_at", "paid_at",
        ]


class AccountOrderListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AccountOrderSerializer

    def get_queryset(self):
        return (
            ProductPurchase.objects.filter(user=self.request.user)
            .select_related("product")
            .order_by("-requested_at")
        )


class AccountOrderRefundView(APIView):
    """Self-service cancel/refund — there's no distinct "cancel a pending
    order" state today (checkout marks everything PAID immediately, see
    CheckoutView), so this is the one action for both: give up this
    purchase, no staff involved. Reuses the exact same
    licensing.services.revoke_purchase_access staff already use, so a
    refunded purchase behaves identically either way.

    Why refunding can't be used to grab a second free trial on the same
    machine: revoking never deletes the MachineLicense row, only changes
    its status — and /api/license/activate only ever issues a trial when
    NO MachineLicense row exists yet for that (product, machine) pair. Once
    a machine has activated at all (trial or paid), that row exists
    forever, so a later refund just leaves it pointing at an inactive
    purchase — the machine is denied, never handed a fresh trial. Nothing
    extra needed here to prevent that; it falls out of how activation
    already works."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        from datetime import timedelta

        from django.utils import timezone

        purchase = ProductPurchase.objects.filter(pk=pk, user=request.user).select_related("product").first()
        if not purchase:
            raise ValidationError({"detail": "Order not found."})
        if purchase.payment_status != ProductPurchase.PaymentStatus.PAID:
            raise ValidationError({"detail": "This order isn't eligible for a refund."})
        if not purchase.paid_at or timezone.now() - purchase.paid_at > timedelta(days=REFUND_WINDOW_DAYS):
            raise ValidationError(
                {"detail": f"This order is outside the {REFUND_WINDOW_DAYS}-day refund window. Contact support for help."}
            )

        revoke_purchase_access(purchase, status=ProductPurchase.PaymentStatus.REFUNDED, reason="customer_requested")
        purchase.refresh_from_db()
        log_activity(
            request.user,
            ActivityVerb.ORDER_REFUND_REQUESTED,
            target_label=purchase.product.name,
            metadata={"self_service": True},
        )
        return Response(AccountOrderSerializer(purchase).data)


class AccountMachineSerializer(serializers.ModelSerializer):
    fingerprint_preview = serializers.SerializerMethodField()

    class Meta:
        model = MachineLicense
        fields = [
            "id", "fingerprint_preview", "status", "started_at", "last_seen_at",
            "install_count", "plugin_version",
        ]

    def get_fingerprint_preview(self, obj):
        h = obj.machine_fingerprint_hash or ""
        return f"{h[:12]}…" if h else ""


class AccountLicenseSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_code = serializers.CharField(source="product.code", read_only=True)
    machines = AccountMachineSerializer(source="machine_licenses", many=True, read_only=True)

    class Meta:
        model = ProductPurchase
        fields = [
            "id", "product_name", "product_code", "payment_status", "license_status", "license_key",
            "seats", "is_trial", "billing_period", "expires_at", "requested_at", "paid_at", "machines",
        ]


class AccountLicenseListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AccountLicenseSerializer

    def get_queryset(self):
        return (
            ProductPurchase.objects.filter(user=self.request.user)
            .select_related("product", "product__product")
            .prefetch_related("machine_licenses")
            .order_by("-requested_at")
        )


class RedeemLicenseCodeView(APIView):
    """Redeem a staff-issued LicenseCode (see admin_api.py's Generate Code
    action) into a real license on the caller's own account — the
    self-service half of the "upgrade the old license key" feature; staff
    generate the code, the customer redeems it themselves, no manual
    admin step in between."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        code = (request.data.get("code") or "").strip()
        if not code:
            raise ValidationError({"code": "A license code is required."})
        try:
            purchase = redeem_license_code(code, request.user)
        except LicenseCodeError as exc:
            raise ValidationError({"code": str(exc)}) from exc
        log_activity(request.user, ActivityVerb.REDEEMED_LICENSE_CODE, target_label=purchase.product.name)
        purchase = (
            ProductPurchase.objects.select_related("product", "product__product")
            .prefetch_related("machine_licenses")
            .get(pk=purchase.pk)
        )
        return Response(AccountLicenseSerializer(purchase).data, status=201)


class AccountDownloadFileSerializer(serializers.Serializer):
    id = serializers.CharField()
    revit_version = serializers.CharField()
    version_label = serializers.CharField()
    is_current = serializers.BooleanField()
    download_url = serializers.CharField()


class AccountDownloadSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    cover_image_url = serializers.SerializerMethodField()
    files = serializers.SerializerMethodField()

    class Meta:
        model = ProductPurchase
        fields = ["id", "product_name", "cover_image_url", "files"]

    def get_cover_image_url(self, obj):
        catalog_product = obj.product.product
        return catalog_product.cover_image_url if catalog_product else ""

    def get_files(self, obj):
        catalog_product = obj.product.product
        if not catalog_product:
            return []
        entries = [
            {
                "id": str(f.id),
                "revit_version": f.revit_version,
                "version_label": f.version_label,
                "is_current": f.is_current,
                # Routed through our own redirect endpoint rather than a raw
                # presigned URL: that's the only way an actual download (as
                # opposed to just seeing the link) ever reaches Django to be
                # logged — a link straight to R2 would never touch our backend
                # again once the page has loaded.
                "download_url": f"/api/account/downloads/{f.id}/get" if f.storage_key else "",
            }
            for f in catalog_product.files.all()
        ]
        # A Revit-plugin build has no static file at all — it's generated
        # live on click (see AccountPluginBuildDownloadView) — so it's listed
        # here as a virtual entry rather than needing a ProductFile row.
        from installer.models import PluginBuild

        for build in PluginBuild.objects.filter(product=catalog_product):
            if not build.is_ready_for_build:
                continue
            entries.append(
                {
                    "id": str(build.id),
                    "revit_version": build.revit_year,
                    "version_label": build.plugin_version,
                    "is_current": True,
                    "download_url": f"/api/account/downloads/plugin-builds/{build.id}/get",
                }
            )
        return entries


class AccountDownloadListView(generics.ListAPIView):
    """Only paid purchases grant downloads — this is the entitlement gate.

    One card per distinct product, never one per purchase: a customer
    holding several independent keys for the same product (see
    CheckoutView — one key per seat) still only has one set of files to
    download, since the .exe/ProductFile itself carries no per-purchase
    data. `distinct("product__product_id")` (Postgres DISTINCT ON) picks
    one representative purchase per product — which purchase doesn't
    matter, get_files() below only ever reads the shared catalog product
    off it, never anything purchase-specific."""

    permission_classes = [IsAuthenticated]
    serializer_class = AccountDownloadSerializer

    def get_queryset(self):
        return (
            ProductPurchase.objects.filter(
                user=self.request.user, payment_status=ProductPurchase.PaymentStatus.PAID
            )
            .select_related("product", "product__product")
            .prefetch_related("product__product__files")
            .order_by("product__product_id", "-paid_at")
            .distinct("product__product_id")
        )


class AccountDownloadFileView(APIView):
    """Re-checks entitlement, logs the download, then redirects to a freshly
    signed R2 URL. Only for manually-uploaded files (scripts, templates,
    libraries, services) — an auto-installer build is never turned into a
    ProductFile, it's listed as a virtual entry pointing at
    AccountPluginBuildDownloadView instead (see AccountDownloadSerializer)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, file_id):
        from django.core.files.storage import default_storage
        from django.db.models import F
        from django.http import HttpResponseRedirect

        from catalog.models import Product, ProductFile

        file = ProductFile.objects.select_related("product").filter(pk=file_id).first()
        if not file or not file.storage_key:
            raise ValidationError({"detail": "File not found."})

        purchase = ProductPurchase.objects.filter(
            user=request.user,
            product__product=file.product,
            payment_status=ProductPurchase.PaymentStatus.PAID,
        ).first()
        if not purchase:
            raise ValidationError({"detail": "You don't have access to this file."})

        log_activity(
            request.user,
            ActivityVerb.DOWNLOADED_FILE,
            target_label=f"{file.product.name} — {file.version_label}",
            metadata={"file_id": file.id, "revit_version": file.revit_version},
        )
        # The one real download counter in the app — every other product list/
        # detail view already displays this field, it just never had anything
        # incrementing it before this endpoint existed.
        Product.objects.filter(pk=file.product_id).update(download_count=F("download_count") + 1)

        return HttpResponseRedirect(default_storage.url(file.storage_key))


class AccountPluginBuildDownloadView(APIView):
    """Generates the .exe live, right now, for this one request — see
    installer.builder.generate_installer_bytes. Nothing is cached: every
    single download re-runs the NSIS build and the result is discarded once
    the response is sent. Streams the bare .exe — no license key attached,
    no auto-import. The plugin only ever gets a key by the customer typing
    one in themselves (copied from /account/licenses); the very first
    `/api/license/activate` call that carries a key is what actually binds
    it to that machine and starts showing its expiry there."""

    permission_classes = [IsAuthenticated]

    def get(self, request, build_id):
        from django.db.models import F
        from django.http import HttpResponse

        from catalog.models import Product
        from installer.builder import generate_installer_bytes
        from installer.models import PluginBuild

        build = PluginBuild.objects.select_related("product").filter(pk=build_id).first()
        if not build:
            raise ValidationError({"detail": "File not found."})

        purchase = ProductPurchase.objects.filter(
            user=request.user,
            product__product=build.product,
            payment_status=ProductPurchase.PaymentStatus.PAID,
        ).first()
        if not purchase:
            raise ValidationError({"detail": "You don't have access to this file."})

        success, log, installer_bytes, installer_name = generate_installer_bytes(build)
        if not success:
            raise ValidationError({"detail": "Could not generate the installer. Please contact support."})

        log_activity(
            request.user,
            ActivityVerb.DOWNLOADED_FILE,
            target_label=f"{build.product.name} — {build.plugin_version}",
            metadata={"revit_version": build.revit_year},
        )
        Product.objects.filter(pk=build.product_id).update(download_count=F("download_count") + 1)

        response = HttpResponse(installer_bytes, content_type="application/vnd.microsoft.portable-executable")
        response["Content-Disposition"] = f'attachment; filename="{installer_name}"'
        return response


class AccountPluginBuildTrialDownloadView(APIView):
    """Any logged-in customer can grab a trial build, as long as the product
    has a trial configured (Product.has_trial) — no checkout involved. Unlike
    the paid download this still streams a bare .exe with no key attached,
    but it DOES create (idempotently, once per user+product — re-downloading
    never resets the clock) a real, account-bound trial ProductPurchase with
    its own license_key and an expires_at set from the product's configured
    trial length. A key — the trial key shown on /account/licenses, or a real
    purchased one — is required to activate; there's no anonymous/keyless
    grant on the plugin side anymore (see license_activate_api)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, build_id):
        from datetime import timedelta
        from decimal import Decimal

        from django.db.models import F
        from django.http import HttpResponse
        from django.utils import timezone

        from catalog.models import Product
        from catalog.models.product import ProductStatus
        from installer.builder import generate_installer_bytes
        from installer.models import PluginBuild

        build = (
            PluginBuild.objects.select_related("product")
            .filter(pk=build_id, product__status=ProductStatus.PUBLISHED)
            .first()
        )
        if not build:
            raise ValidationError({"detail": "File not found."})
        if not build.product.has_trial:
            raise ValidationError({"detail": "This product doesn't offer a trial."})

        sku = LicensedProduct.objects.filter(product=build.product).first()
        if not sku:
            raise ValidationError({"detail": "This product isn't ready for trials yet — try again shortly."})

        # get_or_create + the DB-level partial unique constraint on
        # (user, product) WHERE is_trial=True (see ProductPurchase.Meta) is
        # what actually closes the race — a plain filter-then-create here let
        # two near-simultaneous requests (e.g. a double-click) both pass the
        # "no trial yet" check before either had committed, each minting its
        # own trial purchase/key for the same account.
        trial_purchase, created = ProductPurchase.objects.get_or_create(
            user=request.user,
            product=sku,
            is_trial=True,
            defaults={
                "payment_status": ProductPurchase.PaymentStatus.PAID,
                "amount": Decimal("0.00"),
                "currency": build.product.currency,
                "expires_at": timezone.now() + timedelta(minutes=build.product.trial_minutes_total),
            },
        )
        if created:
            log_activity(request.user, ActivityVerb.CLAIMED_FREE_PRODUCT, target_label=f"{build.product.name} — Trial")

        success, log, installer_bytes, installer_name = generate_installer_bytes(build)
        if not success:
            raise ValidationError({"detail": "Could not generate the trial installer. Please contact support."})

        log_activity(
            request.user,
            ActivityVerb.DOWNLOADED_FILE,
            target_label=f"{build.product.name} — Trial",
            metadata={"revit_version": build.revit_year, "trial": True},
        )
        Product.objects.filter(pk=build.product_id).update(download_count=F("download_count") + 1)

        response = HttpResponse(installer_bytes, content_type="application/vnd.microsoft.portable-executable")
        response["Content-Disposition"] = f'attachment; filename="{installer_name}"'
        return response


class ClaimFreeProductView(APIView):
    """
    The only way to acquire a product today without real checkout (which isn't
    built yet — see /checkout). Free products (price <= 0) can be claimed
    directly: this creates a real, PAID ProductPurchase at $0, so the exact same
    entitlement path (Licenses/Downloads, and eventually plugin activation) a
    paid checkout would produce is exercised end to end, not a special-cased
    shortcut.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from catalog.models import Product

        slug = request.data.get("slug")
        if not slug:
            raise ValidationError({"slug": "Required."})

        product = Product.objects.published().filter(slug=slug).first()
        if not product:
            raise ValidationError({"slug": "No published product with that slug."})
        if not product.is_free:
            raise ValidationError({"slug": "This product isn't free — checkout isn't available yet."})

        sku = LicensedProduct.objects.filter(product=product).first()
        if not sku:
            raise ValidationError({"slug": "This product isn't ready to claim yet — try again shortly."})

        purchase, created = ProductPurchase.objects.get_or_create(
            user=request.user,
            product=sku,
            defaults={
                "payment_status": ProductPurchase.PaymentStatus.PAID,
                "amount": product.price,
                "currency": product.currency,
            },
        )
        if created:
            log_activity(request.user, ActivityVerb.CLAIMED_FREE_PRODUCT, target_label=product.name)
        status_code = 201 if created else 200
        return Response(AccountOrderSerializer(purchase).data, status=status_code)


# Moved to licensing/services.py (subscription_duration/expires_at_for) so
# restore_purchase_access can compute the same expiry when staff manually
# marks a still-PENDING subscription order paid — kept as local aliases here
# so the rest of this module's call sites (_subscription_duration,
# _expires_at_for) didn't need to change.
_subscription_duration = subscription_duration


def _resolve_checkout_items(raw_items):
    """Shared by CheckoutView: validates + prices the cart the same way
    regardless of payment method, returns
    list[(catalog.Product, LicensedProduct, billing_period, unit_price, qty)].
    Raises ValidationError on anything not purchasable as given."""
    from catalog.models import Product

    if not isinstance(raw_items, list) or not raw_items:
        raise ValidationError({"items": "Your cart is empty."})

    valid_periods = {choice for choice, _ in ProductPurchase.BillingPeriod.choices}
    # Keyed by (slug, billingPeriod) rather than just slug — a customer can
    # hold a monthly cart line and a yearly cart line for the same product
    # at once (e.g. mid-decision), and those must never merge into one
    # purchase with an ambiguous price/duration.
    qty_by_key: dict[tuple[str, str], int] = {}
    for entry in raw_items:
        slug = (entry or {}).get("slug")
        if not slug:
            raise ValidationError({"items": "Each cart item needs a slug."})
        billing_period = (entry.get("billingPeriod") or "").strip()
        if billing_period not in valid_periods:
            raise ValidationError({"items": f"Invalid billing period for {slug!r}."})
        try:
            qty = int(entry.get("qty") or 1)
        except (TypeError, ValueError):
            raise ValidationError({"items": f"Invalid quantity for {slug!r}."})
        if qty < 1:
            raise ValidationError({"items": f"Invalid quantity for {slug!r}."})
        key = (slug, billing_period)
        qty_by_key[key] = qty_by_key.get(key, 0) + qty

    resolved = []
    for (slug, billing_period), qty in qty_by_key.items():
        product = Product.objects.published().filter(slug=slug).first()
        if not product:
            raise ValidationError({"items": f"'{slug}' isn't available to purchase right now."})
        sku = LicensedProduct.objects.filter(product=product).first()
        if not sku:
            raise ValidationError({"items": f"'{product.name}' isn't ready to purchase yet — try again shortly."})
        if billing_period and not product.is_subscription:
            raise ValidationError({"items": f"'{product.name}' isn't sold as a subscription."})
        if billing_period == ProductPurchase.BillingPeriod.MONTHLY:
            unit_price = product.monthly_price
        elif billing_period == ProductPurchase.BillingPeriod.YEARLY:
            unit_price = product.yearly_price
        else:
            unit_price = product.price
        if unit_price is None:
            raise ValidationError({"items": f"'{product.name}' doesn't have a price for that billing option."})
        resolved.append((product, sku, billing_period, unit_price, qty))
    return resolved


class CheckoutView(APIView):
    """
    Turns a cart (client-supplied, since the cart itself is localStorage-only —
    see web/lib/cart.tsx) into PENDING ProductPurchase rows, then creates a
    Paymob payment intention for the total and hands back the URL to
    redirect the customer's browser to. Nothing is marked PAID here —
    that only happens once PaymobWebhookView gets a genuine, HMAC-verified
    confirmation (see below); trusting a client-side redirect for that
    would let anyone grant themselves a license by hitting the URL by hand.

    One purchase per unit bought, never one purchase covering a quantity:
    buying qty=3 of the same product creates three independent
    ProductPurchase rows, each its own license_key and seats=1 — one key
    per seat, so each copy activates its own machine and none of them are
    tied together. `payment_reference` is shared across every purchase
    created by one checkout call — that's how the webhook finds them again.

    Each cart item optionally carries a `billingPeriod` ("monthly"/"yearly")
    for a subscription-priced product (Product.is_subscription) — the
    purchase's `amount` comes from that interval's price; `expires_at` is
    computed and set by the webhook once payment actually confirms, not
    here (so an interval as short as the current test override, see
    _subscription_duration, isn't already ticking down while the customer
    is still typing in their card).
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        import uuid

        from django.db import transaction

        resolved = _resolve_checkout_items(request.data.get("items"))
        order_reference = f"bimhive-{uuid.uuid4()}"

        purchases = []
        with transaction.atomic():
            # Superseded by this fresh attempt — a customer who abandons or
            # fails a checkout (e.g. their card gets declined) and then
            # retries left the previous attempt's PENDING purchases stranded
            # forever with no cleanup, silently piling up unusable license
            # keys on their account every retry. A late webhook for one of
            # these can still land after this — PaymobWebhookView matches by
            # payment_reference and only skips rows already PAID, so it'll
            # still correctly grant a license if Paymob reports the OLD
            # attempt actually succeeded.
            ProductPurchase.objects.filter(
                user=request.user, payment_status=ProductPurchase.PaymentStatus.PENDING
            ).update(payment_status=ProductPurchase.PaymentStatus.CANCELLED)

            for product, sku, billing_period, unit_price, qty in resolved:
                for _ in range(qty):
                    purchases.append(
                        ProductPurchase.objects.create(
                            user=request.user,
                            product=sku,
                            payment_status=ProductPurchase.PaymentStatus.PENDING,
                            seats=1,
                            amount=unit_price,
                            currency=product.currency,
                            billing_period=billing_period,
                            payment_reference=order_reference,
                        )
                    )

        total_cents = sum(int(p.amount * 100) for p in purchases)
        items = [
            {
                "name": p.product.name[:100],
                "amount": int(p.amount * 100),
                "description": p.product.name[:200],
                "quantity": 1,
            }
            for p in purchases
        ]
        billing_data = {
            "first_name": request.user.first_name or request.user.username,
            "last_name": request.user.last_name or "N/A",
            "email": request.user.email,
            "phone_number": "+20000000000",
            "apartment": "NA", "floor": "NA", "street": "NA",
            "building": "NA", "city": "NA", "state": "NA", "country": "NA",
        }
        try:
            intention = paymob.create_intention(
                amount_cents=total_cents,
                special_reference=order_reference,
                notification_url=f"{settings.SITE_URL}/api/webhooks/paymob",
                redirection_url=f"{settings.SITE_URL}/checkout/confirmation?reference={order_reference}",
                billing_data=billing_data,
                items=items,
            )
        except paymob.PaymobError as exc:
            raise ValidationError({"detail": f"Could not start payment: {exc}"}) from exc

        return Response(
            {
                "checkoutUrl": paymob.checkout_url(intention["client_secret"]),
                "reference": order_reference,
            },
            status=201,
        )


class CheckoutStatusView(APIView):
    """Polled by /checkout/confirmation after the customer's browser is
    redirected back from Paymob — never trusts that redirect itself (no
    signature on redirection_url's query params), only reports purchases
    once PaymobWebhookView has actually flipped them to PAID."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        reference = (request.query_params.get("reference") or "").strip()
        if not reference:
            raise ValidationError({"reference": "Required."})
        purchases = (
            ProductPurchase.objects.filter(user=request.user, payment_reference=reference)
            .select_related("product")
            .order_by("created_at")
        )
        if not purchases.exists():
            raise ValidationError({"detail": "No order found for that reference."})
        pending = any(p.payment_status == ProductPurchase.PaymentStatus.PENDING for p in purchases)
        return Response({"pending": pending, "purchases": AccountOrderSerializer(purchases, many=True).data})


class PaymobWebhookView(APIView):
    """Server-to-server confirmation from Paymob — POST /api/webhooks/paymob.
    No auth (Paymob doesn't have our session), CSRF-exempt (see urls.py),
    the HMAC signature is what actually proves this came from Paymob and
    wasn't spoofed. This is the ONLY place a checkout ever becomes PAID."""

    authentication_classes = []
    permission_classes = []

    def post(self, request):
        import logging

        logger = logging.getLogger(__name__)
        body = request.data or {}
        obj = body.get("obj") or {}
        received_hmac = request.query_params.get("hmac", "")

        if not paymob.verify_hmac(obj, received_hmac):
            logger.warning("Paymob webhook: HMAC verification failed, ignoring.")
            return Response({"detail": "Invalid signature."}, status=400)

        if not obj.get("success") or obj.get("pending"):
            # Failed or still-pending attempt — nothing to grant. Paymob
            # may call again later for the same order if the customer
            # retries, so this isn't necessarily final.
            return Response({"ok": True})

        # Best-effort: Paymob's docs confirm `special_reference` is meant
        # for exactly this correlation purpose, but the exact field path it
        # comes back on in the webhook body isn't nailed down without a
        # real test transaction to inspect — tries the documented field
        # plus the couple of plausible nested spots seen in other
        # integrations' payloads.
        order_obj = obj.get("order") or {}
        reference = obj.get("special_reference") or order_obj.get("merchant_order_id") or order_obj.get("special_reference")
        if not reference:
            logger.warning("Paymob webhook: no order reference found in payload: %s", body)
            return Response({"ok": True})

        purchases = list(ProductPurchase.objects.filter(payment_reference=reference))
        if not purchases:
            logger.warning("Paymob webhook: no PENDING purchases found for reference %s", reference)
            return Response({"ok": True})

        now = timezone.now()
        for purchase in purchases:
            if purchase.payment_status == ProductPurchase.PaymentStatus.PAID:
                continue  # already processed — webhooks can be delivered more than once
            purchase.payment_status = ProductPurchase.PaymentStatus.PAID
            purchase.expires_at = _expires_at_for(purchase.billing_period, now)
            purchase.save()

        user = purchases[0].user
        log_activity(
            user,
            ActivityVerb.ORDER_PLACED,
            target_label=", ".join(p.product.name for p in purchases),
            metadata={"item_count": len(purchases), "processor": "paymob", "reference": reference},
        )
        return Response({"ok": True})


_expires_at_for = expires_at_for
