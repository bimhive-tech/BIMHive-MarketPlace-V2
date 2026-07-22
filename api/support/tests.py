"""
Customer-facing support ticket API — create/list/view/reply, all scoped to
the caller's own tickets. Staff-side reply is via Django's own /admin/
(support/admin.py) — not covered here, no custom view to test yet.
"""
import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from support.models import SupportTicket, SupportTicketMessage

pytestmark = pytest.mark.django_db
User = get_user_model()


def _login(email="buyer@example.com"):
    user = User.objects.create_user(username=email, email=email, password="pw12345!")
    client = Client()
    client.force_login(user)
    return user, client


def _create_ticket(client, subject="Trial won't activate", body="I entered my key but nothing happens."):
    return client.post(
        "/api/account/support/tickets",
        data={"subject": subject, "body": body},
        content_type="application/json",
    )


def test_tickets_requires_auth():
    resp = Client().get("/api/account/support/tickets")
    assert resp.status_code in (401, 403)


def test_create_ticket_creates_the_ticket_and_first_message():
    user, client = _login()
    resp = _create_ticket(client)
    assert resp.status_code == 201, resp.json()
    body = resp.json()
    assert body["subject"] == "Trial won't activate"
    assert body["status"] == "open"
    assert len(body["messages"]) == 1
    assert body["messages"][0]["body"] == "I entered my key but nothing happens."
    assert body["messages"][0]["is_staff_reply"] is False

    ticket = SupportTicket.objects.get(user=user)
    assert ticket.messages.count() == 1


def test_create_ticket_requires_subject_and_body():
    _, client = _login()
    resp = client.post(
        "/api/account/support/tickets", data={"subject": "", "body": ""}, content_type="application/json",
    )
    assert resp.status_code == 400


def test_list_tickets_scoped_to_current_user():
    owner, owner_client = _login("owner@example.com")
    other, other_client = _login("other@example.com")
    _create_ticket(owner_client)
    _create_ticket(other_client, subject="A different issue")

    resp = owner_client.get("/api/account/support/tickets")
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["subject"] == "Trial won't activate"
    assert rows[0]["message_count"] == 1


def test_cannot_view_someone_elses_ticket():
    _, owner_client = _login("owner@example.com")
    _, other_client = _login("other@example.com")
    ticket_id = _create_ticket(owner_client).json()["id"]

    resp = other_client.get(f"/api/account/support/tickets/{ticket_id}")
    assert resp.status_code == 404


def test_reply_adds_a_message_and_stays_open():
    _, client = _login()
    ticket_id = _create_ticket(client).json()["id"]

    resp = client.post(
        f"/api/account/support/tickets/{ticket_id}/reply",
        data={"body": "Any update?"},
        content_type="application/json",
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["messages"]) == 2
    assert body["status"] == "open"


def test_reply_reopens_a_resolved_ticket():
    _, client = _login()
    ticket_id = _create_ticket(client).json()["id"]
    SupportTicket.objects.filter(pk=ticket_id).update(status=SupportTicket.Status.RESOLVED)

    resp = client.post(
        f"/api/account/support/tickets/{ticket_id}/reply",
        data={"body": "Actually still broken"},
        content_type="application/json",
    )
    assert resp.json()["status"] == "open"


def test_cannot_reply_to_someone_elses_ticket():
    _, owner_client = _login("owner@example.com")
    _, other_client = _login("other@example.com")
    ticket_id = _create_ticket(owner_client).json()["id"]

    resp = other_client.post(
        f"/api/account/support/tickets/{ticket_id}/reply",
        data={"body": "sneaky"},
        content_type="application/json",
    )
    assert resp.status_code == 404
    assert SupportTicketMessage.objects.filter(body="sneaky").count() == 0
