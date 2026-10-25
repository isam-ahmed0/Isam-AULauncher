"""GUI registry: builtin front-ends, user-made custom GUIs, mode resolution.

Builtin interfaces:

- ``qt``  — full PySide6 interface (default)
- ``tk``  — lightweight tkinter "Lite" interface

Custom interfaces are plain Python files in ``<appdata>/IsamAULauncher/guis/``.
They may be ANY kind of Python program (tkinter, CLI, web server, ...): the
launcher never injects or imports a GUI toolkit for them. Each file provides:

- ``GUI_NAME = "Display Name"`` (optional)
- ``main(context)`` — called with an :class:`AppContext`; when it returns the
  launcher exits.

See ``DOC/CUSTOM_GUI.md`` for the full contract.
"""
import ast
import importlib.util
import json
import logging
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

from config import VERSION_URL, GITHUB_REPO, ISAM_CLIENT_URL, LAUNCHER_VERSION, APP_NAME
from file_manager import FileManager
from platform_utils import IS_LINUX, IS_WINDOWS, default_game_dir, wine_prefix
try:
    import platform
except Exception:
    platform = None
try:
    from itch_oauth import (
        itch_login,
        fetch_itch_profile,
        fetch_itch_username,
        read_itch_token,
        save_itch_token,
        clear_itch_token,
    )
except Exception:
    itch_login = None
    fetch_itch_profile = None
    fetch_itch_username = None
    read_itch_token = None
    save_itch_token = None
    clear_itch_token = None


BUILTIN_GUIS = [
    {
        "id": "qt",
        "name": "CrewLauncher (Qt)",
        "description": "Full-featured PySide6 interface",
        "module": "PySide6",
    },
    {
        "id": "tk",
        "name": "CrewLauncher Lite (Tk)",
        "description": "Lightweight tkinter interface",
        "module": "tkinter",
    },
]

_RESOURCES_DIR = Path(__file__).resolve().parent / "resources"
_TEMPLATE_PATH = _RESOURCES_DIR / "custom_gui_template.py"

CUSTOM_TEMPLATES = [
    {
        "id": "quicklaunch",
        "name": "Quick Launch",
        "kind": "gui",
        "description": "One big Launch button with version and status",
        "file": "custom_gui_minimal.py",
    },
    {
        "id": "statusboard",
        "name": "Status Board",
        "kind": "gui",
        "description": "Dashboard + exercises with real launcher data",
        "file": "custom_gui_playground.py",
    },
    {
        "id": "launcher",
        "name": "Launcher Controls",
        "kind": "gui",
        "description": "Install, launch and stop the game with progress",
        "file": "custom_gui_template.py",
    },
    {
        "id": "ctk",
        "name": "Modern Panel",
        "kind": "gui",
        "description": "Rounded dark panel (needs official build / customtkinter)",
        "file": "custom_gui_ctk.py",
    },
    {
        "id": "cli-menu",
        "name": "Terminal Menu",
        "kind": "cli",
        "description": "Install, launch and check status from a text menu",
        "file": "custom_cli_menu.py",
    },
    {
        "id": "cli-auto",
        "name": "Auto-Update & Launch",
        "kind": "cli",
        "description": "Headless: report, update and launch in one go",
        "file": "custom_cli_autolaunch.py",
    },
]


def custom_gui_templates():
    """Available starter templates for Create Custom GUI."""
    return [dict(t) for t in CUSTOM_TEMPLATES]


def _template_file(template_id):
    for t in CUSTOM_TEMPLATES:
        if t["id"] == (template_id or "launcher"):
            return _RESOURCES_DIR / t["file"]
    return _TEMPLATE_PATH


# ---------------------------------------------------------------------------
# discovery
# ---------------------------------------------------------------------------
def _module_available(module):
    if not module:
        return True
    try:
        return importlib.util.find_spec(module) is not None
    except Exception:
        return False


def gui_display_name(path):
    """Read ``GUI_NAME`` from a custom GUI file without executing it."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "GUI_NAME":
                    try:
                        value = ast.literal_eval(node.value)
                    except Exception:
                        continue
                    if isinstance(value, str) and value.strip():
                        return value.strip()
    return None


def _import_roots(path):
    """Top-level module names imported anywhere in a custom GUI file (AST, no exec)."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return []
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                roots.add(node.module.split(".")[0])
    return sorted(roots)


def custom_gui_path(config, name):
    """Resolve a custom GUI name to its file, guarding against path tricks.

    Supports both directory-based (guis/name/main.py) and legacy single-file (guis/name.py).
    Directory-based takes precedence if both exist.
    """
    name = (name or "").strip()
    if not name or "/" in name or "\\" in name or name.startswith("."):
        return None
    dir_path = config.guis_dir / name / "main.py"
    if dir_path.is_file():
        return dir_path
    file_path = config.guis_dir / f"{name}.py"
    return file_path if file_path.is_file() else None


def list_guis(config):
    """All selectable interfaces: builtins first, then custom GUIs."""
    guis = []
    for entry in BUILTIN_GUIS:
        item = dict(entry)
        item["builtin"] = True
        item["available"] = _module_available(entry.get("module"))
        guis.append(item)

    seen = set()
    try:
        for entry in sorted(config.guis_dir.iterdir()):
            if entry.name.startswith("_"):
                continue
            if entry.is_dir():
                main_py = entry / "main.py"
                if main_py.is_file():
                    name = entry.name
                    if name in seen:
                        continue
                    seen.add(name)
                    missing = [m for m in _import_roots(main_py) if not _module_available(m)]
                    guis.append({
                        "id": f"custom:{name}",
                        "name": gui_display_name(main_py) or name,
                        "description": str(main_py),
                        "path": main_py,
                        "builtin": False,
                        "available": not missing,
                        "reason": ("missing " + ", ".join(missing)) if missing else "",
                    })
            elif entry.is_file() and entry.suffix == ".py":
                name = entry.stem
                if name in seen:
                    continue
                seen.add(name)
                missing = [m for m in _import_roots(entry) if not _module_available(m)]
                guis.append({
                    "id": f"custom:{name}",
                    "name": gui_display_name(entry) or name,
                    "description": str(entry),
                    "path": entry,
                    "builtin": False,
                    "available": not missing,
                    "reason": ("missing " + ", ".join(missing)) if missing else "",
                })
    except Exception:
        pass
    return guis


# ---------------------------------------------------------------------------
# mode resolution
# ---------------------------------------------------------------------------
def resolve_mode(cli_mode, config):
    """Pick the interface id to launch.

    Priority: CLI value > config ``ui_mode`` > ``qt``. Legacy values
    (``gui``, ``ctk``) map to ``qt``. Unknown or missing custom GUIs fall
    back to ``qt``.
    """
    mode = (cli_mode or "").strip() or config.get_ui_mode()
    if mode in ("gui", "ctk"):
        mode = "qt"
    if mode.startswith("custom:"):
        name = mode.split(":", 1)[1].strip()
        if not custom_gui_path(config, name):
            logging.warning("Custom GUI %r not found; falling back to Qt", mode)
            return "qt"
        return f"custom:{name}"
    if mode not in ("qt", "tk"):
        logging.warning("Unknown ui_mode %r; falling back to Qt", mode)
        return "qt"
    return mode


# ---------------------------------------------------------------------------
# custom GUI runtime
# ---------------------------------------------------------------------------
class AppContext:
    """Backend context handed to a custom GUI's ``main(context)``.

    Toolkit-free: importing this class never imports PySide6, tkinter or any
    other GUI framework. The custom GUI is in charge of its own interface
    (or none at all).
    """

    def __init__(self, config, network=None, discord=None):
        self.config = config
        from network import NetworkManager, DiscordRPC
        self.network = network if network is not None else NetworkManager()
        self.discord = discord if discord is not None else DiscordRPC()
        from game_core import GameCore
        self.game = GameCore(config, self.network)
        try:
            from gui_qt.profiles import ProfileManager
            self.profiles = ProfileManager(config.profiles_dir)
        except Exception:
            self.profiles = None
        try:
            from gui_qt.game import GameManager
            self._game_manager = GameManager(config)
        except Exception:
            self._game_manager = None

    # -- info -----------------------------------------------------------
    @property
    def guis_dir(self):
        return self.config.guis_dir

    @property
    def appdata_dir(self):
        return self.config.appdata_dir

    @property
    def profiles_dir(self):
        return self.config.profiles_dir

    @property
    def cache_dir(self):
        return getattr(self.config, 'cache_dir', None)

    def version(self):
        return self.config.get_version() or "Not Installed"

    def get_version(self):
        return self.version()

    def game_path(self):
        return self.config.get_game_path()

    def get_game_path(self):
        return self.game_path()

    def set_game_path(self, path):
        try:
            from pathlib import Path
            if isinstance(path, str):
                path = Path(path)
            self.config.set_game_path(path)
            return True
        except Exception:
            return False

    def is_installed(self):
        gp = self.game_path()
        if not gp:
            return False
        try:
            return bool((gp / "Among Us.exe").exists())
        except Exception:
            return False

    @property
    def is_running(self):
        try:
            return self.game.is_running
        except Exception:
            return False

    @property
    def pid(self):
        try:
            return self.game.pid
        except Exception:
            return 0

    def log(self, message):
        logging.info("[custom-gui] %s", message)

    def get_setting(self, key, default=None):
        try:
            return self.config.settings.get(key, default)
        except Exception:
            return default

    def set_setting(self, key, value, save=True):
        try:
            self.config.settings[key] = value
            if save:
                self.config.save_settings()
            return True
        except Exception:
            return False

    def save_settings(self):
        try:
            self.config.save_settings()
            return True
        except Exception:
            return False

    def get_settings(self):
        try:
            return dict(self.config.settings)
        except Exception:
            return {}

    # -- actions --------------------------------------------------------
    def install(self, progress=None, status=None, version=None):
        """Download/update the game. Returns True on success.

        ``progress`` is called with a 0-100 float, ``status`` with
        ``(text, level)``. Callbacks may fire from worker threads.
        """
        gp = self.game_path()
        if not gp:
            if status:
                try:
                    status("No install folder selected", "danger")
                except Exception:
                    pass
            return False
        if not version:
            version = self.network.fetch_text(VERSION_URL)
        if not version:
            if status:
                try:
                    status("Failed to fetch version info", "danger")
                except Exception:
                    pass
            return False
        if progress:
            try:
                self.game.on_progress = progress
            except Exception:
                pass
        if status:
            try:
                self.game.on_status = status
            except Exception:
                pass
        try:
            return bool(self.game.download_update(version, gp))
        except Exception as e:
            self.log(f"install error: {e}")
            return False

    def download_game(self, *args, **kwargs):
        return self.install(*args, **kwargs)

    def update_game(self, *args, **kwargs):
        return self.install(*args, **kwargs)

    def launch(self, profile=None, method=None):
        """Launch the game using the configured Wine/GPU setup (Linux)."""
        gp = self.game_path()
        if not gp:
            return False
        if IS_LINUX:
            try:
                import graphics
                wine = graphics.resolve_wine(self.config.get_wine_binary())
                if not wine:
                    return False
                return bool(self.game.launch_wine(gp, gp / "Among Us.exe"))
            except Exception as e:
                self.log(f"launch error: {e}")
                return False
        try:
            return bool(self.game.launch())
        except Exception as e:
            self.log(f"launch error: {e}")
            return False

    def launch_game(self, *args, **kwargs):
        return self.launch(*args, **kwargs)

    def stop(self):
        try:
            return bool(self.game.stop())
        except Exception:
            return False

    def stop_game(self):
        return self.stop()

    def poll(self):
        try:
            return bool(self.game.poll())
        except Exception:
            return False

    # -- network --------------------------------------------------------
    def fetch_text(self, url):
        try:
            return self.network.fetch_text(url)
        except Exception:
            return None

    def download_file(self, url, output_path, progress_callback=None):
        try:
            return self.network.download_file(url, output_path, progress_callback)
        except Exception:
            return False

    def get_releases(self):
        try:
            return self.network.get_releases()
        except Exception:
            return [], "Failed"

    # -- profiles -------------------------------------------------------
    def list_profiles(self):
        if self.profiles:
            try:
                return self.profiles.list_profiles()
            except Exception:
                pass
        return ["Default"]

    def create_profile(self, name):
        if self.profiles:
            try:
                return self.profiles.create_profile(name)
            except Exception:
                return False
        return False

    def delete_profile(self, name):
        if self.profiles:
            try:
                return self.profiles.delete_profile(name, self.config.get_active_profile())
            except Exception:
                return False
        return False

    def rename_profile(self, old, new):
        if self.profiles:
            try:
                return self.profiles.rename_profile(old, new)
            except Exception:
                return False
        return False

    def get_active_profile(self):
        try:
            return self.config.get_active_profile()
        except Exception:
            return "Default"

    def set_active_profile(self, name):
        try:
            self.config.set_active_profile(name)
            return True
        except Exception:
            return False

    def switch_profile(self, profile_name):
        gp = self.game_path()
        if not gp or not self.profiles:
            return False
        try:
            return self.profiles.switch_to(profile_name, gp)
        except Exception:
            return False

    def get_profile_path(self, name=None):
        if self.profiles:
            try:
                if name is None:
                    name = self.get_active_profile()
                return self.profiles.profile_path(name)
            except Exception:
                pass
        return None

    def import_mods(self, profile_name=None, dll_paths=None):
        if self.profiles and dll_paths:
            try:
                if profile_name is None:
                    profile_name = self.get_active_profile()
                return self.profiles.import_mods(profile_name, dll_paths)
            except Exception:
                return 0
        return 0

    def list_mods(self, profile_name=None):
        if self.profiles:
            try:
                if profile_name is None:
                    profile_name = self.get_active_profile()
                path = self.profiles.profile_path(profile_name)
                if path and path.exists():
                    mods = []
                    for f in path.iterdir():
                        if f.is_file() and f.suffix.lower() == '.dll':
                            mods.append(str(f))
                    return mods
            except Exception:
                pass
        return []

    def remove_mod(self, profile_name=None, mod_path=None):
        try:
            if mod_path:
                from pathlib import Path
                p = Path(mod_path)
                if p.exists():
                    p.unlink()
                    return True
        except Exception:
            pass
        return False

    # -- utils ----------------------------------------------------------
    def run_thread(self, target, *args, **kwargs):
        try:
            t = threading.Thread(target=target, args=args, kwargs=kwargs, daemon=True)
            t.start()
            return t
        except Exception:
            return None

    def run_async(self, fn, callback=None):
        def _wrap():
            try:
                result = fn()
                if callback:
                    try:
                        callback(result)
                    except Exception:
                        pass
            except Exception as e:
                self.log(f"async error: {e}")
        return self.run_thread(_wrap)

    def extract_zip(self, zip_path, extract_to, progress_callback=None):
        try:
            return FileManager.extract_zip(Path(zip_path), Path(extract_to), progress_callback)
        except Exception:
            return False

    def delete(self, path):
        try:
            return FileManager.safe_delete(Path(path))
        except Exception:
            return False

    def format_size(self, b):
        try:
            return FileManager.format_size(b)
        except Exception:
            return str(b)

    def open_folder(self, path=None):
        try:
            if path is None:
                path = self.game_path() or self.appdata_dir
            from pathlib import Path
            p = Path(path)
            if IS_WINDOWS:
                os.startfile(str(p))
            elif IS_LINUX:
                subprocess.Popen(['xdg-open', str(p)])
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', str(p)])
            return True
        except Exception:
            return False

    def show_message(self, title, message):
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showinfo(title, message)
            root.destroy()
            return True
        except Exception:
            try:
                print(f"{title}: {message}")
            except Exception:
                pass
            return False

    def show_error(self, title, message):
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(title, message)
            root.destroy()
            return True
        except Exception:
            try:
                print(f"ERROR {title}: {message}")
            except Exception:
                pass
            return False

    # -- itch.io --------------------------------------------------------
    def itch_login(self, callback=None):
        if itch_login is None:
            return False
        try:
            return itch_login(callback=callback)
        except Exception as e:
            self.log(f"itch login error: {e}")
            return False

    def get_itch_profile(self, timeout=8.0):
        if fetch_itch_profile is None:
            return {}
        try:
            return fetch_itch_profile(timeout=timeout)
        except Exception:
            return {}

    def get_itch_username(self, timeout=8.0):
        if fetch_itch_username is None:
            return None
        try:
            return fetch_itch_username(timeout=timeout)
        except Exception:
            return None

    def get_itch_token(self):
        if read_itch_token is None:
            return None
        try:
            return read_itch_token()
        except Exception:
            return None

    def save_itch_token(self, token):
        if save_itch_token is None:
            return None
        try:
            return save_itch_token(token)
        except Exception:
            return None

    def clear_itch_token(self):
        if clear_itch_token is None:
            return False
        try:
            clear_itch_token()
            return True
        except Exception:
            return False

    # -- misc -----------------------------------------------------------
    @property
    def APP_NAME(self):
        return APP_NAME

    @property
    def LAUNCHER_VERSION(self):
        return LAUNCHER_VERSION

    @property
    def IS_WINDOWS(self):
        return IS_WINDOWS

    @property
    def IS_LINUX(self):
        return IS_LINUX

    def get_platform(self):
        if platform:
            try:
                return platform.system()
            except Exception:
                pass
        return sys.platform

    def get_wine_prefix(self):
        try:
            return self.config.get_wine_prefix()
        except Exception:
            try:
                return wine_prefix()
            except Exception:
                return None

    def get_wine_binary(self):
        try:
            return self.config.get_wine_binary()
        except Exception:
            return ""

    def get_gpu(self):
        try:
            return self.config.get_gpu()
        except Exception:
            return ""

    def set_gpu(self, gpu_id):
        try:
            self.config.set_gpu(gpu_id)
            return True
        except Exception:
            return False

    def set_wine_binary(self, path):
        try:
            self.config.set_wine_binary(path)
            return True
        except Exception:
            return False

    def get_default_game_dir(self):
        try:
            return default_game_dir()
        except Exception:
            return None

    def check_update(self, current_version=None):
        try:
            if current_version is None:
                current_version = self.version()
            latest = self.network.fetch_text(VERSION_URL)
            if not latest:
                return False, current_version
            return latest != current_version, latest
        except Exception:
            return False, current_version

    def get_latest_version(self):
        try:
            return self.network.fetch_text(VERSION_URL)
        except Exception:
            return None

    def restart_launcher(self):
        try:
            from app_restart import restart_launcher
            restart_launcher()
            return True
        except Exception:
            return False

    def get_launcher_log_path(self):
        try:
            from config import config_data_dir
            return config_data_dir() / "logs" / "launcher.log"
        except Exception:
            return None

    def add_to_path(self, *args, **kwargs):
        try:
            if hasattr(self, '_game_manager') and self._game_manager:
                if hasattr(self._game_manager, 'add_to_path'):
                    return self._game_manager.add_to_path(*args, **kwargs)
        except Exception:
            pass
        return None

    def launch_modded(self, *args, **kwargs):
        try:
            if hasattr(self, '_game_manager') and self._game_manager:
                if hasattr(self._game_manager, 'launch_modded'):
                    return self._game_manager.launch_modded(*args, **kwargs)
        except Exception:
            pass
        return self.launch(*args, **kwargs)

    def get_mod_status(self, *args, **kwargs):
        try:
            if hasattr(self, '_game_manager') and self._game_manager:
                if hasattr(self._game_manager, 'get_mod_status'):
                    return self._game_manager.get_mod_status(*args, **kwargs)
        except Exception:
            pass
        return None

    def get_mod_count(self, *args, **kwargs):
        try:
            if hasattr(self, '_game_manager') and self._game_manager:
                if hasattr(self._game_manager, 'get_mod_count'):
                    return self._game_manager.get_mod_count(*args, **kwargs)
        except Exception:
            pass
        return len(self.list_mods())


AppContext.__doc__ = AppContext.__doc__ + "\n\nCustom GUIs have full access to profiles, mods, settings, downloads, itch.io auth, and more."


def load_custom_gui(name, config):
    """Import a custom GUI module. Returns the module or raises."""
    path = custom_gui_path(config, name)
    if not path:
        raise FileNotFoundError(f"Custom GUI {name!r} not found")
    spec = importlib.util.spec_from_file_location(f"isam_custom_gui_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run_custom_gui(mode, config, network=None, discord=None):
    """Run a custom GUI by id (``custom:<name>``). Returns True on success.

    Raises on load errors; returns False when the entry point is missing.
    """
    name = mode.split(":", 1)[1].strip()
    module = load_custom_gui(name, config)
    entry = getattr(module, "main", None)
    if not callable(entry):
        logging.error("Custom GUI %r has no callable main(context)", name)
        return False
    context = AppContext(config, network, discord)
    try:
        entry(context)
        return True
    finally:
        try:
            context.discord.disconnect()
        except Exception:
            pass
        try:
            context.network.session.close()
        except Exception:
            pass


def create_custom_gui(config, name, template_id="launcher"):
    """Copy a starter template into the guis folder as a directory with ``main.py``.

    Returns the created path; raises on invalid names or existing files.
    """
    display = (name or "").strip()
    safe = "".join(ch for ch in display if ch.isalnum() or ch in " _-").strip()
    safe = safe.replace(" ", "_")
    if not safe:
        raise ValueError("Invalid GUI name")
    dest_dir = config.guis_dir / safe
    if dest_dir.exists():
        raise FileExistsError(str(dest_dir))
    dest_dir.mkdir(parents=True, exist_ok=False)
    dest = dest_dir / "main.py"
    embed = display.replace("\\", "").replace('"', "'").replace("\n", " ").strip()
    template = _template_file(template_id)
    if not template.is_file():
        template = _TEMPLATE_PATH
    text = template.read_text(encoding="utf-8")
    text, replaced = re.subn(
        r'^GUI_NAME\s*=\s*"[^"]*"', lambda _m: f'GUI_NAME = "{embed}"',
        text, count=1, flags=re.M)
    if not replaced:
        text = f'GUI_NAME = "{embed}"\n' + text
    dest.write_text(text, encoding="utf-8")
    return dest
