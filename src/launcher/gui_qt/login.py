"""
LoginWindow — full-page Steam/Epic-style login for Isam AULauncher.
Uses the native itch.io OAuth flow from itch_auth.py.
Right sidebar supports image, GIF, and slideshow.
"""
import os
import sys
import logging
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup
from PySide6.QtGui import (
    QPainter, QColor, QFont, QLinearGradient, QBrush, QIcon,
    QPixmap, QMovie,
)
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QApplication,
    QGraphicsOpacityEffect, QMessageBox,
)

from config import APP_NAME, BRAND_SHORT, LAUNCHER_VERSION, MAKER
import gui_qt.theme as theme
from gui_qt.widgets import _ICON_PATH, _hex_to_qcolor
from itch_auth import ItchOAuthSession, save_itch_token
import webbrowser

_LOGIN_DIR = Path(__file__).parent.parent / "resources" / "login"


class _RightSidebar(QWidget):
    """Right sidebar panel that displays image, GIF, or slideshow with cross-fade."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(400)
        self._mode = "gradient"
        self._movie = None
        self._slides = []
        self._slide_index = 0
        self._slide_timer = QTimer(self)
        self._slide_timer.timeout.connect(self._next_slide)
        self._slide_anim_ref = None

        self._label_a = QLabel(self)
        self._label_b = QLabel(self)
        for lbl in (self._label_a, self._label_b):
            lbl.setScaledContents(True)
            lbl.raise_()
        self._active_label = self._label_a
        self._effect_a = QGraphicsOpacityEffect(self._label_a)
        self._effect_b = QGraphicsOpacityEffect(self._label_b)
        self._label_a.setGraphicsEffect(self._effect_a)
        self._label_b.setGraphicsEffect(self._effect_b)
        self._effect_a.setOpacity(1.0)
        self._effect_b.setOpacity(0.0)

        self._load_content()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w, h = self.width(), self.height()
        self._label_a.setGeometry(0, 0, w, h)
        self._label_b.setGeometry(0, 0, w, h)

    def _load_content(self):
        """Determine display mode and load content."""
        if not _LOGIN_DIR.exists():
            self._mode = "gradient"
            return

        gif_path = _LOGIN_DIR / "login_promo.gif"
        if gif_path.exists():
            self._mode = "gif"
            self._movie = QMovie(str(gif_path))
            if self._movie.isValid():
                self._movie.start()
            else:
                self._mode = "gradient"
                self._movie = None
            return

        slides = sorted(_LOGIN_DIR.glob("slide_*.png"))
        if slides:
            self._mode = "slideshow"
            self._slides = slides
            self._slide_index = 0
            self._active_label.setPixmap(self._load_pixmap(self._slides[0]))
            self._slide_timer.start(5000)
            return

        for ext in ("png", "ico"):
            static_path = _LOGIN_DIR / f"login_promo.{ext}"
            if static_path.exists():
                self._mode = "static"
                self._static_path = static_path
                return

        self._mode = "gradient"

    def _load_pixmap(self, path):
        """Load and scale a pixmap to fill the sidebar."""
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            return pixmap
        w, h = self.width(), self.height()
        return pixmap.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                             Qt.TransformationMode.SmoothTransformation)

    def _next_slide(self):
        """Advance to next slide with cross-fade."""
        if not self._slides:
            return
        self._slide_index = (self._slide_index + 1) % len(self._slides)

        incoming = self._label_b if self._active_label is self._label_a else self._label_a
        outgoing = self._active_label
        out_effect = self._effect_a if outgoing is self._label_a else self._effect_b
        in_effect = self._effect_a if incoming is self._label_a else self._effect_b

        incoming.setPixmap(self._load_pixmap(self._slides[self._slide_index]))
        incoming.raise_()

        group = QParallelAnimationGroup(self)
        fade_out = QPropertyAnimation(out_effect, b"opacity", self)
        fade_out.setDuration(600)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.Type.InOutQuad)

        fade_in = QPropertyAnimation(in_effect, b"opacity", self)
        fade_in.setDuration(600)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QEasingCurve.Type.InOutQuad)

        group.addAnimation(fade_out)
        group.addAnimation(fade_in)
        group.start(QParallelAnimationGroup.DeletionPolicy.DeleteWhenStopped)
        self._slide_anim_ref = group
        self._active_label = incoming

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        w, h = self.width(), self.height()

        if self._mode == "gif" and self._movie and self._movie.isValid():
            frame = self._movie.currentPixmap()
            if not frame.isNull():
                scaled = frame.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                      Qt.TransformationMode.SmoothTransformation)
                x = (w - scaled.width()) // 2
                y = (h - scaled.height()) // 2
                p.drawPixmap(x, y, scaled)
                p.end()
                return

        if self._mode == "slideshow" and self._slides:
            p.end()
            return

        if self._mode == "static" and hasattr(self, '_static_path'):
            pixmap = QPixmap(str(self._static_path))
            if not pixmap.isNull():
                scaled = pixmap.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                       Qt.TransformationMode.SmoothTransformation)
                x = (w - scaled.width()) // 2
                y = (h - scaled.height()) // 2
                p.drawPixmap(x, y, scaled)
                p.end()
                return

        # Gradient fallback
        accent = _hex_to_qcolor(theme.ACCENT)
        accent2 = _hex_to_qcolor(theme.ACCENT_2)
        bg_base = _hex_to_qcolor(theme.BG_BASE)
        bg_surface = _hex_to_qcolor(theme.BG_SURFACE)

        gradient = QLinearGradient(0, 0, w, h)
        gradient.setColorAt(0, bg_surface)
        gradient.setColorAt(0.5, bg_base)
        gradient.setColorAt(1, bg_surface)
        p.fillRect(0, 0, w, h, gradient)

        # Glow orbs
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(accent.red(), accent.green(), accent.blue(), 25))
        p.drawEllipse(int(w * 0.3) - 80, int(h * 0.3) - 80, 160, 160)
        p.setBrush(QColor(accent2.red(), accent2.green(), accent2.blue(), 20))
        p.drawEllipse(int(w * 0.7) - 60, int(h * 0.65) - 60, 120, 120)
        p.setBrush(QColor(accent.red(), accent.green(), accent.blue(), 12))
        p.drawEllipse(int(w * 0.5) - 100, int(h * 0.8) - 100, 200, 200)

        # Brand text centered
        p.setPen(QColor(accent.red(), accent.green(), accent.blue(), 80))
        f = QFont("Segoe UI", 28)
        f.setFamilies(["Segoe UI", "Inter", "Helvetica Neue", "Arial"])
        f.setBold(True)
        p.setFont(f)
        p.drawText(0, 0, w, h, Qt.AlignmentFlag.AlignCenter, BRAND_SHORT)

        p.end()


class LoginWindow(QMainWindow):
    """Full-page login window matching the main launcher style."""

    def __init__(self, parent=None, prefix=None):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} — Sign In")
        self.setMinimumSize(960, 580)
        self.resize(1100, 680)
        if _ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(_ICON_PATH)))

        self._status = ""
        self._logging_in = False
        self._prefix = prefix
        self._auth = None

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Split: left content + right sidebar (full height)
        body_widget = QWidget()
        body = QHBoxLayout(body_widget)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        # Left content
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(40, 40, 40, 20)
        left_layout.setSpacing(14)

        # Brand header
        brand = QLabel(BRAND_SHORT)
        brand.setObjectName("brandLabel")
        left_layout.addWidget(brand)

        app_name = QLabel(APP_NAME)
        app_name.setObjectName("brandSubLabel")
        left_layout.addWidget(app_name)

        left_layout.addSpacing(28)
        left_layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine))
        left_layout.addSpacing(20)

        # Section title
        title = QLabel("ITCH.IO LOGIN")
        title.setObjectName("sectionTitle")
        left_layout.addWidget(title)
        left_layout.addSpacing(16)

        # Login button
        self._login_btn = QPushButton("Sign in with itch.io")
        self._login_btn.setObjectName("successBtn")
        self._login_btn.setFixedHeight(38)
        self._login_btn.setMinimumWidth(260)
        self._login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._login_btn.clicked.connect(self._start_login)
        login_row = QHBoxLayout()
        login_row.addWidget(self._login_btn)
        login_row.addStretch()
        left_layout.addLayout(login_row)

        left_layout.addSpacing(12)

        # Warning notice
        warn_widget = QWidget()
        warn_layout = QHBoxLayout(warn_widget)
        warn_layout.setContentsMargins(12, 12, 12, 12)
        warn_layout.setSpacing(10)

        warn_icon = QLabel("!")
        warn_icon.setObjectName("warningText")
        warn_icon.setFixedSize(28, 28)
        warn_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        warn_icon.setStyleSheet(f"""
            background-color: {theme.WARNING};
            color: #000000;
            border-radius: 14px;
            font-weight: 700;
            font-size: 14px;
        """)
        warn_layout.addWidget(warn_icon)

        warn_text = QLabel(
            "You need a free itch.io account to play Among Us online.\n"
            "Create one at itch.io before signing in."
        )
        warn_text.setObjectName("warningText")
        warn_text.setWordWrap(True)
        warn_layout.addWidget(warn_text, 1)
        left_layout.addWidget(warn_widget)

        left_layout.addSpacing(8)

        # Status label
        self._status_label = QLabel("")
        self._status_label.setObjectName("statusText")
        left_layout.addWidget(self._status_label)

        left_layout.addStretch()

        # Footer
        footer = QLabel(f"{APP_NAME} v{LAUNCHER_VERSION} — Made by {MAKER}")
        footer.setObjectName("footerText")
        left_layout.addWidget(footer)

        body.addWidget(left, 1)

        # Right sidebar
        self._sidebar = _RightSidebar()
        body.addWidget(self._sidebar)

        layout.addWidget(body_widget)

    # ------------------------------------------------------------------ sign-in (native)
    def _start_login(self):
        if self._logging_in:
            return
        self._logging_in = True
        self._login_btn.setEnabled(False)

        if self._auth is not None:
            self._auth.stop()
        self._auth = ItchOAuthSession(parent=self)
        self._auth.token.connect(self._on_token)
        self._auth.failed.connect(self._on_auth_failed)
        self._auth.timed_out.connect(self._on_timed_out)

        try:
            self._auth.start()
        except OSError:
            self._finish_port_busy()
            return

        webbrowser.open(self._auth.auth_url())
        self._set_status("Check your browser — authorize your itch.io account there.")

    def _finish_port_busy(self):
        QMessageBox.warning(
            self, "Couldn't Start Login",
            "The itch.io login callback port (7890) is already in use.\n"
            "Close the Itch Login Fixer or any other app using that port, "
            "then try again.",
        )
        self._reset_btn()

    def _on_token(self, token: str):
        try:
            self._save_token(token)
        except OSError as e:
            self._set_status(f"Login succeeded but the token could not be saved: {e}")
            self._reset_btn()
            return
        self._set_status("Login successful! Restarting...")
        QTimer.singleShot(800, self._restart_app)

    def _on_auth_failed(self, message: str):
        self._set_status(message)
        self._reset_btn()

    def _on_timed_out(self):
        self._set_status("Login timed out. Try again.")
        self._reset_btn()

    def _save_token(self, token: str):
        save_itch_token(token, self._prefix)
        logging.info("Itch token saved successfully")

    def _restart_app(self):
        os.execv(sys.executable, [sys.executable] + sys.argv)

    def _reset_btn(self):
        self._logging_in = False
        self._login_btn.setEnabled(True)

    def _set_status(self, text: str):
        self._status = text
        self._status_label.setText(text)

    def closeEvent(self, event):
        if self._auth is not None:
            self._auth.stop()
        if self._sidebar._movie:
            self._sidebar._movie.stop()
        QApplication.quit()
