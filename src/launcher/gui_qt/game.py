"""
GameManager — Qt adapter over the shared, toolkit-free GameCore.

All game lifecycle logic lives in ``game_core.GameCore``; this class keeps the
existing PySide6 signal-based public API used by the rest of the Qt GUI so that
the Tk (lite) front-end can reuse the exact same backend.
"""
from PySide6.QtCore import QObject, Signal

from game_core import GameCore


class GameManager(QObject):
    """Manages Among Us game process and updates (Qt signal facade)."""

    game_started = Signal()
    game_stopped = Signal()
    update_progress = Signal(float)
    status_message = Signal(str, str)  # (text, level)

    def __init__(self, config, network, parent=None):
        super().__init__(parent)
        self.config = config
        self.network = network
        self._core = GameCore(config, network)
        self._core.on_status = lambda text, level: self.status_message.emit(text, level)
        self._core.on_progress = lambda pct: self.update_progress.emit(pct)
        self._core.on_started = self.game_started.emit
        self._core.on_stopped = self.game_stopped.emit

    # ---------------------------------------------------------------- process
    @property
    def is_running(self) -> bool:
        return self._core.is_running

    @property
    def pid(self) -> int:
        return self._core.pid

    def launch(self):
        return self._core.launch()

    def launch_wine(self, gp, exe) -> bool:
        return self._core.launch_wine(gp, exe)

    def launch_lutris(self, game_id) -> bool:
        return self._core.launch_lutris(game_id)

    def stop(self):
        return self._core.stop()

    def poll(self) -> bool:
        return self._core.poll()

    # ---------------------------------------------------------------- update
    def check_update(self, current_version: str):
        return self._core.check_update(current_version)

    def download_update(self, version: str, game_path) -> bool:
        return self._core.download_update(version, game_path)
