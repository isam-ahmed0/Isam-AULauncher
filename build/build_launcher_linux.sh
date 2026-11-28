#!/usr/bin/env bash
# Build CrewLauncher on Linux as a thin source install.
#
#   bash build/build_launcher_linux.sh
#
# Requires Node.js/npm for the Web assets; Pillow is only needed by packaging.
#
# The package deliberately does NOT bundle PySide6, QtWebEngine, ICU or a
# Python runtime: those come from the distro (or a one-time venv bootstrap on
# first launch). Result: ~25 MB instead of ~650 MB, with all three UIs intact.
#
# Running straight from the checkout (`python src/launcher/main.py`) is even
# lighter still and needs no build step at all.
set -euo pipefail
cd "$(dirname "$0")/.."

mkdir -p dist/linux

# Web (pywebview) assets are built from the Astro project and are not committed.
bash build/web_assets.sh

APP="dist/linux/CrewLauncher"
rm -rf "$APP"
mkdir -p "$APP/src" "$APP/release"

# Launcher sources (this also carries resources/web, DOC references and the
# requirements file used by the first-run bootstrap).
cp -a src/launcher "$APP/src/launcher"
find "$APP/src/launcher" -type d -name __pycache__ -prune -exec rm -rf '{}' +

# Docs shown in the in-app help dialogs and the mod payload kept offline.
cp -a DOC "$APP/DOC"
cp release/bepmods.zip "$APP/release/bepmods.zip"

install -m 755 build/pkg/thin_launcher.sh "$APP/CrewLauncher"

printf 'Built thin Linux app in %s (%s)\n' "$APP" "$(du -sh "$APP" | cut -f1)"
