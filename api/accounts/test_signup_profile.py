"""
Signup profession/country capture (accounts.models.Profession, Profile.country)
— the backend-driven /api/auth/signup-options list, registration requiring a
real country, and the profile page being able to edit both afterward.
"""
import pytest
from django.contrib.auth import get_user_model

from accounts.models import Profession, Profile

pytestmark = pytest.mark.django_db
User = get_user_model()


def test_signup_options_lists_professions_and_countries(client):
    body = client.get("/api/auth/signup-options").json()

    values = [p["value"] for p in body["professions"]]
    assert "architect" in values
    assert "bim_manager" in values

    codes = {c["code"] for c in body["countries"]}
    assert "US" in codes
    assert "EG" in codes


def test_registering_requires_a_country(client):
    resp = client.post(
        "/api/auth/register",
        {"email": "new@x.com", "password": "correcthorsebattery9", "full_name": "New User"},
        content_type="application/json",
    )

    assert resp.status_code == 400
    assert "country" in resp.json()


def test_registering_rejects_a_bogus_country_code(client):
    resp = client.post(
        "/api/auth/register",
        {
            "email": "new@x.com", "password": "correcthorsebattery9", "full_name": "New User",
            "country": "ZZ",
        },
        content_type="application/json",
    )

    assert resp.status_code == 400
    assert "country" in resp.json()


def test_registering_saves_profession_and_country(client):
    resp = client.post(
        "/api/auth/register",
        {
            "email": "new@x.com", "password": "correcthorsebattery9", "full_name": "New User",
            "profession": Profession.BIM_MANAGER, "country": "eg",
        },
        content_type="application/json",
    )

    assert resp.status_code == 201, resp.json()
    profile = Profile.objects.get(user__email="new@x.com")
    assert profile.profession == Profession.BIM_MANAGER
    assert str(profile.country) == "EG", "lowercase input is normalized to the ISO code"


def test_profession_is_optional_at_signup(client):
    resp = client.post(
        "/api/auth/register",
        {"email": "new@x.com", "password": "correcthorsebattery9", "full_name": "New User", "country": "US"},
        content_type="application/json",
    )

    assert resp.status_code == 201, resp.json()


def test_login_works_for_an_account_with_no_country_set(client):
    """Regression: a Profile with a blank CountryField used to 500 on login —
    DRF auto-builds a ChoiceField for a model field with `choices` (which
    CountryField carries), and ChoiceField.to_representation's blank-value
    special case returns the raw Country object instead of a string, which
    then fails json.dumps(). Covers every account that existed before
    profession/country were added, not just freshly registered ones."""
    user = User.objects.create_user(username="old@x.com", email="old@x.com", password="pw12345!")
    Profile.objects.create(user=user)  # profession/country left blank, like a pre-migration account

    resp = client.post("/api/auth/login", {"email": "old@x.com", "password": "pw12345!"}, content_type="application/json")

    assert resp.status_code == 200, resp.json()
    assert resp.json()["profile"]["country"] == ""


def test_me_reports_profession_and_country(client):
    user = User.objects.create_user(username="c@x.com", email="c@x.com", password="x")
    Profile.objects.create(user=user, profession=Profession.ARCHITECT, country="FR")
    client.force_login(user)

    body = client.get("/api/auth/me").json()

    assert body["profile"]["profession"] == "architect"
    assert body["profile"]["profession_label"] == "Architect"
    assert body["profile"]["country"] == "FR"
    assert body["profile"]["country_name"] == "France"


def test_profile_page_can_update_profession_and_country(client):
    user = User.objects.create_user(username="c@x.com", email="c@x.com", password="x")
    Profile.objects.create(user=user)
    client.force_login(user)

    resp = client.patch(
        "/api/auth/me",
        {"profile": {"profession": Profession.CONTRACTOR, "country": "de"}},
        content_type="application/json",
    )

    assert resp.status_code == 200, resp.json()
    profile = Profile.objects.get(user=user)
    assert profile.profession == Profession.CONTRACTOR
    assert str(profile.country) == "DE"
