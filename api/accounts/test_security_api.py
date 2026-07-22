"""
/api/auth/sessions — the "active sessions" list on /account/security. Real
Django sessions, not a fake table: a session's device/IP gets stashed into
its own session data at login time (accounts/api.py::_remember_session_device)
since Django's Session model has no columns for either. Uses real POSTs to
/api/auth/login (not client.force_login) so that capture path actually runs.
"""
import pytest
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.test import Client

pytestmark = pytest.mark.django_db
User = get_user_model()


@pytest.fixture(autouse=True)
def _reset_auth_throttle():
    # /api/auth/register and /api/auth/login share a "10/min" ScopedRateThrottle
    # (see DEFAULT_THROTTLE_RATES in settings.py) backed by the process-wide
    # cache — this file's tests make several real POSTs to those endpoints per
    # test, which without this would accumulate across tests and eventually
    # 429 a later, unrelated test (same pattern as licensing/tests.py::_pepper).
    from django.core.cache import cache

    cache.clear()


def _register_and_login(email="buyer@example.com", password="pw12345!strong", user_agent="Mozilla/5.0 Test Browser"):
    client = Client()
    client.post(
        "/api/auth/register",
        data={"email": email, "password": password, "full_name": "Buyer"},
        content_type="application/json",
        HTTP_USER_AGENT=user_agent,
    )
    return client


def test_sessions_requires_auth():
    resp = Client().get("/api/auth/sessions")
    assert resp.status_code in (401, 403)


def test_login_creates_a_session_with_device_info():
    client = _register_and_login()
    resp = client.get("/api/auth/sessions")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["is_current"] is True
    assert rows[0]["user_agent"]  # captured at login, not blank


def test_sessions_only_shows_the_callers_own():
    mine = _register_and_login("mine@example.com")
    _register_and_login("other@example.com")

    rows = mine.get("/api/auth/sessions").json()
    assert len(rows) == 1


def test_revoke_signs_out_a_different_session_for_the_same_user():
    # Two logins for the same account = two real Session rows, same
    # _auth_user_id — simulates "logged in on my laptop and my phone."
    client_a = _register_and_login("multi@example.com")
    client_b = Client()
    client_b.post(
        "/api/auth/login",
        data={"email": "multi@example.com", "password": "pw12345!strong"},
        content_type="application/json",
    )

    rows = client_a.get("/api/auth/sessions").json()
    assert len(rows) == 2
    other_session_id = next(r["id"] for r in rows if not r["is_current"])

    resp = client_a.post(f"/api/auth/sessions/{other_session_id}/revoke")
    assert resp.status_code == 200
    assert not Session.objects.filter(pk=other_session_id).exists()

    rows_after = client_a.get("/api/auth/sessions").json()
    assert len(rows_after) == 1


def test_cannot_revoke_your_own_current_session():
    client = _register_and_login()
    current_id = client.get("/api/auth/sessions").json()[0]["id"]
    resp = client.post(f"/api/auth/sessions/{current_id}/revoke")
    assert resp.status_code == 403
    assert Session.objects.filter(pk=current_id).exists()


def test_cannot_revoke_someone_elses_session():
    victim = _register_and_login("victim@example.com")
    attacker = _register_and_login("attacker@example.com")
    victim_session_id = victim.get("/api/auth/sessions").json()[0]["id"]

    resp = attacker.post(f"/api/auth/sessions/{victim_session_id}/revoke")
    assert resp.status_code == 403
    assert Session.objects.filter(pk=victim_session_id).exists()


def test_revoking_an_unknown_session_key_404s():
    client = _register_and_login()
    resp = client.post("/api/auth/sessions/does-not-exist/revoke")
    assert resp.status_code == 404
