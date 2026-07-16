"""Partner self-service API routes (mounted under /api/partner/ in config/urls.py)."""
from django.urls import path

from catalog.partner_api import BecomeSellerView, PartnerProfileView, PartnerSalesView

urlpatterns = [
    path("apply", BecomeSellerView.as_view(), name="partner-apply"),
    path("profile", PartnerProfileView.as_view(), name="partner-profile"),
    path("sales", PartnerSalesView.as_view(), name="partner-sales"),
]
