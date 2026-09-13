"""
Customer-facing "Notifications" feed (/account/notifications) — a real activity
feed backed by the same ActivityLog every admin/staff action already writes to
(see activity/services.py::log_activity).

Two kinds of row: the caller's own account activity, and — for a seller — the
review outcomes staff record about their partner company (application or
product approved/rejected, a live product sent back for review). Those rows
are actored by the staff member, so they're matched on `metadata.partner_id`
rather than `actor`; that tag is written wherever the outcome is logged (see
catalog.admin_api). There's still no email: this is the in-app channel.
"""
from django.db.models import Q
from rest_framework import generics, serializers
from rest_framework.permissions import IsAuthenticated

from activity.models import ActivityLog, ActivityVerb

MAX_ROWS = 100

# Only verbs a customer could ever be the actor of — excludes every
# staff/admin/product-management verb even though the query is already scoped
# to request.user, purely so a staff member who's also a customer never sees
# their own admin actions mixed into what's meant to read as "your orders and
# downloads."
CUSTOMER_VERBS = [
    ActivityVerb.SIGNED_IN,
    ActivityVerb.SIGNED_UP,
    ActivityVerb.CLAIMED_FREE_PRODUCT,
    ActivityVerb.ORDER_PLACED,
    ActivityVerb.ORDER_REFUND_REQUESTED,
    ActivityVerb.DOWNLOADED_FILE,
    ActivityVerb.POSTED_REVIEW,
    ActivityVerb.REDEEMED_LICENSE_CODE,
]


# Review outcomes a seller is told about. Matched on the partner they concern,
# never on who performed them.
PARTNER_OUTCOME_VERBS = [
    ActivityVerb.PARTNER_APPROVED,
    ActivityVerb.PARTNER_REJECTED,
    ActivityVerb.PRODUCT_APPROVED,
    ActivityVerb.PRODUCT_REJECTED,
    ActivityVerb.PRODUCT_SUBMITTED_FOR_REVIEW,
]


class AccountActivitySerializer(serializers.ModelSerializer):
    # Staff's reason on a rejection, so the seller reads it where they're told.
    note = serializers.SerializerMethodField()

    class Meta:
        model = ActivityLog
        fields = ["id", "verb", "target_label", "note", "created_at"]

    def get_note(self, obj):
        return (obj.metadata or {}).get("note", "")


class AccountActivityListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AccountActivitySerializer

    def get_queryset(self):
        user = self.request.user
        visible = Q(actor=user, verb__in=CUSTOMER_VERBS)
        if user.partner_id:
            visible |= Q(verb__in=PARTNER_OUTCOME_VERBS, metadata__partner_id=user.partner_id)
        return ActivityLog.objects.filter(visible)[:MAX_ROWS]
