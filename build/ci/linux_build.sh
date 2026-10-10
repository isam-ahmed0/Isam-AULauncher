#!/usr/bin/env bash
# Runs INSIDE an archlinux container (as root) to build CrewLauncher for Linux
# and produce the non-versioned package assets:
#
#   dist/packages/CrewLauncher.pkg.tar.zst
#   dist/packages/CrewLauncher.deb
#   dist/packages/CrewLauncher.rpm
#
# The workspace is expected at /work (bind-mounted from the CI checkout).
set -euo pipefail

echo "[ci] installing build dependencies"
pacman -Syu --noconfirm --needed base-devel rpm-tools python python-pip

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
'
