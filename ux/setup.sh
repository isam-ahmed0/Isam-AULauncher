#!/bin/sh
# CrewLauncher installer / updater for any Linux distro.
#
#   curl -fsSL https://raw.githubusercontent.com/isam-ahmed0/Isam-AULauncher/crew/ux/setup.sh | sh
#
#   sh setup.sh [install]       install latest via your package manager   [default]
#   sh setup.sh --user          portable install into ~/.local (no sudo)
#   sh setup.sh update          upgrade only if a newer release exists
#   sh setup.sh is-installed    exit 0 = installed, exit 1 = not
#   sh setup.sh uninstall       remove everything CrewLauncher
#   sh setup.sh --selfbuild     build from source + install (slow, explicit only)
#   sh setup.sh -h              this help
#
# Env: SETUP_MIRROR=url        override the release download base URL (testing)
set -e

ROOT="${SETUP_MIRROR:-https://github.com/isam-ahmed0/Isam-AULauncher/releases/latest/download}"
SRC_URL="https://codeload.github.com/isam-ahmed0/Isam-AULauncher/tar.gz/refs/heads/crew"
PKG_NAME="isam-aulauncher"
APP_ID="isam-au"
APP_BIN="CrewLauncher"
USER_DIR="$HOME/.local/share/IsamAULauncher"
USER_BIN="$HOME/.local/bin/$APP_ID"
VERSION_FILE="$USER_DIR/.version"

CMD="install"
MODE="system"
SELFBUILD=0
TMP=""

log() { printf '==> %s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }

cleanup() { if [ -n "$TMP" ]; then rm -rf "$TMP"; fi; }
trap cleanup EXIT INT TERM

usage() {
    cat <<'EOF'
CrewLauncher installer / updater

  sh setup.sh [install]       install latest via your package manager   [default]
  sh setup.sh --user          portable install into ~/.local (no sudo)
  sh setup.sh update          upgrade only if a newer release exists
  sh setup.sh is-installed    exit 0 = installed, exit 1 = not
  sh setup.sh uninstall       remove everything CrewLauncher
  sh setup.sh --selfbuild     build from source + install (slow, explicit only)
  sh setup.sh -h              this help

curl -fsSL https://raw.githubusercontent.com/isam-ahmed0/Isam-AULauncher/crew/ux/setup.sh | sh
EOF
}

for arg in "$@"; do
    case "$arg" in
        install|update|uninstall|is-installed) CMD="$arg" ;;
        --user) MODE="user" ;;
        --selfbuild) SELFBUILD=1 ;;
        -h|--help|help) usage; exit 0 ;;
        *) die "unknown argument: $arg (try -h)" ;;
    esac
done

# ------------------------------------------------------------------ tools
fetch() { # fetch <url> <dest>
    if have curl; then curl -fL --retry 3 --connect-timeout 10 -o "$2" "$1"
    elif have wget; then wget -q --tries=3 -O "$2" "$1"
    else die "need curl or wget"
    fi
}

run_root() {
    if [ "$(id -u)" -eq 0 ]; then "$@"
    elif have sudo; then sudo "$@"
    else die "needs root (no sudo found) — try: --user"
    fi
}

detect_pm() {
    if have pacman; then PM=pacman
    elif have apt-get; then PM=apt
    elif have dnf; then PM=dnf
    elif have microdnf; then PM=microdnf
    elif have yum; then PM=yum
    elif have zypper; then PM=zypper
    else PM=none
    fi
}

latest_tag() { # newest release tag from the download redirect (no API)
    loc=""
    if have curl; then
        loc=$(curl -fsSI --connect-timeout 10 "$ROOT/CrewLauncher.deb" 2>/dev/null | tr -d '\r' | grep -i '^location:' || true)
    elif have wget; then
        loc=$(wget -S --spider "$ROOT/CrewLauncher.deb" 2>&1 | tr -d '\r' | grep -i 'location:' || true)
    fi
    printf '%s\n' "$loc" | sed -n 's|.*/download/\([^/]*\)/.*|\1|p' | head -n1
}

norm() { printf '%s' "$1" | tr -d '-'; }   # tag 1.0-beta.3 == pkgver 1.0.beta.3

# --------------------------------------------------------------- install
install_release() { # via the distro package manager
    detect_pm
    [ "$PM" != "none" ] || die "unsupported distro (no pacman/apt/dnf/zypper).
       Use --user for a portable install into ~/.local, or --selfbuild to build from source."
    TMP=$(mktemp -d)
    case "$PM" in
        pacman)
            log "downloading CrewLauncher.pkg.tar.zst"
            fetch "$ROOT/CrewLauncher.pkg.tar.zst" "$TMP/app.pkg.tar.zst"
            log "installing with pacman"
            run_root pacman -U --noconfirm "$TMP/app.pkg.tar.zst" ;;
        apt)
            log "downloading CrewLauncher.deb"
            fetch "$ROOT/CrewLauncher.deb" "$TMP/app.deb"
            log "installing with apt"
            run_root apt-get install -y "$TMP/app.deb" ;;
        dnf|microdnf|yum)
            log "downloading CrewLauncher.rpm"
            fetch "$ROOT/CrewLauncher.rpm" "$TMP/app.rpm"
            log "installing with $PM"
            run_root "$PM" install -y "$TMP/app.rpm" ;;
        zypper)
            log "downloading CrewLauncher.rpm"
            fetch "$ROOT/CrewLauncher.rpm" "$TMP/app.rpm"
            log "installing with zypper"
            run_root zypper --non-interactive install -y "$TMP/app.rpm" ;;
    esac
    log "CrewLauncher installed. Run it with: $APP_ID"
}

install_portable() { # --user: no sudo, tarball into ~/.local
    TMP=$(mktemp -d)
    log "downloading CrewLauncher-Linux.tar.gz"
    fetch "$ROOT/CrewLauncher-Linux.tar.gz" "$TMP/app.tar.gz"
    log "unpacking"
    tar -xzf "$TMP/app.tar.gz" -C "$TMP"
    [ -d "$TMP/$APP_BIN" ] || die "bad tarball (no $APP_BIN/ inside)"
    rm -rf "$USER_DIR/app"
    mkdir -p "$USER_DIR" "$HOME/.local/bin"
    cp -a "$TMP/$APP_BIN" "$USER_DIR/app"
    ln -sf "$USER_DIR/app/$APP_BIN" "$USER_BIN"
    latest_tag > "$VERSION_FILE" || true
    log "CrewLauncher installed to $USER_DIR/app"
    case ":$PATH:" in
        *":$HOME/.local/bin:"*) log "run it with: $APP_ID" ;;
        *) log "run it with: $USER_BIN   (add ~/.local/bin to PATH)" ;;
    esac
}

# ------------------------------------------------------------- selfbuild
selfbuild_deps() {
    case "$PM" in
        pacman)
            run_root pacman -Sy --noconfirm --needed \
                base-devel python python-pip \
                mesa libglvnd fontconfig freetype2 libxkbcommon libxcb \
                libx11 libxext libxrender libxi libsm libice \
                libxrandr libxcursor libxfixes libxdamage libxcomposite \
                xcb-util dbus binutils ;;
        apt)
            run_root apt-get update
            run_root apt-get install -y --no-install-recommends \
                build-essential python3 python3-venv python3-pip binutils \
                libegl1 libgl1 libglvnd0 fontconfig libfontconfig1 libfreetype6 \
                libxkbcommon0 libxkbcommon-x11-0 libxcb1 \
                libx11-6 libxext6 libxrender6 libxi6 libsm6 libice6 \
                libxrandr2 libxcursor1 libxfixes3 libxdamage1 libxcomposite1 \
                libdbus-1-3 ;;
        dnf|microdnf|yum)
            run_root "$PM" install -y \
                gcc make python3 python3-pip python3-devel binutils rpm-build \
                mesa-libGL mesa-libEGL libglvnd-egl libglvnd-glx mesa-dri-drivers \
                fontconfig freetype libxkbcommon libxkbcommon-x11 \
                libxcb libX11 libXext libXrender libXi libSM libICE \
                libXrandr libXcursor libXfixes libXdamage libXcomposite dbus-libs ;;
        zypper)
            run_root zypper --non-interactive refresh
            run_root zypper --non-interactive install -y \
                gcc make python3 python3-pip python3-devel binutils \
                Mesa-libGL fontconfig freetype2 libxkbcommon libxcb dbus-1 ;;
        *)
            die "--selfbuild: no known package manager to install build deps" ;;
    esac
}

do_selfbuild() {
    [ "$(id -u)" -ne 0 ] || die "--selfbuild must run as your normal user, not root/sudo"
    detect_pm
    TMP=$(mktemp -d)
    log "downloading source"
    fetch "$SRC_URL" "$TMP/src.tar.gz"
    tar -xzf "$TMP/src.tar.gz" -C "$TMP"
    cd "$TMP"/CrewLauncher-*
    log "installing build dependencies (this can take a while)"
    selfbuild_deps
    log "creating python venv"
    python3 -m venv .venv
    .venv/bin/pip install -q --upgrade pip
    .venv/bin/pip install -q PySide6 requests pypresence pyinstaller pillow
    PATH="$PWD/.venv/bin:$PATH"
    export PATH
    case "$PM" in
        pacman) target=pacman; ext=pkg.tar.zst ;;
        apt)    target=deb;    ext=deb ;;
        *)      target=rpm;    ext=rpm ;;
    esac
    log "building launcher (PyInstaller)"
    bash build/build_launcher_linux.sh
    log "packaging ($target)"
    bash build/build_packages_linux.sh "$target"
    pkg=$(ls dist/packages/*."$ext" 2>/dev/null | head -n1)
    [ -n "$pkg" ] || die "build produced no .$ext package"
    log "installing $(basename "$pkg")"
    case "$target" in
        pacman) run_root pacman -U --noconfirm "$pkg" ;;
        deb)    run_root apt-get install -y "$pkg" ;;
        rpm)    run_root "$PM" install -y "$pkg" ;;
    esac
    log "CrewLauncher built and installed."
}

# --------------------------------------------------------------- update
pkg_installed() {
    detect_pm
    case "$PM" in
        pacman)         have pacman && pacman -Q "$PKG_NAME" >/dev/null 2>&1 ;;
        apt)            have dpkg-query && dpkg-query -W -f='${Status}' "$PKG_NAME" 2>/dev/null | grep -q 'install ok installed' ;;
        dnf|microdnf|yum|zypper) have rpm && rpm -q "$PKG_NAME" >/dev/null 2>&1 ;;
        *) return 1 ;;
    esac
}

installed_version() {
    if pkg_installed; then
        detect_pm
        case "$PM" in
            pacman)         pacman -Q "$PKG_NAME" 2>/dev/null | awk '{print $2}' ;;
            apt)            dpkg-query -W -f='${Version}' "$PKG_NAME" 2>/dev/null ;;
            dnf|microdnf|yum|zypper) rpm -q --qf '%{VERSION}' "$PKG_NAME" 2>/dev/null ;;
        esac
    elif [ -f "$VERSION_FILE" ]; then
        cat "$VERSION_FILE"
    else
        echo ""
    fi
}

do_update() {
    latest=$(latest_tag)
    [ -n "$latest" ] || die "could not reach GitHub"
    # a portable install is updated portably, a package install via the pm
    if [ "$MODE" = "system" ] && ! pkg_installed && [ -x "$USER_DIR/app/$APP_BIN" ]; then
        MODE=user
    fi
    current=$(installed_version)
    if [ -n "$current" ] && [ "$(norm "$current")" = "$(norm "$latest")" ]; then
        log "already up to date ($current)"
        exit 0
    fi
    log "updating ${current:-nothing} -> $latest"
    if [ "$MODE" = "user" ]; then install_portable; else install_release; fi
}

# ----------------------------------------------------------- is-installed
do_is_installed() {
    if pkg_installed; then
        echo "CrewLauncher is installed (version: $(installed_version), via package manager)."
        exit 0
    fi
    if [ -x "$USER_DIR/app/$APP_BIN" ]; then
        echo "CrewLauncher is installed (version: $(installed_version), portable in ~/.local)."
        exit 0
    fi
    echo "CrewLauncher is not installed."
    exit 1
}

# -------------------------------------------------------------- uninstall
do_uninstall() {
    detect_pm
    if pkg_installed; then
        log "removing package $PKG_NAME"
        case "$PM" in
            pacman)         run_root pacman -Rns --noconfirm "$PKG_NAME" ;;
            apt)            run_root apt-get remove -y "$PKG_NAME" ;;
            dnf|microdnf|yum) run_root "$PM" remove -y "$PKG_NAME" ;;
            zypper)         run_root zypper --non-interactive remove "$PKG_NAME" ;;
        esac
    fi
    if [ -d "$USER_DIR/app" ] || [ -L "$USER_BIN" ]; then
        log "removing $USER_DIR"
        rm -rf "$USER_DIR" "$USER_BIN"
    fi
    log "done"
}

# ------------------------------------------------------------------ main
case "$CMD" in
    install)
        if [ "$SELFBUILD" -eq 1 ]; then do_selfbuild
        elif [ "$MODE" = "user" ]; then install_portable
        else install_release
        fi ;;
    update)       do_update ;;
    is-installed) do_is_installed ;;
    uninstall)    do_uninstall ;;
esac
