"""
SplashScreen — Riot-style transparent splash screen for Isam AULauncher.
Frameless, semi-transparent window with brand logo and loading status.
"""
import sys
import math
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, Signal
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QLinearGradient, QFontMetrics

from config import APP_NAME, BRAND_SHORT, LAUNCHER_VERSION


class SplashScreen(QWidget):
    """Transparent splash screen with fade-in/out animations."""

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

        self._status = "Loading..."
        self._opacity = 0.0
        self._glow_phase = 0.0

        # Fade-in animation (fast — splash is only visible 1-2s)
        self._fade_in = QPropertyAnimation(self, b"windowOpacity")
        self._fade_in.setDuration(150)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.setEasingCurve(QEasingCurve.Type.OutQuad)

        # Glow animation (pulsing accent line)
        self._glow_timer = QTimer(self)
        self._glow_timer.timeout.connect(self._tick_glow)
        self._glow_timer.start(30)

    # ------------------------------------------------------------------ public
    def update_status(self, text: str):
        self._status = text
        self.update()

    def finish(self):
        """Fade out and emit finished signal."""
        fade_out = QPropertyAnimation(self, b"windowOpacity")
        fade_out.setDuration(350)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.Type.InCubic)
        fade_out.finished.connect(self._on_fade_out_done)
        fade_out.start()
        self._fade_out_anim = fade_out  # prevent GC

    def _on_fade_out_done(self):
        self._glow_timer.stop()
        self.close()
        self.finished.emit()

    # ------------------------------------------------------------------ animation
    def _tick_glow(self):
        self._glow_phase += 0.06
        if self._glow_phase > 6.28:
            self._glow_phase -= 6.28
        self.update()

    # ------------------------------------------------------------------ paint
    def paintEvent(self, event):
        try:
            self._paint(event)
        except Exception:
            pass

    def _paint(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()

        # --- Dark semi-transparent background ---
        bg = QColor(18, 20, 26, 230)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(0, 0, w, h, 16, 16)

        # --- Subtle border glow (pulsing) ---
        glow_intensity = int(40 + 30 * math.sin(self._glow_phase))
        border_color = QColor(99, 102, 241, glow_intensity)  # accent blue
        p.setPen(QPen(border_color, 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(1, 1, w - 2, h - 2, 15, 15)

        # --- Accent line at top ---
        grad = QLinearGradient(0, 0, w, 0)
        grad.setColorAt(0.0, QColor(99, 102, 241, 0))
        grad.setColorAt(0.3, QColor(99, 102, 241, 180))
        grad.setColorAt(0.5, QColor(52, 211, 153, 220))
        grad.setColorAt(0.7, QColor(99, 102, 241, 180))
        grad.setColorAt(1.0, QColor(99, 102, 241, 0))
        p.setPen(QPen(QBrush(grad), 2))
        p.drawLine(40, 3, w - 40, 3)

        # --- Brand text ---
        brand_font = QFont("Segoe UI", 36, QFont.Weight.Bold)
        p.setFont(brand_font)
        p.setPen(QColor(99, 102, 241))
        brand_rect = p.fontMetrics().boundingRect(BRAND_SHORT)
        bx = (w - brand_rect.width()) // 2
        p.drawText(bx, h // 2 - 30, BRAND_SHORT)

        # --- Version badge ---
        ver_text = f"v{LAUNCHER_VERSION}"
        ver_font = QFont("Segoe UI", 11)
        p.setFont(ver_font)
        fm = p.fontMetrics()
        tw = fm.horizontalAdvance(ver_text) + 20
        bx = (w - tw) // 2
        by = h // 2 + 10
        p.setPen(QColor(99, 102, 241, 100))
        p.setBrush(QColor(32, 36, 46, 200))
        p.drawRoundedRect(bx, by, tw, 24, 12, 12)
        p.setPen(QColor(52, 211, 153))
        p.drawText(bx, by, tw, 24, Qt.AlignmentFlag.AlignCenter, ver_text)

        # --- Loading status at bottom ---
        status_font = QFont("Segoe UI", 10)
        p.setFont(status_font)
        p.setPen(QColor(156, 163, 175))
        sfm = p.fontMetrics()
        stw = sfm.horizontalAdvance(self._status)
        sx = (w - stw) // 2
        p.drawText(sx, h - 30, self._status)

        # --- Loading dots animation ---
        dot_count = int(self._glow_phase / 1.2) % 4
        dots = "." * dot_count
        p.drawText(sx + stw, h - 30, dots)

        p.end()

    # ------------------------------------------------------------------ show
    def showEvent(self, event):
        super().showEvent(event)
        self._fade_in.start()
