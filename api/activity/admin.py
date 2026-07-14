from django.contrib import admin

from activity.models import ActivityLog


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor_label", "verb", "target_label")
    list_filter = ("verb",)
    search_fields = ("actor_label", "target_label")
    readonly_fields = ("actor", "actor_label", "verb", "target_label", "metadata", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
