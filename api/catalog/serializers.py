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
from catalog.models.product import ProductType
from catalog.storage import refresh_storage_url
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
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = Partner
        fields = ["id", "name", "slug", "tagline", "bio", "logo_url", "website", "is_verified"]

    def get_logo_url(self, obj):
        return refresh_storage_url(obj.logo_url)


class ProductMediaSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = ProductMedia
        fields = ["id", "media_type", "url", "caption", "is_cover", "sort_order"]

    def get_url(self, obj):
        return refresh_storage_url(obj.url)


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


class DocumentationListSerializer(serializers.ModelSerializer):
    """The standalone /docs library — distinct from DocumentationSerializer, which
    nests inside a product detail response without needing to say which product
    it belongs to."""

    product_name = serializers.CharField(source="product.name", read_only=True)
    product_slug = serializers.CharField(source="product.slug", read_only=True)
    product_cover_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Documentation
        fields = ["id", "slug", "title", "summary", "product_name", "product_slug", "product_cover_image_url"]

    def get_product_cover_image_url(self, obj):
        return refresh_storage_url(obj.product.cover_image_url)


class DocumentationDetailSerializer(DocumentationListSerializer):
    sections = DocSectionSerializer(many=True, read_only=True)

    class Meta(DocumentationListSerializer.Meta):
        fields = DocumentationListSerializer.Meta.fields + ["overview", "sections"]


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ["id", "author_name", "rating", "title", "body", "is_verified_purchase", "created_at"]


class ReviewCreateSerializer(serializers.ModelSerializer):
    """Customer-facing write shape — only what a reviewer actually types. product,
    author, author_name, and is_verified_purchase are all set server-side in the
    view, never trusted from the client."""

    class Meta:
        model = Review
        fields = ["id", "rating", "title", "body", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_rating(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value


class ProductCardSerializer(serializers.ModelSerializer):
    category = serializers.CharField(source="category.name", read_only=True)
    category_slug = serializers.CharField(source="category.slug", read_only=True)
    price_label = serializers.CharField(read_only=True)
    is_subscription = serializers.BooleanField(read_only=True)
    cover_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "name", "slug", "type", "short_description", "cover_image_url",
            "price", "price_label", "monthly_price", "yearly_price", "is_subscription", "currency",
            "rating_average", "rating_count", "download_count", "category", "category_slug", "is_featured",
        ]

    def get_cover_image_url(self, obj):
        return refresh_storage_url(obj.cover_image_url)


class ProductDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    partner = PartnerSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    media = ProductMediaSerializer(many=True, read_only=True)
    features = KeyFeatureSerializer(many=True, read_only=True)
    changelog = ChangelogEntrySerializer(many=True, read_only=True)
    compatibility = CompatibilityEntrySerializer(many=True, read_only=True)
    documentation = serializers.SerializerMethodField()
    reviews = ReviewSerializer(many=True, read_only=True)
    price_label = serializers.CharField(read_only=True)
    is_free = serializers.BooleanField(read_only=True)
    has_trial = serializers.BooleanField(read_only=True)
    is_subscription = serializers.BooleanField(read_only=True)
    yearly_savings_percent = serializers.IntegerField(read_only=True)
    rating_breakdown = serializers.SerializerMethodField()
    trial_builds = serializers.SerializerMethodField()
    cover_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "name", "slug", "type", "short_description", "description",
            "price", "currency", "price_label", "is_free",
            "monthly_price", "yearly_price", "is_subscription", "yearly_savings_percent",
            "default_trial_days", "default_trial_hours", "default_trial_minutes", "has_trial",
            "trial_builds", "cover_image_url", "version", "released_at",
            "rating_average", "rating_count", "download_count", "rating_breakdown",
            "seo_title", "seo_description",
            "category", "partner", "tags", "media", "features", "changelog",
            "compatibility", "documentation", "reviews",
        ]

    def get_cover_image_url(self, obj):
        return refresh_storage_url(obj.cover_image_url)

    def get_trial_builds(self, obj):
        # Deferred import — installer/models.py imports catalog.models at
        # module level, so importing installer up there would be circular.
        if obj.type != ProductType.PLUGIN or not obj.has_trial:
            return []
        from installer.models import PluginBuild

        return [
            {"id": str(build.id), "revit_year": build.revit_year}
            for build in PluginBuild.objects.filter(product=obj)
            if build.is_ready_for_build
        ]

    def get_documentation(self, obj):
        # A draft (is_published=False) doc is an admin work-in-progress, not a
        # public page yet — the product page falls back to "coming soon" for it
        # exactly as if no Documentation row existed at all.
        doc = getattr(obj, "documentation", None)
        if not doc or not doc.is_published:
            return None
        return DocumentationSerializer(doc).data

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
