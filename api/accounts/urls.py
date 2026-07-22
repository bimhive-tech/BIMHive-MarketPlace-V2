"""Auth API routes (mounted under /api/auth/ in config/urls.py)."""
from django.urls import path

from accounts.api import (
    ChangePasswordView,
    CsrfView,
    LoginView,
    LogoutView,
    MeView,
    RegisterView,
)
from accounts.security_api import AccountSessionListView, AccountSessionRevokeView

urlpatterns = [
    path("csrf", CsrfView.as_view(), name="auth-csrf"),
    path("register", RegisterView.as_view(), name="auth-register"),
    path("login", LoginView.as_view(), name="auth-login"),
    path("logout", LogoutView.as_view(), name="auth-logout"),
    path("me", MeView.as_view(), name="auth-me"),
    path("change-password", ChangePasswordView.as_view(), name="auth-change-password"),
    path("sessions", AccountSessionListView.as_view(), name="auth-sessions"),
    path("sessions/<str:session_key>/revoke", AccountSessionRevokeView.as_view(), name="auth-session-revoke"),
]
