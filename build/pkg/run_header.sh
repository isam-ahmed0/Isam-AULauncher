#!/bin/sh
# CrewLauncher self-extracting installer / uninstaller.
#
#   ./CrewLauncher-<ver>.run            install for the current user (~/.local)
#   ./CrewLauncher-<ver>.run --system   install system-wide (/opt, needs root)
#   ./CrewLauncher-<ver>.run --uninstall
#
# No package manager or root is required for the default per-user install.
set -eu

APP_ID="isam-au"
APP_NAME="CrewLauncher"
VERSION="@VERSION@"
MARKER="__ISAMAU_PAYLOAD_BELOW__"

usage() {
    cat <<EOF
$APP_NAME $VERSION

Usage: $0 [--user | --system | --uninstall]

  --user        Install to ~/.local (default, no root)
  --system      Install to /opt and /usr (needs root/sudo)
  --uninstall   Remove an existing install
  -h, --help    Show this help
EOF
}

MODE="user"
for arg in "$@"; do
    case "$arg" in
        --user) MODE="user" ;;
        --system) MODE="system" ;;
        --uninstall) MODE="uninstall" ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $arg" >&2; usage; exit 2 ;;
    esac
done

as_root() {
    if [ "$(id -u)" -eq 0 ]; then
        "$@"
    elif command -v sudo >/dev/null 2>&1; then
        sudo "$@"
    else
        echo "This step needs root; re-run with sudo or use the per-user install." >&2
        exit 1
    fi
}

if [ "$MODE" = "uninstall" ]; then
    rm -rf "$HOME/.local/share/IsamAULauncher" \
           "$HOME/.local/share/applications/$APP_ID.desktop" \
           "$HOME/.local/bin/$APP_ID"
    find "$HOME/.local/share/icons/hicolor" -name "$APP_ID.png" -delete 2>/dev/null || true
    if [ -e /opt/isam-aulauncher ] || [ -e "/usr/bin/$APP_ID" ]; then
        if [ "$(id -u)" -eq 0 ] || command -v sudo >/dev/null 2>&1; then
            as_root rm -rf /opt/isam-aulauncher "/usr/share/applications/$APP_ID.desktop" "/usr/bin/$APP_ID"
            find "/usr/share/icons/hicolor" -name "$APP_ID.png" -delete 2>/dev/null || true
        fi
    fi
    echo "Uninstalled $APP_NAME."
    exit 0
fi

PAYLOAD_LINE=$(awk "/^${MARKER}\$/ {print NR + 1; exit}" "$0" || true)
[ -n "${PAYLOAD_LINE:-}" ] || { echo "Corrupt installer (no payload)." >&2; exit 1; }

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT INT TERM
tail -n +"$PAYLOAD_LINE" "$0" | tar -xJ -C "$TMP"

[ -e "$TMP/app/CrewLauncher" ] || { echo "Corrupt installer (no app)." >&2; exit 1; }
chmod +x "$TMP/app/CrewLauncher" 2>/dev/null || true

if [ "$MODE" = "system" ]; then
    DEST="/opt/isam-aulauncher"
    as_root rm -rf "$DEST"
    as_root install -d "$DEST"
    as_root cp -a "$TMP/app/." "$DEST/"
    as_root install -d /usr/bin
    as_root ln -sf "$DEST/CrewLauncher" "/usr/bin/$APP_ID"
    as_root install -Dm644 "$TMP/$APP_ID.desktop" "/usr/share/applications/$APP_ID.desktop"
    for sz in 16 32 48 64 128 256; do
        [ -f "$TMP/icons/$sz.png" ] && as_root install -Dm644 "$TMP/icons/$sz.png" "/usr/share/icons/hicolor/${sz}x${sz}/apps/$APP_ID.png"
    done
    echo "Installed $APP_NAME $VERSION to $DEST (command: $APP_ID)"
else
    DATA="$HOME/.local/share/IsamAULauncher"
    APPS="$HOME/.local/share/applications"
    ICON_ROOT="$HOME/.local/share/icons/hicolor"
    BIN="$HOME/.local/bin"
    rm -rf "$DATA/app"
    install -d "$DATA"
    cp -a "$TMP/app" "$DATA/app"
    mkdir -p "$APPS" "$BIN"
    ln -sf "$DATA/app/CrewLauncher" "$BIN/$APP_ID"
    install -m644 "$TMP/$APP_ID.desktop" "$APPS/$APP_ID.desktop"
    for sz in 16 32 48 64 128 256; do
        [ -f "$TMP/icons/$sz.png" ] && install -Dm644 "$TMP/icons/$sz.png" "$ICON_ROOT/${sz}x${sz}/apps/$APP_ID.png"
    done
    echo "Installed $APP_NAME $VERSION to $DATA (command: $APP_ID)"
    case ":$PATH:" in
        *":$HOME/.local/bin:"*) ;;
        *) echo "NOTE: add $HOME/.local/bin to your PATH to use the '$APP_ID' command." ;;
    esac
fi

command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

echo "Done."
exit 0

__ISAMAU_PAYLOAD_BELOW__
