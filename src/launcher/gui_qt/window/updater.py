import os
import subprocess
import logging
from pathlib import Path

from PySide6.QtWidgets import QMessageBox

from config import LAUNCHER_VERSION, LAUNCHER_UPDATE_URL, VERSION_URL


class UpdaterMixin:
    def _load_initial_data(self):
        def go():
            v = self.config.get_version()
            if v:
                self.current_version = v
            latest = self.network.fetch_text(VERSION_URL)
            if latest:
                self.latest_version = latest
            self._invoke_main(self._update_version_display)
            self._invoke_main(self._update_main_btn)
            if self.config.settings.get("discord_rpc"):
                self.discord.connect()
            self._check_launcher_update()
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
            self._update_version_display()
            self._update_main_btn()
            if self.config.settings.get("discord_rpc"):
                self.discord.connect()
        except Exception as e:
            logging.warning(f"Initial data load failed: {e}")

    def _check_launcher_update(self):
        try:
            remote = self.network.fetch_text(LAUNCHER_UPDATE_URL)
            if not remote:
                return
            remote = remote.strip()
            if remote == LAUNCHER_VERSION:
                return
            self._invoke_main(lambda: self._prompt_launcher_update(remote))
        except Exception as e:
            logging.debug(f"Launcher update check failed: {e}")

    def _prompt_launcher_update(self, new_version):
        reply = QMessageBox.information(
            self.window, "Update Available",
            f"A new version (v{new_version}) is available.\n\n"
            f"Current: v{LAUNCHER_VERSION}\n"
            f"New: v{new_version}\n\n"
            f"Download and install now?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._set_status("Downloading launcher update...", "info")
            self._invoke_main(self._busy_on)
            def go():
                import tempfile
                try:
                    setup_url = f"https://github.com/isam-ahmed0/Isam-AULauncher/releases/download/{new_version}/IsamAU-Setup.exe"
                    setup_path = Path(tempfile.gettempdir()) / "IsamAU-Setup.exe"
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
                    self._invoke_main(lambda: self._set_status(f"Update failed: {e}", "danger"))
                    self._invoke_main(self._busy_off)
            self._run(go)
