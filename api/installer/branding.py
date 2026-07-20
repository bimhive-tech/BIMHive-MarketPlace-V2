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
    # segoeui.ttf only exists on Windows — Railway's Linux build host never has
    # it, so this always falls through to load_default() there. Passing
    # size= (Pillow 10.1+) matters: without it, load_default() silently
    # ignores the requested size and returns a fixed ~10px stub font, which
    # made every rendered word tiny enough that the banner/sidebar read as
    # blank rather than branded.
    try:
        return ImageFont.truetype("segoeui.ttf", size)
    except OSError:
        return ImageFont.load_default(size=size)


def _render_header(plugin_name: str) -> Image.Image:
    # Mirrors the original WiX Banner.bmp layout 1:1 (just rescaled to NSIS's
    # fixed 150x57): a thin full-width gold rule across the top, plugin name
    # + "BIMHive" underneath.
    img = Image.new("RGB", HEADER_SIZE, PAPER)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, HEADER_SIZE[0], 4], fill=BRAND_GOLD)
    font = _font(11)
    name = plugin_name
    max_width = HEADER_SIZE[0] - 20
    while draw.textlength(name, font=font) > max_width and len(name) > 1:
        name = name[:-1]
    if name != plugin_name:
        name = name.rstrip() + "…"
    draw.text((10, 11), name, fill=INK, font=font)
    draw.text((10, 30), "BIMHive Installer", fill=BRAND_GOLD_DARK, font=_font(9))
    return img


def _render_welcome(plugin_name: str) -> Image.Image:
    # Mirrors the original WiX Dialog.bmp layout 1:1 (rescaled to NSIS's
    # fixed 164x314): paper background, a left gold rule, "BIMHive" title
    # then the plugin name underneath.
    img = Image.new("RGB", WELCOME_SIZE, PAPER)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, 8, WELCOME_SIZE[1]], fill=BRAND_GOLD)
    draw.text((24, 28), "BIMHive", fill=BRAND_GOLD_DARK, font=_font(18))
    _draw_wrapped_text(draw, plugin_name, (24, 60), WELCOME_SIZE[0] - 40, INK, _font(13), line_height=18)
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
    _render_header(plugin_name).save(branding_dir / "Header.bmp", "BMP")
    _render_welcome(plugin_name).save(branding_dir / "Welcome.bmp", "BMP")
    (branding_dir / "EULA.txt").write_text(_render_eula(plugin_name, manufacturer), encoding="ascii", errors="replace")
