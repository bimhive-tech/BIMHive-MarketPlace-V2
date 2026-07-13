"""Admin API routes for Licenses + Orders (mounted under /api/admin/ in config/urls.py)."""
from django.urls import path

from licensing.admin_api import (
    AdminLicenseExtendView,
    AdminLicenseListView,
    AdminLicenseOptionsView,
    AdminLicenseRestoreView,
    AdminLicenseRevokeView,
    AdminOrderListView,
    AdminOrderStatusView,
)

urlpatterns = [
    path("licenses", AdminLicenseListView.as_view(), name="admin-licenses"),
    path("licenses/options", AdminLicenseOptionsView.as_view(), name="admin-license-options"),
    path("licenses/<uuid:pk>/revoke", AdminLicenseRevokeView.as_view(), name="admin-license-revoke"),
    path("licenses/<uuid:pk>/restore", AdminLicenseRestoreView.as_view(), name="admin-license-restore"),
    path("licenses/<uuid:pk>/extend", AdminLicenseExtendView.as_view(), name="admin-license-extend"),
    path("orders", AdminOrderListView.as_view(), name="admin-orders"),
    path("orders/<uuid:pk>/status", AdminOrderStatusView.as_view(), name="admin-order-status"),
]
