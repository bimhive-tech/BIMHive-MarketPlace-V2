"""
Account models. A custom User (set from day one so we never have to swap it later)
plus a Profile for storefront-facing details shown on the account pages.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from django_countries.fields import CountryField


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
        help_text="Set when this account submits a seller application — see catalog.Partner.status "
        "for whether they actually have partner-portal access yet.",
    )

    def __str__(self):
        return self.get_full_name() or self.username


class Profession(models.TextChoices):
    """The AEC roles collected at signup — a fixed, curated list (not a free-text
    field) so it's actually usable for segmentation/reporting later, the same
    reason catalog.ProductType is a choices field rather than free text."""

    ARCHITECT = "architect", "Architect"
    STRUCTURAL_ENGINEER = "structural_engineer", "Structural Engineer"
    MEP_ENGINEER = "mep_engineer", "MEP Engineer"
    CIVIL_ENGINEER = "civil_engineer", "Civil Engineer"
    BIM_MANAGER = "bim_manager", "BIM Manager"
    BIM_COORDINATOR = "bim_coordinator", "BIM Coordinator"
    BIM_MODELER = "bim_modeler", "BIM Modeler / Technician"
    CONTRACTOR = "contractor", "Contractor"
    PROJECT_MANAGER = "project_manager", "Project Manager"
    INTERIOR_DESIGNER = "interior_designer", "Interior Designer"
    CONSTRUCTION_MANAGER = "construction_manager", "Construction Manager"
    ESTIMATOR = "estimator", "Estimator"
    EDUCATOR = "educator", "Educator / Trainer"
    STUDENT = "student", "Student"
    OTHER = "other", "Other"


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
    profession = models.CharField(max_length=30, choices=Profession.choices, blank=True)
    # ISO 3166-1 alpha-2 (e.g. "US", "EG"). Collected at signup for regional
    # pricing (not yet built) — nothing downstream reads this today besides
    # display, but it's the field that pricing work will key off later.
    country = CountryField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Profile<{self.user}>"
