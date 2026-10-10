#!/usr/bin/env bash
# Runs INSIDE an archlinux container (as root) to build CrewLauncher for Linux
# and produce the non-versioned package assets:
#
#   dist/packages/CrewLauncher.pkg.tar.zst
#   dist/packages/CrewLauncher.deb
#   dist/packages/CrewLauncher.rpm
#   dist/packages/CrewLauncher-Linux.tar.gz   (portable onedir)
#
# The workspace is expected at /work (bind-mounted from the CI checkout).
set -euo pipefail

echo "[ci] installing build dependencies"
# The pip PySide6 wheel links GL/X/font libs at import time even when building
# offscreen (make_icon.py imports PySide6.QtGui), so make sure they are present.
pacman -Syu --noconfirm --needed \
  base-devel rpm-tools python python-pip \
  mesa libglvnd fontconfig freetype2 libxkbcommon \
  libxcb libx11 libxext libxrender libxi libsm libice \
  libxrandr libxcursor libxfixes libxdamage libxcomposite xcb-util \
  dbus

echo "[ci] installing Python packages"
python -m pip install --break-system-packages --upgrade pip
python -m pip install --break-system-packages PySide6 requests pypresence pyinstaller

echo "[ci] creating unprivileged builder (makepkg refuses to run as root)"
useradd -m builder
chown -R builder:builder /work

echo "[ci] building launcher + packages as 'builder'"
runuser -u builder -- env HOME=/home/builder bash -c '
  set -euo pipefail
  cd /work
  bash build/build_launcher_linux.sh
  bash build/build_packages_linux.sh
  tar -C dist/linux -czf dist/packages/CrewLauncher-Linux.tar.gz CrewLauncher
'

