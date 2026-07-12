"""
Account models. A custom User (set from day one so we never have to swap it later)
plus a Profile for storefront-facing details shown on the account pages.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Email is the primary contact; username stays for admin compatibility."""

    email = models.EmailField(unique=True)

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
