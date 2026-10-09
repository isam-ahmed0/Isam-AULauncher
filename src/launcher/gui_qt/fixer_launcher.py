"""Locate and launch the standalone Itch Login Fixer.

On Windows the compiled ``Itch_Login_Fixer.exe`` is launched directly.
On Linux the Windows fixer is launched through the user's global Wine
(``wine`` must already be installed) so it writes the token into the global
Wine prefix. Nothing here installs Wine or modifies any prefix.
"""
import sys
import subprocess
from pathlib import Path

from platform_utils import IS_WINDOWS, find_wine, wine_env

LAUNCHED = "launched"
NO_WINE = "no_wine"
MISSING = "missing"


def find_itch_fixer():
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
        candidates = [
            base / "Fixer" / "Itch_Login_Fixer.exe",
            base / "Itch_Login_Fixer.exe",
        ]
    else:
        root = Path(__file__).resolve().parents[3]
        candidates = [
            root / "release" / "Fixer" / "Itch_Login_Fixer.exe",
            root / "src" / "fixer" / "Itch_Login_Fixer.py",
        ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def launch_itch_fixer(prefix=None) -> str:
    """Return LAUNCHED, NO_WINE or MISSING. Never blocks on the child.

    ``prefix`` pins the Wine prefix the fixer writes its token into; when
    omitted the global prefix (``$WINEPREFIX`` or ``~/.wine``) is used.
    """
    fixer = find_itch_fixer()

    if IS_WINDOWS:
        if fixer is None:
            return MISSING
        if fixer.suffix.lower() == ".exe":
            subprocess.Popen([str(fixer)])
        else:
            subprocess.Popen([sys.executable, str(fixer)])
        return LAUNCHED

    # Linux/macOS: the fixer is a Windows app, run it under the global Wine.
    if fixer is None or fixer.suffix.lower() != ".exe":
        return MISSING
    wine = find_wine()
    if not wine:
        return NO_WINE
    subprocess.Popen([wine, str(fixer)], env=wine_env(prefix))
    return LAUNCHED
