"""
Storefront read API. All endpoints are public (read-only) and only ever expose
published + public products. Write/admin flows live in the Django admin (and later,
authenticated admin API endpoints).
"""
from django.db.models import Count, Prefetch, Q
from rest_framework import viewsets
from rest_framework.decorators import action, api_view, authentication_classes, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from activity.models import ActivityVerb
from activity.services import log_activity
from catalog.models import Category, Collection, Documentation, Partner, Product
from catalog.models.product import ProductStatus, ProductVisibility
from catalog.pricing import (
    banner_promotion,
    live_promotions,
    promotion_for,
    sale_prices,
    unit_price_for,
)
from catalog.serializers import (
    CategorySerializer,
    CollectionSerializer,
    DocumentationDetailSerializer,
    DocumentationListSerializer,
    PartnerSerializer,
    ProductCardSerializer,
    ProductDetailSerializer,
    PromotionBannerSerializer,
    ReviewCreateSerializer,
    ReviewSerializer,
)
from membership.services import active_membership_for
from reviews.models import Review


def _published_products():
    return Product.objects.published().select_related("category", "partner", "membership_plan")


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


def _root_categories():
    """The storefront sidebar's tree: top-level categories with their
    subcategories nested and counted in the same pair of queries."""
    return _categories_with_counts(Category.objects.filter(parent__isnull=True)).prefetch_related(
        Prefetch("children", queryset=_categories_with_counts())
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
            # Matches the category itself OR anything filed under one of its
            # subcategories, so the root ("Revit Plugins") shows the whole
            # catalog while a subcategory narrows to just its own products.
            qs = qs.filter(Q(category__slug=category) | Q(category__parent__slug=category))
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

    def get_serializer_context(self):
        # Both fetched once per request, not once per product — see
        # catalog.pricing.live_promotions and the serializer mixins.
        return {
            **super().get_serializer_context(),
            "promotions": live_promotions(),
            "viewer_membership": active_membership_for(self.request.user),
        }

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
    serializer_class = CategorySerializer
    lookup_field = "slug"

    def get_queryset(self):
        # Detail is looked up across every category, not just roots — a
        # subcategory URL has to resolve too.
        if self.action == "retrieve":
            return _categories_with_counts().prefetch_related(
                Prefetch("children", queryset=_categories_with_counts())
            )
        return _root_categories()


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
    """Everything the homepage needs in one call: categories, featured products,
    collections, and the products the hero rotates through."""
    promotions = live_promotions()
    context = {"promotions": promotions, "viewer_membership": active_membership_for(request.user)}
    featured = list(_published_products().filter(is_featured=True)[:8])
    if not featured:
        featured = list(_published_products()[:8])
    return Response(
        {
            "categories": CategorySerializer(_root_categories(), many=True).data,
            "featured_products": ProductCardSerializer(featured, many=True, context=context).data,
            "collections": CollectionSerializer(
                _collections_with_counts(Collection.objects.filter(is_featured=True))[:8], many=True
            ).data,
            "spotlight_products": ProductCardSerializer(
                _spotlight_products(promotions), many=True, context=context
            ).data,
        }
    )


def _spotlight_products(promotions, limit=6):
    """What the hero carousel rotates through.

    Staff-curated first: any product with `is_hero_featured` set, in
    `hero_sort_order`. Only when nobody has curated anything does this fall
    back to an automatic pick — discounted products first (a live price is
    the most compelling thing to lead with), topped up with featured ones —
    so the hero never runs short, but a real admin choice always wins.
    """
    curated = list(
        _published_products().filter(is_hero_featured=True).order_by("hero_sort_order", "-published_at")
    )
    if curated:
        return curated[:limit]

    products = list(_published_products())
    discounted = [p for p in products if promotion_for(p, promotions)]
    rest = [p for p in products if p not in discounted and p.is_featured]
    return (discounted + rest)[:limit]


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def cart_quote_api(request):
    """Re-prices a cart against today's promotions.

    The cart is localStorage-only and stores the price captured when each item
    was added, which goes stale the moment a promotion starts or ends. The cart
    page calls this on load so what the customer sees matches what CheckoutView
    will actually charge (which recomputes the same way — see
    catalog.pricing.unit_price_for).

    POST because the cart goes in the body rather than the URL, but it is a pure
    read of public catalog data — hence no authentication (which also keeps
    SessionAuthentication's CSRF check off a request that changes nothing, so an
    anonymous visitor's cart doesn't need a token round-trip just to see a price).
    """
    from licensing.models import ProductPurchase

    items = request.data.get("items")
    if not isinstance(items, list):
        raise ValidationError({"items": "Expected a list of cart items."})

    valid_periods = {choice for choice, _ in ProductPurchase.BillingPeriod.choices}
    promotions = live_promotions()
    slugs = {(item or {}).get("slug") for item in items}
    products = {p.slug: p for p in _published_products().filter(slug__in=filter(None, slugs))}

    quotes = []
    for item in items:
        product = products.get((item or {}).get("slug"))
        billing_period = ((item or {}).get("billingPeriod") or "").strip()
        if not product or billing_period not in valid_periods:
            # Unknown slug, unpublished product, or a nonsense interval: no
            # quote. The cart drops the line rather than guessing a price.
            continue
        promo = promotion_for(product, promotions)
        unit_price = unit_price_for(product, billing_period, promo)
        if unit_price is None:
            continue
        quotes.append(
            {
                "slug": product.slug,
                "billing_period": billing_period,
                "unit_price": f"{unit_price:.2f}",
                "discount_percent": promo.discount_percent if promo else 0,
                "monthly_price": _quoted(product, promo, "monthly_price"),
                "yearly_price": _quoted(product, promo, "yearly_price"),
            }
        )
    return Response({"items": quotes})


def _quoted(product, promotion, field):
    """One of a subscription's interval prices, discount applied, as a string —
    None when the product isn't sold on that interval."""
    price = sale_prices(product, promotion).get(field) if promotion else getattr(product, field)
    return None if price is None else f"{price:.2f}"


@api_view(["GET"])
def promotion_banner_api(request):
    """The countdown bar above the nav. `promotion` is null when nothing is
    running — the bar renders nothing rather than a stale or empty offer.
    Enveloped rather than returning a bare null, which DRF renders as an empty
    body with no content type."""
    promo = banner_promotion()
    return Response({"promotion": PromotionBannerSerializer(promo).data if promo else None})
