#!/usr/bin/env python3
"""Render launcher/icons/*.ico into hicolor PNG sizes for packaging.

Uses PySide6 (already a launcher dependency) so no extra tooling is needed.

    python make_icon.py <icon.ico> <outdir>
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSize
from PySide6.QtGui import QGuiApplication, QIcon

SIZES = (16, 32, 48, 64, 128, 256)


def main(argv):
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    src, outdir = argv[1], argv[2]
    if not os.path.isfile(src):
        print(f"ERROR: icon not found: {src}", file=sys.stderr)
        return 1

    app = QGuiApplication.instance() or QGuiApplication([])  # noqa: F841
    icon = QIcon(src)
    if icon.isNull():
        print(f"ERROR: could not read icon: {src}", file=sys.stderr)
        return 1

    os.makedirs(outdir, exist_ok=True)
    made = []
    for size in SIZES:
        pixmap = icon.pixmap(QSize(size, size))
        if pixmap.isNull():
            continue
        path = os.path.join(outdir, f"{size}.png")
        if pixmap.save(path, "PNG"):
            made.append(path)
    if not made:
        print("ERROR: produced no PNGs", file=sys.stderr)
        return 1
    print("Icons: " + ", ".join(os.path.basename(p) for p in made))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
