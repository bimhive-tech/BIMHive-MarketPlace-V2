"""
Storefront read API. All endpoints are public (read-only) and only ever expose
published + public products. Write/admin flows live in the Django admin (and later,
authenticated admin API endpoints).
"""
from django.db.models import Prefetch
from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from catalog.models import Category, Collection, Product
from catalog.serializers import (
    CategorySerializer,
    CollectionSerializer,
    ProductCardSerializer,
    ProductDetailSerializer,
)
from reviews.models import Review


def _published_products():
    return Product.objects.published().select_related("category", "partner")


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """`/api/products/` (list) and `/api/products/<slug>/` (detail)."""

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
        return ProductDetailSerializer if self.action == "retrieve" else ProductCardSerializer


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.filter(parent__isnull=True)
    serializer_class = CategorySerializer
    lookup_field = "slug"


class CollectionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Collection.objects.all()
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
                Category.objects.filter(parent__isnull=True), many=True
            ).data,
            "featured_products": ProductCardSerializer(featured, many=True).data,
            "collections": CollectionSerializer(
                Collection.objects.filter(is_featured=True)[:8], many=True
            ).data,
        }
    )
