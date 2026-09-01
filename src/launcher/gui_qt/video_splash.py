"""
VideoSplash — plays a WebM video as a frameless splash screen.
Falls back to the default SplashScreen when the video ends.
"""
import logging
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget

_RESOURCES_DIR = Path(__file__).parent.parent / "resources"


class VideoSplash(QWidget):
    """Frameless video splash — plays once, then emits finished."""

    finished = Signal()

    WIDTH = 520
    HEIGHT = 320

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(self.WIDTH, self.HEIGHT)

        # Center on screen
        screen = self.screen()
        if screen:
            geo = screen.availableGeometry()
            x = (geo.width() - self.WIDTH) // 2 + geo.x()
            y = (geo.height() - self.HEIGHT) // 2 + geo.y()
            self.move(x, y)

        # Video widget fills the entire splash
        self._video_widget = QVideoWidget(self)
        self._video_widget.setGeometry(0, 0, self.WIDTH, self.HEIGHT)

        # Audio (muted — splash has no sound)
        self._audio = QAudioOutput()
        self._audio.setVolume(0)

        # Media player
        self._player = QMediaPlayer()
        self._player.setVideoOutput(self._video_widget)
        self._player.setAudioOutput(self._audio)
        self._player.mediaStatusChanged.connect(self._on_status)
        self._player.errorOccurred.connect(self._on_error)

    def play(self):
        """Load and play the WebM file."""
        webm = _RESOURCES_DIR / "splash.webm"
        if not webm.exists():
            logging.warning(f"Video splash not found: {webm}")
            self.finished.emit()
            return
        self._player.setSource(webm)
        self._player.play()

    def _on_status(self, status):
        from PySide6.QtMultimedia import QMediaPlayer
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self._player.stop()
            self.close()
            self.finished.emit()

    def _on_error(self, error, msg=""):
        logging.warning(f"Video splash error: {error} — {msg}")
        self._player.stop()
        self.close()
        self.finished.emit()
