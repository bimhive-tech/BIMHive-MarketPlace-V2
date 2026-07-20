"""Customer account API routes (mounted under /api/account/ in config/urls.py)."""
from django.urls import path

from licensing.account_api import (
    AccountDownloadFileView,
    AccountDownloadListView,
    AccountLicenseListView,
    AccountOrderListView,
    AccountPluginBuildDownloadView,
    AccountPluginBuildTrialDownloadView,
    ClaimFreeProductView,
    RedeemLicenseCodeView,
)

urlpatterns = [
    path("orders", AccountOrderListView.as_view(), name="account-orders"),
    path("licenses", AccountLicenseListView.as_view(), name="account-licenses"),
    path("licenses/redeem", RedeemLicenseCodeView.as_view(), name="account-license-redeem"),
    path("downloads", AccountDownloadListView.as_view(), name="account-downloads"),
    path("downloads/<int:file_id>/get", AccountDownloadFileView.as_view(), name="account-download-file"),
    path(
        "downloads/plugin-builds/<uuid:build_id>/get",
        AccountPluginBuildDownloadView.as_view(),
        name="account-download-plugin-build",
    ),
    path(
        "downloads/plugin-builds/<uuid:build_id>/trial",
        AccountPluginBuildTrialDownloadView.as_view(),
        name="account-download-plugin-build-trial",
    ),
    path("claim-free", ClaimFreeProductView.as_view(), name="account-claim-free"),
]
