"""
Signup profession/country capture (accounts.models.Profession, Profile.country)
— the backend-driven /api/auth/signup-options list, registration requiring a
real country, and the profile page being able to edit both afterward.
"""
import pytest
from django.contrib.auth import get_user_model

from accounts.models import Profession, Profile, University

pytestmark = pytest.mark.django_db
User = get_user_model()


def _register(client, **overrides):
    payload = {
        "email": "new@x.com", "password": "correcthorsebattery9",
        "full_name": "New User", "country": "EG",
    }
    payload.update(overrides)
    return client.post("/api/auth/register", payload, content_type="application/json")


def test_signup_options_lists_professions_and_countries(client):
    body = client.get("/api/auth/signup-options").json()

    values = [p["value"] for p in body["professions"]]
    assert "architect" in values
    assert "bim_manager" in values

    codes = {c["code"] for c in body["countries"]}
    assert "US" in codes
    assert "EG" in codes


# ── Student / university / company (all optional) ──
def test_signup_options_lists_active_universities_only(client):
    # Names invented for this test rather than reused from the seeded starter
    # list (migration 0008), so the assertions can't accidentally pass on a row
    # someone else created.
    University.objects.create(name="Test Institute of Modelling")
    University.objects.create(name="Test Closed Down College", is_active=False)

    body = client.get("/api/auth/signup-options").json()

    assert "Test Institute of Modelling" in body["universities"]
    assert "Test Closed Down College" not in body["universities"]


def test_registering_as_a_student_stores_the_university(client):
    resp = _register(client, is_student=True, university="Cairo University")

    assert resp.status_code == 201, resp.json()
    profile = Profile.objects.get(user__email="new@x.com")
    assert profile.is_student is True
    assert profile.university == "Cairo University"
    assert profile.company == ""


def test_a_student_can_type_a_university_that_isnt_on_the_list(client):
    # The dropdown's "Other" path — a curated list must never block signup.
    resp = _register(client, is_student=True, university="Some Brand New Institute")

    assert resp.status_code == 201, resp.json()
    assert Profile.objects.get(user__email="new@x.com").university == "Some Brand New Institute"


def test_registering_as_a_non_student_stores_the_company(client):
    resp = _register(client, is_student=False, company="BIMHIVE")

    assert resp.status_code == 201, resp.json()
    profile = Profile.objects.get(user__email="new@x.com")
    assert profile.is_student is False
    assert profile.company == "BIMHIVE"
    assert profile.university == ""


def test_the_answer_from_the_abandoned_branch_is_discarded(client):
    # Toggling the student question after typing leaves a stale value in the
    # payload; only the one matching is_student should be kept.
    resp = _register(client, is_student=True, university="Cairo University", company="BIMHIVE")

    assert resp.status_code == 201, resp.json()
    profile = Profile.objects.get(user__email="new@x.com")
    assert profile.university == "Cairo University"
    assert profile.company == ""


def test_both_follow_ups_are_optional(client):
    resp = _register(client)

    assert resp.status_code == 201, resp.json()
    profile = Profile.objects.get(user__email="new@x.com")
    assert profile.is_student is False
    assert profile.university == ""
    assert profile.company == ""


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


def test_signup_options_ships_with_a_starter_university_list(client):
    """Migration 0008 seeds the dropdown, so a fresh install offers something
    to pick instead of pushing every student straight to "Other"."""
    body = client.get("/api/auth/signup-options").json()

    assert len(body["universities"]) > 10
    assert "Cairo University" in body["universities"]


def test_switching_to_student_on_the_profile_clears_the_company(client):
    _register(client, is_student=False, company="Hive Design")

    resp = client.patch(
        "/api/auth/me",
        {"profile": {"is_student": True, "university": "Cairo University"}},
        content_type="application/json",
    )

    assert resp.status_code == 200, resp.json()
    profile = Profile.objects.get(user__email="new@x.com")
    assert profile.university == "Cairo University"
    assert profile.company == ""


def test_switching_away_from_student_clears_the_university(client):
    _register(client, is_student=True, university="Cairo University")

    resp = client.patch(
        "/api/auth/me",
        {"profile": {"is_student": False, "company": "Hive Design"}},
        content_type="application/json",
    )

    assert resp.status_code == 200, resp.json()
    profile = Profile.objects.get(user__email="new@x.com")
    assert profile.company == "Hive Design"
    assert profile.university == ""


def test_editing_something_else_leaves_both_answers_alone(client):
    _register(client, is_student=True, university="Cairo University")

    resp = client.patch(
        "/api/auth/me", {"profile": {"bio": "Modelling since 2019."}}, content_type="application/json"
    )

    assert resp.status_code == 200, resp.json()
    profile = Profile.objects.get(user__email="new@x.com")
    assert profile.university == "Cairo University"
    assert profile.is_student is True
