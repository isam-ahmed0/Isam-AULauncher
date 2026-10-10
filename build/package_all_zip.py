#!/usr/bin/env python3
"""Package dist/CrewLauncher-All.zip for the online/universal NSIS installers.

Archive layout (at the zip root), matching what the installers extract:
    CrewLauncher/       PyInstaller onedir output (CrewLauncher.exe + _internal/)
    Itch_Login_Fixer/   PyInstaller onedir output
    7z.exe              release/7z.exe
    bepmods.zip         release/bepmods.zip

Run from anywhere:  python build/package_all_zip.py
"""
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
OUT = DIST / "CrewLauncher-All.zip"

DIRS = [
    (DIST / "CrewLauncher", "CrewLauncher"),
    (DIST / "Itch_Login_Fixer", "Itch_Login_Fixer"),
]
FILES = [
    (ROOT / "release" / "7z.exe", "7z.exe"),
    (ROOT / "release" / "bepmods.zip", "bepmods.zip"),
]


def main():
    missing = [str(src) for src, _ in DIRS if not src.is_dir()]
    missing += [str(src) for src, _ in FILES if not src.is_file()]
    if missing:
        for path in missing:
            print(f"ERROR: missing required input: {path}", file=sys.stderr)
        return 1

    DIST.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zf:
        for src, prefix in DIRS:
            for path in sorted(src.rglob("*")):
                if path.is_file():
                    arc = f"{prefix}/{path.relative_to(src).as_posix()}"
                    zf.write(path, arc)
        for src, name in FILES:
            zf.write(src, name)

    print(f"Wrote {OUT} ({OUT.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
