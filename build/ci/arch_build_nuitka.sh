#!/usr/bin/env bash
# Runs INSIDE an archlinux container (as root) to build CrewLauncher for Arch Linux using Nuitka
# and produces:
#   dist/packages/CrewLauncher.pkg.tar.zst
#
# The workspace is expected at /work (bind-mounted from the CI checkout).
set -euo pipefail

echo "[ci-arch-nuitka] installing build dependencies"
pacman -Syu --noconfirm --needed \
  base-devel python python-pip \
  mesa libglvnd fontconfig freetype2 libxkbcommon \
  libxcb libx11 libxext libxrender libxi libsm libice \
  libxrandr libxcursor libxfixes libxdamage libxcomposite xcb-util \
  dbus tk \
  patchelf

echo "[ci-arch-nuitka] installing Python packages"
python -m pip install --break-system-packages --upgrade pip
python -m pip install --break-system-packages PySide6 requests pypresence pillow customtkinter nuitka

echo "[ci-arch-nuitka] creating unprivileged builder (makepkg refuses to run as root)"
id -u builder &>/dev/null || useradd -m builder
chown -R builder:builder /work

echo "[ci-arch-nuitka] building launcher with Nuitka as 'builder'"
runuser -u builder -- env HOME=/home/builder bash -c '
  set -euo pipefail
  cd /work
  bash build/build_launcher_arch_nuitka.sh
'

echo "[ci-arch-nuitka] packaging Nuitka build as Arch package as 'builder'"
runuser -u builder -- env HOME=/home/builder bash -c '
  set -euo pipefail
  cd /work
  APP_DIR="dist/linux-nuitka/CrewLauncher"
  if [ ! -e "$APP_DIR/CrewLauncher" ]; then
      echo "ERROR: $APP_DIR/CrewLauncher not found." >&2
      exit 1
  fi
  # Temporarily replace dist/linux/CrewLauncher with Nuitka build for packaging
  mv dist/linux/CrewLauncher dist/linux/CrewLauncher.pyinstaller 2>/dev/null || true
  ln -sf linux-nuitka/CrewLauncher dist/linux/CrewLauncher
  bash build/build_packages_linux.sh pacman
  # Restore
  rm -f dist/linux/CrewLauncher
  mv dist/linux/CrewLauncher.pyinstaller dist/linux/CrewLauncher 2>/dev/null || true
'

chmod -R a+rw /work/dist /work/build 2>/dev/null || true
echo "[ci-arch-nuitka] done. Package:"
ls -lh /work/dist/packages/CrewLauncher.pkg.tar.zst