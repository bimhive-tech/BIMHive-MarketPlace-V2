"""
Staff-only admin API powering the Next.js admin portal (/admin-portal).
Separate from Django's built-in /admin. All endpoints require is_staff.
"""
from django.db.models import Count
from rest_framework import generics, serializers
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import Category, KeyFeature, Partner, Product, Tag
from catalog.models.product import ProductStatus


class AdminProductRowSerializer(serializers.ModelSerializer):
    category = serializers.CharField(source="category.name", read_only=True)
    partner = serializers.CharField(source="partner.name", read_only=True, default="")
    partner_verified = serializers.BooleanField(source="partner.is_verified", read_only=True, default=False)

    class Meta:
        model = Product
        fields = [
            "id", "name", "slug", "type", "short_description", "category", "partner",
            "partner_verified", "price", "status", "download_count", "rating_average",
            "rating_count", "updated_at",
        ]


class AdminProductCreateSerializer(serializers.ModelSerializer):
    features = serializers.ListField(child=serializers.DictField(), required=False, write_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "name", "short_description", "description", "type", "category", "partner",
            "price", "team_price", "team_seats", "default_trial_days", "status", "visibility",
            "seo_title", "seo_description", "features",
        ]

    def create(self, validated_data):
        features = validated_data.pop("features", [])
        product = Product.objects.create(**validated_data)
        for i, feat in enumerate(features):
            title = (feat.get("title") or "").strip()
            if title:
                KeyFeature.objects.create(
                    product=product, title=title,
                    description=(feat.get("description") or "").strip(), sort_order=i,
                )
        return product


class AdminStatsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        by_status = dict(
            Product.objects.values_list("status").annotate(n=Count("id"))
        )
        top = (
            Product.objects.order_by("-download_count")
            .values("name", "slug", "download_count")[:5]
        )
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
    queryset = Product.objects.select_related("category", "partner").all()

    def get_serializer_class(self):
        return AdminProductCreateSerializer if self.request.method == "POST" else AdminProductRowSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        status_filter = self.request.query_params.get("status")
        if status_filter and status_filter != "all":
            qs = qs.filter(status=status_filter)
        return qs


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
