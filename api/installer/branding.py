"""
Generates the wizard chrome every NSIS MUI2 installer needs (header image,
welcome/finish sidebar, EULA) at build time instead of shipping static
binary assets in the repo — sized exactly to NSIS Modern UI 2's
requirements and colored with the real BIMHive brand gold (matches
web/styles/tokens.css --gold-600/700), not an arbitrary placeholder color.
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

# NSIS Modern UI 2's fixed, non-negotiable bitmap dimensions — MUI_HEADERIMAGE
# (top strip on the license/directory/install pages) and
# MUI_WELCOMEFINISHPAGE_BITMAP (tall sidebar on the welcome/finish pages).
HEADER_SIZE = (150, 57)
WELCOME_SIZE = (164, 314)


def _font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("segoeui.ttf", size)
    except OSError:
        return ImageFont.load_default()


def _render_header() -> Image.Image:
    img = Image.new("RGB", HEADER_SIZE, PAPER)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, 4, HEADER_SIZE[1]], fill=BRAND_GOLD)
    draw.text((16, 18), "BIMHive", fill=BRAND_GOLD_DARK, font=_font(16))
    return img


def _render_welcome(plugin_name: str) -> Image.Image:
    img = Image.new("RGB", WELCOME_SIZE, BRAND_GOLD)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, WELCOME_SIZE[0], 96], fill=BRAND_GOLD_DARK)
    draw.text((18, 34), "BIMHive", fill=PAPER, font=_font(20))
    _draw_wrapped_text(draw, plugin_name, (18, 116), WELCOME_SIZE[0] - 32, INK, _font(14), line_height=20)
    return img


def _draw_wrapped_text(
    draw: ImageDraw.ImageDraw, text: str, origin: tuple[int, int], max_width: int, fill, font, line_height: int
) -> None:
    # Line height is passed explicitly rather than read off `font.size` —
    # the fallback bitmap font returned when segoeui.ttf isn't installed
    # (any non-Windows build host, i.e. Railway) doesn't expose that
    # attribute the same way a real FreeTypeFont does.
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=font) > max_width and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    x, y = origin
    for line in lines:
        draw.text((x, y), line, fill=fill, font=font)
        y += line_height


def _render_eula(plugin_name: str, manufacturer: str) -> str:
    return (
        f"By installing {plugin_name}, you agree to use it in accordance with the terms "
        f"provided by {manufacturer} at the time of purchase. This software is licensed, "
        "not sold, and is tied to the license key issued to your BIMHive account. "
        "Redistribution or sharing of your license key is not permitted."
    )


def write_branding_assets(staging_dir: Path, plugin_name: str, manufacturer: str) -> None:
    branding_dir = staging_dir / "branding"
    branding_dir.mkdir(parents=True, exist_ok=True)
    _render_header().save(branding_dir / "Header.bmp", "BMP")
    _render_welcome(plugin_name).save(branding_dir / "Welcome.bmp", "BMP")
    (branding_dir / "EULA.txt").write_text(_render_eula(plugin_name, manufacturer), encoding="ascii", errors="replace")
