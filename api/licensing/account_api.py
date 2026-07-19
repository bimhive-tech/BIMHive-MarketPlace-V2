"""
Customer-facing account API — "my orders / my licenses / my downloads"
(mounted under /api/account/). Everything here is scoped to request.user; this is
the read side of the same ProductPurchase/MachineLicense data the admin API manages.
"""
from datetime import timedelta

from django.utils import timezone
from rest_framework import generics, serializers
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from activity.models import ActivityVerb
from activity.services import log_activity
from licensing.models import LicenseEvent, LicensedProduct, MachineLicense, ProductPurchase
from licensing.services import release_machine_binding

# A customer can move their license to a new machine at most this often,
# self-service — more frequent than this needs a support ticket. Chosen to
# comfortably cover "I got a new PC" without enabling casual license sharing
# via repeated reactivation.
REACTIVATION_COOLDOWN_DAYS = 90


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
            "id", "product_name", "product_code", "payment_status", "license_key",
            "requested_at", "paid_at", "machines",
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


class ReactivateLicenseView(APIView):
    """Self-service "this isn't my computer anymore" — releases a paid
    purchase's current machine binding so the next activation (from a new
    PC) binds fresh instead of being denied forever. Rate-limited via the
    LicenseEvent audit trail rather than a separate counter field, mirroring
    how the rest of this app treats LicenseEvent as the source of truth for
    "did X happen recently"."""

    permission_classes = [IsAuthenticated]

    def post(self, request, machine_license_id):
        machine_license = (
            MachineLicense.objects.select_related("purchase", "product")
            .filter(pk=machine_license_id, purchase__user=request.user)
            .first()
        )
        if not machine_license:
            raise ValidationError({"detail": "License not found."})
        if not machine_license.purchase_id or not machine_license.purchase.is_license_active:
            raise ValidationError({"detail": "This license isn't currently active."})
        if machine_license.status == "released":
            raise ValidationError(
                {"detail": "This device is already released — install on your new machine to finish."}
            )

        cooldown_start = timezone.now() - timedelta(days=REACTIVATION_COOLDOWN_DAYS)
        recent_reactivation = LicenseEvent.objects.filter(
            product=machine_license.product,
            event_type="machine_released",
            payload__purchaseId=str(machine_license.purchase_id),
            event_time__gte=cooldown_start,
        ).exists()
        if recent_reactivation:
            raise ValidationError(
                {
                    "detail": (
                        f"You can only reactivate a license once every {REACTIVATION_COOLDOWN_DAYS} days. "
                        "Contact support if you need this sooner."
                    )
                }
            )

        release_machine_binding(machine_license)
        purchase = ProductPurchase.objects.select_related("product", "product__product").prefetch_related(
            "machine_licenses"
        ).get(pk=machine_license.purchase_id)
        return Response(AccountLicenseSerializer(purchase).data)


class AccountDownloadFileSerializer(serializers.Serializer):
    id = serializers.IntegerField()
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
        return [
            {
                "id": f.id,
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
    """Re-checks entitlement, logs the download, then either redirects to a
    freshly signed R2 URL (a manually-uploaded file — unchanged legacy
    behavior) or, for a file the auto-installer pipeline built (see
    installer.builder), streams back a ZIP containing the installer plus a
    `<productCode>.key` file holding the purchaser's own license key — so
    the plugin's first run can auto-import it instead of the customer
    copy-pasting a key by hand."""

    permission_classes = [IsAuthenticated]

    def get(self, request, file_id):
        from django.core.files.storage import default_storage
        from django.db.models import F
        from django.http import HttpResponse, HttpResponseRedirect

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

        auto_build = _matching_plugin_build(file)
        if auto_build:
            return _zip_installer_with_license_key(file, auto_build, purchase)
        return HttpResponseRedirect(default_storage.url(file.storage_key))


def _matching_plugin_build(file):
    from installer.models import PluginBuild

    return PluginBuild.objects.filter(
        product=file.product,
        revit_year=file.revit_version,
        status=PluginBuild.Status.READY,
        built_msi_storage_key=file.storage_key,
    ).first()


def _zip_installer_with_license_key(file, auto_build, purchase):
    import io
    import zipfile

    from django.core.files.storage import default_storage
    from django.http import HttpResponse

    zip_buffer = io.BytesIO()
    msi_name = auto_build.built_msi_storage_key.rsplit("/", 1)[-1]
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        with default_storage.open(auto_build.built_msi_storage_key, "rb") as msi_file:
            archive.writestr(msi_name, msi_file.read())
        # LicLoader (the installed plugin's activation shim) checks for a
        # same-name .key file next to itself in %AppData%\BIMHive\Licenses\
        # on first run before falling back to a manual prompt — see
        # installer-generator-reference project notes.
        archive.writestr(f"{file.product.product_code}.key", purchase.license_key)
        archive.writestr(
            "README.txt",
            f"1. Run {msi_name} to install {file.product.name}.\n"
            f"2. Keep {file.product.product_code}.key in this folder until the first Revit launch "
            "after installing — the plugin reads it automatically to activate your license.\n",
        )
    zip_buffer.seek(0)
    response = HttpResponse(zip_buffer.getvalue(), content_type="application/zip")
    response["Content-Disposition"] = f'attachment; filename="{file.product.slug}-{file.revit_version}.zip"'
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
