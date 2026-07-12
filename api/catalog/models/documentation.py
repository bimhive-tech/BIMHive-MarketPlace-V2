"""
Per-product documentation (migrated concept from v1, which had it populated).

`summary` is deliberately distinct from the product's short description — the admin
editor pre-fills it but labels them separately so the v1 "placeholder summary" bug
can't recur (see REBUILD_PROMPT admin requirements).
"""
from django.db import models
from django.utils.text import slugify

from catalog.models.product import Product
from catalog.models.taxonomy import TimeStamped


class Documentation(TimeStamped):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name="documentation")
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    title = models.CharField(max_length=200)
    summary = models.CharField(
        max_length=260, blank=True, help_text="Distinct from the product's short description."
    )
    overview = models.TextField(blank=True)
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title) or slugify(self.product.slug)
        super().save(*args, **kwargs)


class DocSection(TimeStamped):
    """An ordered how-to / reference section within a product's documentation."""

    documentation = models.ForeignKey(
        Documentation, on_delete=models.CASCADE, related_name="sections"
    )
    title = models.CharField(max_length=180)
    body = models.TextField()
    image_url = models.URLField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.documentation.title}: {self.title}"
