import os
import sys
import time
import logging
import webbrowser
import threading
import urllib.parse
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

import requests as _req
from PySide6.QtCore import Qt, Signal

import gui_qt.theme as theme


ITCH_CLIENT_ID = "1ba9b4bfa1ac7759e8420eed4ec863ba"
ITCH_OAUTH_PORT = 7890

ITCH_TOKEN_DIR = Path(os.environ.get("USERPROFILE", "")) / "AppData" / "LocalLow" / "Innersloth" / "Among Us"
ITCH_TOKEN_FILE = ITCH_TOKEN_DIR / "itch"

ITCHIO_API = "https://itch.io/api/1/key/me"
EOS_AUTH_URL = "https://accounts.innersloth.com/eos-auth"
BACKEND_API = "https://backend.innersloth.com/api"
BACKEND_HEADERS = {
    "Accept": "application/vnd.api+json",
    "Origin": "https://accounts.innersloth.com",
    "Referer": "https://accounts.innersloth.com/",
}
PLATFORM_LABELS = {
    'itchio': 'itch.io', 'itch': 'itch.io',
    'steam': 'Steam', 'epic': 'Epic Games', 'epicgames': 'Epic Games',
    'microsoft': 'Microsoft Store', 'winstore': 'Microsoft Store',
    'xbox': 'Xbox', 'xboxlive': 'Xbox',
}

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


class ItchProfileMixin:
    # ------------------------------------------------------------------ embedded OAuth login
    def start_itch_login(self):
        """Start the OAuth flow: launch HTTP server in a thread, open browser."""
        self._set_status("Opening itch.io login...", "info")

        def run_server():
            try:
                server = HTTPServer(("127.0.0.1", ITCH_OAUTH_PORT), _OAuthHandler)
                server.token = None
                server.timeout = 1
                deadline = time.time() + 300
                while server.token is None and time.time() < deadline:
                    server.handle_request()
                if server.token:
                    self._save_itch_token(server.token)
                    self._invoke_main(lambda: self._set_status("Login successful!", "success"))
                    self._invoke_main(lambda: self._load_itch_profile())
                else:
                    self._invoke_main(lambda: self._set_status("Login timed out", "warning"))
            except OSError as e:
                logging.error(f"OAuth server error: {e}")
                self._invoke_main(lambda: self._set_status(f"Login failed: {e}", "danger"))

        threading.Thread(target=run_server, daemon=True).start()
        webbrowser.open(
            f"https://itch.io/user/oauth?client_id={ITCH_CLIENT_ID}"
            f"&scope=profile:me&redirect_uri=http://127.0.0.1:{ITCH_OAUTH_PORT}"
            f"&response_type=token"
        )

    def _save_itch_token(self, token: str):
        """Save the itch.io access token to the file Among Us reads."""
        try:
            ITCH_TOKEN_DIR.mkdir(parents=True, exist_ok=True)
            ITCH_TOKEN_FILE.write_text(token)
            logging.info("Itch token saved successfully")
        except OSError as e:
            logging.error(f"Failed to save itch token: {e}")

    # ------------------------------------------------------------------ itch profile (read-only)
    def _read_itch_token(self):
        """Read the itch.io token from the saved file. Read-only."""
        try:
            if ITCH_TOKEN_FILE.exists():
                token = ITCH_TOKEN_FILE.read_text().strip()
                if token:
                    return token
        except (OSError, IOError) as e:
            logging.debug(f"Failed to read itch token: {e}")
        return None

    def _fetch_itch_profile(self):
        """Fetch itch.io account data using the saved token. All GET requests, no writes."""
        token = self._read_itch_token()
        if not token:
            return None

        profile = {"token": True, "username": None, "among_us_name": None, "platforms": []}

        try:
            r = _req.get(ITCHIO_API, headers={"Authorization": token}, timeout=8)
            if r.status_code == 200:
                u = r.json().get("user", {})
                profile["username"] = u.get("username")
        except (_req.RequestException, ValueError) as e:
            logging.debug(f"Failed to fetch itch.io username: {e}")

        try:
            r = _req.get(EOS_AUTH_URL, params={"store": "itchio", "token": token},
                         headers={"Accept": "application/json"}, timeout=8)
            if r.status_code == 200:
                eos = r.json()
                if eos.get("token") and eos.get("id_token"):
                    r2 = _req.get(f"{BACKEND_API}/user/query-primary-before-merge",
                                  params={"access_token": eos["token"]},
                                  headers={"Authorization": "Bearer " + eos["id_token"],
                                           **BACKEND_HEADERS}, timeout=8)
                    if r2.status_code == 200:
                        data = r2.json().get("data", {})
                        platforms = data.get("platforms") or []
                        profile["platforms"] = [
                            PLATFORM_LABELS.get(p.lower(), p) for p in platforms
                        ]
                    r3 = _req.get(f"{BACKEND_API}/user/username",
                                  headers={"Authorization": "Bearer " + eos["id_token"],
                                           **BACKEND_HEADERS}, timeout=8)
                    if r3.status_code == 200:
                        attrs = r3.json().get("data", {}).get("attributes", {})
                        name = attrs.get("username")
                        disc = attrs.get("discriminator")
                        if name:
                            profile["among_us_name"] = f"{name}#{disc}" if disc else name
        except (_req.RequestException, ValueError, KeyError) as e:
            logging.debug(f"Failed to fetch Among Us profile data: {e}")

        return profile

    def _load_itch_profile(self):
        """Fetch itch profile in background, update UI on main thread via signal."""
        def go():
            profile = self._fetch_itch_profile()
            self._invoke_main(lambda p=profile: self._update_profile_ui(p))
        self._run(go)

    def _load_itch_profile_sync(self):
        """Synchronous version for splash screen — runs network calls directly."""
        try:
            profile = self._fetch_itch_profile()
            self._update_profile_ui(profile)
        except Exception as e:
            logging.warning(f"Itch profile load failed: {e}")

    def _update_profile_ui(self, profile):
        """Update all profile-related UI elements."""
        if not profile:
            self.profile_game_text.setText("Not logged in")
            self.profile_game_text.setStyleSheet(f"color: {theme.TEXT_MUTED};")
            self.profile_game_detail.setText("Click Profile to authenticate")
            self.profile_game_detail.setStyleSheet(f"color: {theme.TEXT_MUTED};")
            self.profile_page_status.setText("Not logged in")
            self.profile_page_status.setStyleSheet(f"color: {theme.TEXT_MUTED};")
            self.profile_page_name.setText("")
            self.profile_page_au.setText("")
            self.profile_page_platforms.setText("")
            if hasattr(self, '_itch_login_btn'):
                self._itch_login_btn.show()
            return

        username = profile.get("username") or "Unknown"
        au_name = profile.get("among_us_name")
        platforms = profile.get("platforms") or []

        self.profile_game_text.setText(f"Logged in as {username}")
        self.profile_game_text.setStyleSheet(f"color: {theme.SUCCESS}; font-weight: 600;")
        detail_parts = []
        if au_name:
            detail_parts.append(f"Among Us: {au_name}")
        if platforms:
            detail_parts.append(f"Linked: {', '.join(platforms)}")
        self.profile_game_detail.setText(" — ".join(detail_parts) if detail_parts else "")
        self.profile_game_detail.setStyleSheet(f"color: {theme.TEXT_SECONDARY};")

        self.profile_page_status.setText("Logged in")
        self.profile_page_status.setStyleSheet(f"color: {theme.SUCCESS}; font-weight: 600;")
        self.profile_page_name.setText(username)
        if au_name:
            self.profile_page_au.setText(f"Among Us: {au_name}")
            self.profile_page_au.setStyleSheet(f"color: {theme.INFO};")
        else:
            self.profile_page_au.setText("No Among Us data yet")
            self.profile_page_au.setStyleSheet(f"color: {theme.TEXT_MUTED};")
        if platforms:
            self.profile_page_platforms.setText(f"Linked: {', '.join(platforms)}")
            self.profile_page_platforms.setStyleSheet(f"color: {theme.TEXT_SECONDARY};")
        else:
            self.profile_page_platforms.setText("No platforms linked")
            self.profile_page_platforms.setStyleSheet(f"color: {theme.TEXT_MUTED};")

        if hasattr(self, '_itch_login_btn'):
            self._itch_login_btn.hide()
