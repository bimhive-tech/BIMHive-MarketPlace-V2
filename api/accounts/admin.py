from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from accounts.models import Profile, Role, University, User

admin.site.register(User, UserAdmin)
admin.site.register(Profile)
admin.site.register(Role)


@admin.register(University)
class UniversityAdmin(admin.ModelAdmin):
    """The signup dropdown is curated here, so the list can grow without a
    deploy — see University's docstring."""

    list_display = ("name", "country", "is_active")
    list_filter = ("is_active", "country")
    list_editable = ("is_active",)
    search_fields = ("name",)
