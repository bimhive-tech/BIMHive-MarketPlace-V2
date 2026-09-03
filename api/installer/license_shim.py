"""
Wraps every generated installer with LicLoader.dll (see installer/vendor/) —
without this, the real plugin .dll is what Revit loads directly, and
nothing on the customer's machine ever calls /api/license/activate at all.
LicLoader is a small, already-complete Revit add-in shim (source lives
outside this repo, see vendor/README.md): Revit loads it first, it checks
the license online, shows a real "enter your license key" dialog if
needed, and only then loads the real plugin via reflection.

Two things make that work, both handled here:
1. The uploaded .addin manifest's <Assembly>/<FullClassName> get redirected
   to point at the shim instead of the real plugin — see
   rewrite_addin_for_shim().
2. LicLoader needs to find the real plugin file and know what product/API
   it's checking against — it reads two small files it expects sitting
   next to it (see ExternalApp.cs::ParseOnlineLicenseSettings /
   TryLoadRealPlugin) — see build_real_plugin_hint() and
   build_license_config().

Every one of these three files is named per-product (shim_dll_name(),
license_config_filename(), real_plugin_hint_filename() — all take the
product's slug), not a fixed literal like "LicLoader.dll"/"_license.bin".
All BIM Hive plugins for the same Revit year install into the SAME
%APPDATA%\\Autodesk\\Revit\\Addins\\<year>\\ folder — a fixed filename would
mean installing a second plugin overwrites the first one's config (wrong
product license checked, wrong real .dll loaded via reflection) and
uninstalling either one deletes files the other still needs. LicLoader.dll
itself (2026-08-20, see ExternalApp.cs::GetSiblingConfigPath) derives which
config filenames to read from its OWN on-disk filename, so a plain
"LicLoader.dll" (no suffix) still falls back to the original unsuffixed
names for backward compatibility with copies installed before this fix.

**2026-09-03: a distinct filename alone turned out not to be enough.** A
.NET assembly's identity (Name/Version/Culture/PublicKeyToken) is embedded
in its own compiled metadata, completely independent of what the file on
disk is named — and every per-product copy of LicLoader.dll is a byte-for-
byte copy of the exact same compiled build, so they all share the identity
"LicLoader, Version=1.0.0.0". With two or more BIM Hive plugins installed
at once, .NET's assembly loader treats every one of those copies as the
SAME assembly the moment Revit loads the second one — reusing the first
one's already-loaded copy instead of loading the new file — which makes
GetSiblingConfigPath's filename-sniffing (and every static field in
ExternalApp.cs) resolve to whichever plugin loaded *first*, for every
plugin. Confirmed as the actual cause of "only one plugin ever shows up in
the ribbon" when 2+ are installed. Fixed by giving each staged copy a
genuinely distinct assembly identity, not just a distinct filename — see
stage_renamed_shim() below and installer/vendor/README.md.
"""
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from django.conf import settings

VENDOR_DIR = Path(__file__).resolve().parent / "vendor"
SHIM_DLL_PATH = VENDOR_DIR / "LicLoader.dll"
SHIM_FULL_CLASS_NAME = "LicLoader.ExternalApp"


def shim_dll_name(slug: str) -> str:
    return f"LicLoader.{slug}.dll"


def shim_assembly_name(slug: str) -> str:
    """The per-product .NET assembly identity a staged shim copy gets
    rewritten to (see stage_renamed_shim) — deliberately not just
    shim_dll_name()'s filename, which AssemblyRenamer's own validation (and
    .NET assembly-name rules generally) wouldn't accept as-is: a slug can
    contain hyphens, this can't."""
    return "LicLoader_" + re.sub(r"[^A-Za-z0-9_]", "_", slug or "plugin")


class ShimRenameError(Exception):
    """Raised when giving a staged shim copy its own assembly identity
    fails — the caller must treat this as a build failure exactly like
    AddinRewriteError, never fall back to shipping a copy that still shares
    its identity with every other installed BIM Hive plugin."""


def stage_renamed_shim(dest_path: Path, slug: str) -> None:
    """Copies SHIM_DLL_PATH to dest_path, then rewrites *that copy's* own
    .NET assembly identity to shim_assembly_name(slug) via the vendored
    AssemblyRenamer tool (installer/vendor/assembly_renamer/) — see this
    module's docstring for why a merely-renamed file isn't enough on its
    own to stop multiple installed plugins' shims colliding at runtime."""
    args = [
        settings.DOTNET_EXECUTABLE,
        settings.ASSEMBLY_RENAMER_DLL,
        str(SHIM_DLL_PATH),
        shim_assembly_name(slug),
        str(dest_path),
    ]
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=30)
    except FileNotFoundError as exc:
        raise ShimRenameError(
            f"dotnet runtime not found ({settings.DOTNET_EXECUTABLE!r}) — needed to give this "
            f"product's license shim its own identity. ({exc})"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise ShimRenameError("Rewriting the license shim's identity took too long and was aborted.") from exc

    if result.returncode != 0 or not dest_path.exists():
        raise ShimRenameError(f"Could not give the license shim its own identity: {result.stderr.strip()}")


def license_config_filename(slug: str) -> str:
    return f"_license.{slug}.bin"


def real_plugin_hint_filename(slug: str) -> str:
    return f"_real_plugin.{slug}.txt"


class AddinRewriteError(Exception):
    """Raised when an uploaded .addin can't be safely redirected to the
    shim — the caller must treat this as a build failure, never fall back
    to shipping the real plugin unwrapped."""


def rewrite_addin_for_shim(addin_xml_bytes: bytes, assembly_name: str) -> bytes:
    """Redirects every <AddIn> entry in a Revit .addin manifest to load
    the shim (under its per-product filename, see module docstring)
    instead of the real plugin. Deliberately fails loudly
    (AddinRewriteError) on anything that doesn't parse as a normal Revit
    add-in manifest, rather than silently shipping an unwrapped installer —
    that failure mode is exactly the bug this module exists to prevent."""
    try:
        root = ET.fromstring(addin_xml_bytes)
    except ET.ParseError as exc:
        raise AddinRewriteError(f"Could not parse the .addin file as XML: {exc}") from exc

    addins = root.findall("AddIn")
    if not addins:
        raise AddinRewriteError("The .addin file has no <AddIn> element to redirect.")

    for addin in addins:
        assembly = addin.find("Assembly")
        if assembly is None:
            assembly = ET.SubElement(addin, "Assembly")
        assembly.text = assembly_name

        full_class_name = addin.find("FullClassName")
        if full_class_name is None:
            full_class_name = ET.SubElement(addin, "FullClassName")
        full_class_name.text = SHIM_FULL_CLASS_NAME

    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def build_real_plugin_hint(real_plugin_filename: str) -> bytes:
    """LicLoader reads this file (_real_plugin.txt, plain text, no
    trailing newline needed) to know which sibling .dll is the actual
    plugin to load via reflection once the license check passes."""
    return real_plugin_filename.strip().encode("utf-8")


def build_license_config(build) -> bytes:
    """The _license.bin LicLoader reads on startup — plain UTF-8 JSON
    despite the ".bin" name (see ExternalApp.cs::ParseOnlineLicenseSettings,
    which looks for an "onlineLicense" object with these exact keys).

    trialMinutes carries the full days+hours+minutes total; trialDays is
    left at 0 so the shim's own fallback (`TrialMinutes > 0 ? TrialMinutes :
    TrialDays * 1440`) always prefers the precise value. This is display-only
    now (LicLoader's DescribeConfiguredTrialLength(), used to say "Your
    {N}-day trial has ended" by name) — the server no longer reads a
    client-requested trial length at all (see licensing/api_views.py: a key
    is always required to activate, trial or paid; the actual trial length
    lives on the ProductPurchase created at trial-download time, see
    licensing/account_api.py::AccountPluginBuildTrialDownloadView)."""
    config = {
        "onlineLicense": {
            "enabled": True,
            "apiUrl": f"{settings.SITE_URL}/api/license/activate",
            "productCode": build.product.product_code,
            "trialDays": 0,
            "trialMinutes": build.product.trial_minutes_total,
        }
    }
    return json.dumps(config).encode("utf-8")
