"""
/api/auth/me's partner payload — the frontend's only signal for whether a
logged-in user has a seller application and what state it's in (see
catalog.permissions.IsPartnerUser/IsStaffOrPartner for how access is actually
enforced server-side).
"""
import pytest
from django.contrib.auth import get_user_model

from catalog.models import Partner

pytestmark = pytest.mark.django_db
User = get_user_model()


def test_me_has_no_partner_for_a_plain_customer(client):
    user = User.objects.create_user(username="c@x.com", email="c@x.com", password="x")
    client.force_login(user)
    resp = client.get("/api/auth/me")
    assert resp.status_code == 200
    assert resp.json()["partner"] is None


def test_me_includes_partner_summary_for_a_partner_linked_user(client):
    partner = Partner.objects.create(name="Arch Tools", status=Partner.ApplicationStatus.APPROVED)
    user = User.objects.create_user(username="p@x.com", email="p@x.com", password="x", partner=partner)
    client.force_login(user)
    resp = client.get("/api/auth/me")
    body = resp.json()
    assert body["partner"] == {
        "id": partner.id, "name": "Arch Tools", "slug": partner.slug,
        "status": "approved", "rejection_note": "",
    }


def test_me_reports_a_pending_application_status(client):
    partner = Partner.objects.create(name="Arch Tools")  # defaults to pending
    user = User.objects.create_user(username="p2@x.com", email="p2@x.com", password="x", partner=partner)
    client.force_login(user)
    resp = client.get("/api/auth/me")
    assert resp.json()["partner"]["status"] == "pending"
