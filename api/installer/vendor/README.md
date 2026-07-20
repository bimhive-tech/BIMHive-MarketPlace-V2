# LicLoader.dll

A prebuilt binary, not source we own in this repo. It's the activation shim every
*customer-facing* installer wraps the real plugin with (see `installer/license_shim.py` and
`installer/builder.py::generate_installer_bytes` — staff/partner test-downloads pass
`protect_with_license=False` and skip it entirely, since that path must work on unpublished draft
products) — Revit loads `LicLoader.dll` first, it calls `/api/license/activate`, shows a real
"enter your license key" dialog if needed (also reachable anytime via a "License Key" button
LicLoader adds to its own Ribbon tab), and only then loads the actual plugin `.dll` via reflection.
A successful trial grant shows a one-time "trial active, N remaining" notice.

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
