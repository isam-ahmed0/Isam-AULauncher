import logging
import webbrowser
from pathlib import Path

import requests as _req

from platform_utils import IS_WINDOWS, itch_token_dir
from itch_auth import ItchOAuthSession


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


class ItchProfileMixin:
    # ------------------------------------------------------------------ token location
    def _itch_token_file(self) -> Path:
        """Path to the itch token file Among Us reads (Wine prefix on Linux)."""
        prefix = None
        if not IS_WINDOWS and getattr(self, "config", None):
            prefix = self.config.get_wine_prefix()
        return itch_token_dir(prefix) / "itch"

    # ------------------------------------------------------------------ sign-in (native)
    def open_itch_fixer(self):
        """Native itch.io login — Wine required on Linux (forceable).

        Starts the local OAuth callback server, opens itch.io in the browser,
        and on success saves the token to the same prefix the game uses.
        """
        if getattr(self, "_itch_auth_session", None) is not None:
            return

        from gui_qt.dialogs import wine_login_gate
        if not wine_login_gate(getattr(self, "window", None)):
            self._set_status("Wine is required to sign in — see the documentation.", "warning")
            return

        session = ItchOAuthSession()
        session.token.connect(self._on_itch_token)
        session.failed.connect(self._on_itch_auth_failed)
        session.timed_out.connect(self._on_itch_auth_timed_out)
        try:
            session.start()
        except OSError:
            self._set_status(
                "itch.io login could not start: port 7890 is in use. "
                "Close the Itch Login Fixer or any other app using it, then try again.",
                "warning",
            )
            return
        self._itch_auth_session = session
        webbrowser.open(session.auth_url())
        self._set_status("Check your browser to authorize your itch.io account.", "info")

    def _on_itch_token(self, token: str):
        try:
            self._save_itch_token(token)
        except OSError as e:
            self._set_status(f"itch.io login succeeded but the token could not be saved: {e}", "danger")
            self._itch_auth_session = None
            return
        self._itch_auth_session = None
        self._set_status("itch.io login successful!", "success")
        self._load_itch_profile()

    def _on_itch_auth_failed(self, message: str):
        self._set_status(message, "warning")
        self._itch_auth_session = None

    def _on_itch_auth_timed_out(self):
        self._set_status("itch.io login timed out. Try again.", "warning")
        self._itch_auth_session = None

    def _save_itch_token(self, token: str):
        """Save the itch.io access token to the file Among Us reads."""
        try:
            tf = self._itch_token_file()
            tf.parent.mkdir(parents=True, exist_ok=True)
            tf.write_text(token)
            logging.info("Itch token saved successfully")
        except OSError as e:
            logging.error(f"Failed to save itch token: {e}")

    # ------------------------------------------------------------------ itch profile (read-only)
    def _read_itch_token(self):
        """Read the itch.io token from the saved file. Read-only."""
        try:
            tf = self._itch_token_file()
            if tf.exists():
                token = tf.read_text().strip()
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
            self.profile_game_text.setObjectName("mutedText")
            self.profile_game_text.style().polish(self.profile_game_text)
            self.profile_game_detail.setText("Click Profile to authenticate")
            self.profile_game_detail.setObjectName("mutedText")
            self.profile_game_detail.style().polish(self.profile_game_detail)
            self.profile_page_status.setText("Not logged in")
            self.profile_page_status.setObjectName("mutedText")
            self.profile_page_status.style().polish(self.profile_page_status)
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
        self.profile_game_text.setObjectName("successText")
        self.profile_game_text.style().polish(self.profile_game_text)
        detail_parts = []
        if au_name:
            detail_parts.append(f"Among Us: {au_name}")
        if platforms:
            detail_parts.append(f"Linked: {', '.join(platforms)}")
        self.profile_game_detail.setText(" — ".join(detail_parts) if detail_parts else "")
        self.profile_game_detail.setObjectName("statusText")
        self.profile_game_detail.style().polish(self.profile_game_detail)

        self.profile_page_status.setText("Logged in")
        self.profile_page_status.setObjectName("successText")
        self.profile_page_status.style().polish(self.profile_page_status)
        self.profile_page_name.setText(username)
        if au_name:
            self.profile_page_au.setText(f"Among Us: {au_name}")
            self.profile_page_au.setObjectName("infoText")
        else:
            self.profile_page_au.setText("No Among Us data yet")
            self.profile_page_au.setObjectName("mutedText")
        self.profile_page_au.style().polish(self.profile_page_au)
        if platforms:
            self.profile_page_platforms.setText(f"Linked: {', '.join(platforms)}")
            self.profile_page_platforms.setObjectName("statusText")
        else:
            self.profile_page_platforms.setText("No platforms linked")
            self.profile_page_platforms.setObjectName("mutedText")
        self.profile_page_platforms.style().polish(self.profile_page_platforms)

        if hasattr(self, '_itch_login_btn'):
            self._itch_login_btn.hide()
