"""Public Knowledge Base / legal page API: only published articles are visible,
the list can be narrowed by kind, and the detail view includes sections."""
import pytest

from knowledge.models import Article, ArticleSection

pytestmark = pytest.mark.django_db


def _article(**overrides):
    fields = {"title": "Guide", "kind": Article.Kind.KNOWLEDGE, "is_published": True}
    fields.update(overrides)
    return Article.objects.create(**fields)


def test_list_hides_drafts_and_filters_by_kind(client):
    _article(title="Published guide")
    _article(title="Draft guide", is_published=False)
    _article(title="Terms", kind=Article.Kind.LEGAL)

    resp = client.get("/api/articles?kind=knowledge")

    assert resp.status_code == 200
    titles = {a["title"] for a in resp.json()}
    # The seeded Revit guide is also published, so check inclusion, not equality.
    assert "Published guide" in titles
    assert "Draft guide" not in titles
    assert "Terms" not in titles
    assert all(a["kind"] == "knowledge" for a in resp.json())


def test_detail_includes_ordered_sections(client):
    article = _article(title="Join tool")
    ArticleSection.objects.create(article=article, title="Second", body="b", sort_order=2)
    ArticleSection.objects.create(article=article, title="First", body="a", code="var x = 1;", sort_order=1)

    resp = client.get(f"/api/articles/{article.slug}")

    assert resp.status_code == 200
    body = resp.json()
    assert [s["title"] for s in body["sections"]] == ["First", "Second"]
    assert body["sections"][0]["code"] == "var x = 1;"


def test_draft_detail_is_not_found(client):
    draft = _article(title="Hidden", is_published=False)
    assert client.get(f"/api/articles/{draft.slug}").status_code == 404


def test_seeded_pages_exist():
    """The data migrations ship the Revit guide and both legal pages."""
    slugs = set(Article.objects.values_list("slug", flat=True))
    assert {"getting-started-with-revit-automation", "terms-of-service", "privacy-policy"} <= slugs
