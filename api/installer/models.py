"""
Auto-generated plugin installer pipeline. A partner/admin uploads raw build
artifacts (compiled .dll, .addin manifest, optional resources/dependencies)
once per (product, Revit year); the backend packages them into a real WiX
.msi (see wix_builder.py) instead of a human running the legacy
InstallerGenerator GUI. See installer-generator-reference project notes for
the full design rationale.
"""
import uuid

from django.core.exceptions import ValidationError
from django.db import models

from catalog.models import Product
from installer.paths import InvalidDestinationPath, parse_destination_path


class PluginBuild(models.Model):
    """One buildable installer target: a single (product, Revit year) pair —
    purely a container for the raw uploaded inputs (dll, addin, resources).
    There is deliberately no cached/persisted .msi here: the installer is
    generated on demand, live, at the moment someone actually needs the file
    (a customer downloading, or staff/partner testing from the products
    list) — see installer/builder.py::generate_installer_bytes. Nothing
    about the result is stored ahead of time."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="plugin_builds")
    revit_year = models.CharField(max_length=16)
    plugin_version = models.CharField(max_length=30, default="1.0.0")

    dll_storage_key = models.CharField(max_length=400, blank=True)
    dll_filename = models.CharField(max_length=255, blank=True)
    addin_storage_key = models.CharField(max_length=400, blank=True)
    addin_filename = models.CharField(max_length=255, blank=True)

    # Persisted once and reused on every generation. Windows Installer needs
    # a STABLE UpgradeCode across versions of the same (product, Revit year)
    # to detect upgrades — a fresh GUID every time (the legacy generator's
    # bug) makes every install an unrelated side-by-side copy instead of a
    # clean upgrade.
    upgrade_code = models.UUIDField(default=uuid.uuid4, editable=False)
    # "perUser" | "perMachine" — derived purely from resource destinations
    # (see wix_generator.resolve_scope) and kept in sync whenever a resource
    # is added/removed (installer/api.py), so the admin UI reflects it
    # without ever needing to actually generate an installer first.
    scope = models.CharField(max_length=16, default="perUser")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product", "revit_year"], name="unique_plugin_build_per_product_year"
            )
        ]
        ordering = ["revit_year"]

    def __str__(self):
        return f"{self.product.name} [{self.revit_year}]"

    @property
    def is_ready_for_build(self) -> bool:
        return bool(self.dll_storage_key and self.addin_storage_key)


class PluginResourceFile(models.Model):
    """An extra file bundled into the installer alongside the main dll/addin —
    an icon, a config file, or a dependency DLL — placed wherever
    `destination_path` says on the customer's machine."""

    class Kind(models.TextChoices):
        RESOURCE = "resource", "Resource"
        DEPENDENCY = "dependency", "Dependency"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    build = models.ForeignKey(PluginBuild, on_delete=models.CASCADE, related_name="resource_files")
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.RESOURCE)
    storage_key = models.CharField(max_length=400)
    original_filename = models.CharField(max_length=255)
    destination_path = models.CharField(
        max_length=400,
        help_text=r"e.g. {ADDIN_DIR}\MyPlugin\config.json or {INSTALL_DIR}\lib\dependency.dll",
    )
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "original_filename"]

    def __str__(self):
        return f"{self.original_filename} -> {self.destination_path}"

    def clean(self):
        try:
            parse_destination_path(self.destination_path)
        except InvalidDestinationPath as exc:
            raise ValidationError({"destination_path": str(exc)}) from exc
