"""Serializers for account registration and the current-user payload."""
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django_countries import countries
from rest_framework import serializers

from accounts.models import Profession, Profile

User = get_user_model()

_VALID_COUNTRY_CODES = {code for code, _ in countries}


def _validate_country_code(value):
    """Shared by every serializer that accepts a country: normalizes to the
    ISO 3166-1 alpha-2 code CountryField stores, and rejects anything that
    isn't a real one — a signup-options-driven <select> should never send a
    bad code, but this is the last line of defense before it's persisted."""
    value = (value or "").strip().upper()
    if value and value not in _VALID_COUNTRY_CODES:
        raise serializers.ValidationError("Not a recognized country.")
    return value


class ProfileSerializer(serializers.ModelSerializer):
    profession_label = serializers.CharField(source="get_profession_display", read_only=True)
    # Declared explicitly rather than left to ModelSerializer's auto-build: a
    # CountryField carries django_countries' own `choices`, so an auto-built
    # field here would be a ChoiceField — and DRF's ChoiceField.to_representation
    # has a blank-value special case ("if value in ('', None): return value")
    # that, for a blank CountryField, returns the raw Country object instead of
    # a string (Country('') == '' is true, but str() is never called on the
    # branch that matches it) — every response serializing a Profile with no
    # country set 500s on json.dumps(). A plain CharField sidesteps the whole
    # branch and always renders the code string.
    country = serializers.CharField(read_only=True)
    country_name = serializers.CharField(source="country.name", read_only=True)

    class Meta:
        model = Profile
        fields = [
            "company", "job_title", "bio", "avatar_url", "account_type",
            "profession", "profession_label", "country", "country_name",
        ]


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

    # Declared explicitly rather than left to ModelSerializer's auto-build:
    # CountryField carries django_countries' own `choices` (exact-case ISO
    # codes only), which would build a ChoiceField that rejects "de" before
    # validate_country ever runs to normalize it to "DE".
    country = serializers.CharField(required=False, allow_blank=True, max_length=2)

    class Meta:
        model = Profile
        fields = ["company", "job_title", "bio", "profession", "country"]

    def validate_country(self, value):
        return _validate_country_code(value)


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
    # Profession is a nice-to-have for segmentation, so it stays optional —
    # country is required: it's what regional pricing will key off, and an
    # account with no country recorded would need a costly later backfill to
    # ever price correctly.
    profession = serializers.ChoiceField(
        choices=Profession.choices, write_only=True, required=False, allow_blank=True
    )
    country = serializers.CharField(write_only=True, required=True, max_length=2)

    class Meta:
        model = User
        fields = ["email", "password", "full_name", "profession", "country"]

    def validate_email(self, value):
        value = value.lower().strip()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate_country(self, value):
        value = _validate_country_code(value)
        if not value:
            raise serializers.ValidationError("Select your country.")
        return value

    def create(self, validated_data):
        full_name = validated_data.pop("full_name", "").strip()
        profession = validated_data.pop("profession", "")
        country = validated_data.pop("country")
        email = validated_data["email"]
        first, _, last = full_name.partition(" ")
        user = User.objects.create_user(
            username=email,  # email is the login identity; username kept for admin
            email=email,
            password=validated_data["password"],
            first_name=first,
            last_name=last,
        )
        Profile.objects.get_or_create(user=user, defaults={"profession": profession, "country": country})
        return user
