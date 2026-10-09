"""Cross-platform helpers for Windows / Linux / macOS.

Nothing here executes Wine or touches Wine configuration. These helpers only
locate the global Wine prefix so the launcher can read/write the same
``AppData/LocalLow`` files the Windows game uses.
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path

IS_WINDOWS = sys.platform.startswith("win")
IS_LINUX = sys.platform.startswith("linux")
IS_MAC = sys.platform == "darwin"


def open_local_path(path):
    """Open a file or folder with the OS default handler."""
    p = str(path)
    if IS_WINDOWS:
        os.startfile(p)
    elif IS_MAC:
        subprocess.Popen(["open", p])
    else:
        subprocess.Popen(["xdg-open", p])


def find_wine():
    """Return the path to the wine executable, or None. Never installs wine."""
    return shutil.which("wine")


def wine_prefix() -> Path:
    """The user's global Wine prefix ($WINEPREFIX or ~/.wine)."""
    env = os.environ.get("WINEPREFIX")
    if env:
        return Path(env)
    return Path.home() / ".wine"


def _wine_user_dir(prefix: Path) -> Path:
    users = prefix / "drive_c" / "users"
    if users.exists():
        entries = [p for p in sorted(users.iterdir()) if p.is_dir()]
        for candidate in entries:
            if (candidate / "AppData").exists():
                return candidate
        for candidate in entries:
            if candidate.name.lower() not in ("public", "default"):
                return candidate
    user = os.environ.get("USER") or os.environ.get("LOGNAME") or "user"
    return users / user


def wine_local_low() -> Path:
    """The Windows LocalLow equivalent inside the global Wine prefix."""
    return _wine_user_dir(wine_prefix()) / "AppData" / "LocalLow"


def itch_token_dir() -> Path:
    """Directory Among Us reads its itch.io token from, per platform."""
    if IS_WINDOWS:
        return Path(os.environ.get("USERPROFILE", "")) / "AppData" / "LocalLow" / "Innersloth" / "Among Us"
    if IS_LINUX:
        return wine_local_low() / "Innersloth" / "Among Us"
    return Path.home() / "Library" / "Application Support" / "Innersloth" / "Among Us"
