"""Native itch.io login for Isam AULauncher.

This is the Itch Login Fixer's logic embedded in the launcher: the same OAuth
client, the same local callback server on 127.0.0.1:7890, the same redirect
pages and the same token file (the fixer wrote to ``%USERPROFILE%`` under Wine,
which maps to ``itch_token_dir`` here). See ``src/fixer/Itch_Login_Fixer.py``.

The access token is returned in the URL *fragment* (``#access_token=...``), so
the redirect page uses a small script to forward it to ``/token?t=...`` which
the local server picks up. Works on Windows, Linux and macOS. The port must
stay 7890 because that is the redirect URI registered for the OAuth client.
"""
import logging
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from platform_utils import itch_token_dir

CLIENT_ID = "1ba9b4bfa1ac7759e8420eed4ec863ba"
PORT = 7890
ITCH_REDIRECT = f"http://127.0.0.1:{PORT}"
ITCH_SCOPE = "profile:me"
ITCH_TIMEOUT = 300.0

LOADING_PAGE = b"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>ShadowSlime | Authenticating</title>
    <style>
        body { background: #060608; color: #7b61ff; display: flex; flex-direction: column; justify-content: center; align-items: center; height: 100vh; font-family: 'Segoe UI', sans-serif; margin: 0; }
        .loader { border: 4px solid #1a1b1e; border-top: 4px solid #7b61ff; border-radius: 50%; width: 50px; height: 50px; animation: spin 1s linear infinite; margin-bottom: 20px; }
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

SUCCESS_PAGE = b"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>ShadowSlime | Success</title>
    <style>
        body { background: #060608; color: #4ade80; display: flex; flex-direction: column; justify-content: center; align-items: center; height: 100vh; font-family: 'Segoe UI', sans-serif; margin: 0; }
        .icon { font-size: 60px; margin-bottom: 10px; }
        .msg { font-size: 24px; font-weight: bold; }
        .sub { color: #888; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="icon">&#10004;</div>
    <div class="msg">AUTHORIZATION COMPLETE</div>
    <div class="sub">You can close this tab and return to the fixer.</div>
</body>
</html>"""


class OAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path.startswith("/token"):
            token = urllib.parse.parse_qs(parsed.query).get("t", [None])[0]
            self._reply(SUCCESS_PAGE)
            if token:
                self.server.capture_token(token)
            return
        self._reply(LOADING_PAGE)

    def _reply(self, body):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except OSError:
            pass

    def log_message(self, fmt, *args):
        pass


class ItchOAuthServer(HTTPServer):
    allow_reuse_address = True

    def __init__(self, addr, session):
        super().__init__(addr, OAuthHandler)
        self.session = session
        self.token = None
        self.captured = threading.Event()

    def capture_token(self, token):
        if not token or self.captured.is_set():
            return
        self.token = token
        self.captured.set()
        self.session.token.emit(token)
        threading.Thread(target=self.shutdown, daemon=True).start()


class ItchOAuthSession(QObject):
    """One itch.io login attempt. Start it, open ``auth_url()`` in the browser,
    then wait for the ``token`` signal. ``failed`` and ``timed_out`` report the
    corresponding outcomes."""

    token = Signal(str)
    failed = Signal(str)
    timed_out = Signal()

    def __init__(self, timeout=ITCH_TIMEOUT, parent=None):
        super().__init__(parent)
        self._timeout = timeout
        self._httpd = None

    def auth_url(self):
        # Same URL the Itch Login Fixer builds.
        return (f"https://itch.io/user/oauth?client_id={CLIENT_ID}"
                f"&scope={ITCH_SCOPE}&redirect_uri={ITCH_REDIRECT}"
                f"&response_type=token")

    def start(self):
        """Bind the callback server and begin listening.

        Raises ``OSError`` (indicating port 7890 is already in use) when the
        server cannot bind, so the caller can report it immediately.
        """
        if self._httpd is not None:
            return
        self._httpd = ItchOAuthServer(("127.0.0.1", PORT), self)
        threading.Thread(target=self._httpd.serve_forever, daemon=True).start()
        threading.Thread(target=self._watchdog, daemon=True).start()

    def stop(self):
        httpd = self._httpd
        self._httpd = None
        if httpd is None:
            return

        def _close():
            try:
                httpd.shutdown()
            finally:
                httpd.server_close()

        threading.Thread(target=_close, daemon=True).start()

    def _watchdog(self):
        httpd = self._httpd
        if httpd is None:
            return
        if httpd.captured.wait(self._timeout):
            return
        if self._httpd is not None and not self._httpd.captured.is_set():
            self.timed_out.emit()
            self.stop()


def save_itch_token(token, prefix=None) -> Path:
    """Write the itch.io token to the file Among Us reads.

    ``prefix`` pins the Wine prefix on Linux; it is ignored on Windows/macOS.
    The parent directory is created when missing.
    """
    target = itch_token_dir(prefix) / "itch"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(token, encoding="utf-8")
    logging.info("Itch token saved to %s", target)
    return target