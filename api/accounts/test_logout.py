"""Signing out has to work even when there's nothing to sign out of.

The Log Out button was permanently dead for anyone whose session had already
died server-side — expired, revoked from another device, or cleared by a deploy.
The browser still held a sessionid cookie, so the UI showed them as signed in,
but the endpoint was gated on IsAuthenticated and answered the click with a 403.
"""
import pytest
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session

pytestmark = pytest.mark.django_db
User = get_user_model()


@pytest.fixture
def user():
    return User.objects.create_user(username="u@x.com", email="u@x.com", password="x")


def test_logout_ends_a_real_session(client, user):
    client.force_login(user)

    resp = client.post("/api/auth/logout")

    assert resp.status_code == 200
    assert client.get("/api/auth/me").status_code in (401, 403)


def test_logout_succeeds_when_the_session_is_already_gone(client, user):
    """The regression: the cookie outlives the session, so the click has to be
    answered, not refused."""
    client.force_login(user)
    Session.objects.all().delete()

    resp = client.post("/api/auth/logout")

    assert resp.status_code == 200


def test_logout_succeeds_for_a_caller_who_was_never_signed_in(client):
    resp = client.post("/api/auth/logout")

    assert resp.status_code == 200


def test_logout_clears_the_session_cookie(client, user):
    """What actually stops the browser re-sending a dead sessionid on the next
    request — the 403 used to leave it in place."""
    client.force_login(user)

    resp = client.post("/api/auth/logout")

    assert resp.cookies["sessionid"].value == ""


def test_logout_does_not_end_someone_elses_session(client, user):
    """AllowAny widens who may call it, so prove it still only ever affects the
    caller's own session."""
    other = User.objects.create_user(username="o@x.com", email="o@x.com", password="x")
    other_client = client.__class__()
    other_client.force_login(other)
    client.force_login(user)

    client.post("/api/auth/logout")

    assert other_client.get("/api/auth/me").status_code == 200
