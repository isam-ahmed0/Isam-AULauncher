"""Cross-platform helpers for Windows / Linux / macOS.

Nothing here executes Wine or touches Wine configuration. These helpers only
locate the global Wine prefix so the launcher can read/write the same
``AppData/LocalLow`` files the Windows game uses.
"""
import json
import logging
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
    # Strip the GTK/GIO/GDK/Qt overrides too so host tools (Lutris, xdg-open,
    # Wine) load the distro's own libraries on any Linux distribution.
    if getattr(sys, "frozen", False):
        for key in ("LD_LIBRARY_PATH", "QT_PLUGIN_PATH", "QML2_IMPORT_PATH",
                    "QT_QPA_PLATFORM_PLUGIN_PATH", "GI_TYPELIB_PATH",
                    "GDK_PIXBUF_MODULE_FILE", "GIO_EXTRA_MODULES", "GTK_PATH",
                    "GTK_EXE_PREFIX", "GTK_DATA_PREFIX", "GSETTINGS_SCHEMA_DIR"):
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


def find_wine(override=None):
    """Return the path to the wine executable, or None.

    Honours an explicit ``override`` (the user-selected wine binary) before
    falling back to whatever ``wine`` is on PATH. Never installs wine.
    """
    if override:
        p = Path(override).expanduser()
        if p.is_file() and os.access(str(p), os.X_OK):
            return str(p)
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


def wine_env(prefix=None, gpu=None):
    """Environment for running Wine, pinned to the given (or global) prefix.

    ``gpu`` is a GPU id from :mod:`graphics`; when set, the matching PRIME /
    render-offload variables are injected so the game runs on the chosen GPU.
    """
    env = external_env()
    env["WINEPREFIX"] = str(prefix) if prefix else str(wine_prefix())
    try:
        import graphics
        env.update(graphics.gpu_env(gpu))
    except Exception:
        logging.exception("Failed to build GPU environment")
    return env


# ---------------------------------------------------------------------------
# Lutris integration
# ---------------------------------------------------------------------------
_UNSET = object()
_lutris_cmd_cache = _UNSET
_lutris_override = None
_lutris_override_loaded = False

# Extra places distros drop the native binary when it isn't on PATH.
_LUTRIS_EXTRA_DIRS = (
    "/usr/bin", "/usr/local/bin", "/bin", "/snap/bin",
    "/run/current-system/sw/bin", "/var/lib/flatpak/exports/bin",
)
_LUTRIS_FLATPAK_ID = "net.lutris.Lutris"


def _load_override_once():
    """Lazily pull the persisted override so callers need not pre-load it."""
    global _lutris_override, _lutris_override_loaded
    if _lutris_override_loaded:
        return
    _lutris_override_loaded = True
    try:
        import config
        _lutris_override = config.get_lutris_cmd_override()
    except Exception:
        _lutris_override = None


def get_lutris_override():
    """The user-forced Lutris command (list of args), or None."""
    _load_override_once()
    return list(_lutris_override) if _lutris_override else None


def set_lutris_override(cmd, persist=True):
    """Force ``find_lutris`` to use ``cmd`` (the Tools > Fix Lutris button).

    ``cmd`` may be a list of args or a single string/path. Pass ``None`` to
    clear it. Persists to the config file unless ``persist=False``.
    """
    global _lutris_override, _lutris_cmd_cache, _lutris_override_loaded
    if not cmd:
        _lutris_override = None
    elif isinstance(cmd, (list, tuple)):
        _lutris_override = [str(c) for c in cmd]
    else:
        _lutris_override = [str(cmd)]
    _lutris_override_loaded = True
    _lutris_cmd_cache = _UNSET
    if persist:
        try:
            import config
            config.set_lutris_cmd_override(_lutris_override)
        except Exception:
            logging.exception("Failed to persist Lutris command override")


def clear_lutris_override(persist=True):
    """Forget the forced command and return to auto-detection."""
    set_lutris_override(None, persist=persist)


def _snap_has(name, snap):
    try:
        out = subprocess.run(
            [snap, "list", name], capture_output=True, text=True,
            timeout=5, env=external_env())
        return out.returncode == 0
    except Exception:
        return False


def _flatpak_has(app_id, flatpak):
    try:
        out = subprocess.run(
            [flatpak, "info", app_id], capture_output=True, text=True,
            timeout=5, env=external_env())
        if out.returncode == 0:
            return True
    except Exception:
        pass
    try:
        out = subprocess.run(
            [flatpak, "list", "--columns=application"], capture_output=True,
            text=True, timeout=5, env=external_env())
        return app_id in (out.stdout or "")
    except Exception:
        return False


def _lutris_candidates():
    """Yield command prefixes that might invoke Lutris, best first."""
    seen = set()

    def emit(cmd):
        key = tuple(cmd)
        if key not in seen:
            seen.add(key)
            return cmd
        return None

    # 1) Native binary: PATH entries first, then well-known distro dirs.
    dirs = os.environ.get("PATH", "").split(os.pathsep)
    for d in list(dirs) + list(_LUTRIS_EXTRA_DIRS):
        if not d:
            continue
        exe = Path(d) / "lutris"
        try:
            if exe.is_file() and os.access(exe, os.X_OK):
                c = emit([str(exe)])
                if c:
                    yield c
        except OSError:
            pass

    # 2) User-local / Nix / Flatpak-export locations.
    home = Path.home()
    for p in (home / ".local" / "bin" / "lutris",
              home / ".nix-profile" / "bin" / "lutris",
              home / ".local" / "share" / "flatpak" / "exports" / "bin" / "lutris"):
        try:
            if p.is_file() and os.access(p, os.X_OK):
                c = emit([str(p)])
                if c:
                    yield c
        except OSError:
            pass

    # 3) Snap.
    snap = shutil.which("snap")
    if snap and (Path("/snap/bin/lutris").exists() or _snap_has("lutris", snap)):
        c = emit([snap, "run", "lutris"])
        if c:
            yield c

    # 4) Flatpak (system or user install).
    flatpak = shutil.which("flatpak")
    if flatpak and _flatpak_has(_LUTRIS_FLATPAK_ID, flatpak):
        c = emit([flatpak, "run", _LUTRIS_FLATPAK_ID])
        if c:
            yield c


def find_lutris(refresh=False):
    """Return the command prefix used to invoke Lutris, or None.

    Works across distros (native package, Flatpak, Snap, Nix, AppImage) and
    honours a user-forced override. Returns a list (e.g. ``["lutris"]`` or
    ``["flatpak", "run", "net.lutris.Lutris"]``) so callers can append args.
    The result is cached for the session (pass ``refresh=True`` to re-scan).
    """
    global _lutris_cmd_cache
    if not IS_LINUX:
        return None
    if _lutris_cmd_cache is not _UNSET and not refresh:
        return _lutris_cmd_cache

    # 1) A user-forced command always wins (Tools > Fix Lutris).
    _load_override_once()
    if _lutris_override:
        logging.info("find_lutris: using forced override %s", _lutris_override)
        _lutris_cmd_cache = list(_lutris_override)
        return _lutris_cmd_cache

    candidates = list(_lutris_candidates())
    logging.info("find_lutris: %d candidate(s): %s", len(candidates), candidates)

    result = None
    for cmd in candidates:
        ok, detail = _lutris_probe(cmd)
        logging.info("find_lutris: probe %s -> %s (%s)",
                     cmd, "ok" if ok else "failed", detail)
        if ok:
            result = cmd
            break

    # Never report Lutris as missing just because the self-test misbehaved:
    # if a binary exists, use it and let the user fix details via Fix Lutris.
    if result is None and candidates:
        logging.warning(
            "find_lutris: all self-tests failed; using %s anyway", candidates[0])
        result = candidates[0]

    logging.info("find_lutris: resolved to %s", result)
    _lutris_cmd_cache = result
    return result


def _lutris_probe(cmd):
    """Run ``<cmd> --version``. Returns ``(ok, detail)`` for logging/UI."""
    try:
        out = subprocess.run(
            cmd + ["--version"],
            capture_output=True, text=True, timeout=15, env=external_env(),
        )
        combined = ((out.stdout or "") + (out.stderr or "")).strip()
        broken = "No module named 'lutris'" in combined or "No module named lutris" in combined
        ok = out.returncode == 0 and not broken
        return ok, (combined.replace("\n", " ")[:300] or f"rc={out.returncode}")
    except subprocess.TimeoutExpired:
        return False, "timed out"
    except FileNotFoundError:
        return False, "executable not found"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def _lutris_usable(cmd):
    """True if the Lutris command can start (imports its module) successfully."""
    return _lutris_probe(cmd)[0]


def lutris_self_test(cmd=None):
    """(ok, detail) for the Fix Lutris UI. Re-scans when no command is given."""
    cmd = cmd or find_lutris(refresh=True)
    if not cmd:
        return False, "Lutris not found"
    return _lutris_probe(cmd)


def _lutris_games_from_db():
    """Read Lutris's SQLite library directly (read-only, version-agnostic)."""
    db = lutris_paths()["db_path"]
    if not db.exists():
        return []
    try:
        import sqlite3
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        try:
            rows = con.execute(
                "SELECT id, name, slug, runner, directory, configpath FROM games"
            ).fetchall()
        finally:
            con.close()
        return [dict(r) for r in rows]
    except Exception:
        logging.debug("pga.db fallback failed", exc_info=True)
        return []


def lutris_entry_by_configpath(configpath):
    """Return the DB entry (id/name/slug/...) for a game config id, or None."""
    if not configpath:
        return None
    for g in _lutris_games_from_db():
        if g.get("configpath") == configpath:
            return {
                "id": g.get("id"), "name": g.get("name"),
                "slug": g.get("slug"), "runner": g.get("runner"),
                "directory": g.get("directory") or "",
                "configpath": configpath,
            }
    return None



def lutris_paths():
    """Directories Lutris uses, mirroring ``lutris.settings``.

    Returns a dict with ``data_dir``, ``config_dir``, ``games_dir``,
    ``db_path`` and ``config_file``. Honours ``XDG_*`` and an explicit
    ``pga_path`` override in ``lutris.conf`` (read-only).
    """
    home = Path.home()
    data_dir = Path(os.environ.get("XDG_DATA_HOME")
                    or home / ".local" / "share") / "lutris"
    config_dir = Path(os.environ.get("XDG_CONFIG_HOME")
                      or home / ".config") / "lutris"
    if not config_dir.exists():
        # Lutris deprecated ~/.config/lutris and falls back to the data dir.
        config_dir = data_dir
    db_path = data_dir / "pga.db"
    config_file = config_dir / "lutris.conf"
    try:
        if config_file.exists():
            import configparser
            cp = configparser.ConfigParser()
            cp.read(config_file)
            override = cp.get("lutris", "pga_path", fallback="").strip()
            if override:
                db_path = Path(override)
    except Exception:
        logging.debug("Could not read lutris.conf pga_path", exc_info=True)
    return {
        "data_dir": data_dir,
        "config_dir": config_dir,
        "games_dir": config_dir / "games",
        "db_path": db_path,
        "config_file": config_file,
    }


def lutris_is_running():
    """True if a Lutris process is currently running (Linux only)."""
    if not IS_LINUX:
        return False
    me = str(os.getpid())
    try:
        pids = [p for p in os.listdir("/proc") if p.isdigit() and p != me]
    except OSError:
        return False
    for pid in pids:
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as f:
                args = f.read().split(b"\0")
        except OSError:
            continue
        for arg in args:
            s = arg.decode("utf-8", "ignore")
            if s and os.path.basename(s) == "lutris":
                return True
    return False


def _system_python():
    """The system Python that owns Lutris (never the launcher's venv Python)."""
    env = external_env()
    return shutil.which("python3", path=env.get("PATH", "")) or shutil.which("python3")


def _read_simple_yaml_kv(path):
    """Flatten a Lutris game config's ``key: value`` lines (no PyYAML needed)."""
    result = {}
    try:
        text = Path(path).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return result
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, val = line.split(":", 1)
        result[key.strip()] = val.strip().strip('"').strip("'")
    return result


def lutris_find_existing_install(working_dir, exe=None, prefix=None):
    """Return the configpath of the launcher's entry for this install, or None.

    Matches the game config's ``working_dir`` or ``exe``. When ``prefix`` is
    given, only configs whose id starts with it are considered, so unrelated
    user entries pointing at the same executable are never reused.
    """
    games_dir = lutris_paths()["games_dir"]
    if not games_dir.is_dir():
        return None

    def same(a, b):
        try:
            return Path(a).resolve() == Path(b).resolve()
        except Exception:
            return str(a) == str(b)

    for f in games_dir.glob("*.yml"):
        if prefix and not f.stem.startswith(prefix):
            continue
        kv = _read_simple_yaml_kv(f)
        if working_dir and kv.get("working_dir") and same(kv["working_dir"], working_dir):
            return f.stem
        if exe and kv.get("exe") and same(kv["exe"], exe):
            return f.stem
    return None


_LUTRIS_REGISTER_SCRIPT = r'''
import json
import os
import sys

try:
    from lutris import settings
    from lutris.config import write_game_config
    from lutris.database import games as games_db
    from lutris.database.schema import syncdb
except Exception as exc:  # noqa: BLE001
    print("ISAMAU_ERROR:import: %s: %s" % (type(exc).__name__, exc))
    sys.exit(3)

info = json.loads(sys.stdin.read() or "{}")

try:
    # Idempotent: creates missing tables/columns only, like Lutris startup.
    syncdb()
except Exception as exc:  # noqa: BLE001
    print("ISAMAU_ERROR:syncdb: %s: %s" % (type(exc).__name__, exc))
    sys.exit(4)

config = {"game": {
    "exe": info["exe"],
    "prefix": info["prefix"],
    "working_dir": info["working_dir"],
}}
configpath = write_game_config(info["slug"], config)

try:
    gid = games_db.add_game(
        name=info["name"],
        sortname=info["name"],
        slug=info["slug"],
        runner="wine",
        platform="Windows",
        directory=info["working_dir"],
        installed=1,
        year=None,
        lastplayed=None,
        configpath=configpath,
        playtime=0,
        service=None,
        service_id=None,
        discord_id=None,
        has_custom_banner=0,
        has_custom_icon=0,
        has_custom_coverart_big=0,
    )
except Exception as exc:  # noqa: BLE001
    # Roll back the config we just wrote so nothing orphaned is left behind.
    try:
        os.remove(os.path.join(settings.CONFIG_DIR, "games", configpath + ".yml"))
    except OSError:
        pass
    print("ISAMAU_ERROR:insert: %s: %s" % (type(exc).__name__, exc))
    sys.exit(5)

print("ISAMAU_RESULT:" + json.dumps({"id": gid, "configpath": configpath}))
'''


def lutris_api_register(name, slug, exe, working_dir, prefix):
    """Register an existing install using Lutris's own API (no installer).

    Runs Lutris's own ``write_game_config`` + ``games_db.add_game`` through the
    system Python so the row and YAML match Lutris exactly and honour
    ``pga_path``/config-dir overrides. Returns the new entry dict, or None if
    Lutris's modules are unavailable (e.g. a Flatpak/Snap Lutris).
    """
    python = _system_python()
    if not python:
        return None
    # Lutris creates these on startup; do the same so its own writer works.
    try:
        paths = lutris_paths()
        paths["config_dir"].mkdir(parents=True, exist_ok=True)
        paths["games_dir"].mkdir(parents=True, exist_ok=True)
    except OSError:
        logging.exception("lutris_api_register: could not create Lutris dirs")
        return None
    info = {
        "name": name,
        "slug": slug,
        "exe": str(exe),
        "working_dir": str(working_dir),
        "prefix": str(prefix),
    }
    try:
        proc = subprocess.run(
            [python, "-c", _LUTRIS_REGISTER_SCRIPT],
            input=json.dumps(info), capture_output=True, text=True,
            timeout=60, env=external_env(),
        )
    except Exception:
        logging.exception("lutris_api_register: failed to run")
        return None

    for line in reversed((proc.stdout or "").splitlines()):
        if line.startswith("ISAMAU_RESULT:"):
            try:
                res = json.loads(line[len("ISAMAU_RESULT:"):])
            except Exception:
                return None
            return {
                "id": res.get("id"),
                "configpath": res.get("configpath"),
                "name": name,
                "slug": slug,
                "runner": "wine",
                "directory": str(working_dir),
            }
    logging.error(
        "lutris_api_register: no result (rc=%s)\nstdout=%s\nstderr=%s",
        proc.returncode, (proc.stdout or "")[-1000:], (proc.stderr or "")[-1000:])
    return None


def lutris_list_games(lutris_cmd=None):
    """Return Lutris's game list as a list of dicts (best effort).

    Uses ``lutris -l --json`` when available; on older/mismatched Lutris
    builds (any distro) it falls back to reading ``pga.db`` read-only.
    """
    cmd = lutris_cmd or find_lutris()
    if cmd:
        try:
            out = subprocess.run(
                cmd + ["-l", "--json"],
                capture_output=True, text=True, timeout=15, env=external_env(),
            )
            if out.returncode == 0 and out.stdout.strip():
                data = json.loads(out.stdout)
                if isinstance(data, list):
                    return data
        except Exception:
            logging.debug("lutris -l --json failed; trying pga.db", exc_info=True)
    return _lutris_games_from_db()


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
                            gpu=None, wine=None, icon_source=None):
    """Write a freedesktop .desktop launcher. Returns the .desktop path.

    Launches the game with Wine in the given (or global) prefix, injecting the
    environment variables for the selected GPU.
    """
    apps_dir = Path.home() / ".local" / "share" / "applications"
    apps_dir.mkdir(parents=True, exist_ok=True)
    slug_name = "isam-au"
    desktop_path = apps_dir / f"{slug_name}.desktop"

    wine_bin = find_wine(wine)
    if not wine_bin:
        wine_bin = "wine"
    pfx = prefix or wine_prefix()

    env_parts = [f'WINEPREFIX="{pfx}"']
    try:
        import graphics
        for key, val in graphics.gpu_env(gpu).items():
            env_parts.append(f'{key}="{val}"')
    except Exception:
        logging.exception("Failed to build GPU env for shortcut")
    exec_line = "env " + " ".join(env_parts) + f' "{wine_bin}" "{exe_path}"'

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
