#!/usr/bin/env bash
# Build CrewLauncher for Arch Linux using Nuitka (standalone onedir).
# Produces: dist/linux-nuitka/CrewLauncher/
set -euo pipefail

cd "$(dirname "$0")/.."

mkdir -p dist/linux-nuitka

VERSION="$(grep -m1 '^LAUNCHER_VERSION' src/launcher/config.py | sed -E 's/.*"([^"]*)".*/\1/')"
[ -n "$VERSION" ] || VERSION="0.0.0"
echo "[nuitka-arch] Building CrewLauncher $VERSION with Nuitka"

python -m nuitka --standalone \
  --output-filename=CrewLauncher \
  --enable-plugin=pyside6 \
  --enable-plugin=tk-inter \
  --include-module=customtkinter \
  --include-package=customtkinter \
  --include-data-dir=src/launcher/resources=resources \
  --include-data-dir=DOC=DOC \
  --include-data-file=release/bepmods.zip=bepmods.zip \
  --linux-icon=src/launcher/resources/icon.ico \
  --output-dir=dist/linux-nuitka \
  --remove-output \
  --assume-yes-for-downloads \
  --jobs=$(nproc 2>/dev/null || echo 4) \
  src/launcher/main.py

# Nuitka standalone creates main.dist/
echo "[nuitka-arch] Creating onedir structure for packaging"
rm -rf dist/linux-nuitka/CrewLauncher
if [ -d "dist/linux-nuitka/main.dist" ]; then
    mv dist/linux-nuitka/main.dist dist/linux-nuitka/CrewLauncher
elif [ -d "dist/linux-nuitka/src.launcher.main.dist" ]; then
    mv dist/linux-nuitka/src.launcher.main.dist dist/linux-nuitka/CrewLauncher
else
    # Find dist dir
    DISTDIR=$(find dist/linux-nuitka -maxdepth 1 -name "*.dist" -type d | head -1)
    if [ -n "$DISTDIR" ]; then
        mv "$DISTDIR" dist/linux-nuitka/CrewLauncher
    else
        echo "ERROR: Could not find Nuitka dist directory" >&2
        exit 1
    fi
fi

# Ensure data files are present
[ -d "dist/linux-nuitka/CrewLauncher/resources" ] || cp -r src/launcher/resources dist/linux-nuitka/CrewLauncher/
[ -d "dist/linux-nuitka/CrewLauncher/DOC" ] || cp -r DOC dist/linux-nuitka/CrewLauncher/
[ -f "dist/linux-nuitka/CrewLauncher/bepmods.zip" ] || cp release/bepmods.zip dist/linux-nuitka/CrewLauncher/

echo "[nuitka-arch] Built: dist/linux-nuitka/CrewLauncher/"
ls -lh dist/linux-nuitka/CrewLauncher/ | head -5

# Build Itch Login Fixer with Nuitka
echo "[nuitka-arch] Building Itch_Login_Fixer with Nuitka"
python -m nuitka --standalone \
  --output-filename=Itch_Login_Fixer \
  --enable-plugin=tk-inter \
  --include-module=customtkinter \
  --include-package=customtkinter \
  --include-data-dir=src/fixer/assets=assets \
  --linux-icon=src/fixer/assets/icon.ico \
  --output-dir=dist/linux-nuitka \
  --remove-output \
  --assume-yes-for-downloads \
  --jobs=$(nproc 2>/dev/null || echo 4) \
  src/fixer/Itch_Login_Fixer.py

rm -rf dist/linux-nuitka/Itch_Login_Fixer
if [ -d "dist/linux-nuitka/Itch_Login_Fixer.dist" ]; then
    mv dist/linux-nuitka/Itch_Login_Fixer.dist dist/linux-nuitka/Itch_Login_Fixer
else
    DISTDIR=$(find dist/linux-nuitka -maxdepth 1 -name "*Fixer*.dist" -type d | head -1)
    [ -n "$DISTDIR" ] && mv "$DISTDIR" dist/linux-nuitka/Itch_Login_Fixer
fi
[ -d "dist/linux-nuitka/Itch_Login_Fixer/assets" ] || cp -r src/fixer/assets dist/linux-nuitka/Itch_Login_Fixer/ 2>/dev/null || true

echo "[nuitka-arch] Built: dist/linux-nuitka/Itch_Login_Fixer/"