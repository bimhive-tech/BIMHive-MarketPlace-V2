"""
Account models. A custom User (set from day one so we never have to swap it later)
plus a Profile for storefront-facing details shown on the account pages.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.Model):
    """A named permission grant (Admin settings > Roles & Permissions)."""

    name = models.CharField(max_length=60, unique=True)
    description = models.CharField(max_length=200, blank=True)
    grants_staff_access = models.BooleanField(
        default=False, help_text="Users with this role can sign in to the admin portal."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class User(AbstractUser):
    """Email is the primary contact; username stays for admin compatibility."""

    email = models.EmailField(unique=True)
    role = models.ForeignKey(
        Role, on_delete=models.SET_NULL, null=True, blank=True, related_name="users"
    )
    partner = models.ForeignKey(
        "catalog.Partner",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="team_members",
        help_text="Set for partner self-service logins — grants access to the partner portal.",
    )
    must_change_password = models.BooleanField(
        default=False, help_text="Forces a password change on next login (set when an admin issues a password)."
    )

    def __str__(self):
        return self.get_full_name() or self.username


class Profile(models.Model):
    """Extra, optional details surfaced on the account Profile page (see mockups)."""

    class AccountType(models.TextChoices):
        INDIVIDUAL = "individual", "Individual"
        TEAM = "team", "Team"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    company = models.CharField(max_length=140, blank=True)
    job_title = models.CharField(max_length=140, blank=True)
    bio = models.TextField(max_length=200, blank=True)
    avatar_url = models.URLField(blank=True)
    account_type = models.CharField(
        max_length=20, choices=AccountType.choices, default=AccountType.INDIVIDUAL
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Profile<{self.user}>"
