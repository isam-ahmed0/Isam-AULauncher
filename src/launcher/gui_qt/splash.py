"""
SplashScreen — transparent PNG splash screen for Isam AULauncher.
Frameless window displaying a PNG image with loading status overlay.
"""
import sys
import logging
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, Signal
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QFont, QPixmap

from config import LAUNCHER_VERSION
import gui_qt.theme as theme


_RESOURCES_DIR = Path(__file__).parent.parent / "resources"


class SplashScreen(QWidget):
    """Transparent PNG splash screen with fade-out animation."""

    finished = Signal()

    WIDTH = 700
    HEIGHT = 400

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

        self._status = "Loading..."
        self._pixmap = None

        # Load splash image
        splash_path = _RESOURCES_DIR / "splash.png"
        if splash_path.exists():
            self._pixmap = QPixmap(str(splash_path))
            if self._pixmap.isNull():
                logging.warning(f"Failed to load splash image: {splash_path}")
                self._pixmap = None
        else:
            logging.warning(f"Splash image not found: {splash_path}")

        # Fade-in handled in showEvent
        self.setWindowOpacity(0.0)

    # ------------------------------------------------------------------ public
    def update_status(self, text: str):
        self._status = text
        self.update()

    def finish(self):
        """Fade out and emit finished signal."""
        fade_out = QPropertyAnimation(self, b"windowOpacity")
        fade_out.setDuration(150)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.Type.InCubic)
        fade_out.finished.connect(self._on_fade_out_done)
        fade_out.start()
        self._fade_out_anim = fade_out  # prevent GC

    def _on_fade_out_done(self):
        self.close()
        self.finished.emit()

    # ------------------------------------------------------------------ paint
    def paintEvent(self, event):
        try:
            self._paint(event)
        except Exception:
            pass

    def _paint(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()

        # --- Draw splash image centered ---
        if self._pixmap and not self._pixmap.isNull():
            scaled = self._pixmap.scaled(
                w, h,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = (w - scaled.width()) // 2
            y = (h - scaled.height()) // 2
            p.drawPixmap(x, y, scaled)

        # --- Loading status at bottom ---
        text_color = QColor(255, 255, 255, 200)
        shadow_color = QColor(0, 0, 0, 150)

        status_font = QFont("Segoe UI", 10)
        p.setFont(status_font)
        sfm = p.fontMetrics()
        stw = sfm.horizontalAdvance(self._status)
        sx = (w - stw) // 2
        sy = h - 20

        # Shadow
        p.setPen(shadow_color)
        p.drawText(sx + 1, sy + 1, self._status)

        # Text
        p.setPen(text_color)
        p.drawText(sx, sy, self._status)

        p.end()

    # ------------------------------------------------------------------ show
    def showEvent(self, event):
        super().showEvent(event)
        self.setWindowOpacity(0.0)
        fade_in = QPropertyAnimation(self, b"windowOpacity", self)
        fade_in.setDuration(280)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)
        fade_in.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        self._fade_in_ref = fade_in
