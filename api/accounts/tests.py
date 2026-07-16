"""
/api/auth/me's partner payload — the frontend's only signal for whether a
logged-in user has partner-portal access (see catalog.permissions.IsPartnerUser
for how that access is actually enforced server-side).
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
    partner = Partner.objects.create(name="Arch Tools")
    user = User.objects.create_user(username="p@x.com", email="p@x.com", password="x", partner=partner)
    client.force_login(user)
    resp = client.get("/api/auth/me")
    body = resp.json()
    assert body["partner"] == {"id": partner.id, "name": "Arch Tools", "slug": partner.slug}


def test_me_reports_must_change_password(client):
    partner = Partner.objects.create(name="Arch Tools")
    user = User.objects.create_user(
        username="p2@x.com", email="p2@x.com", password="x", partner=partner, must_change_password=True
    )
    client.force_login(user)
    resp = client.get("/api/auth/me")
    assert resp.json()["must_change_password"] is True


def test_changing_password_clears_must_change_password(client):
    partner = Partner.objects.create(name="Arch Tools")
    user = User.objects.create_user(
        username="p3@x.com", email="p3@x.com", password="temp-pw", partner=partner, must_change_password=True
    )
    client.force_login(user)
    resp = client.post(
        "/api/auth/change-password",
        {"current_password": "temp-pw", "new_password": "MyOwnPassword!123"},
        content_type="application/json",
    )
    assert resp.status_code == 200, resp.json()
    user.refresh_from_db()
    assert user.must_change_password is False
    assert user.check_password("MyOwnPassword!123")
