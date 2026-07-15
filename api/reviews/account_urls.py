"""Customer account API routes for reviews (mounted under /api/account/ in config/urls.py)."""
from django.urls import path

from reviews.account_api import AccountReviewDetailView, AccountReviewListView

urlpatterns = [
    path("reviews", AccountReviewListView.as_view(), name="account-reviews"),
    path("reviews/<int:pk>", AccountReviewDetailView.as_view(), name="account-review-detail"),
]
