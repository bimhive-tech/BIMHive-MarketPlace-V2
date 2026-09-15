from rest_framework import serializers

from knowledge.models import Article, ArticleSection


class ArticleSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArticleSection
        fields = ["id", "title", "body", "code", "code_language"]


class ArticleListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = ["id", "slug", "kind", "title", "summary", "updated_at"]


class ArticleDetailSerializer(ArticleListSerializer):
    sections = ArticleSectionSerializer(many=True, read_only=True)

    class Meta(ArticleListSerializer.Meta):
        fields = ArticleListSerializer.Meta.fields + ["sections"]
