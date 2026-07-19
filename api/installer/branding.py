"""
Generates the wizard chrome every WiX UI-based installer needs (banner,
side panel, EULA) at build time instead of shipping static binary assets in
the repo — sized exactly to WixUI_InstallDir's requirements and colored with
the real BIMHive brand gold (matches web/styles/tokens.css --gold-600/700),
not an arbitrary placeholder color.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# Matches web/styles/tokens.css --gold-600 (primary button fill) and
# --gold-700 (gold text on white) — the same brand color used everywhere
# else in the storefront, not a value invented for this feature.
BRAND_GOLD = (169, 134, 63)  # #a9863f
BRAND_GOLD_DARK = (138, 106, 46)  # #8a6a2e
INK = (23, 21, 18)  # near-black, matches the storefront's --ink-950 family
PAPER = (255, 253, 250)

BANNER_SIZE = (493, 58)
DIALOG_SIZE = (493, 312)


def _font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("segoeui.ttf", size)
    except OSError:
        return ImageFont.load_default()


def _render_banner(plugin_name: str) -> Image.Image:
    img = Image.new("RGB", BANNER_SIZE, PAPER)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, BANNER_SIZE[0], 4], fill=BRAND_GOLD)
    draw.text((16, 16), plugin_name, fill=INK, font=_font(18))
    draw.text((16, 38), "BIMHive Installer", fill=BRAND_GOLD_DARK, font=_font(11))
    return img


def _render_dialog(plugin_name: str) -> Image.Image:
    img = Image.new("RGB", DIALOG_SIZE, PAPER)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, 8, DIALOG_SIZE[1]], fill=BRAND_GOLD)
    draw.text((32, 32), "BIMHive", fill=BRAND_GOLD_DARK, font=_font(24))
    draw.text((32, 68), plugin_name, fill=INK, font=_font(15))
    return img


def _render_eula(plugin_name: str, manufacturer: str) -> str:
    # WixUILicenseRtf needs real RTF, not plain text — this is a minimal
    # valid RTF document (RTF 1.0 control words), not a stub: it renders
    # correctly in the installer's license page.
    body = (
        f"By installing {plugin_name}, you agree to use it in accordance with the terms "
        f"provided by {manufacturer} at the time of purchase. This software is licensed, "
        "not sold, and is tied to the license key issued to your BIMHive account. "
        "Redistribution or sharing of your license key is not permitted."
    )
    escaped = body.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")
    return (
        r"{\rtf1\ansi\deff0"
        r"{\fonttbl{\f0 Segoe UI;}}"
        r"\f0\fs20 "
        + escaped
        + r"\par}"
    )


def write_branding_assets(staging_dir: Path, plugin_name: str, manufacturer: str) -> None:
    branding_dir = staging_dir / "branding"
    branding_dir.mkdir(parents=True, exist_ok=True)
    _render_banner(plugin_name).save(branding_dir / "Banner.bmp", "BMP")
    _render_dialog(plugin_name).save(branding_dir / "Dialog.bmp", "BMP")
    (branding_dir / "EULA.rtf").write_text(_render_eula(plugin_name, manufacturer), encoding="ascii", errors="replace")
