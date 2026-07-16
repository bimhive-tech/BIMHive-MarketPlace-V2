"""Partner self-service API routes (mounted under /api/partner/ in config/urls.py)."""
from django.urls import path

from catalog.partner_api import PartnerProfileView

urlpatterns = [
    path("profile", PartnerProfileView.as_view(), name="partner-profile"),
]
