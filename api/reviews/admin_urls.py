"""Admin API routes for review moderation (mounted under /api/admin/)."""
from django.urls import path

from reviews.admin_api import AdminReviewDeleteView, AdminReviewListView

urlpatterns = [
    path("reviews", AdminReviewListView.as_view(), name="admin-reviews"),
    path("reviews/<int:pk>", AdminReviewDeleteView.as_view(), name="admin-review-delete"),
]
