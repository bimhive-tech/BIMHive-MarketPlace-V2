"""
Root URL configuration.

License endpoints keep their exact v1 paths (no trailing slash) — installed plugins
depend on them byte-for-byte. See licensing/api_views.py and ARCHITECTURE §5.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from licensing.api_views import license_activate_api, license_products_api

urlpatterns = [
    path("admin/", admin.site.urls),
    # ── License activation contract (byte-compatible; DO NOT add trailing slash) ──
    path("api/license/products", license_products_api, name="license-products-api"),
    path("api/license/activate", license_activate_api, name="license-activate-api"),
    # ── Auth API (session-based) ──
    path("api/auth/", include("accounts.urls")),
    # ── Customer account API (my orders / licenses / downloads / reviews) ──
    path("api/account/", include("licensing.account_urls")),
    path("api/account/", include("reviews.account_urls")),
    # ── Admin portal API (staff-only) ──
    path("api/admin/", include("catalog.admin_urls")),
    path("api/admin/", include("licensing.admin_urls")),
    path("api/admin/", include("accounts.admin_urls")),
    path("api/admin/", include("reviews.admin_urls")),
    path("api/admin/", include("activity.admin_urls")),
    # ── Partner self-service API (partner-linked users only; product CRUD
    # itself is shared with staff via catalog.admin_urls, see IsStaffOrPartner) ──
    path("api/partner/", include("catalog.partner_urls")),
    # ── Storefront/catalog API ──
    path("api/", include("catalog.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
