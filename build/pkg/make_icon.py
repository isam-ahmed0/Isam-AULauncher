#!/usr/bin/env python3
"""Render launcher/icons/*.ico into hicolor PNG sizes for packaging.

Uses Pillow if available, otherwise falls back to PySide6.

    python make_icon.py <icon.ico> <outdir>
"""
import os
import sys

SIZES = (16, 32, 48, 64, 128, 256)


def make_with_pil(src, outdir):
    try:
        from PIL import Image
    except ImportError:
        return None

    try:
        im = Image.open(src)
        os.makedirs(outdir, exist_ok=True)
        made = []
        for size in SIZES:
            best_img = None
            if hasattr(im, "ico") and (size, size) in getattr(im, "info", {}).get("sizes", set()):
                try:
                    best_img = im.ico.getimage((size, size))
                except Exception:
                    best_img = None
            if best_img is None:
                best_img = im.resize((size, size), Image.Resampling.LANCZOS)
            path = os.path.join(outdir, f"{size}.png")
            best_img.save(path, "PNG")
            made.append(path)
        return made
    except Exception as e:
        print(f"PIL render error: {e}, falling back to PySide6", file=sys.stderr)
        return None


def make_with_pyside(src, outdir):
    try:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtCore import QSize
        from PySide6.QtGui import QGuiApplication, QIcon
    except Exception as e:
        print(f"PySide6 import error: {e}", file=sys.stderr)
        return None

    app = QGuiApplication.instance() or QGuiApplication([])  # noqa: F841
    icon = QIcon(src)
    if icon.isNull():
        print(f"ERROR: could not read icon: {src}", file=sys.stderr)
        return None

    os.makedirs(outdir, exist_ok=True)
    made = []
    for size in SIZES:
        pixmap = icon.pixmap(QSize(size, size))
        if pixmap.isNull():
            continue
        path = os.path.join(outdir, f"{size}.png")
        if pixmap.save(path, "PNG"):
            made.append(path)
    return made


def main(argv):
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    src, outdir = argv[1], argv[2]
    if not os.path.isfile(src):
        print(f"ERROR: icon not found: {src}", file=sys.stderr)
        return 1

    made = make_with_pil(src, outdir)
    if not made:
        made = make_with_pyside(src, outdir)

    if not made:
        print("ERROR: produced no PNGs", file=sys.stderr)
        return 1
    print("Icons: " + ", ".join(os.path.basename(p) for p in made))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
