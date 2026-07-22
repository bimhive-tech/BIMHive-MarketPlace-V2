"""
Real "active sessions" list for /account/security — backed directly by Django's
own session store (django.contrib.sessions.models.Session), not a separate
tracking table. A session's device/IP is stashed into its own data blob at
login time (see accounts/api.py::_remember_session_device); there's nowhere
else that information could live, since Django's session model itself has no
device/IP columns.
"""
from django.contrib.sessions.models import Session
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


def _sessions_for(user):
    """Every non-expired Session belonging to this user, decoded. O(active
    sessions) database rows, decoded in Python — Django's session data is an
    opaque blob with no queryable user-id column, so there's no way to filter
    this in SQL. Fine at this app's scale; would need a custom session
    backend (or a parallel tracking table) to stay fast with many more users."""
    rows = []
    for session in Session.objects.filter(expire_date__gte=timezone.now()):
        data = session.get_decoded()
        if str(data.get("_auth_user_id")) != str(user.pk):
            continue
        rows.append((session, data))
    return rows


class AccountSessionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        current_key = request.session.session_key
        rows = [
            {
                "id": session.session_key,
                "ip_address": data.get("ip_address", ""),
                "user_agent": data.get("user_agent", ""),
                "expires_at": session.expire_date,
                "is_current": session.session_key == current_key,
            }
            for session, data in _sessions_for(request.user)
        ]
        rows.sort(key=lambda r: (not r["is_current"], r["expires_at"]), reverse=False)
        return Response(rows)


class AccountSessionRevokeView(APIView):
    """Signs out one other device — never the caller's own current session
    (that's just the regular Log Out button in the nav)."""

    permission_classes = [IsAuthenticated]

    def post(self, request, session_key):
        if session_key == request.session.session_key:
            raise PermissionDenied("Use Log Out to end your current session.")
        session = Session.objects.filter(pk=session_key, expire_date__gte=timezone.now()).first()
        if not session:
            raise NotFound("Session not found.")
        if str(session.get_decoded().get("_auth_user_id")) != str(request.user.pk):
            raise PermissionDenied("Not your session.")
        session.delete()
        return Response({"detail": "Signed out of that device."})
