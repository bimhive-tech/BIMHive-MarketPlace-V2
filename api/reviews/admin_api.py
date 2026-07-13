"""Staff-only admin API for moderating reviews."""
from rest_framework import generics, serializers
from rest_framework.permissions import IsAdminUser

from reviews.models import Review, refresh_product_rating


class AdminReviewSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = Review
        fields = [
            "id", "product", "product_name", "author_name", "rating", "title", "body",
            "is_verified_purchase", "created_at",
        ]
        read_only_fields = ["product", "author_name", "rating", "created_at"]


class AdminReviewListView(generics.ListAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = AdminReviewSerializer

    def get_queryset(self):
        qs = Review.objects.select_related("product").order_by("-created_at")
        product = self.request.query_params.get("product")
        if product:
            qs = qs.filter(product_id=product)
        return qs


class AdminReviewDeleteView(generics.DestroyAPIView):
    permission_classes = [IsAdminUser]
    queryset = Review.objects.all()

    def perform_destroy(self, instance):
        product = instance.product
        instance.delete()
        refresh_product_rating(product)
