"""
LoginWindow — Steam/Epic-style login page for Isam AULauncher.
Uses the existing itch.io OAuth from itch_profile.py.
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
from PySide6.QtGui import QPainter, QColor, QFont, QLinearGradient, QBrush
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QApplication,
)

from config import APP_NAME, BRAND_SHORT, LAUNCHER_VERSION, MAKER
import gui_qt.theme as theme

# Reuse existing OAuth infrastructure from itch_profile.py — no changes there
from gui_qt.window.itch_profile import (
    ITCH_CLIENT_ID, ITCH_OAUTH_PORT,
    ITCH_TOKEN_DIR, ITCH_TOKEN_FILE,
)

ITCHIO_API = "https://itch.io/api/1/key/me"

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
    """Handles the OAuth redirect from itch.io."""

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


class LoginWindow(QMainWindow):
    """Steam/Epic-style login page using itch.io OAuth."""

    WIDTH = 500
    HEIGHT = 400

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} — Sign In")
        self.setFixedSize(self.WIDTH, self.HEIGHT)
        self.setWindowFlags(Qt.WindowType.Dialog)

        # Center on screen
        screen = self.screen()
        if screen:
            geo = screen.availableGeometry()
            x = (geo.width() - self.WIDTH) // 2 + geo.x()
            y = (geo.height() - self.HEIGHT) // 2 + geo.y()
            self.move(x, y)

        self._status = ""
        self._logging_in = False

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Content area
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(40, 40, 40, 30)
        content_layout.setSpacing(0)

        # Brand
        brand = QLabel(BRAND_SHORT)
        brand.setObjectName("brandLabel")
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(brand)

        app_name = QLabel(APP_NAME)
        app_name.setObjectName("brandSubLabel")
        app_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(app_name)

        content_layout.addSpacing(30)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        content_layout.addWidget(sep)

        content_layout.addSpacing(30)

        # Welcome text
        welcome = QLabel("Sign in to continue")
        welcome.setObjectName("sectionTitle")
        welcome.setStyleSheet(f"font-size: 13px; color: {theme.TEXT_SECONDARY};")
        welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(welcome)

        content_layout.addSpacing(20)

        # Login button
        self._login_btn = QPushButton("Sign in with itch.io")
        self._login_btn.setObjectName("successBtn")
        self._login_btn.setFixedHeight(44)
        self._login_btn.setMinimumWidth(260)
        self._login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._login_btn.clicked.connect(self._start_login)
        login_row = QHBoxLayout()
        login_row.addStretch()
        login_row.addWidget(self._login_btn)
        login_row.addStretch()
        content_layout.addLayout(login_row)

        content_layout.addSpacing(12)

        # Register link
        register_btn = QPushButton("Create a free account")
        register_btn.setObjectName("toolBtn")
        register_btn.setFixedHeight(32)
        register_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        register_btn.clicked.connect(lambda: webbrowser.open("https://itch.io/register"))
        register_row = QHBoxLayout()
        register_row.addStretch()
        register_row.addWidget(register_btn)
        register_row.addStretch()
        content_layout.addLayout(register_row)

        content_layout.addSpacing(8)

        # Status label
        self._status_label = QLabel("")
        self._status_label.setObjectName("statusText")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(self._status_label)

        content_layout.addStretch()

        # Footer
        footer = QLabel(f"{APP_NAME} v{LAUNCHER_VERSION} — Made by {MAKER}")
        footer.setObjectName("footerText")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(footer)

        layout.addWidget(content)

    # ------------------------------------------------------------------ OAuth
    def _start_login(self):
        """Start the OAuth flow: launch HTTP server in a thread, open browser."""
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
        """Save the itch.io access token to the file Among Us reads."""
        try:
            ITCH_TOKEN_DIR.mkdir(parents=True, exist_ok=True)
            ITCH_TOKEN_FILE.write_text(token)
            logging.info("Itch token saved successfully")
        except OSError as e:
            logging.error(f"Failed to save itch token: {e}")

    def _restart_app(self):
        """Restart the launcher app."""
        os.execv(sys.executable, [sys.executable] + sys.argv)

    def _reset_btn(self):
        self._logging_in = False
        self._login_btn.setEnabled(True)

    def _set_status(self, text: str):
        self._status = text
        self._status_label.setText(text)

    # ------------------------------------------------------------------ paint
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        accent = QColor(theme.ACCENT)
        accent2 = QColor(theme.ACCENT_2)
        bg_base = QColor(theme.BG_BASE)
        bg_surface = QColor(theme.BG_SURFACE)

        # Background gradient
        gradient = QLinearGradient(0, 0, w, h)
        gradient.setColorAt(0, bg_base)
        gradient.setColorAt(0.5, bg_surface)
        gradient.setColorAt(1, bg_base)
        p.fillRect(0, 0, w, h, gradient)

        # Subtle glow orb
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(accent.red(), accent.green(), accent.blue(), 15))
        p.drawEllipse(int(w * 0.75) - 80, int(h * 0.3) - 80, 160, 160)
        p.setBrush(QColor(accent2.red(), accent2.green(), accent2.blue(), 12))
        p.drawEllipse(int(w * 0.2) - 60, int(h * 0.7) - 60, 120, 120)

        # Bottom accent line
        grad = QLinearGradient(0, 0, w, 0)
        grad.setColorAt(0, QColor(accent.red(), accent.green(), accent.blue(), 200))
        grad.setColorAt(1, QColor(accent2.red(), accent2.green(), accent2.blue(), 200))
        p.setBrush(grad)
        p.drawRect(0, h - 3, w, 3)

        p.end()

    def closeEvent(self, event):
        """Quit app on close."""
        QApplication.quit()
