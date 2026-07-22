"""
GET /api/account/activity — the "Notifications" tab's real activity feed,
scoped to the caller's own ActivityLog rows only.
"""
import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from activity.models import ActivityLog, ActivityVerb

pytestmark = pytest.mark.django_db
User = get_user_model()


def _login(email="buyer@example.com"):
    user = User.objects.create_user(username=email, email=email, password="pw12345!")
    client = Client()
    client.force_login(user)
    return user, client


def test_activity_requires_auth():
    resp = Client().get("/api/account/activity")
    assert resp.status_code in (401, 403)


def test_activity_scoped_to_current_user():
    owner, owner_client = _login("owner@example.com")
    other, _ = _login("other@example.com")
    ActivityLog.objects.create(actor=owner, actor_label=owner.email, verb=ActivityVerb.SIGNED_IN)
    ActivityLog.objects.create(actor=other, actor_label=other.email, verb=ActivityVerb.SIGNED_IN)

    resp = owner_client.get("/api/account/activity")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_activity_excludes_staff_admin_verbs_even_for_the_actor():
    # A staff member who's also shopping as a customer shouldn't see their
    # own product-management actions mixed into "your account activity."
    user, client = _login("staffshopper@example.com")
    ActivityLog.objects.create(actor=user, actor_label=user.email, verb=ActivityVerb.SIGNED_IN)
    ActivityLog.objects.create(actor=user, actor_label=user.email, verb=ActivityVerb.PRODUCT_CREATED, target_label="Some Tool")

    resp = client.get("/api/account/activity")
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["verb"] == "signed_in"


def test_activity_orders_most_recent_first():
    user, client = _login()
    first = ActivityLog.objects.create(actor=user, actor_label=user.email, verb=ActivityVerb.SIGNED_UP)
    second = ActivityLog.objects.create(actor=user, actor_label=user.email, verb=ActivityVerb.SIGNED_IN)

    rows = client.get("/api/account/activity").json()
    assert [r["id"] for r in rows] == [second.id, first.id]
