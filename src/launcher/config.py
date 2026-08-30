import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict

logging.basicConfig(
    filename='launcher.log', level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ---------------------------------------------------------------------------
# Branding
# ---------------------------------------------------------------------------
APP_NAME = "Isam AULauncher"
BRAND_SHORT = "ISAM AU"
MAKER = "Isam"
LAUNCHER_VERSION = "0.2"

VERSION_URL = "https://raw.githubusercontent.com/jogamerforgames2021/BootstrapperTEST/main/Version.txt"
MESSAGE_URL = "https://raw.githubusercontent.com/jogamerforgames2021/AmongUsLauncherNew/refs/heads/main/message.txt"
PATCHES_URL = "https://raw.githubusercontent.com/jogamerforgames2021/AmongUsLauncherNew/refs/heads/main/Patches.xml"
SOURCE_CODE_URL = "https://github.com/isam-ahmed0/Isam-AULauncher"
GITHUB_REPO = "jogamerforgames2021/AmongUsLauncherNew"
AUNLOCKER_JSON_URL = "https://raw.githubusercontent.com/jogamerforgames2021/AmongUsLauncherNew/refs/heads/main/AUnlockerStuff/Versions.json"
DISCORD_CLIENT_ID = "1543527340963930193"
DISCORD_INVITE = ""
YOUTUBE_CHANNEL = "https://www.youtube.com/@isam0ahmed"
REQUEST_TIMEOUT = 10
CHUNK_SIZE = 8192
FIXER_URL = "https://github.com/jogamerforgames2021/AmongUsLauncherNew/raw/refs/heads/main/Fixer/Itch_Login_Fixer.exe"
LAUNCHER_UPDATE_URL = "https://raw.githubusercontent.com/isam-ahmed0/Isam-AULauncher/main/LAUNCHER_VERSION"
LAUNCHER_SETUP_URL = f"https://github.com/isam-ahmed0/Isam-AULauncher/releases/download/{LAUNCHER_VERSION}/IsamAU-Setup.exe"

GAME_CRITICAL_FILES = ["Among Us.exe"]
GAME_CRITICAL_DIRS = ["BepInEx", "dotnet"]


class Config:
    def __init__(self):
        appdata = os.environ.get("APPDATA") or str(Path.home() / ".isamau")
        self.appdata_dir = Path(appdata) / "IsamAULauncher"
        self.appdata_dir.mkdir(parents=True, exist_ok=True)
        self.version_file = self.appdata_dir / "current_version.txt"
        self.game_path_file = self.appdata_dir / "game_path.txt"
        self.config_file = self.appdata_dir / "config.json"
        self.settings = self._load_settings()

    def _load_settings(self) -> Dict:
        defaults = {
            "auto_update": True, "create_shortcuts": True,
            "discord_rpc": True, "check_integrity": True, "ui_mode": "gui"
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
