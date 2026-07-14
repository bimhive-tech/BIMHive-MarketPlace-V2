"""
Storefront read API. All endpoints are public (read-only) and only ever expose
published + public products. Write/admin flows live in the Django admin (and later,
authenticated admin API endpoints).
"""
from django.db.models import Count, Prefetch, Q
from rest_framework import viewsets
from rest_framework.decorators import action, api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from activity.models import ActivityVerb
from activity.services import log_activity
from catalog.models import Category, Collection, Product
from catalog.models.product import ProductStatus, ProductVisibility
from catalog.serializers import (
    CategorySerializer,
    CollectionSerializer,
    ProductCardSerializer,
    ProductDetailSerializer,
    ReviewCreateSerializer,
    ReviewSerializer,
)
from reviews.models import Review


def _published_products():
    return Product.objects.published().select_related("category", "partner")


def _categories_with_counts(qs=None):
    # One query for the whole list instead of one COUNT per category (see
    # CategorySerializer.get_product_count).
    return (qs if qs is not None else Category.objects).annotate(
        product_count=Count(
            "products",
            filter=Q(products__status=ProductStatus.PUBLISHED, products__visibility=ProductVisibility.PUBLIC),
            distinct=True,
        )
    )


def _collections_with_counts(qs=None):
    return (qs if qs is not None else Collection.objects).annotate(
        product_count=Count("products", distinct=True)
    )


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """`/api/products` (list) and `/api/products/<slug>` (detail)."""

    lookup_field = "slug"

    def get_queryset(self):
        qs = _published_products()
        if self.action == "retrieve":
            return qs.prefetch_related(
                "tags",
                "media",
                "features",
                "changelog",
                "compatibility",
                "documentation__sections",
                Prefetch("reviews", queryset=Review.objects.all()),
            )
        category = self.request.query_params.get("category")
        product_type = self.request.query_params.get("type")
        if category:
            qs = qs.filter(category__slug=category)
        if product_type:
            qs = qs.filter(type=product_type)
        return qs

    def get_serializer_class(self):
        if self.action == "reviews":
            return ReviewCreateSerializer
        return ProductDetailSerializer if self.action == "retrieve" else ProductCardSerializer

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def reviews(self, request, slug=None):
        from licensing.models import ProductPurchase

        product = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        is_verified = ProductPurchase.objects.filter(
            user=request.user,
            product__product=product,
            payment_status=ProductPurchase.PaymentStatus.PAID,
        ).exists()
        review = serializer.save(
            product=product,
            author=request.user,
            author_name=request.user.get_full_name() or request.user.username,
            is_verified_purchase=is_verified,
        )
        log_activity(request.user, ActivityVerb.POSTED_REVIEW, target_label=product.name)
        # Full shape (not the stripped-down input serializer) so the client can
        # render this review immediately without waiting on the product detail
        # page's fetch cache to revalidate.
        return Response(ReviewSerializer(review).data, status=201)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = _categories_with_counts(Category.objects.filter(parent__isnull=True))
    serializer_class = CategorySerializer
    lookup_field = "slug"


class CollectionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = _collections_with_counts(Collection.objects.all())
    serializer_class = CollectionSerializer
    lookup_field = "slug"


@api_view(["GET"])
def home_api(request):
    """Everything the homepage needs in one call: categories, featured products, collections."""
    featured = _published_products().filter(is_featured=True)[:8]
    if not featured:
        featured = _published_products()[:8]
    return Response(
        {
            "categories": CategorySerializer(
                _categories_with_counts(Category.objects.filter(parent__isnull=True)), many=True
            ).data,
            "featured_products": ProductCardSerializer(featured, many=True).data,
            "collections": CollectionSerializer(
                _collections_with_counts(Collection.objects.filter(is_featured=True))[:8], many=True
            ).data,
        }
    )
