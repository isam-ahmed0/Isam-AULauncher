"""Automatic Qt platform selection (Linux).

Qt 6.5+ refuses to load the ``xcb`` (X11) plugin when ``libxcb-cursor`` is
missing on the system, and a failed platform load **aborts the process** with
a native crash that Python cannot catch. To keep the launcher working for
every user, candidate platforms are probed in a throwaway subprocess *before*
the real ``QApplication`` is created; the first one that starts cleanly is
selected via ``QT_QPA_PLATFORM``. If none work the caller can fall back to
the Lite (tkinter) interface.

A user-set ``QT_QPA_PLATFORM`` is always respected and disables probing.
"""
import logging
import os
import subprocess
import sys
from pathlib import Path

_PROBE_CODE = (
    "import sys\n"
    "from PySide6.QtGui import QGuiApplication\n"
    "app = QGuiApplication(sys.argv)\n"
    "print('Qt platform OK')\n"
)

_PROBE_TIMEOUT = 30

_BACKEND_PLATFORMS = {"x11": "xcb", "wayland": "wayland"}


def _probe(platform):
    """True if a QGuiApplication inside a child process starts cleanly."""
    env = dict(os.environ)
    env["QT_QPA_PLATFORM"] = platform
    try:
        result = subprocess.run(
            [sys.executable, "-c", _PROBE_CODE],
            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=_PROBE_TIMEOUT,
        )
        return result.returncode == 0
    except Exception:
        logging.debug("Qt platform probe failed for %s", platform, exc_info=True)
        return False


def detect_platform(preferred=""):
    """Return the first Qt platform that initializes, or None.

    ``preferred`` is the user's display-backend setting ("" for auto, "x11"
    or "wayland"). It is tried first; the auto order (X11, then Wayland) is
    used as a fallback so a bad preference can never break startup.
    """
    if sys.platform.startswith("win") or sys.platform == "darwin":
        return None
    candidates = []
    mapped = _BACKEND_PLATFORMS.get((preferred or "").strip().lower())
    if mapped:
        candidates.append(mapped)
    if os.environ.get("DISPLAY") and "xcb" not in candidates:
        candidates.append("xcb")
    if os.environ.get("WAYLAND_DISPLAY") and "wayland" not in candidates:
        candidates.append("wayland")
    if not candidates:
        candidates.append("xcb")
    for platform in candidates:
        if _probe(platform):
            return platform
    return None


def prepare_qt_platform(preferred=""):
    """Pick and export ``QT_QPA_PLATFORM`` before PySide6 is imported.

    Returns True when a platform is available (including a user-forced one),
    False when no candidate could start and the caller should fall back to
    another interface.
    """
    if os.environ.get("QT_QPA_PLATFORM"):
        return True
    if sys.platform.startswith("win") or sys.platform == "darwin":
        return True
    platform = detect_platform(preferred)
    if platform:
        os.environ["QT_QPA_PLATFORM"] = platform
        logging.info("Selected Qt platform: %s", platform)
        return True
    return False


def distro_hint():
    """Human-readable package hint for the usual missing xcb dependency."""
    text = ""
    try:
        text = Path("/etc/os-release").read_text(encoding="utf-8", errors="replace")
    except Exception:
        pass
    lower = text.lower()
    if any(k in lower for k in ("cachyos", "arch", "manjaro", "endeavouros")):
        return 'Install it with:  sudo pacman -S xcb-util-cursor'
    if any(k in lower for k in ("fedora", "rhel", "centos", "suse", "opensuse", "nobara")):
        return 'Install it with:  sudo dnf install xcb-util-cursor'
    if any(k in lower for k in ("debian", "ubuntu", "mint", "pop!_os", "elementary", "zorin")):
        return 'Install it with:  sudo apt install libxcb-cursor0'
    return 'Install the "xcb-util-cursor" / "libxcb-cursor0" package for your distribution.'
