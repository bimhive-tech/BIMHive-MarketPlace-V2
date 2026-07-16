"""Permission classes for the shared staff+partner product management API.

`IsStaffOrPartner` is deliberately narrow — used only on the product/file/media
endpoints in admin_api.py. Every other admin endpoint (Orders, Customers,
Licenses, Users, Roles, Categories, Tags, Collections, Reviews, Activity,
System Status) keeps the plain `IsAdminUser` it already had; partner-linked
users must never reach those.
"""
from rest_framework.permissions import BasePermission


class IsStaffOrPartner(BasePermission):
    """Staff (BIMHive admins) or a partner-linked user (self-service product
    management). Views using this must scope their queryset to the caller's
    own partner when the caller isn't staff — this class only gates entry."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_staff or user.partner_id is not None))


class IsPartnerUser(BasePermission):
    """A partner-linked user only — used for the partner's own profile endpoint,
    which staff have no equivalent "own partner" record to hit."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.partner_id is not None)
