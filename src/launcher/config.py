import os
import sys
import json
import logging
from pathlib import Path
from typing import Optional, Dict

from platform_utils import default_game_dir


def config_data_dir() -> Path:
    """Per-user app data dir, platform-aware."""
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA") or Path.home() / ".isamau")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    d = base / "IsamAULauncher"
    d.mkdir(parents=True, exist_ok=True)
    return d


_log_dir = config_data_dir() / "logs"
_log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=str(_log_dir / "launcher.log"), level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ---------------------------------------------------------------------------
# Branding
# ---------------------------------------------------------------------------
APP_NAME = "CrewLauncher"
BRAND_SHORT = "CREW AU"
MAKER = "Isam"
LAUNCHER_VERSION = "1.0-beta.5"

VERSION_URL = "https://raw.githubusercontent.com/jogamerforgames2021/BootstrapperTEST/main/Version.txt"
MESSAGE_URL = "https://raw.githubusercontent.com/jogamerforgames2021/AmongUsLauncherNew/refs/heads/main/message.txt"
PATCHES_URL = "https://raw.githubusercontent.com/jogamerforgames2021/AmongUsLauncherNew/refs/heads/main/Patches.xml"
SOURCE_CODE_URL = "https://github.com/isam-ahmed0/Isam-AULauncher"
DOCS_BASE_URL = f"{SOURCE_CODE_URL}/blob/main/DOC"
LINUX_DOC_URL = f"{DOCS_BASE_URL}/LINUX.md"
WINE_DOC_URL = f"{DOCS_BASE_URL}/WINE.md"
DOCS_RAW_BASE = "https://raw.githubusercontent.com/isam-ahmed0/Isam-AULauncher/crew/DOC"
LINUX_DOC_RAW_URL = f"{DOCS_RAW_BASE}/LINUX.md"
WINE_DOC_RAW_URL = f"{DOCS_RAW_BASE}/WINE.md"
GITHUB_REPO = "jogamerforgames2021/AmongUsLauncherNew"
ISAM_CLIENT_URL = "https://raw.githubusercontent.com/isam-ahmed0/Isam-AULauncher/crew/isam-client.zip"
DISCORD_CLIENT_ID = "1543527340963930193"
DISCORD_INVITE = ""
DISCORD_DOWNLOAD_URL = f"{SOURCE_CODE_URL}/releases/latest"
DISCORD_WEBSITE_URL = SOURCE_CODE_URL
YOUTUBE_CHANNEL = "https://www.youtube.com/@isam0ahmed"
REQUEST_TIMEOUT = 10
CHUNK_SIZE = 8192
LAUNCHER_UPDATE_URL = "https://raw.githubusercontent.com/isam-ahmed0/Isam-AULauncher/crew/LAUNCHER_VERSION"
LAUNCHER_SETUP_URL = f"https://github.com/isam-ahmed0/Isam-AULauncher/releases/download/{LAUNCHER_VERSION}/CrewLauncher-Setup.exe"

GAME_CRITICAL_FILES = ["Among Us.exe"]
GAME_CRITICAL_DIRS = ["BepInEx", "dotnet"]
DEFAULT_GAME_DIR = str(default_game_dir())


class Config:
    def __init__(self):
        self.appdata_dir = config_data_dir()
        self.profiles_dir = self.appdata_dir / "Profiles"
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir = self.appdata_dir / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.version_file = self.appdata_dir / "current_version.txt"
        self.game_path_file = self.appdata_dir / "game_path.txt"
        self.config_file = self.appdata_dir / "config.json"
        self.settings = self._load_settings()

    def _load_settings(self) -> Dict:
        defaults = {
            "auto_update": True, "create_shortcuts": True,
            "discord_rpc": True, "ui_mode": "gui",
            "active_profile": "Default", "theme": "Forest",
            "launch_method": "ask", "warn_plain_wine": True,
            "wine_prefix": "", "lutris_game_ids": {}, "lutris_entries": {},
            "lutris_cmd_override": None,
            "gpu_id": "", "wine_binary": "", "linux_setup_complete": False,
            "home_image_path": "", "home_note": "",
        }
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    return {**defaults, **json.load(f)}
        except Exception as e:
            logging.error(f"Failed to load settings: {e}")
        return defaults

    def save_settings(self):
        import tempfile
        try:
            fd, tmp = tempfile.mkstemp(dir=self.appdata_dir, suffix=".json")
            with os.fdopen(fd, 'w') as f:
                json.dump(self.settings, f, indent=4)
            import shutil
            shutil.move(tmp, self.config_file)
        except Exception as e:
            logging.error(f"Failed to save settings: {e}")

    def get_version(self) -> Optional[str]:
        try:
            if self.version_file.exists():
                return self.version_file.read_text().strip()
        except Exception as e:
            logging.error(f"Failed to read version: {e}")
        return None

    def set_version(self, version: str):
        try:
            self.version_file.write_text(version)
        except Exception as e:
            logging.error(f"Failed to write version: {e}")

    def get_game_path(self) -> Optional[Path]:
        try:
            if self.game_path_file.exists():
                path = Path(self.game_path_file.read_text().strip())
                if path.exists():
                    return path
        except Exception as e:
            logging.error(f"Failed to read game path: {e}")
        return None

    def set_game_path(self, path: Path):
        try:
            self.game_path_file.write_text(str(path))
        except Exception as e:
            logging.error(f"Failed to write game path: {e}")

    def get_active_profile(self) -> str:
        return self.settings.get("active_profile", "Default")

    def set_active_profile(self, name: str):
        self.settings["active_profile"] = name
        self.save_settings()

    # ------------------------------------------------------------------ linux
    def get_wine_prefix(self) -> Path:
        """Wine prefix the game/fixer should use (setting overrides global)."""
        from platform_utils import wine_prefix
        val = (self.settings.get("wine_prefix") or "").strip()
        return Path(val) if val else wine_prefix()

    def get_gpu(self) -> str:
        """Selected GPU id (PCI slot) or \"\" for system default."""
        return (self.settings.get("gpu_id") or "").strip()

    def set_gpu(self, gpu_id: str):
        self.settings["gpu_id"] = (gpu_id or "").strip()
        self.save_settings()

    def get_wine_binary(self) -> str:
        """Preferred wine executable path, or \"\" to auto-detect."""
        return (self.settings.get("wine_binary") or "").strip()

    def set_wine_binary(self, path: str):
        self.settings["wine_binary"] = (path or "").strip()
        self.save_settings()

    def is_linux_setup_complete(self) -> bool:
        return bool(self.settings.get("linux_setup_complete", False))

    def set_linux_setup_complete(self, done: bool):
        self.settings["linux_setup_complete"] = bool(done)
        self.save_settings()

    def get_lutris_id(self, game_path):
        """Cached Lutris numeric game id for a given install path."""
        entry = self.get_lutris_entry(game_path)
        if entry and entry.get("id") is not None:
            return entry.get("id")
        ids = self.settings.get("lutris_game_ids", {}) or {}
        return ids.get(str(game_path))

    def get_lutris_entry(self, game_path):
        """Cached Lutris entry (id/name/slug/...) for a given install path."""
        entries = self.settings.get("lutris_entries", {}) or {}
        entry = entries.get(str(game_path))
        return entry if isinstance(entry, dict) else None

    def set_lutris_entry(self, game_path, entry):
        """Cache a Lutris entry dict for a given install path (or clear it)."""
        entries = dict(self.settings.get("lutris_entries", {}) or {})
        if entry:
            entries[str(game_path)] = {
                k: entry.get(k) for k in ("id", "name", "slug", "runner", "directory")
            }
        else:
            entries.pop(str(game_path), None)
        self.settings["lutris_entries"] = entries
        self.save_settings()

    def clear_lutris_entry(self, game_path):
        self.set_lutris_entry(game_path, None)

    def get_lutris_cmd_override(self):
        """User-forced Lutris command (list of args) or None."""
        return _coerce_cmd(self.settings.get("lutris_cmd_override"))

    def set_lutris_cmd_override(self, cmd):
        self.settings["lutris_cmd_override"] = list(cmd) if cmd else None
        self.save_settings()

    def clear_lutris_cmd_override(self):
        self.set_lutris_cmd_override(None)

    def set_lutris_id(self, game_path, game_id):
        ids = dict(self.settings.get("lutris_game_ids", {}) or {})
        if game_id is None:
            ids.pop(str(game_path), None)
        else:
            ids[str(game_path)] = int(game_id)
        self.settings["lutris_game_ids"] = ids
        self.save_settings()


def _coerce_cmd(value):
    """Normalize a stored override into a non-empty list of arg strings."""
    if isinstance(value, (list, tuple)):
        parts = [str(v) for v in value if str(v).strip()]
        return parts or None
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return None


def get_lutris_cmd_override():
    """Read the forced Lutris command straight from config.json.

    Used by ``platform_utils`` so it can honour the override without needing a
    :class:`Config` instance (avoids import cycles).
    """
    try:
        p = config_data_dir() / "config.json"
        if p.exists():
            with open(p, "r") as f:
                return _coerce_cmd(json.load(f).get("lutris_cmd_override"))
    except Exception as e:
        logging.error(f"Failed to read Lutris override: {e}")
    return None


def set_lutris_cmd_override(cmd):
    """Persist the forced Lutris command directly to config.json."""
    import tempfile
    import shutil as _shutil
    p = config_data_dir() / "config.json"
    try:
        data = {}
        if p.exists():
            try:
                with open(p, "r") as f:
                    data = json.load(f)
            except Exception:
                data = {}
        data["lutris_cmd_override"] = list(cmd) if cmd else None
        fd, tmp = tempfile.mkstemp(dir=p.parent, suffix=".json")
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=4)
        _shutil.move(tmp, p)
    except Exception as e:
        logging.error(f"Failed to save Lutris override: {e}")
