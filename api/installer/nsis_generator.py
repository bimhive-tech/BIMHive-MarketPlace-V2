"""
NSIS (.nsi) installer script generation — replaces the earlier WiX/.wxs
pipeline. WiX v5 turned out not to actually work on Linux: it prints
`warning WIX0000: The WiX Toolset only supports Windows ... All behavior
after this point is undefined` and then fails to compile even the most
ordinary `<Directory Name="...">` elements. NSIS's compiler (`makensis`)
is a real, long-supported Linux-hosted cross-compiler for Windows
installers (Debian/Ubuntu ship it as the `nsis` package), so this produces
the exact same install layout the WiX version did — fixed files always in
%APPDATA%\\Autodesk\\Revit\\Addins\\<year>\\, extra per-machine resources in
%ProgramFiles%\\<manufacturer>\\<product>\\ — through a toolchain that
actually runs where this app is deployed.
"""
from django.conf import settings

from installer.paths import INSTALL_DIR_TOKEN, parse_destination_path

OUTPUT_FILENAME = "installer.exe"


def resolve_scope(resource_files) -> str:
    """Per-user (AppData only, no install prompt) unless something targets
    Program Files, in which case the whole package must run elevated —
    NSIS's execution level, like MSI's install scope, is a package-level
    setting, not something that can be mixed section-by-section."""
    for resource in resource_files:
        token, _ = parse_destination_path(resource.destination_path)
        if token == INSTALL_DIR_TOKEN:
            return "perMachine"
    return "perUser"


def _nsis_str(value: str) -> str:
    """Escapes a value for safe interpolation inside a double-quoted NSIS
    string literal. NSIS has no XML-style attribute quoting — the only
    character that can break out of a "..." literal is an unescaped '"',
    written back as $\\" ."""
    return value.replace('"', '$\\"')


def _version_quad(raw: str) -> str:
    """VIProductVersion requires exactly four numeric dot-separated parts.
    Partner-supplied version strings are free text (could be "2.5", "beta",
    anything), so this is a best-effort mapping with a safe fallback rather
    than something that can fail the build over cosmetic exe metadata."""
    parts = [p for p in raw.split(".") if p.isdigit()][:4]
    parts += ["0"] * (4 - len(parts))
    return ".".join(parts)


def _dest_dir(root: str, folder_segments: list[str]) -> str:
    return "\\".join([root, *folder_segments]) if folder_segments else root


def generate_nsis_script(build, resource_files) -> tuple[str, list[str]]:
    """Returns (nsi_script_source, list_of_staging_relative_payload_paths)
    — the caller stages files at those relative paths (forward slashes,
    resolved from the staging dir) before invoking `makensis`.

    Every value that can contain arbitrary partner input (product name,
    plugin version) goes through _nsis_str() before landing inside a
    quoted literal, the NSIS equivalent of the WiX generator's quoteattr()
    discipline — never a bare f-string straight into a "..." literal."""
    scope = resolve_scope(resource_files)
    plugin_name = build.product.name
    manufacturer = settings.INSTALLER_MANUFACTURER
    version = build.plugin_version or "1.0.0"
    revit_year = build.revit_year
    slug = build.product.slug or "plugin"
    upgrade_key = str(build.upgrade_code)

    addin_dir = f"$APPDATA\\Autodesk\\Revit\\Addins\\{revit_year}"
    install_dir = f"$PROGRAMFILES64\\{manufacturer}\\{plugin_name}"

    payload_paths: list[str] = []

    addin_source = f"payload\\{build.addin_filename}"
    dll_source = f"payload\\{build.dll_filename}"
    payload_paths.append(f"payload/{build.addin_filename}")
    payload_paths.append(f"payload/{build.dll_filename}")

    install_lines = [
        f'SetOutPath "{addin_dir}"',
        f'File "{addin_source}"',
        f'File "{dll_source}"',
    ]
    uninstall_dirs = [addin_dir]

    for index, resource in enumerate(resource_files):
        token, segments = parse_destination_path(resource.destination_path)
        root = install_dir if token == INSTALL_DIR_TOKEN else addin_dir
        folder_segments = segments[:-1]
        filename = segments[-1] if segments else resource.original_filename
        dest_dir = _dest_dir(root, folder_segments)
        source_rel = f"payload/resources/{index}_{resource.original_filename}"
        payload_paths.append(source_rel)
        install_lines.append(f'SetOutPath "{dest_dir}"')
        install_lines.append(f'File "/oname={_nsis_str(filename)}" "{source_rel.replace("/", chr(92))}"')
        if dest_dir not in uninstall_dirs:
            uninstall_dirs.append(dest_dir)

    if scope == "perMachine" and install_dir not in uninstall_dirs:
        uninstall_dirs.append(install_dir)

    uninstall_lines = ["RMDir /r /REBOOTOK \"" + d + "\"" for d in uninstall_dirs if d != addin_dir]
    # The addin dir holds the uninstaller itself while it's running, so it's
    # removed last via the delayed-delete idiom (Uninstall.exe can't delete
    # its own containing files mid-execution on Windows).
    uninstall_lines.append(f'Delete "{addin_dir}\\{build.dll_filename}"')
    uninstall_lines.append(f'Delete "{addin_dir}\\{build.addin_filename}"')
    uninstall_lines.append('Delete "$INSTDIR\\Uninstall.exe"')
    uninstall_lines.append('RMDir "$INSTDIR"')

    uninstall_key = (
        f'Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{{{upgrade_key}}}'
    )
    registry_root = "HKCU" if scope == "perUser" else "HKLM"

    execution_level = "user" if scope == "perUser" else "admin"

    script = f"""\
!include "MUI2.nsh"

Name "{_nsis_str(plugin_name)}"
OutFile "{OUTPUT_FILENAME}"
InstallDir "{addin_dir}"
RequestExecutionLevel {execution_level}

VIProductVersion "{_version_quad(version)}"
VIAddVersionKey "ProductName" "{_nsis_str(plugin_name)}"
VIAddVersionKey "CompanyName" "{_nsis_str(manufacturer)}"
VIAddVersionKey "FileVersion" "{_nsis_str(version)}"
VIAddVersionKey "ProductVersion" "{_nsis_str(version)}"

!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_BITMAP "branding\\Header.bmp"
!define MUI_WELCOMEFINISHPAGE_BITMAP "branding\\Welcome.bmp"
!define MUI_UNWELCOMEFINISHPAGE_BITMAP "branding\\Welcome.bmp"
!define MUI_ABORTWARNING

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "branding\\EULA.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

Section "Install"
  SetOutPath "$INSTDIR"
  {chr(10).join("  " + line for line in install_lines)}

  WriteUninstaller "$INSTDIR\\Uninstall.exe"
  WriteRegStr {registry_root} "{uninstall_key}" "DisplayName" "{_nsis_str(plugin_name)}"
  WriteRegStr {registry_root} "{uninstall_key}" "DisplayVersion" "{_nsis_str(version)}"
  WriteRegStr {registry_root} "{uninstall_key}" "Publisher" "{_nsis_str(manufacturer)}"
  WriteRegStr {registry_root} "{uninstall_key}" "UninstallString" "$INSTDIR\\Uninstall.exe"
  WriteRegStr {registry_root} "{uninstall_key}" "InstallLocation" "$INSTDIR"
  WriteRegDWORD {registry_root} "{uninstall_key}" "NoModify" 1
  WriteRegDWORD {registry_root} "{uninstall_key}" "NoRepair" 1
SectionEnd

Section "Uninstall"
  {chr(10).join("  " + line for line in uninstall_lines)}
  DeleteRegKey {registry_root} "{uninstall_key}"
SectionEnd
"""
    return script, payload_paths
