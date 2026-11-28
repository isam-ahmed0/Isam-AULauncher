#!/bin/sh
# CrewLauncher launcher for the thin, source-based Linux packages.
#
# The package installs the Python sources and assets but not PySide6/webview.
# System packages are preferred; if they are missing, a private virtualenv is
# bootstrapped once from src/launcher/requirements.txt on first launch.
#
# This script resolves symlinks because both /usr/bin/isam-au and
# ~/.local/bin/isam-au point at it.
set -eu

self=$0
links=0
while [ -L "$self" ] && [ "$links" -lt 40 ]; do
    dir=$(CDPATH= cd -P -- "$(dirname -- "$self")" && pwd)
    target=$(readlink -- "$self")
    case $target in
        /*) self=$target ;;
        *)  self=$dir/$target ;;
    esac
    links=$((links + 1))
done

root=$(CDPATH= cd -P -- "$(dirname -- "$self")" && pwd)
src=$root/src/launcher

py=${CREWLAUNCHER_PYTHON:-python3}
if ! command -v "$py" >/dev/null 2>&1; then
    echo "CrewLauncher: python3 is required but was not found on PATH." >&2
    exit 1
fi

# find_spec avoids importing the heavy Qt/webview modules just to test them.
if ! "$py" -c '
import importlib.util
mods = ("PySide6.QtWidgets", "PySide6.QtWebEngineWidgets", "webview", "qtpy",
        "requests", "pypresence", "packaging", "tkinter")
raise SystemExit(0 if all(importlib.util.find_spec(m) for m in mods) else 1)
' >/dev/null 2>&1; then
    venv="${XDG_DATA_HOME:-$HOME/.local/share}/IsamAULauncher/venv"
    if [ ! -x "$venv/bin/python" ]; then
        printf '==> Installing CrewLauncher Python dependencies into %s\n' "$venv" >&2
        mkdir -p "$(dirname -- "$venv")"
        if ! "$py" -m venv "$venv"; then
            echo "CrewLauncher: could not create a virtual environment." >&2
            echo "Install python3-venv (Debian/Ubuntu) or python (Arch) and retry." >&2
            exit 1
        fi
        "$venv/bin/python" -m pip install --quiet --upgrade pip || true
        if ! "$venv/bin/python" -m pip install --quiet -r "$src/requirements.txt"; then
            echo "CrewLauncher: dependency installation failed (check your network)." >&2
            exit 1
        fi
    fi
    py=$venv/bin/python
fi

PYTHONPATH=$src${PYTHONPATH:+:$PYTHONPATH}
export PYTHONPATH
exec "$py" "$src/main.py" "$@"
