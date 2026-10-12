#!/usr/bin/env bash
# Build Linux installer packages from the PyInstaller onedir build.
#
#   bash build/build_launcher_linux.sh      # first, produces dist/linux/CrewLauncher/
#   bash build/build_packages_linux.sh      # then, produces dist/packages/*
#
# Outputs (dist/packages/):
#   CrewLauncher.pkg.tar.zst   Arch/CachyOS/Manjaro (pacman -U)      [internal pkg: isam-aulauncher]
#   CrewLauncher.deb           Debian/Ubuntu/Mint/Pop (apt install ./) [internal pkg: isam-aulauncher]
#   CrewLauncher.rpm           Fedora/RHEL/openSUSE (dnf install ./) [if rpmbuild; internal pkg: isam-aulauncher]
#
# The file names are intentionally unversioned so release download URLs stay
# stable; the packages' internal name/version metadata keeps upgrades working.
# Set BUILD_RUN=1 to additionally build the CrewLauncher-<ver>.run installer.
#
# The Itch Login Fixer stays a separate standalone Windows tool (account
# merging). The launcher's own itch.io login is native and needs no Wine.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

APP_NAME="CrewLauncher"
APP_ID="isam-au"
PKG_NAME="isam-aulauncher"
MAINTAINER="Isam Ahmed <isam-ahmed0@users.noreply.github.com>"
HOMEPAGE="https://github.com/isam-ahmed0/Isam-AULauncher"
DESC_SHORT="Among Us launcher with mod support"

APP_DIR="$ROOT/dist/linux/$APP_NAME"
OUT="$ROOT/dist/packages"
WORK="$ROOT/build/pkg-work"
STAGE="$WORK/stage"

if [ ! -e "$APP_DIR/$APP_NAME" ]; then
    echo "ERROR: $APP_DIR/$APP_NAME not found." >&2
    echo "Build the launcher first:  bash build/build_launcher_linux.sh" >&2
    exit 1
fi

VERSION="$(grep -m1 '^LAUNCHER_VERSION' src/launcher/config.py | sed -E 's/.*"([^"]*)".*/\1/')"
[ -n "$VERSION" ] || VERSION="0.0.0"
PKGVER="${VERSION//-/.}"          # pacman/rpm versions may not contain '-'
DEBVER="${VERSION//-/.}"          # keep it simple and valid

echo "CrewLauncher packaging"
echo "  version : $VERSION  (pkgver $PKGVER)"
echo "  app dir : $APP_DIR"
echo "  output  : $OUT"
echo

rm -rf "$WORK"
mkdir -p "$STAGE" "$OUT"

echo "[stage] copying app + icons + desktop entry"
cp -a "$APP_DIR" "$STAGE/app"
PYTHON_BIN="python"
if ! command -v python >/dev/null 2>&1 && command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
fi
"$PYTHON_BIN" build/pkg/make_icon.py src/launcher/resources/icon.ico "$STAGE/icons"
cp build/pkg/isam-au.desktop "$STAGE/$APP_ID.desktop"

# ---------------------------------------------------------------- pacman
build_pacman() {
    if ! command -v makepkg >/dev/null 2>&1; then
        echo "[pacman] skipped (makepkg not installed)"
        return 0
    fi
    echo "[pacman] building .pkg.tar.zst"
    local dir="$WORK/arch"
    mkdir -p "$dir"
    export STAGE
    cat > "$dir/PKGBUILD" <<EOF
pkgname=$PKG_NAME
pkgver=$PKGVER
pkgrel=1
pkgdesc="$DESC_SHORT"
arch=('x86_64')
url="$HOMEPAGE"
license=('custom')
options=('!strip' '!debug')
depends=('glibc' 'libglvnd' 'fontconfig' 'freetype2' 'libxcb' 'libxkbcommon' 'dbus' 'zlib')
optdepends=('wine: run Among Us directly' 'lutris: manage and launch the game' 'xdg-utils: open folders and links')
source=()
package() {
  install -d "\$pkgdir/opt/isam-aulauncher"
  cp -a "\$STAGE/app/." "\$pkgdir/opt/isam-aulauncher/"
  install -d "\$pkgdir/usr/bin"
  ln -s /opt/isam-aulauncher/$APP_NAME "\$pkgdir/usr/bin/$APP_ID"
  install -Dm644 "\$STAGE/$APP_ID.desktop" "\$pkgdir/usr/share/applications/$APP_ID.desktop"
  for sz in 16 32 48 64 128 256; do
    [ -f "\$STAGE/icons/\$sz.png" ] && install -Dm644 "\$STAGE/icons/\$sz.png" "\$pkgdir/usr/share/icons/hicolor/\${sz}x\${sz}/apps/$APP_ID.png"
  done
}
EOF
    ( cd "$dir" && PKGDEST="$OUT" makepkg -f --nodeps --noconfirm >/dev/null )
    mv "$OUT"/${PKG_NAME}-${PKGVER}-1-*.pkg.tar.zst "$OUT/CrewLauncher.pkg.tar.zst"
    echo "  -> $OUT/CrewLauncher.pkg.tar.zst"
}

# ------------------------------------------------------------------- deb
build_deb() {
    if ! command -v ar >/dev/null 2>&1; then
        echo "[deb] skipped (ar not installed; install 'binutils' to build one)"
        return 0
    fi
    echo "[deb] building .deb"
    local root="$WORK/deb" data="$WORK/deb/data"
    rm -rf "$root"
    mkdir -p "$data" "$root/control"
    install -d "$data/opt/isam-aulauncher"
    cp -a "$STAGE/app/." "$data/opt/isam-aulauncher/"
    install -d "$data/usr/bin"
    ln -s /opt/isam-aulauncher/$APP_NAME "$data/usr/bin/$APP_ID"
    install -Dm644 "$STAGE/$APP_ID.desktop" "$data/usr/share/applications/$APP_ID.desktop"
    for sz in 16 32 48 64 128 256; do
        [ -f "$STAGE/icons/$sz.png" ] && install -Dm644 "$STAGE/icons/$sz.png" "$data/usr/share/icons/hicolor/${sz}x${sz}/apps/$APP_ID.png"
    done

    local size_kb
    size_kb=$(du -sk "$data" | cut -f1)
    cat > "$root/control/control" <<EOF
Package: $PKG_NAME
Version: $DEBVER-1
Architecture: amd64
Maintainer: $MAINTAINER
Installed-Size: $size_kb
Depends: libc6, libgl1, libegl1, libfontconfig1, libfreetype6, libxcb1, libxkbcommon0, libdbus-1-3, zlib1g
Recommends: wine, lutris, xdg-utils
Section: games
Priority: optional
Homepage: $HOMEPAGE
Description: $DESC_SHORT
 CrewLauncher is an Among Us launcher with mod support.
EOF

    ( cd "$data" && tar --owner=0 --group=0 --numeric-owner -cJf "$root/data.tar.xz" . )
    ( cd "$root/control" && tar --owner=0 --group=0 --numeric-owner -cJf "$root/control.tar.xz" ./control )
    printf '2.0\n' > "$root/debian-binary"

    local deb="$OUT/CrewLauncher.deb"
    ( cd "$root" && ar rc "$deb" debian-binary control.tar.xz data.tar.xz )
    echo "  -> $deb"
}

# ------------------------------------------------------------------- rpm
build_rpm() {
    if ! command -v rpmbuild >/dev/null 2>&1; then
        echo "[rpm] skipped (rpmbuild not installed; install 'rpm-tools' to build one)"
        return 0
    fi
    echo "[rpm] building .rpm"
    local top="$WORK/rpm"
    mkdir -p "$top"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}
    cat > "$top/SPECS/$PKG_NAME.spec" <<EOF
Name: $PKG_NAME
Version: $PKGVER
Release: 1%{?dist}
Summary: $DESC_SHORT
License: Custom
URL: $HOMEPAGE
Requires: glibc, mesa-libGL, fontconfig, freetype, libxcb, libxkbcommon, dbus-libs, zlib
Recommends: wine
Recommends: lutris
%global debug_package %{nil}
%global __os_install_post %{nil}
%description
CrewLauncher is an Among Us launcher with mod support.
%install
rm -rf %{buildroot}
mkdir -p %{buildroot}/opt/isam-aulauncher
cp -a $STAGE/app/. %{buildroot}/opt/isam-aulauncher/
mkdir -p %{buildroot}/usr/bin
ln -s /opt/isam-aulauncher/$APP_NAME %{buildroot}/usr/bin/$APP_ID
install -Dm644 $STAGE/$APP_ID.desktop %{buildroot}/usr/share/applications/$APP_ID.desktop
for sz in 16 32 48 64 128 256; do
  [ -f $STAGE/icons/\$sz.png ] && install -Dm644 $STAGE/icons/\$sz.png %{buildroot}/usr/share/icons/hicolor/\${sz}x\${sz}/apps/$APP_ID.png
done
%files
/opt/isam-aulauncher
/usr/bin/$APP_ID
/usr/share/applications/$APP_ID.desktop
/usr/share/icons/hicolor/*/apps/$APP_ID.png
EOF
    rpmbuild -bb --define "_topdir $top" "$top/SPECS/$PKG_NAME.spec" >/dev/null
    find "$top/RPMS" -name '*.rpm' -exec cp {} "$OUT/CrewLauncher.rpm" \;
    echo "  -> $OUT/CrewLauncher.rpm"
}

# ------------------------------------------------------------------- run
build_run() {
    echo "[run] building universal self-extracting installer"
    local payload="$WORK/run-payload.tar.xz"
    local out="$OUT/CrewLauncher-$VERSION.run"
    ( cd "$STAGE" && tar -cJf "$payload" app icons "$APP_ID.desktop" )
    sed "s/@VERSION@/$VERSION/" build/pkg/run_header.sh > "$WORK/run-header.sh"
    cat "$WORK/run-header.sh" "$payload" > "$out"
    chmod +x "$out"
    echo "  -> $out"
}

TARGETS=("$@")
if [ ${#TARGETS[@]} -eq 0 ]; then
    TARGETS=("pacman" "deb" "rpm")
    if [ "${BUILD_RUN:-0}" = "1" ]; then
        TARGETS+=("run")
    fi
fi

for target in "${TARGETS[@]}"; do
    case "$target" in
        pacman|arch) build_pacman ;;
        deb|ubuntu|debian) build_deb ;;
        rpm|fedora) build_rpm ;;
        run) build_run ;;
        *) echo "Unknown package target: $target" >&2; exit 1 ;;
    esac
done

echo
echo "Packages in $OUT:"
ls -lh "$OUT"

# The staging tree holds full copies of the app (hundreds of MB). Drop it unless
# explicitly kept for debugging.
if [ "${KEEP_PKG_WORK:-0}" = "1" ]; then
    echo
    echo "Kept staging dir (KEEP_PKG_WORK=1): $WORK"
else
    rm -rf "$WORK"
fi
