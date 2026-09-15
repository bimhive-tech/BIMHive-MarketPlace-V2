"""Admin-portal permission classes.

Admin (`is_superuser=True`) has full, unrestricted access and bypasses all
granular checks below. Staff (`is_staff=True, is_superuser=False`) is scoped
by `request.user.role.permissions` — a list of keys from ADMIN_PERMISSION_KEYS.

Users, Roles & Permissions, and Settings are gated by `IsSuperAdmin` only —
never assignable via a Role, never in ADMIN_PERMISSIONS below. That absence is
what keeps Staff from ever affecting Admin or other staff/admin accounts.
"""
from rest_framework.permissions import BasePermission

# (key, sidebar group) — grouped to match web/features/admin/AdminShell/AdminSidebar.tsx
# so the Roles & Permissions checklist mirrors the sidebar exactly. Deliberately
# excludes Users, Roles & Permissions, and Settings (General/Payments) — see module
# docstring. Support Tickets/Knowledge Base have no backing admin API yet.
ADMIN_PERMISSIONS = [
    ("dashboard.view", "Overview"),
    ("activity.view", "Overview"),
    ("orders.manage", "Overview"),
    ("customers.view", "Overview"),
    ("reviews.moderate", "Overview"),
    ("licenses.manage", "Overview"),
    ("memberships.manage", "Overview"),
    ("products.manage", "Products & Content"),
    ("promotions.manage", "Products & Content"),
    ("membership_plans.manage", "Products & Content"),
    ("categories.manage", "Products & Content"),
    ("tags.manage", "Products & Content"),
    ("partners.manage", "Products & Content"),
]
ADMIN_PERMISSION_KEYS = {key for key, _group in ADMIN_PERMISSIONS}


class IsSuperAdmin(BasePermission):
    """Real Admin only. Use on Users, Roles & Permissions, and Settings — never
    grant equivalent access via Role.permissions."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)


class HasAdminPermission(BasePermission):
    """Staff (or Admin) with a specific granular permission. Set
    `required_permission` — a key from ADMIN_PERMISSION_KEYS — as a class
    attribute on the view."""

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and user.is_staff):
            return False
        if user.is_superuser:
            return True
        required = getattr(view, "required_permission", None)
        return bool(required and user.role_id and required in (user.role.permissions or []))
