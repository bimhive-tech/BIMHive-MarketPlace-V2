"""Permission classes for the partner (external seller) side of the shared
product-management API.

`IsApprovedPartner` gates entry for a partner's own product/build/sales
endpoints (partner_api.py) — no staff branch, since staff have their own
granular check. The staff side of that same shared surface (product/file/
media/plugin-build endpoints in catalog/admin_api.py and installer/api.py)
composes accounts.permissions.HasAdminPermission with IsApprovedPartner
(`IsApprovedPartner | (IsAuthenticated & HasAdminPermission)`) — replacing the
old blanket "any is_staff" grant with a specific granular permission. Users,
Roles & Permissions, and Settings use accounts.permissions.IsSuperAdmin;
partner-linked users must never reach those either way.
"""
from rest_framework.permissions import BasePermission


def _is_approved_partner(user) -> bool:
    return bool(
        user.partner_id is not None
        and getattr(user.partner, "status", None) == user.partner.ApplicationStatus.APPROVED
    )


class IsPartnerUser(BasePermission):
    """A partner-linked user, REGARDLESS of application status — used only for
    the partner's own profile endpoint, so a pending/rejected applicant can
    still see their status and fix their company name/logo. Staff have no
    equivalent "own partner" record to hit here."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.partner_id is not None)


class IsApprovedPartner(BasePermission):
    """An approved partner only, no staff branch — used for partner-only views
    like Sales, where staff already have their own equivalent (the admin
    Orders page) and don't need this one."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and _is_approved_partner(user))
