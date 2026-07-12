"""
Admin for the licensing SKUs and records. Gives the Licenses section the ability to
look up / extend / revoke / re-issue licenses and see fingerprint + trial state —
something v1 could only do by hand-editing the DB (REBUILD_PROMPT admin requirement).
"""
from django.contrib import admin

from licensing.models import LicensedProduct, LicenseEvent, MachineLicense, ProductPurchase


@admin.register(LicensedProduct)
class LicensedProductAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "revit_year", "default_trial_days", "is_active", "product")
    list_filter = ("is_active", "revit_year")
    search_fields = ("code", "name")


@admin.register(ProductPurchase)
class ProductPurchaseAdmin(admin.ModelAdmin):
    list_display = ("license_key", "user", "product", "payment_status", "amount", "paid_at")
    list_filter = ("payment_status",)
    search_fields = ("license_key", "user__email", "product__code")
    readonly_fields = ("created_at", "updated_at", "requested_at")


@admin.register(MachineLicense)
class MachineLicenseAdmin(admin.ModelAdmin):
    list_display = ("product", "status", "started_at", "expires_at", "install_count", "last_seen_at")
    list_filter = ("status", "product")
    search_fields = ("machine_fingerprint_hash", "product__code")


@admin.register(LicenseEvent)
class LicenseEventAdmin(admin.ModelAdmin):
    list_display = ("product", "event_type", "event_time")
    list_filter = ("event_type",)
    search_fields = ("product__code", "machine_fingerprint_hash")
