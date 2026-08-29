"""Generate the Isam AULauncher icon (.ico) and PNG preview.

Draws a rounded badge with a gradient (cyan -> violet) and the "ISAM" wordmark.
Outputs:
  src/launcher/resources/icon.ico
  release/icon.ico
  docs/preview.png
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Pillow is required: pip install pillow")
    sys.exit(1)

CYAN = (0, 212, 255)
VIOLET = (124, 92, 255)
DARK = (14, 17, 22)


def color_at(start, end, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(start, end))


def font_for(size):
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/segoeuib.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def draw_badge(size):
    scale = size / 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    margin = int(12 * scale)
    r = int(52 * scale)
    # rounded square
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=r, fill=DARK
    )

    # gradient border ring
    ring = int(10 * scale)
    for i in range(int(44 * scale), 0, -1):
        t = i / (44 * scale)
        col = color_at(CYAN, VIOLET, 1 - t)
        draw.rounded_rectangle(
            [margin + i, margin + i, size - margin - i, size - margin - i],
            radius=max(r - i, 1), outline=col, width=1
        )

    # inner diagonal accent bar
    bar_w = int(52 * scale)
    top_color = color_at(CYAN, VIOLET, 0.15)
    bot_color = color_at(CYAN, VIOLET, 0.85)
    for i in range(bar_w):
        t = i / bar_w
        col = color_at(top_color, bot_color, t)
        draw.rectangle(
            [size - margin - ring - bar_w + i, margin + ring,
             size - margin - ring - bar_w + i + 1, size - margin - ring],
            fill=col
        )

    # wordmark
    font = font_for(int(64 * scale))
    text = "ISAM"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text(
        ((size - tw) / 2 - bbox[0], (size - th) / 2 - bbox[1] - int(16 * scale)),
        text, font=font, fill=(238, 241, 248)
    )

    font_small = font_for(int(26 * scale))
    sub = "AU LAUNCHER"
    bbox = draw.textbbox((0, 0), sub, font=font_small)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text(
        ((size - tw) / 2 - bbox[0], (size - th) / 2 - bbox[1] + int(44 * scale)),
        sub, font=font_small, fill=(139, 147, 167)
    )
    return img


def main():
    badge = draw_badge(512)

    src_icon = ROOT / "src" / "launcher" / "resources" / "icon.ico"
    release_icon = ROOT / "release" / "icon.ico"
    preview = ROOT / "docs" / "preview.png"
    src_icon.parent.mkdir(parents=True, exist_ok=True)
    release_icon.parent.mkdir(parents=True, exist_ok=True)

    badge.save(src_icon, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (256, 256)])
    badge.save(release_icon, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (256, 256)])
    badge.resize((256, 256)).save(preview)

    print("Icon written to:")
    print(f"  {src_icon}")
    print(f"  {release_icon}")
    print(f"  {preview}")


if __name__ == "__main__":
    main()