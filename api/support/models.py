"""
Customer support tickets — a real thread per ticket (SupportTicketMessage),
not a single-body model, so the first message a customer types and every
reply (theirs or staff's) live in one uniform list. See support/account_api.py
for the customer-facing create/list/reply API and support/admin.py for how
staff see and respond to them (Django's own /admin/ for now — no dedicated
Admin Portal page yet).
"""
import uuid

from django.conf import settings
from django.db import models


class SupportTicket(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        AWAITING_CUSTOMER = "awaiting_customer", "Awaiting Customer"
        RESOLVED = "resolved", "Resolved"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="support_tickets")
    subject = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.subject} [{self.status}]"


class SupportTicketMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name="messages")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="support_ticket_messages"
    )
    # Snapshot, same reasoning as ActivityLog.actor_label — stays readable
    # even if the staff account that wrote it is later deleted.
    author_label = models.CharField(max_length=180, blank=True)
    is_staff_reply = models.BooleanField(default=False)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.ticket.subject}: {self.body[:40]}"
