"""Customer account API routes (mounted under /api/account/ in config/urls.py)."""
from django.urls import path

from licensing.account_api import (
    AccountDownloadListView,
    AccountLicenseListView,
    AccountOrderListView,
    ClaimFreeProductView,
)

urlpatterns = [
    path("orders", AccountOrderListView.as_view(), name="account-orders"),
    path("licenses", AccountLicenseListView.as_view(), name="account-licenses"),
    path("downloads", AccountDownloadListView.as_view(), name="account-downloads"),
    path("claim-free", ClaimFreeProductView.as_view(), name="account-claim-free"),
]
