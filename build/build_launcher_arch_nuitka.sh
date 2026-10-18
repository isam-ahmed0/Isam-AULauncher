#!/usr/bin/env bash
# Build CrewLauncher for Arch Linux using Nuitka (standalone onedir).
# Produces: dist/linux-nuitka/CrewLauncher/
#
# Usage: bash build/build_launcher_arch_nuitka.sh
set -euo pipefail

cd "$(dirname "$0")/.."

mkdir -p dist/linux-nuitka

VERSION="$(grep -m1 '^LAUNCHER_VERSION' src/launcher/config.py | sed -E 's/.*"([^"]*)".*/\1/')"
[ -n "$VERSION" ] || VERSION="0.0.0"
echo "[nuitka-arch] Building CrewLauncher $VERSION with Nuitka"

python -m nuitka --standalone \
  --name CrewLauncher \
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
  --jobs=$(nproc) \
  src/launcher/main.py

echo "[nuitka-arch] Built: dist/linux-nuitka/CrewLauncher/"
ls -lh dist/linux-nuitka/CrewLauncher/

# Build Itch Login Fixer with Nuitka
echo "[nuitka-arch] Building Itch_Login_Fixer with Nuitka"
python -m nuitka --standalone \
  --name Itch_Login_Fixer \
  --enable-plugin=tk-inter \
  --include-module=customtkinter \
  --include-package=customtkinter \
  --include-data-dir=src/fixer/assets=assets \
  --linux-icon=src/fixer/assets/icon.ico \
  --output-dir=dist/linux-nuitka \
  --remove-output \
  --assume-yes-for-downloads \
  --jobs=$(nproc) \
  src/fixer/Itch_Login_Fixer.py

echo "[nuitka-arch] Built: dist/linux-nuitka/Itch_Login_Fixer/"
ls -lh dist/linux-nuitka/Itch_Login_Fixer/