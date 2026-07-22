"""
Staff-facing support ticket view — Django's own /admin/ for now (no dedicated
Admin Portal page built yet, see project notes). A staff member types a reply
directly into the inline message form here; is_staff_reply/author get set
automatically, same as the customer-facing API does for its own replies.
"""
from django.contrib import admin

from support.models import SupportTicket, SupportTicketMessage


class SupportTicketMessageInline(admin.TabularInline):
    model = SupportTicketMessage
    extra = 1
    fields = ["body", "is_staff_reply", "author_label", "created_at"]
    readonly_fields = ["is_staff_reply", "author_label", "created_at"]


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ["subject", "user", "status", "created_at", "updated_at"]
    list_filter = ["status"]
    search_fields = ["subject", "user__email"]
    inlines = [SupportTicketMessageInline]

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            if isinstance(instance, SupportTicketMessage) and not instance.pk:
                instance.author = request.user
                instance.author_label = request.user.email
                instance.is_staff_reply = True
            instance.save()
        formset.save_m2m()
