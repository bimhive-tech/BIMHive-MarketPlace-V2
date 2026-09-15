from rest_framework import viewsets

from knowledge.models import Article
from knowledge.serializers import ArticleDetailSerializer, ArticleListSerializer


class ArticleViewSet(viewsets.ReadOnlyModelViewSet):
    """`/api/articles?kind=knowledge` (list) and `/api/articles/<slug>` (detail).
    Only published articles are public; drafts stay admin-only."""

    lookup_field = "slug"

    def get_queryset(self):
        qs = Article.objects.filter(is_published=True)
        if self.action == "retrieve":
            return qs.prefetch_related("sections")
        kind = self.request.query_params.get("kind")
        return qs.filter(kind=kind) if kind else qs

    def get_serializer_class(self):
        return ArticleDetailSerializer if self.action == "retrieve" else ArticleListSerializer
