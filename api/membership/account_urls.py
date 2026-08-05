"""Customer membership routes (mounted under /api/account/)."""
from django.urls import path

from membership.api import AccountMembershipCancelView, AccountMembershipView, MembershipCheckoutView

urlpatterns = [
    path("membership", AccountMembershipView.as_view(), name="account-membership"),
    path("membership/checkout", MembershipCheckoutView.as_view(), name="account-membership-checkout"),
    path("membership/cancel", AccountMembershipCancelView.as_view(), name="account-membership-cancel"),
]
