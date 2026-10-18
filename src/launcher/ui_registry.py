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
import logging
import re
import sys
from pathlib import Path

from config import VERSION_URL

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

    # -- info -----------------------------------------------------------
    @property
    def guis_dir(self):
        return self.config.guis_dir

    def version(self):
        return self.config.get_version() or "Not Installed"

    def game_path(self):
        return self.config.get_game_path()

    def is_installed(self):
        gp = self.game_path()
        return bool(gp and (gp / "Among Us.exe").exists())

    @property
    def is_running(self):
        return self.game.is_running

    def log(self, message):
        logging.info("[custom-gui] %s", message)

    # -- actions --------------------------------------------------------
    def install(self, progress=None, status=None):
        """Download/update the game. Returns True on success.

        ``progress`` is called with a 0-100 float, ``status`` with
        ``(text, level)``. Callbacks may fire from worker threads.
        """
        gp = self.game_path()
        if not gp:
            if status:
                status("No install folder selected", "danger")
            return False
        version = self.network.fetch_text(VERSION_URL)
        if not version:
            if status:
                status("Failed to fetch version info", "danger")
            return False
        if progress:
            self.game.on_progress = progress
        if status:
            self.game.on_status = status
        return bool(self.game.download_update(version, gp))

    def launch(self):
        """Launch the game using the configured Wine/GPU setup (Linux)."""
        gp = self.game_path()
        if not gp:
            return False
        from platform_utils import IS_LINUX
        if IS_LINUX:
            import graphics
            wine = graphics.resolve_wine(self.config.get_wine_binary())
            if not wine:
                return False
            return bool(self.game.launch_wine(gp, gp / "Among Us.exe"))
        self.game.launch()
        return True

    def stop(self):
        self.game.stop()

    def poll(self):
        return self.game.poll()


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
