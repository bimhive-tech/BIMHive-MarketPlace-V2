"""Serializers for account registration and the current-user payload."""
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from accounts.models import Profile

User = get_user_model()


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ["company", "job_title", "bio", "avatar_url", "account_type"]


class UserPartnerSerializer(serializers.Serializer):
    """Minimal partner summary attached to /api/auth/me — enough for the frontend
    to know a user's seller-application status without a second round trip.
    `status` is pending/approved/rejected (see catalog.Partner.ApplicationStatus) —
    only "approved" grants real partner-portal access."""

    id = serializers.IntegerField()
    name = serializers.CharField()
    slug = serializers.CharField()
    status = serializers.CharField()
    rejection_note = serializers.CharField()


class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)
    full_name = serializers.SerializerMethodField()
    partner = UserPartnerSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name", "full_name",
            "is_staff", "date_joined", "profile", "partner",
        ]

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Partial update of the editable Profile Information fields (see mockup)."""

    class Meta:
        model = Profile
        fields = ["company", "job_title", "bio"]


class MeUpdateSerializer(serializers.ModelSerializer):
    """PATCH /api/auth/me — updates name/email and the nested profile fields together."""

    profile = ProfileUpdateSerializer(required=False)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "profile"]

    def validate_email(self, value):
        value = value.lower().strip()
        if User.objects.exclude(pk=self.instance.pk).filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def update(self, instance, validated_data):
        profile_data = validated_data.pop("profile", None)
        if "email" in validated_data:
            # username == email is this app's login identity (see RegisterSerializer).
            instance.username = validated_data["email"]
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if profile_data:
            profile, _ = Profile.objects.get_or_create(user=instance)
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()
        return instance


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])

    def validate_current_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    full_name = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ["email", "password", "full_name"]

    def validate_email(self, value):
        value = value.lower().strip()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def create(self, validated_data):
        full_name = validated_data.pop("full_name", "").strip()
        email = validated_data["email"]
        first, _, last = full_name.partition(" ")
        user = User.objects.create_user(
            username=email,  # email is the login identity; username kept for admin
            email=email,
            password=validated_data["password"],
            first_name=first,
            last_name=last,
        )
        Profile.objects.get_or_create(user=user)
        return user
