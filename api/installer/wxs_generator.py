"""
WiX v5 source (.wxs) generation. Studied the legacy InstallerGenerator's
`Templates/InstallerTemplate.wxs.tmpl` for the schema shape (StandardDirectory
under AppDataFolder -> Autodesk/Revit/Addins/<year>, WixUI_InstallDir) — this
is a from-scratch generator, not a copy, because it needs to support an
arbitrary resource/dependency tree and two install scopes the legacy
single-purpose template never had to.
"""
from dataclasses import dataclass, field
from xml.sax.saxutils import quoteattr

from django.conf import settings

from installer.paths import INSTALL_DIR_TOKEN, parse_destination_path

WIX_NS = "http://wixtoolset.org/schemas/v4/wxs"
WIX_UI_NS = "http://wixtoolset.org/schemas/v4/wxs/ui"


def resolve_scope(resource_files) -> str:
    """Per-user (AppData only, no install prompt) unless something targets
    Program Files, in which case the whole package must be per-machine —
    WiX/MSI scope is a package-level setting, not something that can be
    mixed component-by-component within one install."""
    for resource in resource_files:
        token, _ = parse_destination_path(resource.destination_path)
        if token == INSTALL_DIR_TOKEN:
            return "perMachine"
    return "perUser"


@dataclass
class _DirNode:
    id: str
    name: str
    children: dict = field(default_factory=dict)  # name -> _DirNode
    files: list = field(default_factory=list)  # list of (component_id, file_id, source_rel_path)


def _safe_id(*parts: str) -> str:
    """WiX Ids must be <= 72 chars, start with a letter/underscore, and
    contain only [A-Za-z0-9_.]. Hashing keeps it short and unique enough
    without depending on filesystem-unsafe characters in a filename."""
    import hashlib

    raw = "/".join(parts)
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]
    return f"id_{digest}"


def _insert_resource(root: _DirNode, segments: list[str], component_id: str, file_id: str, source_rel: str) -> None:
    node = root
    for segment in segments[:-1]:
        if segment not in node.children:
            node.children[segment] = _DirNode(id=_safe_id(node.id, segment), name=segment)
        node = node.children[segment]
    filename = segments[-1] if segments else source_rel.rsplit("/", 1)[-1]
    node.files.append((component_id, file_id, source_rel, filename))


def _render_dir_node(node: _DirNode, component_refs: list[str]) -> str:
    parts = []
    for component_id, file_id, source_rel, filename in node.files:
        component_refs.append(component_id)
        parts.append(
            f'<Component Id="{component_id}">'
            f'<File Id="{file_id}" Source={quoteattr(source_rel)} Name={quoteattr(filename)} KeyPath="yes"/>'
            f"</Component>"
        )
    for child in node.children.values():
        parts.append(
            f'<Directory Id="{child.id}" Name={quoteattr(child.name)}>'
            f"{_render_dir_node(child, component_refs)}"
            f"</Directory>"
        )
    return "".join(parts)


def generate_wxs(build, resource_files) -> tuple[str, list[str]]:
    """Returns (wxs_xml_source, list_of_staging_relative_payload_paths) — the
    caller stages files at those relative paths before invoking `wix build`.

    Every value that can contain arbitrary user input (product name, plugin
    version — both set freely by a partner) is quoted with quoteattr(), not
    a bare escape() wrapped in manual quotes: escape() only handles &, <, >
    and leaves a literal `"` free to break out of an XML attribute early.
    quoteattr() returns the value already delimited and fully escaped."""
    scope = resolve_scope(resource_files)
    plugin_name_raw = build.product.name
    plugin_name_attr = quoteattr(plugin_name_raw)
    manufacturer_attr = quoteattr(settings.INSTALLER_MANUFACTURER)
    upgrade_code_attr = quoteattr(str(build.upgrade_code).upper())
    version_attr = quoteattr(build.plugin_version or "1.0.0")
    revit_year_attr = quoteattr(build.revit_year)
    scope_attr = quoteattr(scope)
    downgrade_message_attr = quoteattr(f"A newer version of {plugin_name_raw} is already installed.")

    payload_paths: list[str] = []

    addin_root = _DirNode(id="DIR_ADDIN_YEAR", name=build.revit_year)
    install_root = _DirNode(id="DIR_INSTALL", name=build.product.name) if scope == "perMachine" else None

    # The two fixed files every build has — addin manifest + compiled plugin —
    # always land directly in the Revit Addins year folder, same as the
    # legacy tool, regardless of where extra resources go.
    addin_source = f"payload/{build.addin_filename}"
    dll_source = f"payload/{build.dll_filename}"
    payload_paths.append(addin_source)
    payload_paths.append(dll_source)

    component_refs: list[str] = ["cmp_Addin", "cmp_PluginDll"]
    fixed_components = (
        f'<Component Id="cmp_Addin">'
        f'<File Id="fil_Addin" Source={quoteattr(addin_source)} Name={quoteattr(build.addin_filename)} KeyPath="yes"/>'
        f"</Component>"
        f'<Component Id="cmp_PluginDll">'
        f'<File Id="fil_PluginDll" Source={quoteattr(dll_source)} Name={quoteattr(build.dll_filename)} KeyPath="yes"/>'
        f"</Component>"
    )

    for index, resource in enumerate(resource_files):
        token, segments = parse_destination_path(resource.destination_path)
        source_rel = f"payload/resources/{index}_{resource.original_filename}"
        payload_paths.append(source_rel)
        component_id = _safe_id("cmp", str(resource.id))
        file_id = _safe_id("fil", str(resource.id))
        target_root = install_root if token == INSTALL_DIR_TOKEN else addin_root
        _insert_resource(target_root, segments, component_id, file_id, source_rel)

    addin_dir_ref_body = fixed_components + _render_dir_node(addin_root, component_refs)

    install_dir_block = ""
    install_dir_ref = ""
    if scope == "perMachine":
        install_dir_ref_body = _render_dir_node(install_root, component_refs)
        install_dir_block = (
            '<StandardDirectory Id="ProgramFilesFolder">'
            f'<Directory Name={quoteattr(settings.INSTALLER_MANUFACTURER)}>'
            f'<Directory Id="DIR_INSTALL" Name={quoteattr(build.product.name)}/>'
            "</Directory>"
            "</StandardDirectory>"
        )
        if install_dir_ref_body:
            install_dir_ref = f'<DirectoryRef Id="DIR_INSTALL">{install_dir_ref_body}</DirectoryRef>'

    feature_refs = "".join(f'<ComponentRef Id="{cid}"/>' for cid in component_refs)

    wxs = f"""<?xml version="1.0" encoding="UTF-8"?>
<Wix xmlns="{WIX_NS}" xmlns:ui="{WIX_UI_NS}">
  <Package Name={plugin_name_attr}
           Manufacturer={manufacturer_attr}
           Version={version_attr}
           UpgradeCode={upgrade_code_attr}
           Scope={scope_attr}
           InstallerVersion="500"
           Compressed="yes">

    <MajorUpgrade DowngradeErrorMessage={downgrade_message_attr}/>
    <Media Id="1" Cabinet="data.cab" EmbedCab="yes" CompressionLevel="high"/>

    <WixVariable Id="WixUIBannerBmp" Value="branding/Banner.bmp"/>
    <WixVariable Id="WixUIDialogBmp" Value="branding/Dialog.bmp"/>
    <WixVariable Id="WixUILicenseRtf" Value="branding/EULA.rtf"/>

    <StandardDirectory Id="AppDataFolder">
      <Directory Name="Autodesk">
        <Directory Name="Revit">
          <Directory Name="Addins">
            <Directory Id="DIR_ADDIN_YEAR" Name={revit_year_attr}/>
          </Directory>
        </Directory>
      </Directory>
    </StandardDirectory>
    {install_dir_block}

    <Property Id="WIXUI_INSTALLDIR" Value="DIR_ADDIN_YEAR"/>

    <DirectoryRef Id="DIR_ADDIN_YEAR">
      {addin_dir_ref_body}
    </DirectoryRef>
    {install_dir_ref}

    <Feature Id="feat_Main" Title={plugin_name_attr} Level="1">
      {feature_refs}
    </Feature>

    <ui:WixUI Id="WixUI_InstallDir"/>
  </Package>
</Wix>
"""
    return wxs, payload_paths
