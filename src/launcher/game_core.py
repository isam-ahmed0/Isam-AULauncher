"""
GameCore — Qt-free game lifecycle logic (launch, stop, update, install).

All game lifecycle logic lives here. GUIs (Qt and Tk) only wire up callbacks:
``on_status(text, level)``, ``on_progress(pct)``, ``on_started()`` and
``on_stopped()``. No GUI toolkit is imported, so lightweight front-ends can
reuse the exact same backend without pulling in PySide6.
"""
import sys
import time
import logging
import subprocess
from pathlib import Path

from config import VERSION_URL, GITHUB_REPO, ISAM_CLIENT_URL
from network import NetworkManager
from file_manager import FileManager

log = logging.getLogger(__name__)


class GameCore:
    """Manages the Among Us game process, updates and installation."""

    def __init__(self, config, network: NetworkManager):
        self.config = config
        self.network = network
        self._process = None

        # Callbacks wired up by the front-end (all optional).
        self.on_status = None    # Callable[[str, str], None]
        self.on_progress = None  # Callable[[float], None]
        self.on_started = None   # Callable[[], None]
        self.on_stopped = None   # Callable[[], None]

    # ------------------------------------------------------------- callbacks
    def _status(self, text: str, level: str = "info"):
        if self.on_status:
            self.on_status(text, level)

    def _progress(self, pct: float):
        if self.on_progress:
            self.on_progress(pct)

    def _started(self):
        if self.on_started:
            self.on_started()

    def _stopped(self):
        if self.on_stopped:
            self.on_stopped()

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
            self._status("Game not installed!", "danger")
            return False

        exe = gp / "Among Us.exe"
        if not exe.exists():
            self._status("Among Us.exe not found!", "danger")
            return False

        if self.is_running:
            self._status("Game is already running!", "warning")
            return False

        try:
            self._process = subprocess.Popen([str(exe)], cwd=str(gp))
            self._status("Game launched!", "success")
            self._started()
            return True
        except PermissionError:
            self._status("Permission denied. Try running as admin.", "danger")
            return False
        except OSError as e:
            self._status(f"Failed to launch: {e}", "danger")
            return False

    def launch_wine(self, gp: Path, exe: Path) -> bool:
        """Launch the Windows game with native Wine (Linux). Returns True on success."""
        from platform_utils import find_wine, wine_env
        wine = find_wine()
        if not wine:
            self._status("Wine not found", "danger")
            return False
        prefix = self.config.get_wine_prefix()
        try:
            self._process = subprocess.Popen(
                [wine, exe.name], cwd=str(gp), env=wine_env(prefix)
            )
            self._status("Game launched (Wine)!", "success")
            self._started()
            return True
        except OSError as e:
            self._status(f"Failed to launch: {e}", "danger")
            return False

    def launch_lutris(self, game_id) -> bool:
        """Launch the game through Lutris by numeric id. Returns True on success."""
        from platform_utils import lutris_run
        proc = lutris_run(game_id)
        if proc is None:
            self._status("Lutris not found", "danger")
            return False
        self._process = proc
        time.sleep(0.6)
        code = proc.poll()
        if code is not None and code != 0:
            self._process = None
            self._status("Lutris failed to start the game", "danger")
            return False
        self._status("Game launched (Lutris)!", "success")
        self._started()
        return True

    def stop(self):
        """Kill the game process."""
        if not self.is_running:
            self._status("No game running.", "warning")
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
        self._status("Game stopped.", "info")
        self._stopped()
        return True

    def poll(self) -> bool:
        """Check if process is still alive. Emits stopped if it ended."""
        if self._process is None:
            return False
        if self._process.poll() is not None:
            self._process = None
            self._stopped()
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
        cache_path = self.config.cache_dir / f"{version}.app.zip"

        if cache_path.exists() and cache_path.stat().st_size > 0:
            self._status(f"Using cached v{version}", "info")
            self._progress(100)
        else:
            self._status(f"Downloading v{version}...", "info")

            def prog(cur, total, spd):
                pct = cur / total * 100 if total else 0
                self._progress(pct)
                self._status(f"Downloading: {pct:.1f}% — {FileManager.format_size(spd)}/s", "info")

            if not self.network.download_file(url, cache_path, prog):
                self._status("Download failed!", "danger")
                return False

        self._status("Extracting...", "info")
        game_path.mkdir(parents=True, exist_ok=True)

        def xp(cur, total):
            pct = cur / total * 100 if total else 0
            self._progress(pct)
            self._status(f"Extracting: {pct:.0f}%", "info")

        if not FileManager.extract_zip(cache_path, game_path, xp):
            self._status("Extraction failed!", "danger")
            return False

        exe = game_path / "Among Us.exe"
        if not exe.exists():
            found = list(game_path.rglob("Among Us.exe"))
            if found:
                game_path = found[0].parent
                self._status(f"Game found in subfolder: {game_path.name}", "info")
            else:
                self._status("Among Us.exe not found after extraction!", "danger")
                return False

        self._status("Installing BepInEx...", "info")
        self._install_bepinex(game_path)

        self._status("Installing isam-client...", "info")
        self._install_isam_client(game_path)

        self.config.set_version(version)
        self.config.set_game_path(game_path)
        self._status("Installation complete!", "success")
        return True

    def _find_bepmods_zip(self):
        """Locate the bundled bepmods.zip."""
        if getattr(sys, 'frozen', False):
            base = Path(sys.executable).parent
            # PyInstaller >= 6 (onedir) puts datas in ``_internal/``; PyInstaller
            # 5.x (used for the Win7 build) places them straight next to the exe.
            for zp in (base / "_internal" / "bepmods.zip", base / "bepmods.zip"):
                if zp.exists():
                    return zp
        else:
            # game_core.py lives in src/launcher/, so repo root is three up.
            zp = Path(__file__).resolve().parent.parent.parent / "release" / "bepmods.zip"
            if zp.exists():
                return zp
        return None

    def _install_bepinex(self, game_path: Path):
        """Extract bepmods.zip into the game folder if found."""
        zp = self._find_bepmods_zip()
        if not zp:
            self._status("bepmods.zip not found — skipping BepInEx", "warning")
            return
        self._status("Extracting BepInEx...", "info")
        if not FileManager.extract_zip(zp, game_path):
            self._status("BepInEx extraction failed", "warning")
            return
        self._status("BepInEx installed!", "success")

    def _install_isam_client(self, game_path: Path):
        """Download and extract isam-client.zip into the game folder."""
        zf = self.config.cache_dir / "isam-client.zip"
        self._status("Downloading isam-client.zip...", "info")

        def prog(cur, total, spd):
            pct = cur / total * 100 if total else 0
            self._progress(pct)

        if not self.network.download_file(ISAM_CLIENT_URL, zf, prog):
            self._status("Failed to download isam-client.zip", "warning")
            return
        self._status("Extracting isam-client...", "info")
        if not FileManager.extract_zip(zf, game_path):
            self._status("isam-client extraction failed", "warning")
            return
        FileManager.safe_delete(zf)
        self._status("isam-client installed!", "success")
