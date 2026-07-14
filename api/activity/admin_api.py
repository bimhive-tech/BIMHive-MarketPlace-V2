"""Staff-only "who did what, when" log for the admin portal (mounted under /api/admin/)."""
from django.utils.dateparse import parse_date
from rest_framework import generics, serializers
from rest_framework.permissions import IsAdminUser

from activity.models import ActivityLog

# Recent-first, capped: this table can grow fast (every sign-in, download, review,
# admin edit...), and — like every other admin list in this app — there's no
# pagination yet, so an unbounded query here would be the one that actually hurts.
MAX_ROWS = 300


class AdminActivityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityLog
        fields = ["id", "actor_label", "verb", "target_label", "metadata", "created_at"]


class AdminActivityLogListView(generics.ListAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = AdminActivityLogSerializer

    def get_queryset(self):
        qs = ActivityLog.objects.select_related("actor")
        params = self.request.query_params

        if actor := params.get("actor"):
            qs = qs.filter(actor_label__icontains=actor)
        if (verb := params.get("verb")) and verb != "all":
            qs = qs.filter(verb=verb)
        if date_from := parse_date(params.get("date_from") or ""):
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to := parse_date(params.get("date_to") or ""):
            qs = qs.filter(created_at__date__lte=date_to)

        return qs[:MAX_ROWS]
