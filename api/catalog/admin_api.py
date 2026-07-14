"""
Staff-only admin API powering the Next.js admin portal (/admin-portal).
Separate from Django's built-in /admin. All endpoints require is_staff.
"""
from django.db import transaction
from django.db.models import Count
from rest_framework import generics, serializers, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from activity.models import ActivityVerb
from activity.services import log_activity
from catalog.models import (
    Category,
    ChangelogEntry,
    Collection,
    CompatibilityEntry,
    KeyFeature,
    Partner,
    Product,
    ProductFile,
    ProductMedia,
    Tag,
)
from catalog.models.product import ProductStatus


# ─────────────────────────────────────────────────────────────
# Product — list row (compact, for the table)
# ─────────────────────────────────────────────────────────────
class AdminProductRowSerializer(serializers.ModelSerializer):
    category = serializers.CharField(source="category.name", read_only=True)
    partner = serializers.CharField(source="partner.name", read_only=True, default="")
    partner_verified = serializers.BooleanField(source="partner.is_verified", read_only=True, default=False)

    class Meta:
        model = Product
        fields = [
            "id", "name", "slug", "product_code", "type", "short_description", "category",
            "partner", "partner_verified", "price", "status", "download_count",
            "rating_average", "rating_count", "updated_at",
        ]


# ─────────────────────────────────────────────────────────────
# Product — nested list items (repeatable rows the form edits inline)
# ─────────────────────────────────────────────────────────────
class KeyFeatureItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = KeyFeature
        fields = ["title", "description", "icon", "sort_order"]


class ProductMediaItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductMedia
        fields = ["media_type", "url", "caption", "is_cover", "sort_order"]


class ChangelogItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChangelogEntry
        fields = ["version", "released_at", "notes", "sort_order"]


class CompatibilityItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompatibilityEntry
        fields = ["label", "value", "sort_order"]


class ProductFileSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = ProductFile
        fields = [
            "id", "revit_version", "version_label", "storage_key", "file_size_bytes",
            "is_current", "download_url",
        ]
        read_only_fields = ["storage_key", "file_size_bytes"]

    def get_download_url(self, obj):
        from django.core.files.storage import default_storage

        if not obj.storage_key:
            return ""
        # In prod this is a short-lived presigned R2 URL (see STORAGES in
        # settings.py); in local dev without R2/MinIO configured it falls back to
        # a plain /media/ path served by Django in DEBUG.
        return default_storage.url(obj.storage_key)


# ─────────────────────────────────────────────────────────────
# Product — full detail (edit form) + write (create/update)
# ─────────────────────────────────────────────────────────────
class AdminProductDetailSerializer(serializers.ModelSerializer):
    tags = serializers.PrimaryKeyRelatedField(many=True, queryset=Tag.objects.all(), required=False)
    features = KeyFeatureItemSerializer(many=True, required=False)
    media = ProductMediaItemSerializer(many=True, required=False)
    changelog = ChangelogItemSerializer(many=True, required=False)
    compatibility = CompatibilityItemSerializer(many=True, required=False)
    files = ProductFileSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "name", "slug", "product_code", "short_description", "description", "type",
            "category", "partner", "tags", "price", "team_price", "team_seats",
            "default_trial_days", "status", "visibility", "is_featured", "cover_image_url",
            "version", "released_at", "seo_title", "seo_description", "features", "media",
            "changelog", "compatibility", "files", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "slug", "created_at", "updated_at"]

    def validate_product_code(self, value):
        value = (value or "").strip()
        instance = self.instance
        if instance and instance.status == ProductStatus.PUBLISHED and instance.product_code:
            if value and value != instance.product_code:
                raise ValidationError(
                    "Product code can't be changed once the product is live — it would break "
                    "activation for every installed copy in the field."
                )
            return instance.product_code
        return value

    @staticmethod
    def _ordered(model, product, items):
        """Build model instances from client item dicts, with list position as the
        authoritative sort_order (a client-supplied sort_order, if present, is
        overridden rather than colliding as a duplicate constructor argument)."""
        return [model(product=product, **{**item, "sort_order": i}) for i, item in enumerate(items)]

    def _sync_nested(self, product, validated_data):
        """Replace-all-on-save for the repeatable list fields (same pattern as v1's
        inline formsets, minus the placeholder problem: nothing here is fabricated,
        every row is exactly what the admin typed)."""
        if "features" in validated_data:
            items = validated_data.pop("features")
            product.features.all().delete()
            KeyFeature.objects.bulk_create(self._ordered(KeyFeature, product, items))
        if "media" in validated_data:
            items = validated_data.pop("media")
            product.media.all().delete()
            ProductMedia.objects.bulk_create(self._ordered(ProductMedia, product, items))
        if "changelog" in validated_data:
            items = validated_data.pop("changelog")
            product.changelog.all().delete()
            ChangelogEntry.objects.bulk_create(self._ordered(ChangelogEntry, product, items))
        if "compatibility" in validated_data:
            items = validated_data.pop("compatibility")
            product.compatibility.all().delete()
            CompatibilityEntry.objects.bulk_create(self._ordered(CompatibilityEntry, product, items))
        return validated_data

    @transaction.atomic
    def create(self, validated_data):
        tags = validated_data.pop("tags", [])
        nested = {
            k: validated_data.pop(k)
            for k in ("features", "media", "changelog", "compatibility")
            if k in validated_data
        }
        product = Product.objects.create(**validated_data)
        if tags:
            product.tags.set(tags)
        self._sync_nested(product, nested)
        # request is absent when this serializer is exercised directly (unit
        # tests of the save/update logic itself) rather than through the
        # admin view — nothing to attribute the action to in that case.
        if request := self.context.get("request"):
            log_activity(request.user, ActivityVerb.PRODUCT_CREATED, target_label=product.name)
        return product

    @transaction.atomic
    def update(self, instance, validated_data):
        tags = validated_data.pop("tags", None)
        validated_data = self._sync_nested(instance, validated_data)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if tags is not None:
            instance.tags.set(tags)
        if request := self.context.get("request"):
            log_activity(request.user, ActivityVerb.PRODUCT_UPDATED, target_label=instance.name)
        return instance


# ─────────────────────────────────────────────────────────────
# Views
# ─────────────────────────────────────────────────────────────
class AdminStatsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        by_status = dict(Product.objects.values_list("status").annotate(n=Count("id")))
        top = Product.objects.order_by("-download_count").values("name", "slug", "download_count")[:5]
        return Response(
            {
                "total": Product.objects.count(),
                "published": by_status.get(ProductStatus.PUBLISHED, 0),
                "pending": by_status.get(ProductStatus.PENDING, 0),
                "draft": by_status.get(ProductStatus.DRAFT, 0),
                "rejected": by_status.get(ProductStatus.REJECTED, 0),
                "top_products": list(top),
            }
        )


class AdminProductListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = AdminProductDetailSerializer
    queryset = Product.objects.select_related("category", "partner").prefetch_related(
        "tags", "features", "media", "changelog", "compatibility", "files"
    )

    def get_serializer_class(self):
        return AdminProductRowSerializer if self.request.method == "GET" else AdminProductDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset() if self.request.method != "GET" else Product.objects.select_related(
            "category", "partner"
        )
        status_filter = self.request.query_params.get("status")
        if status_filter and status_filter != "all":
            qs = qs.filter(status=status_filter)
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(name__icontains=search)
        return qs


class AdminProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = AdminProductDetailSerializer
    queryset = Product.objects.select_related("category", "partner").prefetch_related(
        "tags", "features", "media", "changelog", "compatibility", "files"
    )

    def perform_destroy(self, instance):
        log_activity(self.request.user, ActivityVerb.PRODUCT_DELETED, target_label=instance.name)
        instance.delete()


class AdminProductFileListCreateView(generics.ListCreateAPIView):
    """Multi-variant file upload (Files & Downloads tab) — one row per Revit version."""

    permission_classes = [IsAdminUser]
    serializer_class = ProductFileSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        return ProductFile.objects.filter(product_id=self.kwargs["product_id"])

    def perform_create(self, serializer):
        from django.core.files.storage import default_storage

        product = Product.objects.get(pk=self.kwargs["product_id"])
        uploaded = self.request.FILES.get("file")
        if not uploaded:
            raise ValidationError({"file": "A file is required."})

        # default_storage routes to R2/MinIO in any environment where they're
        # configured (see STORAGES in settings.py) and only touches local disk as a
        # bare-bones fallback — the actual key it lands on (with any dedupe suffix
        # the backend applies) is what we record, not the name we asked for.
        key = default_storage.save(f"product_files/{product.id}/{uploaded.name}", uploaded)
        serializer.save(product=product, storage_key=key, file_size_bytes=uploaded.size)


class AdminProductFileDetailView(generics.DestroyAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = ProductFileSerializer
    queryset = ProductFile.objects.all()

    def perform_destroy(self, instance):
        from django.core.files.storage import default_storage

        if instance.storage_key and default_storage.exists(instance.storage_key):
            default_storage.delete(instance.storage_key)
        instance.delete()


class AdminOptionsView(APIView):
    """Select options for the product form (categories, partners, tags, enums)."""

    permission_classes = [IsAdminUser]

    def get(self, request):
        return Response(
            {
                "categories": list(Category.objects.values("id", "name")),
                "partners": list(Partner.objects.values("id", "name")),
                "tags": list(Tag.objects.values("id", "name")),
                "types": [{"value": v, "label": l} for v, l in Product._meta.get_field("type").choices],
            }
        )


# ─────────────────────────────────────────────────────────────
# Taxonomy CRUD (Categories, Tags, Partners, Collections)
# ─────────────────────────────────────────────────────────────
class ProductCountMixin:
    """Reads `product_count` off an annotation when the queryset provides one
    (see each ViewSet's `get_queryset`), falling back to a live count so
    create/update responses — whose instance never goes through that
    annotated queryset — still work. Keeps taxonomy list pages at one query
    total instead of one COUNT per row."""

    def get_product_count(self, obj):
        count = getattr(obj, "product_count", None)
        return count if count is not None else obj.products.count()


class CategorySerializer(ProductCountMixin, serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "description", "icon", "parent", "sort_order", "product_count"]
        read_only_fields = ["slug"]


class AdminCategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    serializer_class = CategorySerializer

    def get_queryset(self):
        return Category.objects.annotate(product_count=Count("products", distinct=True))


class TagSerializer(ProductCountMixin, serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Tag
        fields = ["id", "name", "slug", "product_count"]
        read_only_fields = ["slug"]


class AdminTagViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    serializer_class = TagSerializer

    def get_queryset(self):
        return Tag.objects.annotate(product_count=Count("products", distinct=True))


class PartnerSerializer(ProductCountMixin, serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Partner
        fields = [
            "id", "name", "slug", "tagline", "bio", "logo_url", "website", "is_verified",
            "product_count",
        ]
        read_only_fields = ["slug"]


class AdminPartnerViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    serializer_class = PartnerSerializer

    def get_queryset(self):
        return Partner.objects.annotate(product_count=Count("products", distinct=True))


class CollectionSerializer(ProductCountMixin, serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()
    products = serializers.PrimaryKeyRelatedField(many=True, queryset=Product.objects.all(), required=False)

    class Meta:
        model = Collection
        fields = [
            "id", "name", "slug", "description", "icon", "is_featured", "sort_order",
            "products", "product_count",
        ]
        read_only_fields = ["slug"]


class AdminCollectionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    serializer_class = CollectionSerializer

    def get_queryset(self):
        return Collection.objects.annotate(product_count=Count("products", distinct=True)).prefetch_related(
            "products"
        )
