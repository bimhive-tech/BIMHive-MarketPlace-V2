"""
Storefront read API. All endpoints are public (read-only) and only ever expose
published + public products. Write/admin flows live in the Django admin (and later,
authenticated admin API endpoints).
"""
from django.db.models import Count, Prefetch, Q
from rest_framework import viewsets
from rest_framework.decorators import action, api_view
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from activity.models import ActivityVerb
from activity.services import log_activity
from catalog.models import Category, Collection, Documentation, Partner, Product
from catalog.models.product import ProductStatus, ProductVisibility
from catalog.serializers import (
    CategorySerializer,
    CollectionSerializer,
    DocumentationDetailSerializer,
    DocumentationListSerializer,
    PartnerSerializer,
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


class ProductPagination(PageNumberPagination):
    # A big catalog (or a "load everything" caller like a collection/partner
    # page) can override via ?page_size=, capped so no one request can force
    # the DB to hand back the whole table.
    page_size = 24
    page_size_query_param = "page_size"
    max_page_size = 100


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """`/api/products` (list) and `/api/products/<slug>` (detail)."""

    pagination_class = ProductPagination

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
        collection = self.request.query_params.get("collection")
        partner = self.request.query_params.get("partner")
        search = self.request.query_params.get("q")
        if category:
            qs = qs.filter(category__slug=category)
        if product_type:
            qs = qs.filter(type=product_type)
        if collection:
            qs = qs.filter(collections__slug=collection)
        if partner:
            qs = qs.filter(partner__slug=partner)
        if search:
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(short_description__icontains=search)
                | Q(description__icontains=search)
                | Q(tags__name__icontains=search)
            ).distinct()
        return qs

    def get_serializer_class(self):
        if self.action == "reviews":
            return ReviewCreateSerializer
        return ProductDetailSerializer if self.action == "retrieve" else ProductCardSerializer

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def reviews(self, request, slug=None):
        from licensing.models import ProductPurchase

        product = self.get_object()

        is_verified = ProductPurchase.objects.filter(
            user=request.user,
            product__product=product,
            payment_status=ProductPurchase.PaymentStatus.PAID,
        ).exists()
        if not is_verified:
            raise PermissionDenied("You can only review products you own.")
        if Review.objects.filter(product=product, author=request.user).exists():
            raise ValidationError(
                {"detail": "You've already reviewed this product — edit your existing review instead."}
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
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


class PartnerViewSet(viewsets.ReadOnlyModelViewSet):
    """Public seller profile — only APPROVED partners with at least one live
    product are listed. The status filter is belt-and-suspenders: a pending/
    rejected applicant can't have a published product yet anyway (product
    creation itself is gated on approval — see catalog.permissions), but a
    freshly-un-verified partner should never be reachable regardless."""

    queryset = Partner.objects.filter(
        status=Partner.ApplicationStatus.APPROVED, products__in=_published_products()
    ).distinct()
    serializer_class = PartnerSerializer
    lookup_field = "slug"


class DocumentationViewSet(viewsets.ReadOnlyModelViewSet):
    """The standalone /docs library — the "Learn more" destination linked from a
    product page's Documentation tab. Same publish gating as the product itself:
    a doc marked published on an unpublished/hidden product still isn't public."""

    queryset = (
        Documentation.objects.filter(is_published=True, product__in=_published_products())
        .select_related("product")
        .prefetch_related("sections")
    )
    lookup_field = "slug"

    def get_serializer_class(self):
        return DocumentationDetailSerializer if self.action == "retrieve" else DocumentationListSerializer


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
