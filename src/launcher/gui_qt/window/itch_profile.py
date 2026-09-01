import os
import sys
import logging
import webbrowser
import subprocess
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton, QMessageBox,
)
from PySide6.QtCore import Qt

import gui_qt.theme as theme


ITCH_FIXER_NAME = "Itch_Login_Fixer.exe"

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


class ItchProfileMixin:
    # ------------------------------------------------------------------ itchfixer
    def _find_itch_fixer(self):
        """Find Itch_Login_Fixer.exe relative to the launcher."""
        if getattr(sys, 'frozen', False):
            base = Path(sys.executable).parent
            fixer = base / "Fixer" / ITCH_FIXER_NAME
            if fixer.exists():
                return fixer
            return base / ITCH_FIXER_NAME
        return Path(__file__).parent.parent.parent.parent / "release" / "Fixer" / ITCH_FIXER_NAME

    def _launch_itch_fixer(self):
        """Launch ItchFixer as a separate process."""
        exe = self._find_itch_fixer()
        if exe.exists():
            try:
                subprocess.Popen([str(exe)], cwd=str(exe.parent))
            except OSError as e:
                logging.error(f"Failed to launch ItchFixer: {e}")
        else:
            logging.warning(f"ItchFixer not found: {exe}")

    def _show_itch_auth_dialog(self):
        """Show 2-step itch.io authentication popup."""
        dialog = QDialog(self.window)
        dialog.setWindowTitle("itch.io Authentication")
        dialog.setFixedSize(480, 320)
        dialog.setModal(True)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("itch.io Login Required")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        layout.addSpacing(4)
        layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine))
        layout.addSpacing(8)

        step1_label = QLabel("Step 1")
        step1_label.setObjectName("profileName")
        layout.addWidget(step1_label)

        step1_desc = QLabel("Open itch.io and sign in or create an account.")
        step1_desc.setObjectName("profileDetail")
        step1_desc.setWordWrap(True)
        layout.addWidget(step1_desc)

        open_btn = QPushButton("Open itch.io")
        open_btn.setObjectName("modalPrimary")
        open_btn.setFixedHeight(36)
        open_btn.clicked.connect(lambda: webbrowser.open("https://itch.io/login"))
        layout.addWidget(open_btn)

        layout.addSpacing(12)

        step2_label = QLabel("Step 2")
        step2_label.setObjectName("profileName")
        layout.addWidget(step2_label)

        step2_desc = QLabel("After logging in, click Authenticate to open ItchFixer and complete the login.")
        step2_desc.setObjectName("profileDetail")
        step2_desc.setWordWrap(True)
        layout.addWidget(step2_desc)

        auth_btn = QPushButton("Authenticate")
        auth_btn.setObjectName("modalPrimary")
        auth_btn.setFixedHeight(36)
        layout.addWidget(auth_btn)

        def do_authenticate():
            dialog.accept()
            self._launch_itch_fixer()
            self.app.quit()

        auth_btn.clicked.connect(do_authenticate)

        dialog.exec()

    # ------------------------------------------------------------------ itch profile (read-only)
    def _read_itch_token(self):
        """Read the itch.io token from ItchFixer's saved file. Read-only."""
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
        import requests as _req

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
            if not self._itch_auth_shown:
                self._itch_auth_shown = True
                self._show_itch_auth_dialog()
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
