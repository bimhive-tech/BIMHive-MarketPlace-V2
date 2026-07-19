from django.contrib import admin

from installer.models import PluginBuild, PluginResourceFile


class PluginResourceFileInline(admin.TabularInline):
    model = PluginResourceFile
    extra = 0


@admin.register(PluginBuild)
class PluginBuildAdmin(admin.ModelAdmin):
    list_display = ("product", "revit_year", "plugin_version", "status", "scope", "built_at")
    list_filter = ("status", "revit_year", "scope")
    search_fields = ("product__name", "product__product_code")
    readonly_fields = ("upgrade_code", "build_log", "created_at", "updated_at")
    inlines = [PluginResourceFileInline]
