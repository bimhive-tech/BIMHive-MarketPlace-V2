"""
Staff-only admin API for Users, Roles & Permissions, and Customers.
"""
from django.contrib.auth import get_user_model
from django.db.models import Count
from rest_framework import generics, serializers, viewsets
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Role

User = get_user_model()


class RoleSerializer(serializers.ModelSerializer):
    user_count = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = ["id", "name", "description", "grants_staff_access", "user_count"]

    def get_user_count(self, obj):
        # `get_queryset` below annotates this so the list view is one query
        # total rather than one COUNT per role; fall back for the
        # create/update response, whose instance skips that queryset.
        count = getattr(obj, "user_count", None)
        return count if count is not None else obj.users.count()


class AdminRoleViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
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
            "id", "email", "full_name", "first_name", "last_name", "is_staff", "is_active",
            "date_joined", "role", "role_name", "order_count",
        ]

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["role", "is_active", "is_staff"]

    def update(self, instance, validated_data):
        role = validated_data.get("role", instance.role)
        instance.role = role
        instance.is_active = validated_data.get("is_active", instance.is_active)
        # Staff access follows the assigned role, unless explicitly overridden here.
        instance.is_staff = validated_data.get(
            "is_staff", role.grants_staff_access if role else instance.is_staff
        )
        instance.save(update_fields=["role", "is_active", "is_staff"])
        return instance


class AdminUserListView(generics.ListAPIView):
    """Also used for the Customers admin view (same underlying user list)."""

    permission_classes = [IsAdminUser]
    serializer_class = AdminUserSerializer

    def get_queryset(self):
        qs = User.objects.select_related("role").annotate(order_count=Count("product_purchases"))
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(email__icontains=search)
        return qs.order_by("-date_joined")


class AdminUserUpdateView(generics.UpdateAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = AdminUserUpdateSerializer
    queryset = User.objects.all()

    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        return Response(AdminUserSerializer(self.get_object()).data)


class AdminCustomerStatsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        total = User.objects.count()
        with_orders = User.objects.filter(product_purchases__isnull=False).distinct().count()
        return Response({"total_customers": total, "customers_with_orders": with_orders})
