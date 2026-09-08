"""
LoginWindow — full-page Steam/Epic-style login for Isam AULauncher.
Uses the existing itch.io OAuth from itch_profile.py.
Right sidebar supports image, GIF, and slideshow.
"""
import os
import sys
import time
import logging
import webbrowser
import threading
import urllib.parse
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import (
    QPainter, QColor, QFont, QLinearGradient, QBrush, QIcon,
    QPixmap, QMovie,
)
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QApplication,
)

from config import APP_NAME, BRAND_SHORT, LAUNCHER_VERSION, MAKER
import gui_qt.theme as theme
from gui_qt.widgets import HeroBanner, _ICON_PATH, _hex_to_qcolor

# Reuse existing OAuth infrastructure from itch_profile.py
from gui_qt.window.itch_profile import (
    ITCH_CLIENT_ID, ITCH_OAUTH_PORT,
    ITCH_TOKEN_DIR, ITCH_TOKEN_FILE,
)

_LOGIN_DIR = Path(__file__).parent.parent / "resources" / "login"

_LOADING_PAGE = b"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Isam AU | Authenticating</title>
    <style>
        body { background: #060608; color: #6366f1; display: flex; flex-direction: column;
               justify-content: center; align-items: center; height: 100vh;
               font-family: 'Segoe UI', sans-serif; margin: 0; }
        .loader { border: 4px solid #1a1b1e; border-top: 4px solid #6366f1; border-radius: 50%;
                  width: 50px; height: 50px; animation: spin 1s linear infinite; margin-bottom: 20px; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .text { font-weight: bold; letter-spacing: 1px; }
    </style>
</head>
<body>
    <div class="loader"></div>
    <div class="text">CONNECTING TO ITCH.IO...</div>
    <script>
        const params = new URLSearchParams(window.location.hash.slice(1));
        const token = params.get('access_token');
        if (token) window.location = '/token?t=' + token;
    </script>
</body>
</html>"""

_SUCCESS_PAGE = b"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Isam AU | Success</title>
    <style>
        body { background: #060608; color: #4ade80; display: flex; flex-direction: column;
               justify-content: center; align-items: center; height: 100vh;
               font-family: 'Segoe UI', sans-serif; margin: 0; }
        .icon { font-size: 60px; margin-bottom: 10px; }
        .msg { font-size: 24px; font-weight: bold; }
        .sub { color: #888; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="icon">&#10004;</div>
    <div class="msg">AUTHORIZATION COMPLETE</div>
    <div class="sub">You can close this tab and return to the launcher.</div>
</body>
</html>"""


class _OAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/token"):
            params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            self.server.token = params.get("t", [None])[0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(_SUCCESS_PAGE)
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(_LOADING_PAGE)

    def log_message(self, format, *args):
        pass


class _RightSidebar(QWidget):
    """Right sidebar panel that displays image, GIF, or slideshow."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(400)
        self._mode = "gradient"
        self._movie = None
        self._slides = []
        self._slide_index = 0
        self._slide_timer = QTimer(self)
        self._slide_timer.timeout.connect(self._next_slide)

        self._load_content()

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
            self._slide_timer.start(5000)
            return

        static_path = _LOGIN_DIR / "login_promo.png"
        if static_path.exists():
            self._mode = "static"
            return

        self._mode = "gradient"

    def _next_slide(self):
        """Advance to next slide."""
        if self._slides:
            self._slide_index = (self._slide_index + 1) % len(self._slides)
            self.update()

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
            pixmap = QPixmap(str(self._slides[self._slide_index]))
            if not pixmap.isNull():
                scaled = pixmap.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                       Qt.TransformationMode.SmoothTransformation)
                x = (w - scaled.width()) // 2
                y = (h - scaled.height()) // 2
                p.drawPixmap(x, y, scaled)
                p.end()
                return

        if self._mode == "static":
            static_path = _LOGIN_DIR / "login_promo.png"
            pixmap = QPixmap(str(static_path))
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

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} — Sign In")
        self.setMinimumSize(960, 580)
        self.resize(1100, 680)
        if _ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(_ICON_PATH)))

        self._status = ""
        self._logging_in = False

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Hero banner (full width)
        self._hero = HeroBanner(
            "Sign In",
            "Authenticate with itch.io to play Among Us online",
        )
        layout.addWidget(self._hero)

        # Split: left content + right sidebar
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        # Left content
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(28, 24, 28, 0)
        left_layout.setSpacing(12)

        title = QLabel("ITCH.IO LOGIN")
        title.setObjectName("sectionTitle")
        left_layout.addWidget(title)
        left_layout.addSpacing(4)
        left_layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine))
        left_layout.addSpacing(20)

        # Login button
        self._login_btn = QPushButton("Sign in with itch.io")
        self._login_btn.setObjectName("successBtn")
        self._login_btn.setFixedHeight(44)
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

        layout.addWidget(body)

    # ------------------------------------------------------------------ OAuth
    def _start_login(self):
        if self._logging_in:
            return
        self._logging_in = True
        self._login_btn.setEnabled(False)
        self._set_status("Opening itch.io login...")

        def run_server():
            try:
                server = HTTPServer(("127.0.0.1", ITCH_OAUTH_PORT), _OAuthHandler)
                server.token = None
                server.timeout = 1
                deadline = time.time() + 300
                while server.token is None and time.time() < deadline:
                    server.handle_request()
                if server.token:
                    self._save_token(server.token)
                    QTimer.singleShot(0, lambda: self._set_status("Login successful!"))
                    QTimer.singleShot(1000, self._restart_app)
                else:
                    QTimer.singleShot(0, lambda: self._set_status("Login timed out. Try again."))
                    QTimer.singleShot(0, self._reset_btn)
            except OSError as e:
                logging.error(f"OAuth server error: {e}")
                QTimer.singleShot(0, lambda: self._set_status(f"Login failed: {e}"))
                QTimer.singleShot(0, self._reset_btn)

        threading.Thread(target=run_server, daemon=True).start()
        webbrowser.open(
            f"https://itch.io/user/oauth?client_id={ITCH_CLIENT_ID}"
            f"&scope=profile:me&redirect_uri=http://127.0.0.1:{ITCH_OAUTH_PORT}"
            f"&response_type=token"
        )

    def _save_token(self, token: str):
        try:
            ITCH_TOKEN_DIR.mkdir(parents=True, exist_ok=True)
            ITCH_TOKEN_FILE.write_text(token)
            logging.info("Itch token saved successfully")
        except OSError as e:
            logging.error(f"Failed to save itch token: {e}")

    def _restart_app(self):
        os.execv(sys.executable, [sys.executable] + sys.argv)

    def _reset_btn(self):
        self._logging_in = False
        self._login_btn.setEnabled(True)

    def _set_status(self, text: str):
        self._status = text
        self._status_label.setText(text)

    def closeEvent(self, event):
        if self._sidebar._movie:
            self._sidebar._movie.stop()
        QApplication.quit()
