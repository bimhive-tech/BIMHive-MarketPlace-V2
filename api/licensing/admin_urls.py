"""Admin API routes for Licenses + Orders (mounted under /api/admin/ in config/urls.py)."""
from django.urls import path

from licensing.admin_api import (
    AdminLicenseCodeListCreateView,
    AdminLicenseCodeRevokeView,
    AdminLicenseExtendView,
    AdminLicenseListView,
    AdminLicenseOptionsView,
    AdminLicenseReleaseView,
    AdminLicenseRestoreView,
    AdminLicenseRevokeView,
    AdminOrderListView,
    AdminOrderSeatsView,
    AdminOrderStatusView,
)

urlpatterns = [
    path("licenses", AdminLicenseListView.as_view(), name="admin-licenses"),
    path("licenses/options", AdminLicenseOptionsView.as_view(), name="admin-license-options"),
    path("licenses/<uuid:pk>/revoke", AdminLicenseRevokeView.as_view(), name="admin-license-revoke"),
    path("licenses/<uuid:pk>/restore", AdminLicenseRestoreView.as_view(), name="admin-license-restore"),
    path("licenses/<uuid:pk>/extend", AdminLicenseExtendView.as_view(), name="admin-license-extend"),
    path("licenses/<uuid:pk>/release", AdminLicenseReleaseView.as_view(), name="admin-license-release"),
    path("orders", AdminOrderListView.as_view(), name="admin-orders"),
    path("orders/<uuid:pk>/status", AdminOrderStatusView.as_view(), name="admin-order-status"),
    path("orders/<uuid:pk>/seats", AdminOrderSeatsView.as_view(), name="admin-order-seats"),
    path("license-codes", AdminLicenseCodeListCreateView.as_view(), name="admin-license-codes"),
    path("license-codes/<uuid:pk>/revoke", AdminLicenseCodeRevokeView.as_view(), name="admin-license-code-revoke"),
]
