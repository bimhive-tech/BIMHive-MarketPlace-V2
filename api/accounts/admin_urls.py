"""Admin API routes for Users, Roles, Customers (mounted under /api/admin/)."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from accounts.admin_api import (
    AdminCustomerStatsView,
    AdminRoleViewSet,
    AdminUserListView,
    AdminUserUpdateView,
)

router = DefaultRouter(trailing_slash=False)  # see catalog/admin_urls.py for why
router.register("roles", AdminRoleViewSet, basename="admin-role")

urlpatterns = [
    path("users", AdminUserListView.as_view(), name="admin-users"),
    path("users/<int:pk>", AdminUserUpdateView.as_view(), name="admin-user-update"),
    path("customers", AdminUserListView.as_view(), name="admin-customers"),
    path("customers/stats", AdminCustomerStatsView.as_view(), name="admin-customer-stats"),
    path("", include(router.urls)),
]
