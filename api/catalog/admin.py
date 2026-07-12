"""
Admin for the catalog. The Add/Edit Product screen (see mockup) is organised with
inlines for media, features, changelog, compatibility, files and documentation, and
guards the product code as immutable once a product is live.
"""
from django.contrib import admin

from catalog.models import (
    Category,
    ChangelogEntry,
    Collection,
    CompatibilityEntry,
    Documentation,
    DocSection,
    KeyFeature,
    Partner,
    Product,
    ProductFile,
    ProductMedia,
    Tag,
)


class ProductMediaInline(admin.TabularInline):
    model = ProductMedia
    extra = 1


class KeyFeatureInline(admin.TabularInline):
    model = KeyFeature
    extra = 1


class ChangelogEntryInline(admin.TabularInline):
    model = ChangelogEntry
    extra = 1


class CompatibilityEntryInline(admin.TabularInline):
    model = CompatibilityEntry
    extra = 1


class ProductFileInline(admin.TabularInline):
    model = ProductFile
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "category", "partner", "price", "status", "is_featured")
    list_filter = ("status", "visibility", "type", "category", "is_featured")
    search_fields = ("name", "short_description")
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ("tags",)
    inlines = [
        ProductMediaInline,
        KeyFeatureInline,
        ChangelogEntryInline,
        CompatibilityEntryInline,
        ProductFileInline,
    ]


class DocSectionInline(admin.StackedInline):
    model = DocSection
    extra = 1


@admin.register(Documentation)
class DocumentationAdmin(admin.ModelAdmin):
    list_display = ("title", "product", "is_published")
    inlines = [DocSectionInline]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "sort_order")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_featured", "product_count")
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ("products",)


admin.site.register(Tag)
admin.site.register(Partner)
