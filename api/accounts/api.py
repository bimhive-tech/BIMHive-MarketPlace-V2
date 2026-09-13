"""
Session-based auth API for the Next.js client (same-origin cookies).

Security: passwords go through Django's hashers + validators; login is throttled to
blunt credential stuffing; CSRF is enforced on the state-changing endpoints (the
client fetches a token from /api/auth/csrf first). See ARCHITECTURE §7.
"""
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django_countries import countries
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from accounts.models import Profession, University
from accounts.serializers import (
    ChangePasswordSerializer,
    MeUpdateSerializer,
    RegisterSerializer,
    UserSerializer,
)
from activity.models import ActivityVerb
from activity.services import log_activity


def _client_ip(request):
    # Same XFF-aware lookup as licensing/api_views.py::_client_ip — Railway
    # sits behind a proxy, so REMOTE_ADDR alone would just be the proxy's IP.
    xff = (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip()
    return xff or request.META.get("REMOTE_ADDR") or "unknown"


def _remember_session_device(request):
    """Stashes who/where a session belongs to, at the moment it's created —
    Django's own Session model has no device/IP columns, only an opaque
    encoded blob, so this is the only place that information can ever be
    captured. Read back by AccountSessionListView (accounts/security_api.py)
    for the real "active sessions" list."""
    request.session["ip_address"] = _client_ip(request)
    request.session["user_agent"] = (request.META.get("HTTP_USER_AGENT") or "")[:200]


@method_decorator(ensure_csrf_cookie, name="get")
class CsrfView(APIView):
    """GET to receive a csrftoken cookie before posting to login/register."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"detail": "CSRF cookie set."})


class SignupOptionsView(APIView):
    """The profession, country and university dropdowns on /signup. Backend is
    the single source of truth for all three — the frontend never hardcodes
    them, so a new profession, a country-list update, or a university nobody
    had added yet only ever needs to change here (universities are rows, so
    that one doesn't even need a deploy)."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response(
            {
                "professions": [{"value": v, "label": l} for v, l in Profession.choices],
                "countries": [{"code": code, "name": name} for code, name in countries],
                "universities": list(
                    University.objects.filter(is_active=True).values_list("name", flat=True)
                ),
            }
        )


class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        login(request, user)  # start a session immediately after signup
        _remember_session_device(request)
        log_activity(user, ActivityVerb.SIGNED_UP)
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        email = (request.data.get("email") or "").lower().strip()
        password = request.data.get("password") or ""
        # username == email in this app (see RegisterSerializer).
        user = authenticate(request, username=email, password=password)
        if user is None:
            return Response(
                {"detail": "Invalid email or password."}, status=status.HTTP_401_UNAUTHORIZED
            )
        login(request, user)
        _remember_session_device(request)
        log_activity(user, ActivityVerb.SIGNED_IN)
        return Response(UserSerializer(user).data)


class _SessionAuthWithoutCsrf(SessionAuthentication):
    """SessionAuthentication that identifies the caller but doesn't refuse them
    over CSRF. Only for LogoutView — see the reasoning there."""

    def enforce_csrf(self, request):
        return None


class LogoutView(APIView):
    """Signing out always works, whatever state the caller's session or CSRF
    token is in. Both of the ways this endpoint could refuse a click left the
    user stuck pressing a dead button:

    - Gated on IsAuthenticated, a session that had already died server-side
      (expired, revoked from another device, cleared by a deploy) answered with
      a 403 — even though the browser still held a sessionid cookie and still
      showed the user as signed in. Hence AllowAny; auth.logout() is simply a
      no-op for an anonymous request.
    - Under the default SessionAuthentication, a stale CSRF token or an
      untrusted Origin answered with a 403 *and left the session alive*, so the
      user stayed signed in with no way to stop being signed in. Note the
      asymmetry that hid this: an anonymous request never reaches enforce_csrf
      at all (DRF returns early when there's no user, and APIView is
      csrf_exempt at the middleware level), so signing *in* kept working
      normally while signing out was the only broken action.

    Dropping the CSRF check here costs nothing worth keeping. The only thing it
    protected against is a forced logout — a nuisance, not a breach, with no
    attacker-readable response — and SESSION_COOKIE_SAMESITE = "Lax" already
    stops a cross-site POST carrying the session cookie, so it isn't reachable
    cross-site anyway. Authentication itself is untouched: the session still has
    to be real for there to be anything to end.
    """

    authentication_classes = [_SessionAuthWithoutCsrf]
    permission_classes = [AllowAny]

    def post(self, request):
        logout(request)
        return Response({"detail": "Signed out."})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = MeUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)

    def delete(self, request):
        # Self-service account deletion (mockup's "Delete Account" danger zone).
        # Real and irreversible by design, matching the UI copy — the client is
        # responsible for a confirmation step before calling this.
        user = request.user
        logout(request)
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save()
        update_session_auth_hash(request, request.user)  # keep the session valid
        return Response({"detail": "Password updated."})
