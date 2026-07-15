"""Product reviews + a helper to refresh the denormalised aggregate on Product."""
from django.conf import settings
from django.db import models
from django.db.models import Avg, Count

from catalog.models import Product


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="reviews"
    )
    author_name = models.CharField(max_length=140, blank=True)
    rating = models.PositiveSmallIntegerField()  # 1..5
    title = models.CharField(max_length=180, blank=True)
    body = models.TextField(blank=True)
    is_verified_purchase = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["product", "author"], name="one_review_per_user_per_product"),
        ]

    def __str__(self):
        return f"{self.product.name} {self.rating}★"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        refresh_product_rating(self.product)


def refresh_product_rating(product):
    """Recompute and persist the product's rating aggregate from its reviews."""
    stats = product.reviews.aggregate(avg=Avg("rating"), count=Count("id"))
    product.rating_average = round(stats["avg"] or 0, 2)
    product.rating_count = stats["count"] or 0
    product.save(update_fields=["rating_average", "rating_count"])
