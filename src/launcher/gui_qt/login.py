"""
LoginWindow — full-page Steam/Epic-style login for Isam AULauncher.
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
from PySide6.QtGui import QPainter, QColor, QFont, QLinearGradient, QBrush, QIcon
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QApplication,
)

from config import APP_NAME, BRAND_SHORT, LAUNCHER_VERSION, MAKER
import gui_qt.theme as theme
from gui_qt.widgets import HeroBanner, _ICON_PATH

# Reuse existing OAuth infrastructure from itch_profile.py
from gui_qt.window.itch_profile import (
    ITCH_CLIENT_ID, ITCH_OAUTH_PORT,
    ITCH_TOKEN_DIR, ITCH_TOKEN_FILE,
)

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

        # Hero banner
        self._hero = HeroBanner(
            "Sign In",
            "Authenticate with itch.io to play Among Us online",
        )
        layout.addWidget(self._hero)

        # Content area
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(28, 24, 28, 0)
        content_layout.setSpacing(12)

        # Section title
        title = QLabel("ITCH.IO LOGIN")
        title.setObjectName("sectionTitle")
        content_layout.addWidget(title)
        content_layout.addSpacing(4)
        content_layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine))
        content_layout.addSpacing(20)

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
        content_layout.addLayout(login_row)

        content_layout.addSpacing(12)

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
        content_layout.addWidget(warn_widget)

        content_layout.addSpacing(8)

        # Status label
        self._status_label = QLabel("")
        self._status_label.setObjectName("statusText")
        content_layout.addWidget(self._status_label)

        content_layout.addStretch()

        # Footer
        footer = QLabel(f"{APP_NAME} v{LAUNCHER_VERSION} — Made by {MAKER}")
        footer.setObjectName("footerText")
        content_layout.addWidget(footer)

        layout.addWidget(content)

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
        QApplication.quit()
