"""
VideoSplash — plays a transparent WebM video as a frameless splash screen.
Uses QVideoSink for frame-by-frame rendering with alpha channel support.
Falls back to the default SplashScreen when the video ends.
"""
import logging
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QImage, QPixmap, QPainter
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput, QVideoSink, QVideoFrame

_RESOURCES_DIR = Path(__file__).parent.parent / "resources"


class VideoSplash(QWidget):
    """Frameless video splash with alpha support — plays once, then emits finished."""

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

        self._pixmap = None

        # Audio (muted)
        self._audio = QAudioOutput()
        self._audio.setVolume(0)

        # Video sink for frame-by-frame rendering
        self._sink = QVideoSink()
        self._sink.videoFrameChanged.connect(self._on_frame)

        # Media player
        self._player = QMediaPlayer()
        self._player.setVideoSink(self._sink)
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
        self._player.setSource(QUrl.fromLocalFile(str(webm)))
        self._player.play()

    def _on_frame(self, frame: QVideoFrame):
        """Convert each video frame to QPixmap with Alpha support and repaint."""
        if not frame.isValid():
            return

        # Ensure frame is converted into standard ARGB32 format for transparency
        image = frame.toImage()
        if image.isNull():
            return

        if image.format() != QImage.Format.Format_ARGB32:
            image = image.convertToFormat(QImage.Format.Format_ARGB32)

        # Scale to fit splash size cleanly
        self._pixmap = QPixmap.fromImage(image).scaled(
            self.WIDTH,
            self.HEIGHT,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.update()

    def paintEvent(self, event):
        """Paint the current frame on a transparent background."""
        if self._pixmap is None:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Center the scaled frame in the splash area
        x = (self.WIDTH - self._pixmap.width()) // 2
        y = (self.HEIGHT - self._pixmap.height()) // 2
        p.drawPixmap(x, y, self._pixmap)
        p.end()

    def _on_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self._player.stop()
            self.close()
            self.finished.emit()

    def _on_error(self, error, msg=""):
        logging.warning(f"Video splash error: {error} — {msg}")
        self._player.stop()
        self.close()
        self.finished.emit()
