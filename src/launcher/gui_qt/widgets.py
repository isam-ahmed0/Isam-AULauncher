from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QPainter, QColor, QLinearGradient, QFont, QFontMetrics
from PySide6.QtWidgets import QLabel

from config import LAUNCHER_VERSION


_RESOURCES_DIR = Path(__file__).parent.parent / "resources"
_HERO_IMAGE_PATH = _RESOURCES_DIR / "hero.png"
_ICON_PATH = _RESOURCES_DIR / "icon.ico"

SIDEBAR_W = 200


class HeroBanner(QLabel):
    """Custom hero banner that draws a gradient background with overlay text."""

    def __init__(self, title, subtitle, parent=None):
        super().__init__(parent)
        self._title = title
        self._subtitle = subtitle
        self._hero_image = None
        self.setMinimumHeight(220)
        self.setMaximumHeight(220)

        if _HERO_IMAGE_PATH.exists():
            self._hero_image = QPixmap(str(_HERO_IMAGE_PATH))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Background
        if self._hero_image and not self._hero_image.isNull():
            scaled = self._hero_image.scaled(
                w, h,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            painter.drawPixmap(0, 0, scaled)
            painter.fillRect(0, 0, w, h, QColor(12, 14, 20, 160))
        else:
            gradient = QLinearGradient(0, 0, w, h)
            gradient.setColorAt(0, QColor(18, 20, 26))
            gradient.setColorAt(0.5, QColor(24, 27, 34))
            gradient.setColorAt(1, QColor(18, 20, 26))
            painter.fillRect(0, 0, w, h, gradient)

        # Subtle glow orb
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(99, 102, 241, 25))
        painter.drawEllipse(int(w * 0.75) - 80, int(h * 0.35) - 80, 160, 160)
        painter.setBrush(QColor(52, 211, 153, 20))
        painter.drawEllipse(int(w * 0.15) - 65, int(h * 0.7) - 65, 130, 130)

        # Bottom accent gradient line
        gradient = QLinearGradient(0, 0, w, 0)
        gradient.setColorAt(0, QColor(99, 102, 241, 200))
        gradient.setColorAt(1, QColor(52, 211, 153, 200))
        painter.setBrush(gradient)
        painter.drawRect(0, h - 3, w, 3)

        # Title text
        painter.setPen(QColor(255, 255, 255))
        title_font = QFont("Segoe UI", 24)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.drawText(28, int(h * 0.45), self._title)

        # Subtitle text
        painter.setPen(QColor(156, 163, 175))
        sub_font = QFont("Segoe UI", 13)
        painter.setFont(sub_font)
        painter.drawText(28, int(h * 0.45) + 32, self._subtitle)

        # Version badge
        badge_text = f"v{LAUNCHER_VERSION}"
        badge_font = QFont("Segoe UI", 10)
        painter.setFont(badge_font)
        fm = painter.fontMetrics()
        tw = fm.horizontalAdvance(badge_text) + 20
        bx, by = 28, h - 38
        painter.setBrush(QColor(32, 36, 46, 220))
        painter.setPen(QColor(99, 102, 241, 100))
        painter.drawRoundedRect(bx, by, tw, 24, 12, 12)
        painter.setPen(QColor(52, 211, 153))
        painter.drawText(bx, by, tw, 24, Qt.AlignmentFlag.AlignCenter, badge_text)

        painter.end()
