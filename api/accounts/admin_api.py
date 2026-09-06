"""
Staff-only admin API for Users, Roles & Permissions, and Customers.

Users and Roles & Permissions are Admin-only (IsSuperAdmin) — a Staff account
must never be able to touch either, since that's exactly how Staff could
otherwise affect Admin or other staff accounts. Customers is a separate,
read-only, granular-permission-gated view (AdminCustomerListView below) — see
its docstring for why it isn't just AdminUserListView reused.
"""
from django.contrib.auth import get_user_model
from django.db.models import Count
from rest_framework import generics, serializers, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Role
from accounts.permissions import ADMIN_PERMISSION_KEYS, HasAdminPermission, IsSuperAdmin

User = get_user_model()


class RoleSerializer(serializers.ModelSerializer):
    user_count = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = ["id", "name", "description", "grants_staff_access", "permissions", "user_count"]

    def get_user_count(self, obj):
        # `get_queryset` below annotates this so the list view is one query
        # total rather than one COUNT per role; fall back for the
        # create/update response, whose instance skips that queryset.
        count = getattr(obj, "user_count", None)
        return count if count is not None else obj.users.count()

    def validate_permissions(self, value):
        unknown = set(value) - ADMIN_PERMISSION_KEYS
        if unknown:
            raise serializers.ValidationError(f"Unknown permission(s): {', '.join(sorted(unknown))}")
        return value


class AdminRoleViewSet(viewsets.ModelViewSet):
    permission_classes = [IsSuperAdmin]
    serializer_class = RoleSerializer

    def get_queryset(self):
        return Role.objects.annotate(user_count=Count("users", distinct=True))


class AdminUserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    role_name = serializers.CharField(source="role.name", read_only=True, default="")
    order_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = User
        fields = [
            "id", "email", "full_name", "first_name", "last_name", "is_staff", "is_superuser",
            "is_active", "date_joined", "role", "role_name", "order_count",
        ]

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["role", "is_active", "is_staff", "is_superuser"]

    def validate(self, attrs):
        # is_superuser is the Admin tier — never role-derived, always an explicit,
        # deliberate toggle (unlike is_staff, which can follow the assigned role
        # below). Guard against locking everyone out of Users/Roles/Settings by
        # demoting the last remaining Admin.
        demoting_superuser = "is_superuser" in attrs and not attrs["is_superuser"] and self.instance.is_superuser
        if demoting_superuser and not User.objects.filter(is_superuser=True).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError({"is_superuser": "At least one Admin must remain."})
        return attrs

    def update(self, instance, validated_data):
        role = validated_data.get("role", instance.role)
        instance.role = role
        instance.is_active = validated_data.get("is_active", instance.is_active)
        # Staff access follows the assigned role, unless explicitly overridden here.
        instance.is_staff = validated_data.get(
            "is_staff", role.grants_staff_access if role else instance.is_staff
        )
        instance.is_superuser = validated_data.get("is_superuser", instance.is_superuser)
        instance.save(update_fields=["role", "is_active", "is_staff", "is_superuser"])
        return instance


class AdminUserListView(generics.ListAPIView):
    permission_classes = [IsSuperAdmin]
    serializer_class = AdminUserSerializer

    def get_queryset(self):
        qs = User.objects.select_related("role").annotate(order_count=Count("product_purchases"))
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(email__icontains=search)
        return qs.order_by("-date_joined")


class AdminUserUpdateView(generics.UpdateAPIView):
    permission_classes = [IsSuperAdmin]
    serializer_class = AdminUserUpdateSerializer
    queryset = User.objects.all()

    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        return Response(AdminUserSerializer(self.get_object()).data)


class AdminCustomerSerializer(serializers.ModelSerializer):
    """Deliberately narrower than AdminUserSerializer — no is_staff/role, so
    granting `customers.view` to Staff can never expose or imply account-
    administration capability. is_active is still shown (account status is
    useful for support) but this view has no write endpoint to change it."""

    full_name = serializers.SerializerMethodField()
    order_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = User
        fields = ["id", "email", "full_name", "is_active", "date_joined", "order_count"]

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class AdminCustomerListView(generics.ListAPIView):
    """Read-only customer browsing for support/sales — genuinely separate from
    AdminUserListView (Users), not just a second URL for the same view: a Staff
    member granted `customers.view` must never gain the ability to see or edit
    is_staff/role, which AdminUserListView/AdminUserUpdateView carry and are
    Admin-only. Staff/admin accounts themselves aren't "customers", so they're
    excluded from this list."""

    permission_classes = [HasAdminPermission]
    required_permission = "customers.view"
    serializer_class = AdminCustomerSerializer

    def get_queryset(self):
        qs = User.objects.filter(is_staff=False).annotate(order_count=Count("product_purchases"))
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(email__icontains=search)
        return qs.order_by("-date_joined")


class AdminCustomerStatsView(APIView):
    permission_classes = [HasAdminPermission]
    required_permission = "customers.view"

    def get(self, request):
        customers = User.objects.filter(is_staff=False)
        total = customers.count()
        with_orders = customers.filter(product_purchases__isnull=False).distinct().count()
        return Response({"total_customers": total, "customers_with_orders": with_orders})
