"""Written content that isn't tied to a product: Knowledge Base guides and the
site's legal pages (Terms of Service, Privacy Policy).

Both are the same shape — a titled page made of ordered sections — so they
share one model, told apart by `kind`. Edited in the Django admin (/admin).
"""
from django.db import models
from django.utils.text import slugify

from catalog.models.taxonomy import TimeStamped


class Article(TimeStamped):
    class Kind(models.TextChoices):
        KNOWLEDGE = "knowledge", "Knowledge Base guide"
        LEGAL = "legal", "Legal page"

    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.KNOWLEDGE, db_index=True)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    title = models.CharField(max_length=200)
    summary = models.CharField(max_length=300, blank=True)
    is_published = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0, help_text="Lower numbers are listed first.")

    class Meta:
        ordering = ["sort_order", "title"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)


class ArticleSection(TimeStamped):
    """One heading + text, optionally followed by a code sample."""

    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="sections")
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True, help_text="Plain text. Blank lines start a new paragraph.")
    code = models.TextField(blank=True, help_text="Optional code sample shown under the text.")
    code_language = models.CharField(max_length=30, blank=True, help_text='e.g. "csharp", "xml", "text".')
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.article.title}: {self.title}"
