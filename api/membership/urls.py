"""Public membership routes (mounted under /api/membership/)."""
from django.urls import path

from membership.api import MembershipPlanListView

urlpatterns = [
    path("plans", MembershipPlanListView.as_view(), name="membership-plans"),
]
