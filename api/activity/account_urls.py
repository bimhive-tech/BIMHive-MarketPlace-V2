"""Customer-facing activity routes (mounted under /api/account/ in config/urls.py)."""
from django.urls import path

from activity.account_api import AccountActivityListView

urlpatterns = [
    path("activity", AccountActivityListView.as_view(), name="account-activity"),
]
