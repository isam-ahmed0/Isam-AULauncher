"""Qt-free itch.io OAuth flow.

The same OAuth client, local callback server on 127.0.0.1:7890, redirect pages
and token file used by the rest of the launcher. This module imports no GUI
toolkit so both the Qt and Tk front-ends can share it.

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

import requests as _req

from platform_utils import itch_token_dir

CLIENT_ID = "1ba9b4bfa1ac7759e8420eed4ec863ba"
PORT = 7890
ITCH_REDIRECT = f"http://127.0.0.1:{PORT}"
ITCH_SCOPE = "profile:me"
ITCH_TIMEOUT = 300.0

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
        self.session._emit_token(token)
        threading.Thread(target=self.shutdown, daemon=True).start()


class ItchOAuthFlow:
    """One itch.io login attempt (toolkit-free).

    Start it, open ``auth_url()`` in the browser, then wait for the
    ``on_token`` callback. ``on_failed`` and ``on_timed_out`` report the
    corresponding outcomes (all callbacks are optional).
    """

    def __init__(self, timeout=ITCH_TIMEOUT):
        self._timeout = timeout
        self._httpd = None
        self.on_token = None      # Callable[[str], None]
        self.on_failed = None     # Callable[[str], None]
        self.on_timed_out = None  # Callable[[], None]

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

    def _emit_token(self, token):
        if self.on_token:
            self.on_token(token)

    def _watchdog(self):
        httpd = self._httpd
        if httpd is None:
            return
        if httpd.captured.wait(self._timeout):
            return
        if self._httpd is not None and not self._httpd.captured.is_set():
            if self.on_timed_out:
                self.on_timed_out()
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


def itch_token_file(prefix=None) -> Path:
    """Path to the itch.io token file Among Us reads."""
    return itch_token_dir(prefix) / "itch"


def read_itch_token(prefix=None):
    """Read the saved itch.io token, or None if missing/empty. Read-only."""
    try:
        token_file = itch_token_file(prefix)
        if token_file.exists():
            token = token_file.read_text().strip()
            if token:
                return token
    except (OSError, IOError) as e:
        logging.debug("Failed to read itch token: %s", e)
    return None


def _fetch_itch_username(token: str, timeout: float):
    """One itch.io ``key/me`` call returning the account username or None."""
    try:
        r = _req.get(ITCHIO_API, headers={"Authorization": token}, timeout=timeout)
        if r.status_code == 200:
            return r.json().get("user", {}).get("username")
    except (_req.RequestException, ValueError) as e:
        logging.debug("Failed to fetch itch.io username: %s", e)
    return None


def fetch_itch_username(prefix=None, timeout=8.0):
    """Fetch just the itch.io account username for the saved token.

    Single bounded call — safe for quick header updates. Returns None when no
    token exists or the lookup fails.
    """
    token = read_itch_token(prefix)
    if not token:
        return None
    return _fetch_itch_username(token, timeout)


def fetch_itch_profile(prefix=None, timeout=8.0, username=None) -> dict:
    """Fetch itch.io account info for the saved token. All GET requests.

    Returns ``{"token": bool, "username": str|None, "among_us_name": str|None,
    "platforms": [str]}``. Runs no network calls when no token is present.
    ``username`` may be passed in to avoid a duplicate ``key/me`` call.
    """
    token = read_itch_token(prefix)
    profile = {"token": bool(token), "username": username, "among_us_name": None, "platforms": []}
    if not token:
        return profile

    if profile["username"] is None:
        profile["username"] = _fetch_itch_username(token, timeout)

    try:
        r = _req.get(EOS_AUTH_URL, params={"store": "itchio", "token": token},
                     headers={"Accept": "application/json"}, timeout=timeout)
        if r.status_code == 200:
            eos = r.json()
            if eos.get("token") and eos.get("id_token"):
                bearer = {"Authorization": "Bearer " + eos["id_token"], **BACKEND_HEADERS}
                r2 = _req.get(f"{BACKEND_API}/user/query-primary-before-merge",
                              params={"access_token": eos["token"]}, headers=bearer,
                              timeout=timeout)
                if r2.status_code == 200:
                    data = r2.json().get("data", {})
                    platforms = data.get("platforms") or []
                    profile["platforms"] = [
                        PLATFORM_LABELS.get(p.lower(), p) for p in platforms
                    ]
                r3 = _req.get(f"{BACKEND_API}/user/username", headers=bearer, timeout=timeout)
                if r3.status_code == 200:
                    attrs = r3.json().get("data", {}).get("attributes", {})
                    name = attrs.get("username")
                    disc = attrs.get("discriminator")
                    if name:
                        profile["among_us_name"] = f"{name}#{disc}" if disc else name
    except (_req.RequestException, ValueError, KeyError) as e:
        logging.debug("Failed to fetch Among Us profile data: %s", e)

    return profile
