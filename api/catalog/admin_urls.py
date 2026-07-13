"""Admin portal API routes (mounted under /api/admin/ in config/urls.py)."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from catalog.admin_api import (
    AdminCategoryViewSet,
    AdminCollectionViewSet,
    AdminOptionsView,
    AdminPartnerViewSet,
    AdminProductDetailView,
    AdminProductFileDetailView,
    AdminProductFileListCreateView,
    AdminProductListCreateView,
    AdminStatsView,
    AdminTagViewSet,
)
from catalog.admin_status_api import AdminSystemStatusView


# trailing_slash=False: the Next.js dev rewrite proxy strips trailing slashes
# before forwarding to Django, which would otherwise hit APPEND_SLASH's redirect
# on every router-based endpoint. Matching that here avoids depending on a
# framework-specific proxy quirk.
router = DefaultRouter(trailing_slash=False)
router.register("categories", AdminCategoryViewSet, basename="admin-category")
router.register("tags", AdminTagViewSet, basename="admin-tag")
router.register("partners", AdminPartnerViewSet, basename="admin-partner")
router.register("collections", AdminCollectionViewSet, basename="admin-collection")

urlpatterns = [
    path("stats", AdminStatsView.as_view(), name="admin-stats"),
    path("system-status", AdminSystemStatusView.as_view(), name="admin-system-status"),
    path("options", AdminOptionsView.as_view(), name="admin-options"),
    path("products", AdminProductListCreateView.as_view(), name="admin-products"),
    path("products/<int:pk>", AdminProductDetailView.as_view(), name="admin-product-detail"),
    path(
        "products/<int:product_id>/files",
        AdminProductFileListCreateView.as_view(),
        name="admin-product-files",
    ),
    path(
        "products/files/<int:pk>",
        AdminProductFileDetailView.as_view(),
        name="admin-product-file-detail",
    ),
    path("", include(router.urls)),
]
