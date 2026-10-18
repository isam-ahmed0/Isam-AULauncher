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
  PKG_NAME_NUITKA="isam-aulauncher-nuitka"
  PKGVER="${VERSION//-/.}"
  WORK="/work/build/pkg-work"
  STAGE="$WORK/stage"
  rm -rf "$WORK"
  mkdir -p "$STAGE"
  cp -a "$APP_DIR" "$STAGE/app"
  PYTHON_BIN="python"
  if ! command -v python >/dev/null 2>&1 && command -v python3 >/dev/null 2>&1; then
      PYTHON_BIN="python3"
  fi
  "$PYTHON_BIN" build/pkg/make_icon.py src/launcher/resources/icon.ico "$STAGE/icons"
  cp build/pkg/isam-au.desktop "$STAGE/isam-au.desktop"
  
  if command -v makepkg >/dev/null 2>&1; then
      echo "[pacman] building .pkg.tar.zst (Nuitka)"
      local dir="$WORK/arch"
      mkdir -p "$dir"
      export STAGE
      cat > "$dir/PKGBUILD" <<EOF
pkgname=$PKG_NAME_NUITKA
pkgver=$PKGVER
pkgrel=1
pkgdesc="Among Us launcher with mod support (Nuitka compiled)"
arch=('"'"'x86_64'"'"')
url="https://github.com/isam-ahmed0/Isam-AULauncher"
license=('"'"'custom'"'"')
options=('"'"'!strip'"'"' '"'"'!debug'"'"')
depends=('"'"'glibc'"'"' '"'"'libglvnd'"'"' '"'"'fontconfig'"'"' '"'"'freetype2'"'"' '"'"'libxcb'"'"' '"'"'libxkbcommon'"'"' '"'"'dbus'"'"' '"'"'zlib'"'"')
optdepends=('"'"'wine: run Among Us directly'"'"' '"'"'lutris: manage and launch the game'"'"' '"'"'xdg-utils: open folders and links'"'"')
source=()
package() {
  install -d "\$pkgdir/opt/isam-aulauncher"
  cp -a "\$STAGE/app/." "\$pkgdir/opt/isam-aulauncher/"
  install -d "\$pkgdir/usr/bin"
  ln -s /opt/isam-aulauncher/CrewLauncher "\$pkgdir/usr/bin/isam-au"
  install -Dm644 "\$STAGE/isam-au.desktop" "\$pkgdir/usr/share/applications/isam-au.desktop"
  for sz in 16 32 48 64 128 256; do
    [ -f "\$STAGE/icons/\$sz.png" ] && install -Dm644 "\$STAGE/icons/\$sz.png" "\$pkgdir/usr/share/icons/hicolor/\${sz}x\${sz}/apps/isam-au.png"
  done
}
EOF
      ( cd "$dir" && PKGDEST="/work/dist/packages" makepkg -f --nodeps --noconfirm >/dev/null )
      mv "/work/dist/packages"/${PKG_NAME_NUITKA}-${PKGVER}-1-*.pkg.tar.zst "/work/dist/packages/CrewLauncher-nuitka.pkg.tar.zst"
      echo "  -> /work/dist/packages/CrewLauncher-nuitka.pkg.tar.zst"
  fi
  # Restore
  rm -f dist/linux/CrewLauncher
  mv dist/linux/CrewLauncher.pyinstaller dist/linux/CrewLauncher 2>/dev/null || true
'

chmod -R a+rw /work/dist /work/build 2>/dev/null || true
echo "[ci-arch-nuitka] done. Package:"
ls -lh /work/dist/packages/CrewLauncher-nuitka.pkg.tar.zst