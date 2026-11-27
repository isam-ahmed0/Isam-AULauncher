import os
import subprocess
import logging
from pathlib import Path
from packaging.version import Version, InvalidVersion

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMessageBox

from config import LAUNCHER_VERSION, LAUNCHER_UPDATE_URL, VERSION_URL, SOURCE_CODE_URL
from mod_catalog import version_newer
import news as news_feed


class UpdaterMixin:
    def _load_initial_data(self):
        def go():
            v = self.config.get_version()
            if v:
                self.current_version = v
            latest = self.network.fetch_text(VERSION_URL)
            if latest:
                self.latest_version = latest
            self._load_news()
            self._invoke_main(self._update_version_display)
            self._invoke_main(self._update_main_btn)
            if self.config.settings.get("discord_rpc"):
                self.discord.connect()
            self._check_launcher_update()
            self._check_game_update()
        self._run(go)

    def _load_initial_data_sync(self):
        """Synchronous version for splash screen — runs network calls directly."""
        try:
            v = self.config.get_version()
            if v:
                self.current_version = v
            latest = self.network.fetch_text(VERSION_URL)
            if latest:
                self.latest_version = latest
            # Fetch available releases for version picker
            try:
                self.available_versions, self._releases_error = self.network.get_releases()
            except Exception as e:
                self.available_versions = []
                self._releases_error = str(e)
            self._load_news()
            self._update_version_display()
            self._update_main_btn()
            if self.config.settings.get("discord_rpc"):
                self.discord.connect()
            self._check_launcher_update()
            self._check_game_update()
        except Exception as e:
            logging.warning(f"Initial data load failed: {e}")

    # ------------------------------------------------------------------ news
    def _load_news(self):
        """Fetch the remote message; fall back to the cached copy offline."""
        item = news_feed.fetch_news(self.network)
        if item is None:
            item = news_feed.get_cached_news(self.config)
        else:
            news_feed.cache_news(self.config, item)
        self._invoke_main(lambda: self._apply_news(item))

    def _apply_news(self, item):
        self.news_item = item
        browser = getattr(self, "news_browser", None)
        if browser is not None:
            if item and item.text:
                browser.setMarkdown(item.text)
            else:
                browser.clear()
        if news_feed.is_unseen(self.config.settings, item):
            self._news_notice_pending = item
            QTimer.singleShot(600, lambda: self._maybe_show_news_notice(60))

    def _maybe_show_news_notice(self, attempts=60):
        """Prompt once the main window is visible (splash/login may be up)."""
        if self._shutting_down or self._news_notice_pending is None:
            return
        if not self.window.isVisible():
            if attempts > 0:
                QTimer.singleShot(
                    500, lambda: self._maybe_show_news_notice(attempts - 1))
            return
        item = self._news_notice_pending
        self._news_notice_pending = None
        self._prompt_news(item)

    def _prompt_news(self, item):
        if self._shutting_down or item is None:
            return
        preview = news_feed.news_to_plain(news_feed.newest_post(item))
        if len(preview) > 600:
            preview = preview[:600].rstrip() + "..."
        box = QMessageBox(self.window)
        box.setWindowTitle("News")
        box.setIcon(QMessageBox.Icon.Information)
        box.setText(
            "A new message was posted on the News page.\n\n" + preview)
        open_btn = box.addButton("Open News", QMessageBox.ButtonRole.AcceptRole)
        box.addButton("Later", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        news_feed.mark_seen(self.config, item)
        if box.clickedButton() is open_btn:
            self._switch_page(7, "News")

    def _check_launcher_update(self):
        try:
            remote = self.network.fetch_text(LAUNCHER_UPDATE_URL)
            if not remote:
                return
            remote = remote.strip()
            if remote == self.config.settings.get("skipped_launcher_version"):
                return
            try:
                if Version(remote) <= Version(LAUNCHER_VERSION):
                    return
            except InvalidVersion:
                logging.warning(
                    "Skipping launcher update check: invalid version "
                    "(local=%r, remote=%r)",
                    LAUNCHER_VERSION, remote,
                )
                return

            self._invoke_main(lambda: self._prompt_launcher_update(remote))
        except Exception as e:
            logging.debug(f"Launcher update check failed: {e}")

    def _prompt_launcher_update(self, new_version):
        from platform_utils import IS_LINUX
        box = QMessageBox(self.window)
        box.setWindowTitle("Update Available")
        box.setIcon(QMessageBox.Icon.Information)
        if IS_LINUX:
            box.setText(
                f"A new launcher version (v{new_version}) is available.\n\n"
                f"Current: v{LAUNCHER_VERSION}\n\n"
                "Open the downloads page?"
            )
            action_btn = box.addButton("Open Downloads", QMessageBox.ButtonRole.AcceptRole)
        else:
            box.setText(
                f"A new launcher version (v{new_version}) is available.\n\n"
                f"Current: v{LAUNCHER_VERSION}\n"
                f"New: v{new_version}\n\n"
                "Download and install now?"
            )
            action_btn = box.addButton("Install Now", QMessageBox.ButtonRole.AcceptRole)
        skip_btn = box.addButton("Skip This Version", QMessageBox.ButtonRole.ActionRole)
        box.addButton("Later", QMessageBox.ButtonRole.RejectRole)
        box.exec()

        clicked = box.clickedButton()
        if clicked is skip_btn:
            self.config.settings["skipped_launcher_version"] = new_version
            self.config.save_settings()
            return
        if clicked is not action_btn:
            return

        if IS_LINUX:
            from PySide6.QtCore import QUrl
            from PySide6.QtGui import QDesktopServices
            QDesktopServices.openUrl(QUrl(f"{SOURCE_CODE_URL}/releases/latest"))
            return

        self._set_status("Downloading launcher update...", "info")
        self._invoke_main(self._busy_on)

        def go():
            import tempfile
            try:
                setup_url = (
                    "https://github.com/isam-ahmed0/Isam-AULauncher/"
                    f"releases/download/{new_version}/CrewLauncher-Setup.exe"
                )
                setup_path = Path(tempfile.gettempdir()) / "CrewLauncher-Setup.exe"
                ok = self.network.download_file(setup_url, setup_path)
                if not ok:
                    self._invoke_main(lambda: self._set_status("Download failed", "danger"))
                    self._invoke_main(self._busy_off)
                    return
                self._invoke_main(lambda: self._set_status("Launching installer...", "info"))
                subprocess.Popen([str(setup_path)])
                os._exit(0)
            except Exception as e:
                logging.error(f"Launcher update failed: {e}")
                self._invoke_main(lambda err=e: self._set_status(f"Update failed: {err}", "danger"))
                self._invoke_main(self._busy_off)

        self._run(go)

    # ------------------------------------------------------------- game updates
    def _check_game_update(self):
        """Prompt once when the installed game is behind the remote version."""
        remote = (self.latest_version or "").strip()
        if not remote or remote in ("Checking...", "Unknown"):
            return
        if self.current_version in ("Not Installed", "", None):
            return  # the main button already offers a fresh install
        if remote == self.config.settings.get("skipped_game_version"):
            return
        if not version_newer(remote, self.current_version):
            return
        self._invoke_main(lambda: self._set_game_update_pending(remote))

    def _set_game_update_pending(self, version):
        self._game_update_notice_pending = version
        QTimer.singleShot(800, lambda: self._maybe_show_game_update(60))

    def _maybe_show_game_update(self, attempts=60):
        if self._shutting_down or not getattr(self, "_game_update_notice_pending", None):
            return
        if not self.window.isVisible():
            if attempts > 0:
                QTimer.singleShot(500, lambda: self._maybe_show_game_update(attempts - 1))
            return
        version = self._game_update_notice_pending
        self._game_update_notice_pending = None
        self._prompt_game_update(version)

    def _prompt_game_update(self, version):
        box = QMessageBox(self.window)
        box.setWindowTitle("Game Update Available")
        box.setIcon(QMessageBox.Icon.Information)
        box.setText(
            f"A new game version (v{version}) is available.\n\n"
            f"Current: v{self.current_version}\n\n"
            "Download and install it now?"
        )
        update_btn = box.addButton("Update Now", QMessageBox.ButtonRole.AcceptRole)
        skip_btn = box.addButton("Skip This Version", QMessageBox.ButtonRole.ActionRole)
        box.addButton("Later", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        clicked = box.clickedButton()
        if clicked is skip_btn:
            self.config.settings["skipped_game_version"] = version
            self.config.save_settings()
        elif clicked is update_btn:
            self._download_latest()
