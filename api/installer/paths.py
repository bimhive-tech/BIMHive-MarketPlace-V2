"""
Destination-path resolution for files bundled into an auto-generated plugin
installer. A partner/admin choosing where a dependency lands on the
customer's machine picks one of two roots (see DESTINATION_TOKENS) rather
than typing a raw filesystem path, so the value stays portable across every
customer's PC regardless of username or drive letter.
"""
import re

ADDIN_DIR_TOKEN = "{ADDIN_DIR}"
INSTALL_DIR_TOKEN = "{INSTALL_DIR}"

# Keyed by the literal token a partner types into the destination field.
# `scope` decides the MSI's overall install scope (see wix_builder.py) — a
# build that places anything under INSTALL_DIR becomes a per-machine
# (admin-elevated) installer; one that only ever touches ADDIN_DIR stays
# per-user, matching the legacy generator's default (no install prompt).
DESTINATION_TOKENS = {
    ADDIN_DIR_TOKEN: {
        "scope": "perUser",
        "label": "Revit Add-ins folder (per-user, no admin prompt)",
        "hint": (
            r"Lands in %APPDATA%\Autodesk\Revit\Addins\<year>\ on the customer's PC — "
            r"e.g. C:\Users\<name>\AppData\Roaming\Autodesk\Revit\Addins\2025\. "
            r"Use this for small files that ship alongside the .addin manifest."
        ),
    },
    INSTALL_DIR_TOKEN: {
        "scope": "perMachine",
        "label": "Program Files (machine-wide, installer asks for admin)",
        "hint": (
            r"Lands in %ProgramFiles%\BIMHive\<Plugin Name>\ on the customer's PC — "
            r"e.g. C:\Program Files\BIMHive\My Plugin\. Use this for larger shared "
            r"dependencies; the installer will prompt for administrator approval."
        ),
    },
}

_SEGMENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._-]*$")


class InvalidDestinationPath(ValueError):
    pass


def parse_destination_path(raw: str) -> tuple[str, list[str]]:
    """Validates and splits a `{TOKEN}\\sub\\path` string into (token, segments).

    Rejects traversal, drive letters, and anything outside the two recognised
    roots — this value is later used as a literal filesystem path on every
    customer's machine, so it's treated as untrusted input, not a trusted
    admin-only convenience field."""
    raw = (raw or "").strip()
    for token in DESTINATION_TOKENS:
        if raw == token or raw.startswith(token + "\\") or raw.startswith(token + "/"):
            rest = raw[len(token) :].strip("\\/")
            if not rest:
                return token, []
            segments = [seg for seg in re.split(r"[\\/]+", rest) if seg]
            for seg in segments:
                if seg in (".", "..") or not _SEGMENT_RE.match(seg):
                    raise InvalidDestinationPath(
                        f"'{seg}' isn't a valid path segment. Use letters, numbers, spaces, "
                        "dots, dashes, or underscores only — no '..' and no drive letters."
                    )
            return token, segments
    valid = " or ".join(DESTINATION_TOKENS)
    raise InvalidDestinationPath(f"Path must start with {valid}.")


def scope_for_token(token: str) -> str:
    return DESTINATION_TOKENS[token]["scope"]
