"""Staff membership routes (mounted under /api/admin/)."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from membership.admin_api import (
    AdminMembershipPlanViewSet,
    AdminMembershipReinstateView,
    AdminMembershipRevokeView,
    AdminMembershipViewSet,
)

# trailing_slash=False for the same reason as catalog/admin_urls.py — the Next
# dev proxy strips trailing slashes before forwarding.
router = DefaultRouter(trailing_slash=False)
router.register("membership-plans", AdminMembershipPlanViewSet, basename="admin-membership-plan")
router.register("memberships", AdminMembershipViewSet, basename="admin-membership")

urlpatterns = [
    path("memberships/<uuid:pk>/revoke", AdminMembershipRevokeView.as_view(), name="admin-membership-revoke"),
    path(
        "memberships/<uuid:pk>/reinstate",
        AdminMembershipReinstateView.as_view(),
        name="admin-membership-reinstate",
    ),
    path("", include(router.urls)),
]
