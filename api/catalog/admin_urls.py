"""Admin portal API routes (mounted under /api/admin/ in config/urls.py)."""
from django.urls import path

from catalog.admin_api import (
    AdminOptionsView,
    AdminProductListCreateView,
    AdminStatsView,
)

urlpatterns = [
    path("stats", AdminStatsView.as_view(), name="admin-stats"),
    path("products", AdminProductListCreateView.as_view(), name="admin-products"),
    path("options", AdminOptionsView.as_view(), name="admin-options"),
]
