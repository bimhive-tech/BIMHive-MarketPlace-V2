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
    Documentation,
    DocSection,
    KeyFeature,
    Partner,
    Product,
    ProductFile,
    ProductMedia,
    Tag,
)
from catalog.models.product import ProductStatus
from catalog.permissions import IsStaffOrPartner


def _effective_partner_id(request):
    """The partner a caller is scoped to for this request, or None for an
    unrestricted view. Always set for a non-staff partner-linked user — that's
    the only view they have. A staff user who's *also* partner-linked keeps
    the full, unrestricted admin view by default, and is only scoped to their
    own partner when they explicitly signal they're browsing the partner
    portal (?mine=1) — otherwise the same account could see every partner's
    products while using their own company's dashboard."""
    if request is None or request.user.partner_id is None:
        return None
    if not request.user.is_staff:
        return request.user.partner_id
    return request.user.partner_id if request.query_params.get("mine") == "1" else None


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
            "rating_average", "rating_count", "updated_at", "cover_image_url",
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


class DocSectionItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocSection
        fields = ["title", "body", "image_url", "sort_order"]


class DocumentationItemSerializer(serializers.ModelSerializer):
    sections = DocSectionItemSerializer(many=True, required=False)

    class Meta:
        model = Documentation
        fields = ["title", "summary", "overview", "is_published", "sections"]


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
    documentation = DocumentationItemSerializer(required=False, allow_null=True)
    files = ProductFileSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "name", "slug", "product_code", "short_description", "description", "type",
            "category", "partner", "tags", "price", "download_count",
            "default_trial_days", "status", "rejection_note", "visibility", "is_featured",
            "cover_image_url", "version", "released_at", "seo_title", "seo_description",
            "features", "media", "changelog", "compatibility", "documentation", "files",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "slug", "download_count", "created_at", "updated_at"]

    @staticmethod
    def _is_partner_caller(request):
        """True when this request is scoped to a partner (self-service, or
        staff explicitly browsing the partner portal — see
        _effective_partner_id) rather than BIMHive's unrestricted admin view."""
        return _effective_partner_id(request) is not None

    def validate_product_code(self, value):
        value = (value or "").strip()
        instance = self.instance
        # Gated on downloads, not publish status: a published-but-never-downloaded
        # product genuinely has no installed copies to break yet, so there's no
        # activation risk in renaming its code.
        if instance and instance.download_count > 0 and instance.product_code:
            if value and value != instance.product_code:
                raise ValidationError(
                    "Product code can't be changed once the product has real downloads — it "
                    "would break activation for every installed copy in the field."
                )
            return instance.product_code
        return value

    def validate(self, attrs):
        request = self.context.get("request")
        if self._is_partner_caller(request):
            # The safety gate: a partner can only ever save a draft or submit for
            # review. Only BIMHive staff can flip a product to published/rejected —
            # that's the human review this whole feature exists for. Compared
            # against the CURRENT value (not just "is status in the payload"), the
            # same way the publish-file-gate below only fires on an actual attempt
            # to publish — otherwise a partner re-saving an already-approved
            # product's description (the frontend always resends its loaded
            # status) would trip this on every unrelated edit.
            current_status = self.instance.status if self.instance else None
            new_status = attrs.get("status")
            if new_status is not None and new_status != current_status and new_status not in (
                ProductStatus.DRAFT, ProductStatus.PENDING,
            ):
                raise ValidationError(
                    {"status": "Only BIMHive staff can publish or reject a product. Submit it for review instead."}
                )
            # Force-scoped to their own org and blocked from writing the review
            # note — both apply on create (ignored payload) and update (can't
            # repoint an existing product to another partner's id).
            attrs.pop("partner", None)
            attrs.pop("rejection_note", None)

        # Only when this request is actually transitioning INTO Published — an
        # unrelated partial update (e.g. just fixing a typo) on a product that's
        # already published, where the frontend resends its currently-loaded
        # status unchanged, must not get blocked by this, only a genuine attempt
        # to publish. (current_status computed above when there's a partner
        # caller; recomputed here too since that branch may not have run.)
        if attrs.get("status") == ProductStatus.PUBLISHED and (
            not self.instance or self.instance.status != ProductStatus.PUBLISHED
        ):
            # Files are managed on their own endpoint (see ProductFileListCreateView),
            # not part of this payload, so what matters is what's already attached —
            # on create() there's never anything attached yet, which is intentional:
            # a brand-new product can't be published in the very same request that
            # creates it, only after at least one file has actually been uploaded.
            has_files = self.instance.files.exists() if self.instance else False
            if not has_files:
                raise ValidationError(
                    {"status": "Upload at least one product file before publishing. Save as a draft first."}
                )
        return attrs

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
            # cover_image_url is what ProductCard / the admin product list actually
            # render (see catalog/serializers.py) — it isn't a separate field the
            # admin fills in, it's derived from whichever gallery item is marked
            # "cover" here, so the two can never drift apart.
            cover = next(
                (item["url"] for item in items if item.get("is_cover") and item.get("media_type") == "image"), ""
            )
            product.cover_image_url = cover
            product.save(update_fields=["cover_image_url"])
        if "changelog" in validated_data:
            items = validated_data.pop("changelog")
            product.changelog.all().delete()
            ChangelogEntry.objects.bulk_create(self._ordered(ChangelogEntry, product, items))
        if "compatibility" in validated_data:
            items = validated_data.pop("compatibility")
            product.compatibility.all().delete()
            CompatibilityEntry.objects.bulk_create(self._ordered(CompatibilityEntry, product, items))
        if "documentation" in validated_data:
            self._sync_documentation(product, validated_data.pop("documentation"))
        return validated_data

    @staticmethod
    def _sync_documentation(product, doc_data):
        """Documentation is a single OneToOne, not a repeatable list — replace-all
        doesn't apply the same way, so this is its own method rather than another
        `_ordered`/bulk_create branch. A blank title means "no documentation yet",
        so that's the signal to delete rather than save an empty row."""
        if not doc_data or not (doc_data.get("title") or "").strip():
            Documentation.objects.filter(product=product).delete()
            return
        sections = doc_data.pop("sections", [])
        doc, _ = Documentation.objects.update_or_create(product=product, defaults=doc_data)
        doc.sections.all().delete()
        DocSection.objects.bulk_create(
            [DocSection(documentation=doc, **{**s, "sort_order": i}) for i, s in enumerate(sections)]
        )

    @transaction.atomic
    def create(self, validated_data):
        request = self.context.get("request")
        if self._is_partner_caller(request):
            validated_data["partner"] = request.user.partner
        tags = validated_data.pop("tags", [])
        nested = {
            k: validated_data.pop(k)
            for k in ("features", "media", "changelog", "compatibility", "documentation")
            if k in validated_data
        }
        product = Product.objects.create(**validated_data)
        if tags:
            product.tags.set(tags)
        self._sync_nested(product, nested)
        # request is absent when this serializer is exercised directly (unit
        # tests of the save/update logic itself) rather than through the
        # admin view — nothing to attribute the action to in that case.
        if request:
            log_activity(request.user, ActivityVerb.PRODUCT_CREATED, target_label=product.name)
        return product

    @transaction.atomic
    def update(self, instance, validated_data):
        request = self.context.get("request")
        old_status = instance.status
        tags = validated_data.pop("tags", None)
        validated_data = self._sync_nested(instance, validated_data)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if tags is not None:
            instance.tags.set(tags)
        if request:
            verb = ActivityVerb.PRODUCT_UPDATED
            if instance.status != old_status:
                verb = {
                    ProductStatus.PENDING: ActivityVerb.PRODUCT_SUBMITTED_FOR_REVIEW,
                    ProductStatus.PUBLISHED: ActivityVerb.PRODUCT_APPROVED,
                    ProductStatus.REJECTED: ActivityVerb.PRODUCT_REJECTED,
                }.get(instance.status, verb)
            log_activity(request.user, verb, target_label=instance.name)
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
    permission_classes = [IsStaffOrPartner]
    serializer_class = AdminProductDetailSerializer
    queryset = Product.objects.select_related("category", "partner").prefetch_related(
        "tags", "features", "media", "changelog", "compatibility", "files", "documentation__sections"
    )

    def get_serializer_class(self):
        return AdminProductRowSerializer if self.request.method == "GET" else AdminProductDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset() if self.request.method != "GET" else Product.objects.select_related(
            "category", "partner"
        )
        partner_id = _effective_partner_id(self.request)
        if partner_id is not None:
            qs = qs.filter(partner_id=partner_id)
        status_filter = self.request.query_params.get("status")
        if status_filter and status_filter != "all":
            qs = qs.filter(status=status_filter)
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(name__icontains=search)
        return qs


class AdminProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsStaffOrPartner]
    serializer_class = AdminProductDetailSerializer
    queryset = Product.objects.select_related("category", "partner").prefetch_related(
        "tags", "features", "media", "changelog", "compatibility", "files", "documentation__sections"
    )

    def get_queryset(self):
        qs = super().get_queryset()
        # 404s (not 403) on another partner's product id via the normal
        # get_object() lookup below — doesn't confirm the id even exists.
        partner_id = _effective_partner_id(self.request)
        if partner_id is not None:
            qs = qs.filter(partner_id=partner_id)
        return qs

    def perform_destroy(self, instance):
        log_activity(self.request.user, ActivityVerb.PRODUCT_DELETED, target_label=instance.name)
        instance.delete()


class AdminProductFileListCreateView(generics.ListCreateAPIView):
    """Multi-variant file upload (Files & Downloads tab) — one row per Revit version."""

    permission_classes = [IsStaffOrPartner]
    serializer_class = ProductFileSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        qs = ProductFile.objects.filter(product_id=self.kwargs["product_id"])
        partner_id = _effective_partner_id(self.request)
        if partner_id is not None:
            qs = qs.filter(product__partner_id=partner_id)
        return qs

    def perform_create(self, serializer):
        from django.core.files.storage import default_storage
        from django.shortcuts import get_object_or_404

        product_qs = Product.objects.all()
        partner_id = _effective_partner_id(self.request)
        if partner_id is not None:
            product_qs = product_qs.filter(partner_id=partner_id)
        product = get_object_or_404(product_qs, pk=self.kwargs["product_id"])
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
    permission_classes = [IsStaffOrPartner]
    serializer_class = ProductFileSerializer
    queryset = ProductFile.objects.all()

    def get_queryset(self):
        qs = super().get_queryset()
        partner_id = _effective_partner_id(self.request)
        if partner_id is not None:
            qs = qs.filter(product__partner_id=partner_id)
        return qs

    def perform_destroy(self, instance):
        from django.core.files.storage import default_storage

        if instance.storage_key and default_storage.exists(instance.storage_key):
            default_storage.delete(instance.storage_key)
        instance.delete()


class AdminProductMediaUploadView(APIView):
    """Real file upload for the Media & Previews tab — the client picks a file,
    this stores it in R2's public-media bucket and hands back a permanent URL
    plus the auto-detected media type, so nothing about it needs to be typed."""

    permission_classes = [IsStaffOrPartner]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, product_id):
        from django.conf import settings
        from django.core.files.storage import storages

        # ProductMedia.url is a URLField — without R2 configured, storage falls
        # back to a relative /media/ path (see settings.py STORAGES) that would
        # save here successfully but then fail URL validation later when the
        # product itself is saved, as a confusing, unrelated-looking error.
        # Fail fast with a clear message instead.
        if not (settings.R2_ACCESS_KEY_ID and settings.R2_SECRET_ACCESS_KEY and settings.R2_BUCKET_NAME):
            raise ValidationError(
                {"detail": "Media uploads need Cloudflare R2 storage configured on the server first."}
            )

        product_qs = Product.objects.filter(pk=product_id)
        partner_id = _effective_partner_id(request)
        if partner_id is not None:
            product_qs = product_qs.filter(partner_id=partner_id)
        if not product_qs.exists():
            raise ValidationError({"detail": "Product not found."})

        uploaded = request.FILES.get("file")
        if not uploaded:
            raise ValidationError({"file": "A file is required."})

        content_type = uploaded.content_type or ""
        if content_type.startswith("video/"):
            media_type = "video"
        elif content_type.startswith("image/"):
            media_type = "image"
        else:
            raise ValidationError({"file": "Only image or video files are supported."})

        public_storage = storages["public_media"]
        key = public_storage.save(f"product_media/{product_id}/{uploaded.name}", uploaded)
        return Response({"url": public_storage.url(key), "media_type": media_type}, status=201)


class AdminOptionsView(APIView):
    """Select options for the product form (categories, partners, tags, enums).
    A partner-linked caller never sees the `partners` list — their product form
    hides the partner picker entirely and auto-scopes to their own org, so
    handing them every other partner's name here would be a pure data leak."""

    permission_classes = [IsStaffOrPartner]

    def get(self, request):
        return Response(
            {
                "categories": list(Category.objects.values("id", "name")),
                "partners": list(Partner.objects.values("id", "name")) if request.user.is_staff else [],
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
    owner_email = serializers.SerializerMethodField()

    class Meta:
        model = Partner
        fields = [
            "id", "name", "slug", "tagline", "bio", "logo_url", "website", "is_verified",
            "status", "rejection_note", "product_count", "owner_email",
        ]
        read_only_fields = ["slug"]

    def get_owner_email(self, obj):
        # The account that submitted the seller application (see
        # catalog.partner_api.BecomeSellerView) — read-only here, staff never
        # sets this directly.
        member = obj.team_members.first()
        return member.email if member else ""


class AdminPartnerViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    serializer_class = PartnerSerializer

    def get_queryset(self):
        return Partner.objects.annotate(product_count=Count("products", distinct=True))

        return Response({"email": user.email, "password": password}, status=201)


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
