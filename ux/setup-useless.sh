#!/usr/bin/env bash
# CrewLauncher installer / updater for any Linux distro.
#
#   curl -fsSL https://raw.githubusercontent.com/isam-ahmed0/Isam-AULauncher/main/ux/setup.sh | bash
#
# Commands (first argument, default: install):
#   install            install / reinstall the latest release   [needs root unless --user]
#   update             check GitHub and upgrade only if newer
#   is-installed       exit 0 = installed, exit 1 = not (prints details)
#   uninstall          remove every CrewLauncher install found
#
# Flags:
#   --user             install into ~/.local (no root needed)
#   --system           install system-wide (default; needs root/sudo)
#   -h, --help         this help
#
# Env:
#   SETUP_FILE=path    use a local .deb/.rpm/.pkg.tar.zst/.tar.gz instead of downloading
set -euo pipefail

ROOT_LINK="https://github.com/isam-ahmed0/Isam-AULauncher/releases/latest/download/"
RAW_LINK="https://raw.githubusercontent.com/isam-ahmed0/Isam-AULauncher/main/ux/setup.sh"
API_LINK="https://api.github.com/repos/isam-ahmed0/Isam-AULauncher/releases/latest"
PKG_NAME="isam-aulauncher"
APP_NAME="CrewLauncher"
APP_ID="isam-au"
OPT_DIR="/opt/$PKG_NAME"
USER_ROOT="$HOME/.local/share/IsamAULauncher"
USER_APP="$USER_ROOT/app"
BIN_DIR="$HOME/.local/bin"
BIN_LINK="$BIN_DIR/$APP_ID"
DESKTOP_NAME="$APP_ID.desktop"
ICON_SIZES="16 32 48 64 128 256"

MODE="system"
CMD="install"
TMP=""

log()  { printf '==> %s\n' "$*"; }
warn() { printf 'WARNING: %s\n' "$*" >&2; }
die()  { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }

cleanup() { if [ -n "$TMP" ]; then rm -rf "$TMP"; fi; return 0; }
trap cleanup EXIT INT TERM

# When run via 'curl | sudo bash', keep the self-installed copy in the real
# user's home instead of /root.

usage() { sed -n '2,18p' "${BASH_SOURCE[0]:-$0}" | sed 's/^# \{0,1\}//'; }

# ------------------------------------------------------------------ args
for arg in "$@"; do
    case "$arg" in
        install|update|uninstall|is-installed|status) CMD="$arg" ;;
        --user)   MODE="user" ;;
        --system) MODE="system" ;;
        -y|--yes) ;;   # installs are already non-interactive; accepted for compatibility
        -h|--help|help) usage; exit 0 ;;
        *) die "unknown argument: $arg (try --help)" ;;
    esac
done
[ "$CMD" = "status" ] && CMD="is-installed"

# ----------------------------------------------------------------- root
is_root() { [ "$(id -u)" -eq 0 ]; }

as_root() {
    if is_root; then "$@"
    elif have sudo; then sudo "$@"
    else die "this step needs root (sudo not found). Use --user for a per-user install."
    fi
}

# Self-installed copy goes to the invoking user's home (not /root under sudo).
SELF_HOME="$HOME"
if is_root && [ -n "${SUDO_USER:-}" ] && have getent; then
    _h=$(getent passwd "$SUDO_USER" | cut -d: -f6) && [ -n "$_h" ] && SELF_HOME="$_h"
fi
SETUP_BIN="$SELF_HOME/.local/bin/crewlauncher-setup"

# ------------------------------------------------------------- download
fetch() { # fetch <url> <dest>
    if have curl; then curl -fsSL --retry 3 --connect-timeout 10 -o "$2" "$1"
    elif have wget; then wget -q --tries=3 -O "$2" "$1"
    else die "need curl or wget to download"
    fi
}

github_version() { # prints the latest release tag, or "unknown"
    local tag="" loc
    if have curl; then
        loc=$(curl -fsSI --connect-timeout 10 "$ROOT_LINK$APP_NAME.deb" 2>/dev/null \
              | tr -d '\r' | grep -i '^location:' || true)
    elif have wget; then
        loc=$(wget -S --spider "$ROOT_LINK$APP_NAME.deb" 2>&1 \
              | tr -d '\r' | grep -i 'location:' || true)
    else
        loc=""
    fi
    if [ -n "$loc" ]; then
        tag=$(printf '%s' "$loc" | sed -n 's|.*/download/\([^/]*\)/.*|\1|p')
    fi
    if [ -z "$tag" ] && have curl; then
        tag=$(curl -fsSL --connect-timeout 10 "$API_LINK" 2>/dev/null \
              | sed -n 's/.*"tag_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n1) || true
    fi
    printf '%s\n' "${tag:-unknown}"
}

# ----------------------------------------------------------- detect pm
PM="none"
detect_pm() {
    if have apt-get; then PM="apt"
    elif have dnf; then PM="dnf"
    elif have microdnf; then PM="microdnf"
    elif have yum; then PM="yum"
    elif have zypper; then PM="zypper"
    elif have pacman; then PM="pacman"
    else PM="none"
    fi
}

asset_for_pm() {
    case "$PM" in
        apt) echo "$APP_NAME.deb" ;;
        dnf|microdnf|yum|zypper) echo "$APP_NAME.rpm" ;;
        pacman) echo "$APP_NAME.pkg.tar.zst" ;;
        *) echo "$APP_NAME.deb" ;;
    esac
}

pm_installed() { # pm_installed <pkg>  → 0 if installed by the package manager
    case "$PM" in
        apt) have dpkg-query && dpkg-query -W -f='${Status}' "$1" 2>/dev/null | grep -q 'install ok installed' ;;
        pacman) have pacman && pacman -Q "$1" >/dev/null 2>&1 ;;
        dnf|microdnf|yum|zypper) have rpm && rpm -q "$1" >/dev/null 2>&1 ;;
        *)
            if have dpkg-query; then dpkg-query -W -f='${Status}' "$1" 2>/dev/null | grep -q 'install ok installed'
            elif have rpm; then rpm -q "$1" >/dev/null 2>&1
            elif have pacman; then pacman -Q "$1" >/dev/null 2>&1
            else return 1; fi ;;
    esac
}

pm_install() { # pm_install <file>
    local f="$1"
    log "installing with $PM"
    case "$PM" in
        apt)        as_root apt-get install -y --no-install-recommends "$f" ;;
        dnf)        as_root dnf install -y "$f" ;;
        microdnf)   as_root microdnf install -y "$f" ;;
        yum)        as_root yum install -y "$f" ;;
        zypper)     as_root zypper --non-interactive install -y "$f" ;;
        pacman)     as_root pacman -U --noconfirm "$f" ;;
        *)          return 1 ;;
    esac
}

pm_remove() { # pm_remove <pkg>
    case "$PM" in
        apt)        as_root apt-get remove -y "$PKG_NAME" ;;
        dnf|microdnf|yum) as_root "$PM" remove -y "$PKG_NAME" ;;
        zypper)     as_root zypper --non-interactive remove "$PKG_NAME" ;;
        pacman)     as_root pacman -Rns --noconfirm "$PKG_NAME" ;;
        *)          return 1 ;;
    esac
}

# --------------------------------------------------------------- desktop
desktop_file() { # desktop_file <dest>
    mkdir -p "$(dirname "$1")"
    cat > "$1" <<EOF
[Desktop Entry]
Type=Application
Name=CrewLauncher
GenericName=Among Us Launcher
Comment=Among Us launcher with mod support
Exec=$APP_ID
Icon=$APP_ID
Terminal=false
Categories=Game;
StartupNotify=true
StartupWMClass=$APP_NAME
EOF
    chmod 644 "$1"
}

refresh_desktop() {
    local d
    for d in "$HOME/.local/share/applications" /usr/share/applications; do
        [ -d "$d" ] || continue
        have update-desktop-database && update-desktop-database "$d" 2>/dev/null || true
    done
    have gtk-update-icon-cache && gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
}

# --------------------------------------------------------- extract payload
# Extracts the app into $1/app, icons into $1/icons/<size>.png
# Accepts a .deb (app + icons + desktop) or a .tar.gz (app only).
# Layout is discovered, not hardcoded, so Lite/renamed variants work too.
find_app_bin() { # find_app_bin <dir>  → prints the launcher executable inside
    local d="$1"
    [ -d "$d" ] || return 1
    if [ -x "$d/$APP_NAME" ]; then echo "$d/$APP_NAME"; return 0; fi
    find "$d" -maxdepth 1 -type f -perm -u+x 2>/dev/null | head -n1 | grep . || return 1
}

stage_payload() { # stage_payload <file> <dest-dir>
    local file="$1" dest="$2" data root app_root
    mkdir -p "$dest"
    case "$file" in
        *.deb)
            mkdir -p "$dest/ar"
            if have ar; then
                ( cd "$dest/ar" && ar x "$(cd "$(dirname "$file")" && pwd)/$(basename "$file")" )
            elif have bsdtar; then
                bsdtar -xf "$file" -C "$dest/ar"
            else
                warn "no ar/bsdtar; falling back to the portable tarball"
                return 2
            fi
            data=$(ls "$dest/ar"/data.tar.* 2>/dev/null | head -n1 || true)
            [ -n "$data" ] || return 2
            root="$dest/root"
            mkdir -p "$root"
            tar -xf "$data" -C "$root"
            app_root=$(ls -d "$root"/opt/* 2>/dev/null | head -n1 || true)
            [ -n "$app_root" ] && [ -d "$app_root" ] || return 2
            mkdir -p "$dest/app"
            cp -a "$app_root/." "$dest/app/"
            for sz in $ICON_SIZES; do
                if [ -f "$root/usr/share/icons/hicolor/${sz}x${sz}/apps/$APP_ID.png" ]; then
                    mkdir -p "$dest/icons"
                    cp "$root/usr/share/icons/hicolor/${sz}x${sz}/apps/$APP_ID.png" "$dest/icons/$sz.png"
                fi
            done
            ;;
        *.tar.gz|*.tgz)
            mkdir -p "$dest/root"
            tar -xzf "$file" -C "$dest/root"
            app_root=$(ls -d "$dest/root"/*/ 2>/dev/null | head -n1 || true)
            [ -n "$app_root" ] && [ -d "$app_root" ] || return 2
            mkdir -p "$dest/app"
            cp -a "$app_root/." "$dest/app/"
            ;;
        *)
            return 2 ;;
    esac
    find_app_bin "$dest/app" >/dev/null || return 2
    chmod +x "$dest/app"/* 2>/dev/null || true
    return 0
}

# ------------------------------------------------------------ meta info
meta_path() {
    if [ "$MODE" = "system" ] && { is_root || have sudo; }; then
        if [ -d "$OPT_DIR" ] || pm_installed "$PKG_NAME"; then echo "$OPT_DIR/.setup-meta"; return; fi
    fi
    echo "$USER_ROOT/.setup-meta"
}

meta_get() { # meta_get <key> [default]
    local f v; f=$(meta_path)
    v=""
    if [ -f "$f" ]; then v=$(sed -n "s/^$1=//p" "$f" | head -n1); fi
    printf '%s\n' "${v:-${2:-}}"
}

pkg_version() { # version reported by the package manager, if installed by one
    detect_pm
    case "$PM" in
        apt)      dpkg-query -W -f='${Version}' "$PKG_NAME" 2>/dev/null || true ;;
        pacman)   pacman -Q "$PKG_NAME" 2>/dev/null | awk '{print $2}' || true ;;
        dnf|microdnf|yum|zypper)
            if have rpm; then rpm -q --qf '%{VERSION}' "$PKG_NAME" 2>/dev/null || true; fi ;;
        *) echo "" ;;
    esac
}

norm_ver() { printf '%s' "$1" | tr -d '-'; }   # tag 1.0-beta.3 == pkgver 1.0.beta.3

meta_write() { # meta_write <dir> <version> <method>
    {
        mkdir -p "$1"
        printf 'VERSION=%s\nMETHOD=%s\nDATE=%s\n' "$2" "$3" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
            > "$1/.setup-meta"
        chmod 644 "$1/.setup-meta"
    } 2>/dev/null
}

installed_app() { # prints path of the installed binary, empty if none
    local b
    if [ -d "$USER_APP" ] && b=$(find_app_bin "$USER_APP"); then echo "$b"
    elif [ -d "$OPT_DIR" ] && b=$(find_app_bin "$OPT_DIR"); then echo "$b"
    elif command -v "$APP_ID" >/dev/null 2>&1; then command -v "$APP_ID"
    else echo ""
    fi
}

# --------------------------------------------------------------- install
install_crew() {
    detect_pm

    if [ "$MODE" = "system" ] && ! is_root && ! have sudo; then
        die "system install needs root. Re-run with sudo, or use: $0 --user install"
    fi

    local asset file stage method version
    version=$(github_version)
    [ -n "${SETUP_FILE:-}" ] && file="$SETUP_FILE"

    if [ -z "${file:-}" ]; then
        if [ "$MODE" = "system" ] && [ "$PM" != "none" ]; then
            asset=$(asset_for_pm)
        else
            asset="$APP_NAME.deb"   # universal payload: app + icons + desktop
        fi
        TMP=$(mktemp -d)
        log "downloading $asset"
        fetch "$ROOT_LINK$asset" "$TMP/$asset"
        file="$TMP/$asset"
    else
        log "using local file: $file"
        [ -f "$file" ] || die "local file not found: $file"
        file="$(cd "$(dirname "$file")" && pwd)/$(basename "$file")"
        TMP=$(mktemp -d)
    fi

    # --- fast path: native package manager, system-wide
    if [ "$MODE" = "system" ] && [ "$PM" != "none" ] && pm_install "$file"; then
        method="$PM"
        meta_write "$OPT_DIR" "$version" "$method" 2>/dev/null \
            || meta_write "$USER_ROOT" "$version" "$method"
        finish "$method" "$version"
        return 0
    fi

    # --- fallback: unpack payload ourselves
    log "unpacking payload"
    stage="$TMP/stage"
    local stage_rc=0 app_bin bin_name
    stage_payload "$file" "$stage" || stage_rc=$?
    if [ "$stage_rc" -ne 0 ] && [ -z "${SETUP_FILE:-}" ] \
       && [ "$file" != "$TMP/$APP_NAME.tar.gz" ]; then
        log "extractor unavailable, downloading the portable tarball"
        fetch "$ROOT_LINK$APP_NAME.tar.gz" "$TMP/$APP_NAME.tar.gz"
        stage_rc=0
        stage_payload "$TMP/$APP_NAME.tar.gz" "$stage" || stage_rc=$?
    fi
    [ "$stage_rc" -eq 0 ] || die "could not extract a launcher from $(basename "$file")"
    app_bin=$(find_app_bin "$stage/app") || die "no launcher executable in the payload"
    bin_name=$(basename "$app_bin")

    if [ "$MODE" = "system" ]; then
        log "installing to $OPT_DIR"
        as_root rm -rf "$OPT_DIR"
        as_root mkdir -p "$OPT_DIR"
        as_root cp -a "$stage/app/." "$OPT_DIR/"
        as_root mkdir -p /usr/bin
        as_root ln -sf "$OPT_DIR/$bin_name" "/usr/bin/$APP_ID"
        desktop_file "$TMP/$DESKTOP_NAME"
        as_root install -Dm644 "$TMP/$DESKTOP_NAME" "/usr/share/applications/$DESKTOP_NAME"
        if [ -d "$stage/icons" ]; then
            for sz in $ICON_SIZES; do
                [ -f "$stage/icons/$sz.png" ] && \
                    as_root install -Dm644 "$stage/icons/$sz.png" "/usr/share/icons/hicolor/${sz}x${sz}/apps/$APP_ID.png"
            done
        fi
        method="manual"
        meta_write "$OPT_DIR" "$version" "$method"
    else
        log "installing to $USER_ROOT"
        rm -rf "$USER_APP"
        mkdir -p "$USER_ROOT" "$BIN_DIR" "$HOME/.local/share/applications"
        cp -a "$stage/app" "$USER_APP"
        ln -sf "$USER_APP/$bin_name" "$BIN_LINK"
        desktop_file "$HOME/.local/share/applications/$DESKTOP_NAME"
        if [ -d "$stage/icons" ]; then
            for sz in $ICON_SIZES; do
                [ -f "$stage/icons/$sz.png" ] && \
                    install -Dm644 "$stage/icons/$sz.png" "$HOME/.local/share/icons/hicolor/${sz}x${sz}/apps/$APP_ID.png"
            done
        fi
        method="user"
        meta_write "$USER_ROOT" "$version" "$method"
    fi

    finish "$method" "$version"
}

finish() { # finish <method> <version>
    self_install
    refresh_desktop
    log "CrewLauncher installed (version: $2, method: $1)"
    case ":$PATH:" in
        *":$BIN_DIR:"*) log "run it with: $APP_ID" ;;
        *) log "run it with: $BIN_DIR/$APP_ID  (add $BIN_DIR to PATH)" ;;
    esac
    log "update any time with: crewlauncher-setup update"
}

self_install() { # best-effort: keep a copy so 'crewlauncher-setup update' works later
    local src="${BASH_SOURCE[0]:-}"
    mkdir -p "$(dirname "$SETUP_BIN")" 2>/dev/null || return 0
    if [ -f "$src" ] && [ ! -L "$src" ]; then
        cp "$src" "$SETUP_BIN" 2>/dev/null || return 0
    else
        fetch "$RAW_LINK" "$SETUP_BIN" 2>/dev/null || return 0
    fi
    chmod 755 "$SETUP_BIN" 2>/dev/null || true
    if is_root && [ -n "${SUDO_USER:-}" ] && have chown; then
        chown "$SUDO_USER" "$SETUP_BIN" 2>/dev/null || true
    fi
}

# ---------------------------------------------------------------- update
update_crew() {
    if ! is_installed >/dev/null 2>&1; then
        log "not installed yet — installing"
        install_crew
        return 0
    fi
    local latest current
    latest=$(github_version)
    current=$(meta_get VERSION)
    [ -z "$current" ] && current=$(pkg_version)
    if [ "$latest" != "unknown" ] && [ -n "$current" ] \
       && [ "$(norm_ver "$latest")" = "$(norm_ver "$current")" ]; then
        log "already up to date ($current)"
        return 0
    fi
    log "updating: ${current:-unknown} -> $latest"
    install_crew
}

# ------------------------------------------------------------ is-installed
is_installed() {
    detect_pm
    local path="" version method
    path=$(installed_app)
    if pm_installed "$PKG_NAME" || { [ -n "$path" ] && [ -x "$path" ]; }; then
        version=$(meta_get VERSION); [ -z "$version" ] && version=$(pkg_version)
        method=$(meta_get METHOD); [ -z "$method" ] && method="${PM:-manual}"
        echo "CrewLauncher is installed."
        echo "  version : ${version:-unknown}"
        echo "  method  : $method"
        echo "  path    : ${path:-/usr/bin/$APP_ID}"
        echo "  command : $APP_ID"
        return 0
    fi
    echo "CrewLauncher is not installed."
    return 1
}

# -------------------------------------------------------------- uninstall
uninstall_crew() {
    detect_pm
    local removed=0
    if pm_installed "$PKG_NAME"; then
        log "removing package $PKG_NAME"
        if pm_remove "$PKG_NAME"; then removed=1; fi
    fi
    if [ -d "$OPT_DIR" ] || [ -L "/usr/bin/$APP_ID" ] \
       || [ -f "/usr/share/applications/$DESKTOP_NAME" ]; then
        log "removing $OPT_DIR"
        as_root rm -rf "$OPT_DIR" "/usr/bin/$APP_ID" "/usr/share/applications/$DESKTOP_NAME"
        for sz in $ICON_SIZES; do
            as_root rm -f "/usr/share/icons/hicolor/${sz}x${sz}/apps/$APP_ID.png"
        done
        removed=1
    fi
    if [ -d "$USER_APP" ] || [ -L "$BIN_LINK" ] || [ -f "$HOME/.local/share/applications/$DESKTOP_NAME" ]; then
        log "removing $USER_APP"
        rm -rf "$USER_APP" "$BIN_LINK" "$HOME/.local/share/applications/$DESKTOP_NAME"
        for sz in $ICON_SIZES; do
            rm -f "$HOME/.local/share/icons/hicolor/${sz}x${sz}/apps/$APP_ID.png"
        done
        removed=1
    fi
    rm -f "$SETUP_BIN" 2>/dev/null || true
    refresh_desktop
    if [ "$removed" -eq 1 ]; then log "CrewLauncher uninstalled."
    else echo "CrewLauncher is not installed."; fi
}

# ------------------------------------------------------------------ main
case "$CMD" in
    install)     install_crew ;;
    update)      update_crew ;;
    is-installed) is_installed ;;
    uninstall)   uninstall_crew ;;
esac
