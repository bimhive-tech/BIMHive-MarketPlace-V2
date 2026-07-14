"""Admin API routes for the activity log (mounted under /api/admin/ in config/urls.py)."""
from django.urls import path

from activity.admin_api import AdminActivityLogListView

urlpatterns = [
    path("activity", AdminActivityLogListView.as_view(), name="admin-activity"),
]
