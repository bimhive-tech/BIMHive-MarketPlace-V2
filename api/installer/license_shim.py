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
   to point at LicLoader instead of the real plugin — see
   rewrite_addin_for_shim().
2. LicLoader needs to find the real plugin file and know what product/API
   it's checking against — it reads two small files it expects sitting
   next to it: _real_plugin.txt (the real plugin's filename) and
   _license.bin (a plain JSON config, despite the name — see
   ExternalApp.cs::ParseOnlineLicenseSettings) — see build_real_plugin_hint()
   and build_license_config().
"""
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from django.conf import settings

VENDOR_DIR = Path(__file__).resolve().parent / "vendor"
SHIM_DLL_PATH = VENDOR_DIR / "LicLoader.dll"
SHIM_DLL_NAME = "LicLoader.dll"
SHIM_ASSEMBLY_NAME = "LicLoader.dll"
SHIM_FULL_CLASS_NAME = "LicLoader.ExternalApp"


class AddinRewriteError(Exception):
    """Raised when an uploaded .addin can't be safely redirected to the
    shim — the caller must treat this as a build failure, never fall back
    to shipping the real plugin unwrapped."""


def rewrite_addin_for_shim(addin_xml_bytes: bytes) -> bytes:
    """Redirects every <AddIn> entry in a Revit .addin manifest to load
    LicLoader instead of the real plugin. Deliberately fails loudly
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
        assembly.text = SHIM_ASSEMBLY_NAME

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
    TrialDays * 1440`) always prefers the precise value. Either way this is
    only what the client *requests* — the server clamps to its own
    configured max regardless (see api_views.py's trial clamp), so this
    can't be tampered with to extend a trial."""
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
