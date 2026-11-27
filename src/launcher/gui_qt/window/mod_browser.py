"""Callbacks for the Mod Browser page (Qt mixin)."""

import logging

from PySide6.QtWidgets import QMessageBox

from mod_inspector import inspect_profile_dlls


class ModBrowserMixin:
    """Wires ``ModBrowserPage`` signals to the shared catalog backend."""

    # ------------------------------------------------------------------ loading
    def _load_mod_catalog(self, force: bool = False):
        page = getattr(self, "mod_browser", None)
        if page is not None:
            page.set_status("Fetching catalog...", "info")

        def go():
            try:
                self.catalog_mgr.fetch(force=force)
            except Exception as exc:
                logging.exception("Mod catalog load failed")
                self.catalog_mgr.error = str(exc)
            self._invoke_main(lambda: self._refresh_mod_browser())
        self._run(go)

    def _refresh_mod_browser(self, catalog=None):
        page = getattr(self, "mod_browser", None)
        if page is None:
            return
        catalog = catalog if catalog is not None else self.catalog_mgr.catalog
        profile = self.config.get_active_profile()
        states = self.catalog_mgr.status(profile, catalog)
        page.set_catalog(catalog, states, profile)

        if self.catalog_mgr.error:
            page.set_status(self.catalog_mgr.error,
                            "warning" if self.catalog_mgr.offline else "danger")
        else:
            count = len(catalog.mods) if catalog else 0
            page.set_status(f"{count} mod(s) available", "info")
        if hasattr(self, "_cb_refresh_mods"):
            self._cb_refresh_mods()

    # ------------------------------------------------------------------ actions
    def _cb_browse_mods(self):
        self._switch_page(8, "Mod Browser")
        self._load_mod_catalog()

    def _cb_install_mod(self, entry):
        profile = self.config.get_active_profile()
        if not profile:
            QMessageBox.warning(self.window, "Error", "Select or create a profile first.")
            return
        if self.game.is_running:
            QMessageBox.warning(self.window, "Error", "Close Among Us before installing mods.")
            return

        page = self.mod_browser
        page.set_busy(True)
        page.set_status(f"Installing {entry.name}...", "info")

        def go():
            def progress(downloaded, total, speed):
                pct = (downloaded / total * 100) if total else 0
                self._invoke_main(lambda: page.set_progress(pct))

            ok, message = self.catalog_mgr.install(
                entry, profile,
                progress_callback=progress,
                is_running=lambda: self.game.is_running,
            )

            def done():
                page.set_busy(False)
                page.set_status(message, "success" if ok else "danger")
                if ok:
                    self._show_mod_warnings(profile)
                self._refresh_mod_browser()

            self._invoke_main(done)

        self._run(go)

    def _cb_remove_mod(self, entry):
        profile = self.config.get_active_profile()
        if not profile:
            QMessageBox.warning(self.window, "Error", "No active profile.")
            return
        if self.game.is_running:
            QMessageBox.warning(self.window, "Error", "Close Among Us before removing mods.")
            return
        reply = QMessageBox.question(
            self.window, "Confirm", f"Remove '{entry.name}' from profile '{profile}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        ok, message = self.catalog_mgr.uninstall(entry.id, profile)
        self.mod_browser.set_status(message, "success" if ok else "danger")
        self._refresh_mod_browser()

    def _show_mod_warnings(self, profile_name):
        """Surface dependency/duplicate issues after changing a profile."""
        try:
            from gui_qt.mod_warnings import ModWarningDialog
            _, issues = inspect_profile_dlls(self.profile_mgr.profile_path(profile_name))
            if issues:
                ModWarningDialog(issues, self.window).exec()
        except Exception:
            logging.exception("Could not check mod warnings")
