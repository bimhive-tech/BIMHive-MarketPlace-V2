"""
Customer-facing "Notifications" feed (/account/notifications) — a real activity
feed backed by the same ActivityLog every admin/staff action already writes to
(see activity/services.py::log_activity), scoped to the caller's own actions.
There's no separate notification system (no email digests, no cross-user "staff
did X to your order" events yet) — this is honestly just "your recent account
activity," which is what's actually buildable from data that exists today.
"""
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


class AccountActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityLog
        fields = ["id", "verb", "target_label", "created_at"]


class AccountActivityListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AccountActivitySerializer

    def get_queryset(self):
        return ActivityLog.objects.filter(actor=self.request.user, verb__in=CUSTOMER_VERBS)[:MAX_ROWS]
