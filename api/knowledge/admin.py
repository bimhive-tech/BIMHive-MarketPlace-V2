from django.contrib import admin

from knowledge.models import Article, ArticleSection


class ArticleSectionInline(admin.StackedInline):
    model = ArticleSection
    extra = 1
    fields = ("sort_order", "title", "body", "code_language", "code")


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "is_published", "sort_order", "updated_at")
    list_filter = ("kind", "is_published")
    search_fields = ("title", "summary")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [ArticleSectionInline]
