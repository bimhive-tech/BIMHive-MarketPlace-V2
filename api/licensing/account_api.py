"""
Customer-facing account API — "my orders / my licenses / my downloads"
(mounted under /api/account/). Everything here is scoped to request.user; this is
the read side of the same ProductPurchase/MachineLicense data the admin API manages.
"""
from rest_framework import generics, serializers
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from activity.models import ActivityVerb
from activity.services import log_activity
from licensing.models import LicensedProduct, MachineLicense, ProductPurchase
from licensing.services import LicenseCodeError, redeem_license_code


class AccountOrderSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_code = serializers.CharField(source="product.code", read_only=True)

    class Meta:
        model = ProductPurchase
        fields = [
            "id", "product_name", "product_code", "amount", "currency", "payment_status",
            "license_key", "requested_at", "paid_at",
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


class AccountMachineSerializer(serializers.ModelSerializer):
    fingerprint_preview = serializers.SerializerMethodField()

    class Meta:
        model = MachineLicense
        fields = ["id", "fingerprint_preview", "status", "last_seen_at", "install_count", "plugin_version"]

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
            "seats", "expires_at", "requested_at", "paid_at", "machines",
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
    """Only paid purchases grant downloads — this is the entitlement gate."""

    permission_classes = [IsAuthenticated]
    serializer_class = AccountDownloadSerializer

    def get_queryset(self):
        return (
            ProductPurchase.objects.filter(
                user=self.request.user, payment_status=ProductPurchase.PaymentStatus.PAID
            )
            .select_related("product", "product__product")
            .prefetch_related("product__product__files")
            .order_by("-paid_at")
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
    the response is sent, then zips it with the purchaser's own license key
    (already issued at purchase time) so the plugin's first run can
    auto-import it instead of the customer copy-pasting a key by hand."""

    permission_classes = [IsAuthenticated]

    def get(self, request, build_id):
        from django.db.models import F

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

        return _zip_installer_bytes_with_license_key(installer_name, installer_bytes, build.product, purchase)


class AccountPluginBuildTrialDownloadView(APIView):
    """No purchase required — any logged-in customer can grab a trial build,
    as long as the product has a trial configured (Product.has_trial). Unlike
    the paid download, this streams the raw .exe with no license-key zip —
    there's no key yet. The plugin's own first `/api/license/activate` call
    (sent with no licenseKey) falls into the server's trial-issuing branch
    on its own; nothing about that flow needs to know this came from a
    trial download specifically."""

    permission_classes = [IsAuthenticated]

    def get(self, request, build_id):
        from django.db.models import F
        from django.http import HttpResponse

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


def _zip_installer_bytes_with_license_key(installer_name, installer_bytes, product, purchase):
    import io
    import zipfile

    from django.http import HttpResponse

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(installer_name, installer_bytes)
        # LicLoader (the installed plugin's activation shim) checks for a
        # same-name .key file next to itself in %AppData%\BIMHive\Licenses\
        # on first run before falling back to a manual prompt — see
        # installer-generator-reference project notes.
        archive.writestr(f"{product.product_code}.key", purchase.license_key)
        archive.writestr(
            "README.txt",
            f"1. Run {installer_name} to install {product.name}.\n"
            f"2. Keep {product.product_code}.key in this folder until the first Revit launch "
            "after installing — the plugin reads it automatically to activate your license.\n",
        )
    zip_buffer.seek(0)
    response = HttpResponse(zip_buffer.getvalue(), content_type="application/zip")
    response["Content-Disposition"] = f'attachment; filename="{installer_name.rsplit(".", 1)[0]}.zip"'
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
