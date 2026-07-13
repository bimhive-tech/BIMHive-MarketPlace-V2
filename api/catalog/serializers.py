"""
DRF serializers for the storefront API. Two shapes for products:
- ProductCardSerializer: compact, for grids (home featured, catalog).
- ProductDetailSerializer: full, for the product detail page (tabs, gallery, etc.).
"""
from rest_framework import serializers

from catalog.models import (
    Category,
    ChangelogEntry,
    Collection,
    CompatibilityEntry,
    Documentation,
    DocSection,
    KeyFeature,
    Partner,
    Product,
    ProductMedia,
    Tag,
)
from reviews.models import Review


class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "icon", "description", "product_count"]

    def get_product_count(self, obj):
        # Queryset call sites annotate `product_count` (see catalog/views.py) so this
        # is a single query for the whole list rather than one COUNT per category.
        # Fall back to a live count only when an unannotated instance slips through
        # (e.g. the single nested category on a product detail page).
        count = getattr(obj, "product_count", None)
        return count if count is not None else obj.products.published().count()


class CollectionSerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Collection
        fields = ["id", "name", "slug", "icon", "description", "product_count", "is_featured"]

    def get_product_count(self, obj):
        count = getattr(obj, "product_count", None)
        return count if count is not None else obj.products.count()


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "slug"]


class PartnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Partner
        fields = ["id", "name", "slug", "tagline", "bio", "logo_url", "website", "is_verified"]


class ProductMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductMedia
        fields = ["id", "media_type", "url", "caption", "is_cover", "sort_order"]


class KeyFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = KeyFeature
        fields = ["id", "title", "description", "icon", "sort_order"]


class ChangelogEntrySerializer(serializers.ModelSerializer):
    notes = serializers.SerializerMethodField()

    class Meta:
        model = ChangelogEntry
        fields = ["id", "version", "released_at", "notes"]

    def get_notes(self, obj):
        return [line.strip() for line in obj.notes.splitlines() if line.strip()]


class CompatibilityEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = CompatibilityEntry
        fields = ["id", "label", "value", "sort_order"]


class DocSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocSection
        fields = ["id", "title", "body", "image_url", "sort_order"]


class DocumentationSerializer(serializers.ModelSerializer):
    sections = DocSectionSerializer(many=True, read_only=True)

    class Meta:
        model = Documentation
        fields = ["id", "slug", "title", "summary", "overview", "is_published", "sections"]


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ["id", "author_name", "rating", "title", "body", "is_verified_purchase", "created_at"]


class ProductCardSerializer(serializers.ModelSerializer):
    category = serializers.CharField(source="category.name", read_only=True)
    category_slug = serializers.CharField(source="category.slug", read_only=True)
    price_label = serializers.CharField(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "name", "slug", "type", "short_description", "cover_image_url",
            "price", "price_label", "currency", "rating_average", "rating_count",
            "download_count", "category", "category_slug", "is_featured",
        ]


class ProductDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    partner = PartnerSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    media = ProductMediaSerializer(many=True, read_only=True)
    features = KeyFeatureSerializer(many=True, read_only=True)
    changelog = ChangelogEntrySerializer(many=True, read_only=True)
    compatibility = CompatibilityEntrySerializer(many=True, read_only=True)
    documentation = DocumentationSerializer(read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True)
    price_label = serializers.CharField(read_only=True)
    rating_breakdown = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "name", "slug", "type", "short_description", "description",
            "price", "team_price", "team_seats", "currency", "price_label",
            "default_trial_days", "cover_image_url", "version", "released_at",
            "rating_average", "rating_count", "download_count", "rating_breakdown",
            "seo_title", "seo_description",
            "category", "partner", "tags", "media", "features", "changelog",
            "compatibility", "documentation", "reviews",
        ]

    def get_rating_breakdown(self, obj):
        """Percentage of ratings at each star level (5→1), for the ratings bars.

        Uses the stored aggregate distribution (rating_distribution) so the bars
        reflect all ratings, not just the reviews rendered on the page. Falls back
        to counting review rows when no distribution is stored.
        """
        dist = obj.rating_distribution or {}
        counts = {star: int(dist.get(str(star), 0)) for star in range(1, 6)}
        if not any(counts.values()):
            for review in obj.reviews.all():
                if review.rating in counts:
                    counts[review.rating] += 1
        total = sum(counts.values()) or obj.rating_count or 0
        return [
            {
                "stars": star,
                "count": counts[star],
                "percent": round((counts[star] / total) * 100) if total else 0,
            }
            for star in range(5, 0, -1)
        ]
