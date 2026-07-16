"""Permission classes for the shared staff+partner product management API.

`IsStaffOrPartner`/`IsApprovedPartner` are deliberately narrow — used only on
the product/file/media/sales endpoints in admin_api.py and partner_api.py.
Every other admin endpoint (Orders, Customers, Licenses, Users, Roles,
Categories, Tags, Collections, Reviews, Activity, System Status) keeps the
plain `IsAdminUser` it already had; partner-linked users must never reach
those.
"""
from rest_framework.permissions import BasePermission


def _is_approved_partner(user) -> bool:
    return bool(
        user.partner_id is not None
        and getattr(user.partner, "status", None) == user.partner.ApplicationStatus.APPROVED
    )


class IsStaffOrPartner(BasePermission):
    """Staff (BIMHive admins) or an APPROVED partner (self-service product
    management) — a pending or rejected seller application has no product
    access yet. Views using this must scope their queryset to the caller's
    own partner when the caller isn't staff — this class only gates entry."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_staff or _is_approved_partner(user)))


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
