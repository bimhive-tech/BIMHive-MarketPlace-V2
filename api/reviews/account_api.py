"""
Customer-facing "my reviews" API (mounted under /api/account/). Same Review
rows the product page displays and catalog.views.ProductViewSet.reviews
creates — this is the list/edit/delete side scoped to request.user.
"""
from rest_framework import generics, serializers
from rest_framework.permissions import IsAuthenticated

from reviews.models import Review, refresh_product_rating


class AccountReviewSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_slug = serializers.CharField(source="product.slug", read_only=True)
    product_cover_image_url = serializers.CharField(source="product.cover_image_url", read_only=True)

    class Meta:
        model = Review
        fields = [
            "id", "product_name", "product_slug", "product_cover_image_url",
            "rating", "title", "body", "is_verified_purchase", "created_at",
        ]
        read_only_fields = ["is_verified_purchase", "created_at"]


class AccountReviewListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AccountReviewSerializer

    def get_queryset(self):
        return Review.objects.filter(author=self.request.user).select_related("product")


class AccountReviewDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Edit or delete a review the current user wrote themselves — product and
    verified-purchase status aren't part of this payload, only what a reviewer
    can actually change after the fact (rating/title/body)."""

    permission_classes = [IsAuthenticated]
    serializer_class = AccountReviewSerializer

    def get_queryset(self):
        return Review.objects.filter(author=self.request.user).select_related("product")

    def perform_destroy(self, instance):
        product = instance.product
        instance.delete()
        refresh_product_rating(product)
