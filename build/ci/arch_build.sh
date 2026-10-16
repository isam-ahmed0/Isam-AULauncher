#!/usr/bin/env bash
# Runs INSIDE an archlinux container (as root) to build CrewLauncher for Arch Linux
# and produces:
#   dist/packages/CrewLauncher.pkg.tar.zst
#
# The workspace is expected at /work (bind-mounted from the CI checkout).
set -euo pipefail

echo "[ci-arch] installing build dependencies"
pacman -Syu --noconfirm --needed \
  base-devel python python-pip \
  mesa libglvnd fontconfig freetype2 libxkbcommon \
  libxcb libx11 libxext libxrender libxi libsm libice \
  libxrandr libxcursor libxfixes libxdamage libxcomposite xcb-util \
  dbus tk

echo "[ci-arch] installing Python packages"
python -m pip install --break-system-packages --upgrade pip
python -m pip install --break-system-packages PySide6 requests pypresence pyinstaller pillow customtkinter

echo "[ci-arch] creating unprivileged builder (makepkg refuses to run as root)"
id -u builder &>/dev/null || useradd -m builder
chown -R builder:builder /work

echo "[ci-arch] building launcher + Arch package as 'builder'"
runuser -u builder -- env HOME=/home/builder bash -c '
  set -euo pipefail
  cd /work
  bash build/build_launcher_linux.sh
  bash build/build_packages_linux.sh pacman
'

chmod -R a+rw /work/dist /work/build 2>/dev/null || true
echo "[ci-arch] done. Package:"
ls -lh /work/dist/packages/CrewLauncher.pkg.tar.zst
