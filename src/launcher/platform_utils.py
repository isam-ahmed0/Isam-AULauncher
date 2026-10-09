"""Cross-platform helpers for Windows / Linux / macOS.

Nothing here executes Wine or touches Wine configuration. These helpers only
locate the global Wine prefix so the launcher can read/write the same
``AppData/LocalLow`` files the Windows game uses.
"""
import json
import os
import sys
import shutil
import subprocess
from pathlib import Path

IS_WINDOWS = sys.platform.startswith("win")
IS_LINUX = sys.platform.startswith("linux")
IS_MAC = sys.platform == "darwin"


def external_env(extra=None):
    """A sanitized environment for launching external tools.

    The launcher may run from a virtualenv (or a PyInstaller bundle). Those
    environments put the launcher's own Python (and bundled libs) first, which
    breaks external programs -- most notably the ``lutris`` launcher script,
    whose ``#!/usr/bin/env python3`` shebang would otherwise pick the venv
    Python and fail with "No module named 'lutris'".

    This strips the venv/PyInstaller contamination while keeping the system
    tools (e.g. ``/usr/bin``) intact.
    """
    env = os.environ.copy()

    # Don't leak the launcher's Python configuration into child processes.
    for key in ("VIRTUAL_ENV", "PYTHONHOME", "PYTHONPATH", "PYTHONSTARTUP",
                "PYTHONUSERBASE", "PYTHONEXECUTABLE"):
        env.pop(key, None)

    # Drop the active venv's bin directory from PATH (but never /usr/bin), so
    # `#!/usr/bin/env python3` resolves to the system Python.
    venv_bins = set()
    prefix = getattr(sys, "prefix", None)
    base_prefix = getattr(sys, "base_prefix", None)
    if prefix and prefix != base_prefix:
        venv_bins.add(os.path.abspath(os.path.join(prefix, "bin")))
    venv = os.environ.get("VIRTUAL_ENV")
    if venv:
        venv_bins.add(os.path.abspath(os.path.join(venv, "bin")))
    if venv_bins:
        parts = [p for p in env.get("PATH", "").split(os.pathsep)
                 if p and os.path.abspath(p) not in venv_bins]
        env["PATH"] = os.pathsep.join(parts)

    # Frozen builds inject bundled libraries that break external GUI apps.
    if getattr(sys, "frozen", False):
        for key in ("LD_LIBRARY_PATH", "QT_PLUGIN_PATH", "QML2_IMPORT_PATH",
                    "QT_QPA_PLATFORM_PLUGIN_PATH", "GI_TYPELIB_PATH"):
            env.pop(key, None)
        orig_ld = os.environ.get("LD_LIBRARY_PATH_ORIG")
        if orig_ld:
            env["LD_LIBRARY_PATH"] = orig_ld

    if extra:
        env.update(extra)
    return env


def open_local_path(path):
    """Open a file or folder with the OS default handler."""
    p = str(path)
    if IS_WINDOWS:
        os.startfile(p)
    elif IS_MAC:
        subprocess.Popen(["open", p], env=external_env())
    else:
        subprocess.Popen(["xdg-open", p], env=external_env())


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


def itch_token_dir(prefix=None) -> Path:
    """Directory Among Us reads its itch.io token from, per platform.

    On Linux this is inside the given (or global) Wine prefix so it always
    matches the prefix the game is launched with.
    """
    if IS_WINDOWS:
        return Path(os.environ.get("USERPROFILE", "")) / "AppData" / "LocalLow" / "Innersloth" / "Among Us"
    if IS_LINUX:
        p = Path(prefix) if prefix else wine_prefix()
        return _wine_user_dir(p) / "AppData" / "LocalLow" / "Innersloth" / "Among Us"
    return Path.home() / "Library" / "Application Support" / "Innersloth" / "Among Us"


def default_game_dir() -> Path:
    """Default folder the launcher installs Among Us into."""
    if IS_WINDOWS:
        return Path("C:/Isam-AULauncher/Among-Us")
    return Path.home() / "Games" / "Isam-AULauncher" / "Among-Us"


def wine_env(prefix=None):
    """Environment for running Wine, pinned to the given (or global) prefix."""
    env = external_env()
    env["WINEPREFIX"] = str(prefix) if prefix else str(wine_prefix())
    return env


# ---------------------------------------------------------------------------
# Lutris integration
# ---------------------------------------------------------------------------
_UNSET = object()
_lutris_cmd_cache = _UNSET


def find_lutris(refresh=False):
    """Return the command prefix used to invoke Lutris, or None.

    Prefers a native ``lutris`` binary, then the Flatpak ``net.lutris.Lutris``
    app. Returns a list (e.g. ``["lutris"]`` or
    ``["flatpak", "run", "net.lutris.Lutris"]``) so callers can append args.
    The result is cached for the session (pass ``refresh=True`` to re-probe).
    """
    global _lutris_cmd_cache
    if _lutris_cmd_cache is not _UNSET and not refresh:
        return _lutris_cmd_cache

    result = None
    if IS_LINUX:
        native = shutil.which("lutris")
        if native:
            # Verify it actually runs: the launcher script can break when a
            # venv (or the frozen bundle) leaks its Python into the child PATH.
            if _lutris_usable([native]):
                result = [native]
        if result is None:
            flatpak = shutil.which("flatpak")
            if flatpak:
                try:
                    out = subprocess.run(
                        [flatpak, "list", "--columns=application"],
                        capture_output=True, text=True, timeout=5,
                        env=external_env(),
                    )
                    if "net.lutris.Lutris" in out.stdout:
                        fp = [flatpak, "run", "net.lutris.Lutris"]
                        if _lutris_usable(fp):
                            result = fp
                except Exception:
                    pass

    _lutris_cmd_cache = result
    return result


def _lutris_usable(cmd):
    """True if the Lutris command can start (imports its module) successfully."""
    try:
        out = subprocess.run(
            cmd + ["--version"],
            capture_output=True, text=True, timeout=15, env=external_env(),
        )
        combined = (out.stdout or "") + (out.stderr or "")
        return out.returncode == 0 and "No module named" not in combined
    except Exception:
        return False


def lutris_list_games(lutris_cmd=None):
    """Return Lutris's game list as a list of dicts (best effort)."""
    cmd = lutris_cmd or find_lutris()
    if not cmd:
        return []
    try:
        out = subprocess.run(
            cmd + ["-l", "--json"],
            capture_output=True, text=True, timeout=15, env=external_env(),
        )
        if out.returncode != 0 or not out.stdout.strip():
            return []
        data = json.loads(out.stdout)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def lutris_find_entry(game_path, cached_id=None, lutris_cmd=None):
    """Find the Lutris game entry for an install, or None.

    Matches by cached numeric id first, then by the game's install directory
    (``directory`` in ``lutris -l --json``). Returns the raw Lutris dict with
    keys such as ``id``, ``name``, ``slug``, ``runner`` and ``directory``.
    """
    gp_res = None
    try:
        gp_res = Path(game_path).resolve()
    except Exception:
        pass
    try:
        cached_id = int(cached_id) if cached_id is not None else None
    except (TypeError, ValueError):
        cached_id = None

    for g in lutris_list_games(lutris_cmd):
        if cached_id is not None and g.get("id") == cached_id:
            return g
        d = g.get("directory")
        if d and gp_res is not None:
            try:
                if Path(d).resolve() == gp_res:
                    return g
            except Exception:
                pass
    return None


def format_lutris_entry(entry):
    """Human-readable name/identifier for a Lutris entry (or a fallback)."""
    if not entry:
        return "Not in Lutris"
    parts = [entry.get("name") or "Unnamed"]
    if entry.get("id") is not None:
        parts.append(f"id {entry['id']}")
    if entry.get("slug"):
        parts.append(f"slug {entry['slug']}")
    return " — ".join(parts)


def lutris_run(game_id, lutris_cmd=None):
    """Launch a Lutris game by numeric id. Returns the Popen or None."""
    cmd = lutris_cmd or find_lutris()
    if not cmd:
        return None
    return subprocess.Popen(cmd + [f"lutris:rungameid/{game_id}"], env=external_env())


def lutris_install_script(yaml_path, lutris_cmd=None):
    """Open Lutris's installer with a generated YAML (Lutris asks to confirm).

    Returns the Popen, or None if Lutris is unavailable.
    """
    cmd = lutris_cmd or find_lutris()
    if not cmd:
        return None
    return subprocess.Popen(cmd + ["-i", str(yaml_path)], env=external_env())


def lutris_unique_name_slug(base_name, base_slug, existing_names):
    """Pick a name/slug that does not collide with existing Lutris entries."""
    names = {n.strip().lower() for n in existing_names if n}
    name = base_name
    slug = base_slug
    i = 2
    while name.strip().lower() in names:
        name = f"{base_name} ({i})"
        slug = f"{base_slug}-{i}"
        i += 1
    return name, slug


def create_desktop_shortcut(name, exe_path, working_dir, prefix=None,
                            lutris_id=None, icon_source=None):
    """Write a freedesktop .desktop launcher. Returns the .desktop path.

    Prefers launching through Lutris when an entry id is provided; otherwise
    runs the game with Wine in the given (or global) prefix.
    """
    apps_dir = Path.home() / ".local" / "share" / "applications"
    apps_dir.mkdir(parents=True, exist_ok=True)
    slug_name = "isam-au"
    desktop_path = apps_dir / f"{slug_name}.desktop"

    lutris_cmd = find_lutris() if lutris_id else None
    if lutris_id and lutris_cmd:
        exec_line = " ".join(lutris_cmd) + f" lutris:rungameid/{lutris_id}"
    else:
        pfx = prefix or wine_prefix()
        exec_line = f'env WINEPREFIX="{pfx}" wine "{exe_path}"'

    icon_path = _ensure_icon(icon_source)
    lines = [
        "[Desktop Entry]",
        "Type=Application",
        f"Name={name}",
        f"Comment=Launch {name}",
        f"Exec={exec_line}",
        f"Path={working_dir}",
        "Terminal=false",
        "Categories=Game;",
        "StartupNotify=true",
    ]
    if icon_path:
        lines.append(f"Icon={icon_path}")
    content = "\n".join(lines) + "\n"

    desktop_path.write_text(content)
    desktop_path.chmod(0o755)

    desktop_dir = Path.home() / "Desktop"
    if desktop_dir.is_dir():
        try:
            copy = desktop_dir / f"{slug_name}.desktop"
            copy.write_text(content)
            copy.chmod(0o755)
        except OSError:
            pass
    return desktop_path


def _ensure_icon(source):
    """Render a PNG icon for .desktop files from any Qt-readable image."""
    if not source:
        return None
    source = Path(source)
    if not source.exists():
        return None
    icons_dir = Path.home() / ".local" / "share" / "icons" / "hicolor" / "256x256" / "apps"
    icons_dir.mkdir(parents=True, exist_ok=True)
    target = icons_dir / "isam-au.png"
    if target.exists():
        return str(target)
    try:
        from PySide6.QtCore import QSize
        from PySide6.QtGui import QIcon
        expiry = QIcon(str(source))
        pix = expiry.pixmap(QSize(256, 256))
        if pix.isNull() or not pix.save(str(target)):
            return None
        return str(target)
    except Exception:
        return None
