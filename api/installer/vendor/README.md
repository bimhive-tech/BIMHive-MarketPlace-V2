# LicLoader.dll

A prebuilt binary, not source we own in this repo. It's the activation shim every
*customer-facing* installer wraps the real plugin with (see `installer/license_shim.py` and
`installer/builder.py::generate_installer_bytes` — staff/partner test-downloads pass
`protect_with_license=False` and skip it entirely, since that path must work on unpublished draft
products) — Revit loads `LicLoader.dll` first, it calls `/api/license/activate`, shows a real
"enter your license key" dialog if needed (also reachable anytime via a "License Key" button
LicLoader adds to its own Ribbon tab), and only then loads the actual plugin `.dll` via reflection.
A successful trial grant shows a one-time "trial active, N remaining" notice; a denial caused
specifically by an expired trial says so by name ("Your 7-day free trial has ended...") instead of a
generic "Access denied." Entering a wrong/expired key re-shows the same dialog immediately (pre-filled
with what was just typed, with the server's denial message as the reason) until it succeeds or the
customer cancels — no Revit restart needed to try again (2026-07-22).

**Source lives outside this repo**, in a separate .NET Framework 4.8 / Revit API project:
`E:\Eng. Youssef Sami\Installer Generator 3\Installer Generator 2\InstallerGenerator\LoaderShim\`
(`ExternalApp.cs` + `LoaderShim.csproj`). That project needs Visual Studio / the .NET Framework 4.8
reference assemblies (pulled via the `Microsoft.NETFramework.ReferenceAssemblies.net48` NuGet
package — `dotnet build` handles it fine, no full Framework SDK install required) and a local Revit
2024 or 2025 install for `RevitAPI.dll`/`RevitAPIUI.dll` — none of which exist in this Django/Next.js
repo or on Railway, which is why the compiled `.dll` is checked in here instead of built at deploy
time.

**To rebuild after changing the shim's C# source:**
```
cd "E:\Eng. Youssef Sami\Installer Generator 3\Installer Generator 2\InstallerGenerator\LoaderShim"
dotnet build LoaderShim.csproj -c Release
```
then copy `bin\Release\LicLoader.dll` over this file and commit it.

## `assembly_renamer/` — why every installer needs it, not just LicLoader.dll itself

Every generated installer stages its own copy of this exact file, renamed per product
(`LicLoader.<slug>.dll`, see `license_shim.py::shim_dll_name`) so multiple BIM Hive plugins can
coexist in the same `%APPDATA%\Autodesk\Revit\Addins\<year>\` folder. That's not enough on its own,
though: a .NET assembly's *identity* (Name/Version/Culture/PublicKeyToken) lives in its own compiled
metadata, completely independent of the filename it's given afterward — every renamed copy here is
still byte-for-byte the same compiled build, so they all share the identity `LicLoader,
Version=1.0.0.0`. With two or more BIM Hive plugins installed at once, .NET's assembly loader treats
every one of those copies as *the same assembly* the moment Revit loads the second one, silently
reusing the first one's already-loaded copy — which makes every "which product am I"
`Assembly.GetExecutingAssembly().Location`-based lookup inside `ExternalApp.cs` resolve to whichever
plugin loaded *first*, for every plugin. Confirmed (2026-09-03) as the actual cause of a real report:
"when I download 2+ plugins, only one loads in the ribbon."

`assembly_renamer/AssemblyRenamer.dll` fixes this at install-packaging time: `installer/
license_shim.py::stage_renamed_shim()` calls it (via the `dotnet` **runtime**, not the SDK — see the
Dockerfile) right after staging each product's copy, rewriting *that copy's own* assembly Name to
`shim_assembly_name(slug)` (e.g. `LicLoader_iso_19650_workset_manager`) using
[Mono.Cecil](https://github.com/jbevain/cecil) — a pure-managed library for reading/writing .NET
assembly metadata, so the rewritten file's PE/CLR structure stays fully valid (verified: identical
type/method count before and after, only the identity changes). This is a genuinely separate, tiny
tool (source: `..\AssemblyRenamer\` next to `LoaderShim\`, **not** part of LoaderShim.csproj) because
it targets `net8.0` and needs zero Revit API references, unlike LicLoader itself — so, unlike
LicLoader, it's something Railway's Linux container actually *can* run (it just can't *compile*
Revit-API-referencing .NET Framework projects, which is why LicLoader.dll still has to be vendored
pre-built while this tool's `dotnet publish` output can be vendored just as easily, framework-
dependent, ~400KB total including Mono.Cecil.dll).

**To rebuild after changing `AssemblyRenamer`'s source:**
```
cd "E:\Eng. Youssef Sami\Installer Generator 3\Installer Generator 2\InstallerGenerator\AssemblyRenamer"
dotnet publish -c Release -o publish
```
then copy `publish\AssemblyRenamer.dll`, `AssemblyRenamer.deps.json`, `AssemblyRenamer.
runtimeconfig.json`, `Mono.Cecil.dll`, and `Mono.Cecil.Rocks.dll` over this folder's copies and commit
them (skip `AssemblyRenamer.exe`/`.pdb` and the other `Mono.Cecil.*.dll` debug-symbol-format
libraries in that publish output — not needed to run the tool).
