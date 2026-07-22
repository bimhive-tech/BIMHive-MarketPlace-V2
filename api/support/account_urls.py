"""Customer support ticket routes (mounted under /api/account/ in config/urls.py)."""
from django.urls import path

from support.account_api import SupportTicketDetailView, SupportTicketListCreateView, SupportTicketReplyView

urlpatterns = [
    path("support/tickets", SupportTicketListCreateView.as_view(), name="account-support-tickets"),
    path("support/tickets/<uuid:pk>", SupportTicketDetailView.as_view(), name="account-support-ticket-detail"),
    path("support/tickets/<uuid:pk>/reply", SupportTicketReplyView.as_view(), name="account-support-ticket-reply"),
]
