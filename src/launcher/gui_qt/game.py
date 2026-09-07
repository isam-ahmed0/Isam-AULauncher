"""
GameManager — game launch, stop, update, and process tracking.
All game lifecycle logic lives here; window.py just calls these methods.
"""
import sys
import logging
import subprocess
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from config import VERSION_URL, GITHUB_REPO, PLUGIN_DLL_URL
from network import NetworkManager
from file_manager import FileManager

log = logging.getLogger(__name__)


class GameManager(QObject):
    """Manages Among Us game process and updates."""

    game_started = Signal()
    game_stopped = Signal()
    update_progress = Signal(float)
    status_message = Signal(str, str)  # (text, level)

    def __init__(self, config, network: NetworkManager, parent=None):
        super().__init__(parent)
        self.config = config
        self.network = network
        self._process = None

    # ---------------------------------------------------------------- process
    @property
    def is_running(self) -> bool:
        if self._process is None:
            return False
        return self._process.poll() is None

    @property
    def pid(self) -> int:
        if self._process:
            return self._process.pid
        return 0

    def launch(self):
        """Launch Among Us. Returns True on success."""
        gp = self.config.get_game_path()
        if not gp:
            self.status_message.emit("Game not installed!", "danger")
            return False

        exe = gp / "Among Us.exe"
        if not exe.exists():
            self.status_message.emit("Among Us.exe not found!", "danger")
            return False

        if self.is_running:
            self.status_message.emit("Game is already running!", "warning")
            return False

        try:
            self._process = subprocess.Popen([str(exe)], cwd=str(gp))
            self.status_message.emit("Game launched!", "success")
            self.game_started.emit()
            return True
        except PermissionError:
            self.status_message.emit("Permission denied. Try running as admin.", "danger")
            return False
        except OSError as e:
            self.status_message.emit(f"Failed to launch: {e}", "danger")
            return False

    def stop(self):
        """Kill the game process."""
        if not self.is_running:
            self.status_message.emit("No game running.", "warning")
            return False
        try:
            self._process.terminate()
            self._process.wait(timeout=5)
        except Exception:
            try:
                self._process.kill()
            except Exception:
                pass
        self._process = None
        self.status_message.emit("Game stopped.", "info")
        self.game_stopped.emit()
        return True

    def poll(self) -> bool:
        """Check if process is still alive. Emits game_stopped if it ended."""
        if self._process is None:
            return False
        if self._process.poll() is not None:
            self._process = None
            self.game_stopped.emit()
            return False
        return True

    # ---------------------------------------------------------------- update
    def check_update(self, current_version: str) -> tuple[bool, str]:
        """Check for updates. Returns (needs_update, latest_version)."""
        latest = self.network.fetch_text(VERSION_URL)
        if not latest:
            return False, current_version
        return latest != current_version, latest

    def download_update(self, version: str, game_path: Path) -> bool:
        """Download and extract game update. Blocks until done."""
        url = f"https://github.com/{GITHUB_REPO}/releases/download/{version}/app.zip"
        zf = Path("game.zip")

        self.status_message.emit(f"Downloading v{version}...", "info")

        def prog(cur, total, spd):
            pct = cur / total * 100 if total else 0
            self.update_progress.emit(pct)
            self.status_message.emit(f"Downloading: {pct:.1f}% — {FileManager.format_size(spd)}/s", "info")

        if not self.network.download_file(url, zf, prog):
            self.status_message.emit("Download failed!", "danger")
            return False

        self.status_message.emit("Extracting...", "info")
        game_path.mkdir(parents=True, exist_ok=True)

        def xp(cur, total):
            pct = cur / total * 100 if total else 0
            self.update_progress.emit(pct)
            self.status_message.emit(f"Extracting: {pct:.0f}%", "info")

        if not FileManager.extract_zip(zf, game_path, xp):
            self.status_message.emit("Extraction failed!", "danger")
            return False

        FileManager.safe_delete(zf)

        exe = game_path / "Among Us.exe"
        if not exe.exists():
            found = list(game_path.rglob("Among Us.exe"))
            if found:
                game_path = found[0].parent
                self.status_message.emit(f"Game found in subfolder: {game_path.name}", "info")
            else:
                self.status_message.emit("Among Us.exe not found after extraction!", "danger")
                return False

        self.status_message.emit("Installing BepInEx...", "info")
        self._install_bepinex(game_path)

        self.status_message.emit("Installing isam-client.dll to all profiles...", "info")
        self._install_plugin_to_all_profiles(game_path)

        self.config.set_version(version)
        self.config.set_game_path(game_path)
        self.status_message.emit("Installation complete!", "success")
        return True

    def _find_bepmods_zip(self):
        """Locate the bundled bepmods.zip."""
        if getattr(sys, 'frozen', False):
            base = Path(sys.executable).parent
            zp = base / "_internal" / "bepmods.zip"
            if zp.exists():
                return zp
        else:
            zp = Path(__file__).parent.parent.parent.parent / "release" / "bepmods.zip"
            if zp.exists():
                return zp
        return None

    def _install_bepinex(self, game_path: Path):
        """Extract bepmods.zip into the game folder if found."""
        zp = self._find_bepmods_zip()
        if not zp:
            self.status_message.emit("bepmods.zip not found — skipping BepInEx", "warning")
            return
        self.status_message.emit("Extracting BepInEx...", "info")
        if not FileManager.extract_zip(zp, game_path):
            self.status_message.emit("BepInEx extraction failed", "warning")
            return
        self.status_message.emit("BepInEx installed!", "success")

    def _install_plugin_to_all_profiles(self, game_path: Path):
        """Download isam-client.dll, cache it, and copy it to every profile folder."""
        from gui_qt.profiles import ProfileManager

        profiles_dir = self.config.appdata_dir / "Profiles"
        profile_mgr = ProfileManager(profiles_dir)

        cached_dll = self.config.appdata_dir / "isam-client.dll"
        if not self.network.download_file(PLUGIN_DLL_URL, cached_dll):
            self.status_message.emit("Failed to download isam-client.dll", "warning")
            return

        for name in profile_mgr.list_profiles():
            target = profile_mgr.profile_path(name)
            try:
                target.mkdir(parents=True, exist_ok=True)
                import shutil
                shutil.copy2(str(cached_dll), str(target / "isam-client.dll"))
                self.status_message.emit(f"Copied isam-client.dll to profile: {name}", "info")
            except OSError as e:
                self.status_message.emit(f"Failed to copy to profile {name}: {e}", "warning")
