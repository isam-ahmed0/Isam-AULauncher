import os
import sys
import shutil
import logging
from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog, QMessageBox, QProgressBar,
)
from PySide6.QtCore import Qt

from config import DEFAULT_GAME_DIR, VERSION_URL
from file_manager import FileManager
import gui_qt.theme as theme
from gui_qt.zipextract import list_contents, extract_to

# Config-id prefix for entries this launcher creates in Lutris. Used to tell
# our own entries apart from unrelated user entries that point at the same exe.
LUTRIS_SLUG_PREFIX = "among-us-isam"


class GameActionsMixin:
    # ------------------------------------------------------------------ callbacks
    def _cb_main_action(self):
        txt = self.main_action_btn.text()
        if "INSTALL" in txt or "UPDATE" in txt:
            self._download_latest()
        elif "LAUNCH" in txt:
            self._launch_game()
        elif "PLAYING" in txt:
            self.game.stop()
            self._update_main_btn()

    def _cb_create_shortcut(self):
        self._create_shortcut()

    def _cb_open_folder(self):
        gp = self.config.get_game_path()
        if gp and gp.exists():
            from platform_utils import open_local_path
            open_local_path(gp)
        else:
            QMessageBox.warning(self.window, "Error", "Game not installed!")

    def _cb_change_location(self):
        self._change_location_pending = True
        folder = QFileDialog.getExistingDirectory(self.window, "Select Game Folder")
        if folder:
            self._folder_selected(folder)
        else:
            self._change_location_pending = False

    def _cb_locate_game(self):
        self._locate_pending = True
        folder = QFileDialog.getExistingDirectory(self.window, "Select Among Us Folder")
        if folder:
            self._folder_selected(folder)
        else:
            self._locate_pending = False

    def _cb_verify(self):
        self._verify_files()

    def _cb_reinstall(self):
        self._reinstall_game()

    def _cb_uninstall(self):
        self._uninstall_game()

    def _cb_add_to_lutris(self):
        self._add_to_lutris_action()

    def _cb_check_lutris(self):
        self._check_lutris_action()

    def _cb_fix_lutris(self):
        self._fix_lutris_action()

    def _open_version_picker(self):
        from gui_qt.version_picker import VersionPickerDialog
        releases = getattr(self, 'available_versions', [])
        error = getattr(self, '_releases_error', None)
        dlg = VersionPickerDialog(
            releases=releases,
            current_version=self.current_version,
            latest_version=self.latest_version,
            error_message=error,
            parent=self.window,
        )
        dlg.version_selected.connect(self._download_version)
        dlg.retry_requested.connect(self._retry_fetch_releases)
        dlg.exec()

    def _retry_fetch_releases(self, callback):
        """Re-fetch releases from GitHub and pass results to callback."""
        def go():
            try:
                versions, err = self.network.get_releases()
                self.available_versions = versions
                self._releases_error = err
                self._invoke_main(lambda: callback(versions, err))
            except Exception as e:
                self._invoke_main(lambda: callback([], str(e)))
        self._run(go)

    def _download_version(self, version_tag: str):
        """Download a specific version selected from the version picker."""
        self.latest_version = version_tag
        self._update_version_display()
        self._download_latest()

    # ------------------------------------------------------------------ folder selected
    def _folder_selected(self, folder):
        path = Path(folder)
        if self._install_folder_pending:
            self._install_folder_pending = False
            self._pending_install_path = path
            self._download_latest()
            return
        if self._change_location_pending:
            self._change_location_pending = False
            self._change_location(path)
            return
        if self._locate_pending:
            self._locate_pending = False
            result = FileManager.verify_game_folder(path)
            if not result["exe_found"]:
                self._set_status("Among Us.exe not found in this folder", "danger")
                QMessageBox.warning(self.window, "Error",
                                    "Among Us.exe not found.\nSelect a valid Among Us installation.")
                return
            self.config.set_game_path(path)
            ver = self.latest_version if self.latest_version != "Checking..." else "Unknown"
            self.config.set_version(ver)
            self.current_version = ver
            self._update_version_display()
            self._update_main_btn()
            self._set_status(f"Game located at {path}", "success")
            return

    # ------------------------------------------------------------------ actions
    def _download_latest(self):
        def go():
            try:
                self._invoke_main(self._busy_on)
                self._invoke_main(lambda: self._set_status("Preparing download...", "info"))
                if self.discord.connected:
                    self.discord.update_status("Updating Game", "Downloading...")
                latest = self.latest_version
                if latest == "Checking...":
                    latest = self.network.fetch_text(VERSION_URL)
                    if not latest:
                        self._invoke_main(lambda: self._set_status("Failed to fetch version info", "danger"))
                        return
                gp = self.config.get_game_path()
                if not gp:
                    gp = self._pending_install_path
                    if not gp:
                        self._install_folder_pending = True
                        self._invoke_main(lambda: self._set_status("Select a folder to install into", "info"))
                        def _pick_folder():
                            default = Path(DEFAULT_GAME_DIR)
                            default.mkdir(parents=True, exist_ok=True)
                            folder = QFileDialog.getExistingDirectory(
                                self.window, "Select Install Folder",
                                str(default),
                                QFileDialog.Option.ShowDirsOnly,
                            )
                            if folder:
                                self._folder_selected(Path(folder))
                            else:
                                self._invoke_main(self._busy_off)
                        self._invoke_main(_pick_folder)
                        return

                def on_progress(pct):
                    self._invoke_main(lambda p=pct: self._update_progress(p))

                def on_status(text, level):
                    self._invoke_main(lambda t=text, l=level: self._set_status(t, l))

                self.game.update_progress.connect(on_progress)
                self.game.status_message.connect(on_status)
                try:
                    ok = self.game.download_update(latest, gp)
                    if ok:
                        self._pending_install_path = None
                        self.current_version = latest
                        self._invoke_main(self._update_version_display)
                        self._invoke_main(lambda: self._update_progress(100))
                finally:
                    self.game.update_progress.disconnect(on_progress)
                    self.game.status_message.disconnect(on_status)
            except Exception as e:
                self._invoke_main(lambda: self._set_status(f"Error: {e}", "danger"))
            finally:
                self._invoke_main(self._busy_off)
                self._invoke_main(self._update_main_btn)
                if self.discord.connected:
                    self.discord.update_status("In Launcher", "Browsing Menu")
        self._run(go)

    def _launch_game(self):
        from mod_inspector import inspect_profile_dlls
        from ..mod_warnings import ModWarningDialog
        from PySide6.QtWidgets import QDialog

        profile_name = self.config.get_active_profile()
        profile_path = self.profile_mgr.profile_path(profile_name)
        _, issues = inspect_profile_dlls(profile_path)
        if issues:
            dlg = ModWarningDialog(issues, parent=self.window)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return
        from platform_utils import IS_LINUX
        ok = self._launch_linux_game() if IS_LINUX else self.game.launch()
        if ok:
            self._update_main_btn()

    # --------------------------------------------------------------- linux launch
    def _cache_lutris_entry(self, gp, entry):
        """Store the matched Lutris entry (or clear it) and refresh the UI."""
        if entry:
            self.config.set_lutris_entry(gp, entry)
            if entry.get("id") is not None:
                self.config.set_lutris_id(gp, entry.get("id"))
        else:
            self.config.clear_lutris_entry(gp)
        if hasattr(self, "_update_lutris_info"):
            self._update_lutris_info()

    def _resolve_lutris_entry(self, gp, lutris_cmd):
        """Match THIS install to one of the launcher's own Lutris entries.

        Only a previously cached id, or a launcher-created config (id prefix
        ``among-us-isam``) is used. A user's separate entry that happens to
        point at the same executable is never reused, so several Among Us
        installs each keep their own entry.
        """
        from platform_utils import (
            lutris_list_games, lutris_find_existing_install,
            lutris_entry_by_configpath,
        )
        games = lutris_list_games(lutris_cmd)
        by_id = {g.get("id"): g for g in games if g.get("id") is not None}

        cached_id = self.config.get_lutris_id(gp)
        if cached_id is not None and cached_id in by_id:
            entry = dict(by_id[cached_id])
            entry.setdefault("configpath", None)
            return entry

        configpath = lutris_find_existing_install(
            gp, gp / "Among Us.exe", prefix=LUTRIS_SLUG_PREFIX)
        if configpath:
            entry = lutris_entry_by_configpath(configpath)
            if entry and entry.get("id") is not None:
                return entry
        return None

    def _launch_linux_game(self):
        from platform_utils import find_lutris
        gp = self.config.get_game_path()
        method = self.config.settings.get("launch_method", "ask")

        try:
            lutris_cmd = find_lutris()
            entry = None
            if lutris_cmd:
                entry = self._resolve_lutris_entry(gp, lutris_cmd)
                self._cache_lutris_entry(gp, entry)

            if method == "wine":
                return self._launch_with_wine_warning()

            if method == "lutris":
                if not lutris_cmd:
                    return self._launch_with_wine_warning()
                if entry and entry.get("id") is not None:
                    return self.game.launch_lutris(entry.get("id"))
                return self._add_to_lutris(gp)

            # method == "ask": let the user pick the launcher / GPU each time.
            return self._prompt_launch_choice(gp, entry, lutris_cmd)
        except Exception as e:
            logging.exception("Linux launch flow failed")
            QMessageBox.warning(self.window, "Launch failed", str(e))
            return False

    def _prompt_launch_choice(self, gp, entry, lutris_cmd):
        """Popup letting the user launch via Lutris (GPU configurable) or Wine."""
        box = QMessageBox(self.window)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle("Launch Among Us")
        box.setText("How do you want to launch Among Us?")

        lutris_btn = add_btn = wine_btn = None
        if lutris_cmd:
            if entry and entry.get("id") is not None:
                lutris_btn = box.addButton(
                    "Launch with Lutris", QMessageBox.ButtonRole.AcceptRole)
            else:
                add_btn = box.addButton(
                    "Add to Lutris & Launch", QMessageBox.ButtonRole.AcceptRole)
            wine_btn = box.addButton(
                "Launch with Wine", QMessageBox.ButtonRole.ActionRole)
            box.setInformativeText(
                "Lutris is recommended — it lets you choose your GPU and other "
                "options (Lutris → Configure → System options).\n\n"
                "Wine runs the game directly with your global prefix and can "
                "use a different GPU.")
        else:
            wine_btn = box.addButton(
                "Launch with Wine", QMessageBox.ButtonRole.AcceptRole)
            box.setInformativeText(
                "Lutris was not found, so the game will run with Wine.\n\n"
                "If you have Lutris installed, use Tools > Fix Lutris.")
        box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(lutris_btn or add_btn or wine_btn)
        box.exec()

        clicked = box.clickedButton()
        if lutris_btn is not None and clicked is lutris_btn:
            return self.game.launch_lutris(entry.get("id"))
        if add_btn is not None and clicked is add_btn:
            return self._add_to_lutris(gp)
        if wine_btn is not None and clicked is wine_btn:
            return self._launch_with_wine_warning()
        return False

    def _launch_with_wine_warning(self):
        from platform_utils import find_wine
        if not find_wine():
            QMessageBox.warning(
                self.window, "Wine not found",
                "Wine is not installed.\nInstall Wine or add the game to "
                "Lutris, then try again.")
            return False
        if self.config.settings.get("warn_plain_wine", True):
            box = QMessageBox(self.window)
            box.setIcon(QMessageBox.Icon.Warning)
            box.setWindowTitle("Launch with Wine")
            box.setText("Running Among Us directly with Wine is not recommended.")
            box.setInformativeText(
                "Wine may cause crashes or broken mods, and may use a different "
                "GPU than you expect. Lutris is recommended — it lets you choose "
                "your GPU in its settings.\n\nLaunch anyway?")
            box.setStandardButtons(
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            box.setDefaultButton(QMessageBox.StandardButton.No)
            if box.exec() != QMessageBox.StandardButton.Yes:
                return False
        gp = self.config.get_game_path()
        return self.game.launch_wine(gp, gp / "Among Us.exe")

    def _add_to_lutris_action(self):
        """Tools action: add an already-installed game to Lutris (Linux)."""
        from platform_utils import IS_LINUX
        if not IS_LINUX:
            return
        gp = self.config.get_game_path()
        if not gp or not (gp / "Among Us.exe").exists():
            QMessageBox.warning(self.window, "Error", "Game not installed!")
            return
        from platform_utils import find_lutris, format_lutris_entry
        lutris_cmd = find_lutris(refresh=True)
        if not lutris_cmd:
            QMessageBox.warning(
                self.window, "Lutris not found",
                "Lutris was not found on this system.\n\n"
                "Click \"Fix Lutris\" in Tools to locate it (or set it "
                "manually).\nLog: "
                f"{self.config.appdata_dir / 'logs' / 'launcher.log'}")
            return

        entry = self._resolve_lutris_entry(gp, lutris_cmd)
        self._cache_lutris_entry(gp, entry)
        if entry:
            box = QMessageBox(self.window)
            box.setIcon(QMessageBox.Icon.Information)
            box.setWindowTitle("Already in Lutris")
            box.setText("This install is already in your Lutris library:")
            box.setInformativeText(format_lutris_entry(entry))
            launch_btn = box.addButton("Launch", QMessageBox.ButtonRole.AcceptRole)
            box.addButton("Close", QMessageBox.ButtonRole.RejectRole)
            box.exec()
            if box.clickedButton() is launch_btn and entry.get("id") is not None:
                self.game.launch_lutris(entry.get("id"))
                self._update_main_btn()
            return

        self._add_to_lutris(gp)

    def _check_lutris_action(self):
        """Tools action: verify whether this install has a Lutris entry (Linux)."""
        from platform_utils import IS_LINUX
        if not IS_LINUX:
            return
        gp = self.config.get_game_path()
        if not gp:
            QMessageBox.warning(self.window, "Error", "Game not installed!")
            return
        from platform_utils import find_lutris, format_lutris_entry
        lutris_cmd = find_lutris(refresh=True)
        if not lutris_cmd:
            QMessageBox.warning(
                self.window, "Lutris not found",
                "Lutris was not found on this system.\n\n"
                "Click \"Fix Lutris\" in Tools to locate it.")
            return

        entry = self._resolve_lutris_entry(gp, lutris_cmd)
        self._cache_lutris_entry(gp, entry)
        if entry:
            box = QMessageBox(self.window)
            box.setIcon(QMessageBox.Icon.Information)
            box.setWindowTitle("Lutris Status")
            box.setText("This install is in your Lutris library.")
            box.setInformativeText(format_lutris_entry(entry))
            launch_btn = box.addButton("Launch", QMessageBox.ButtonRole.AcceptRole)
            box.addButton("Close", QMessageBox.ButtonRole.RejectRole)
            box.exec()
            if box.clickedButton() is launch_btn and entry.get("id") is not None:
                self.game.launch_lutris(entry.get("id"))
                self._update_main_btn()
        else:
            box = QMessageBox(self.window)
            box.setIcon(QMessageBox.Icon.Warning)
            box.setWindowTitle("Lutris Status")
            box.setText("This install is not in your Lutris library.")
            box.setInformativeText("Add it to Lutris for better compatibility.")
            add_btn = box.addButton("Add to Lutris", QMessageBox.ButtonRole.AcceptRole)
            box.addButton("Close", QMessageBox.ButtonRole.RejectRole)
            box.exec()
            if box.clickedButton() is add_btn:
                self._add_to_lutris(gp)

    def _fix_lutris_action(self):
        """Tools action: force-detect / set the Lutris command (Linux)."""
        from platform_utils import (
            IS_LINUX, find_lutris, lutris_self_test, set_lutris_override,
            clear_lutris_override,
        )
        if not IS_LINUX:
            return

        # Fresh scan so a stale failed result from earlier is discarded.
        cmd = find_lutris(refresh=True)
        ok, detail = lutris_self_test(cmd) if cmd else (False, "Lutris not found")
        logging.info("Fix Lutris: cmd=%s ok=%s detail=%s", cmd, ok, detail)

        if cmd and ok:
            set_lutris_override(cmd)
            self.config.set_lutris_cmd_override(cmd)
            if hasattr(self, "_update_lutris_info"):
                self._update_lutris_info()
            QMessageBox.information(
                self.window, "Lutris fixed",
                "Lutris was found and enabled:\n\n"
                f"{' '.join(cmd)}\n\n"
                "Add to Lutris and launching through Lutris now work.")
            return

        box = QMessageBox(self.window)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle("Fix Lutris")
        if cmd:
            box.setText("Lutris was found but its self-test failed.")
            box.setInformativeText(
                f"Command: {' '.join(cmd)}\nResult: {detail}\n\n"
                "You can use it anyway, or pick the correct executable.")
        else:
            box.setText("Lutris was not found automatically.")
            box.setInformativeText(
                "Pick your Lutris executable. Usually one of:\n"
                "/usr/bin/lutris (native), /snap/bin/lutris (Snap), or\n"
                "/usr/bin/flatpak (Flatpak).")
        use_btn = box.addButton(
            "Use anyway", QMessageBox.ButtonRole.AcceptRole) if cmd else None
        browse_btn = box.addButton("Browse\u2026", QMessageBox.ButtonRole.ActionRole)
        retry_btn = box.addButton("Retry", QMessageBox.ButtonRole.ActionRole)
        auto_btn = box.addButton("Auto-detect", QMessageBox.ButtonRole.DestructiveRole)
        box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        clicked = box.clickedButton()

        if use_btn is not None and clicked is use_btn:
            set_lutris_override(cmd)
            self.config.set_lutris_cmd_override(cmd)
            self._set_status("Lutris forced on.", "success")
        elif clicked is browse_btn:
            self._browse_for_lutris()
        elif clicked is retry_btn:
            clear_lutris_override()
            self.config.clear_lutris_cmd_override()
            self._fix_lutris_action()
        elif clicked is auto_btn:
            clear_lutris_override()
            self.config.clear_lutris_cmd_override()
            self._set_status("Lutris auto-detection restored.", "info")

    def _browse_for_lutris(self):
        """Let the user pick the Lutris executable, then force it."""
        from platform_utils import set_lutris_override
        start = "/usr/bin" if Path("/usr/bin").is_dir() else str(Path.home())
        path, _ = QFileDialog.getOpenFileName(
            self.window, "Select the Lutris executable", start, "Executables (*)")
        if not path:
            return
        cmd = [path]
        set_lutris_override(cmd)
        self.config.set_lutris_cmd_override(cmd)
        if hasattr(self, "_update_lutris_info"):
            self._update_lutris_info()
        QMessageBox.information(
            self.window, "Lutris set", f"Lutris command forced to:\n\n{path}")

    def _add_to_lutris(self, gp):
        """Add an existing install to the Lutris library (no installer/download).

        Uses Lutris's own API so the new entry matches Lutris exactly. Writes
        exactly one ``games`` row and one ``games/<id>.yml``; never touches
        Lutris settings or other entries.
        """
        from platform_utils import (
            find_lutris, lutris_is_running, lutris_list_games,
            lutris_unique_name_slug, lutris_paths,
        )
        lutris_cmd = find_lutris()
        if not lutris_cmd:
            return self._launch_with_wine_warning()

        exe = gp / "Among Us.exe"
        prefix = self.config.get_wine_prefix()

        entry = self._resolve_lutris_entry(gp, lutris_cmd)
        if entry:
            self._cache_lutris_entry(gp, entry)
            if entry.get("id") is not None:
                return self.game.launch_lutris(entry.get("id"))
            return False

        if lutris_is_running():
            box = QMessageBox(self.window)
            box.setIcon(QMessageBox.Icon.Warning)
            box.setWindowTitle("Close Lutris first")
            box.setText("Lutris is currently running.")
            box.setInformativeText(
                "So your library is not overwritten, close Lutris completely, "
                "then click Retry.\n\n"
                "(Lutris rewrites its library on exit and could otherwise "
                "discard the new entry.)")
            retry_btn = box.addButton("Retry", QMessageBox.ButtonRole.AcceptRole)
            box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
            box.exec()
            if box.clickedButton() is not retry_btn:
                return False
            return self._add_to_lutris(gp)

        paths = lutris_paths()
        box = QMessageBox(self.window)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle("Add to Lutris")
        box.setText("Add this install to your Lutris library?")
        box.setInformativeText(
            "No download or installer is run. This adds one entry:\n"
            f"\u2022 one row in {paths['db_path']}\n"
            f"\u2022 one config in {paths['games_dir']}\n\n"
            "Your Lutris settings and other games are left untouched.")
        add_btn = box.addButton("Add", QMessageBox.ButtonRole.AcceptRole)
        box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() is not add_btn:
            return False

        ver = self.config.get_version() or ""
        suffix = f" {ver}" if ver and ver not in ("Unknown", "Not Installed") else ""
        base_name = f"Among Us (Isam AU){suffix}"
        existing = [g.get("name", "") for g in lutris_list_games(lutris_cmd)]
        name, slug = lutris_unique_name_slug(
            base_name, LUTRIS_SLUG_PREFIX, existing)

        self._set_status("Adding to Lutris library\u2026", "info")
        self._run(lambda: self._register_in_lutris(name, slug, exe, gp, prefix))
        return False

    def _register_in_lutris(self, name, slug, exe, gp, prefix):
        """Worker: register via Lutris's API, then launch on success."""
        from platform_utils import lutris_api_register
        entry = lutris_api_register(name, slug, exe, gp, prefix)
        if not entry:
            self._invoke_main(lambda: self._lutris_register_failed())
            return
        self._invoke_main(lambda e=entry: self._cache_lutris_entry(gp, e))
        self._invoke_main(lambda: self._set_status(
            f"Added \u201c{name}\u201d to Lutris.", "success"))
        gid = entry.get("id")
        if gid is not None:
            self._invoke_main(lambda i=gid: self.game.launch_lutris(i))

    def _lutris_register_failed(self):
        box = QMessageBox(self.window)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle("Could not add to Lutris")
        box.setText("The game could not be added to your Lutris library.")
        box.setInformativeText(
            "Lutris's own modules could not be used (this can happen with a "
            "Flatpak or Snap Lutris).\n\n"
            "You can add it manually in Lutris with "
            "\u201cAdd locally installed game\u201d.")
        box.addButton("OK", QMessageBox.ButtonRole.RejectRole)
        box.exec()

    def _create_shortcut(self):
        from platform_utils import IS_LINUX
        gp = self.config.get_game_path()
        if not gp:
            QMessageBox.warning(self.window, "Error", "Game not installed!")
            return
        if IS_LINUX:
            self._create_linux_shortcut(gp)
            return
        try:
            import win32com.client
        except ImportError:
            QMessageBox.warning(self.window, "Error", "pywin32 not installed")
            return
        exe = gp / "Among Us.exe"
        ver = self.config.get_version() or "Unknown"
        try:
            sc = Path.home() / "Desktop" / f"Among Us {ver}.lnk"
            sh = win32com.client.Dispatch("WScript.Shell")
            lnk = sh.CreateShortCut(str(sc))
            lnk.Targetpath = str(exe)
            lnk.WorkingDirectory = str(gp)
            lnk.IconLocation = str(exe)
            lnk.save()
            QMessageBox.information(self.window, "Info", "Shortcut created on Desktop!")
        except Exception as e:
            QMessageBox.warning(self.window, "Error", f"Failed: {e}")

    def _create_linux_shortcut(self, gp):
        from platform_utils import create_desktop_shortcut, find_lutris
        exe = gp / "Among Us.exe"
        lutris_id = None
        if find_lutris():
            entry = self._resolve_lutris_entry(gp, find_lutris())
            if entry and entry.get("id") is not None:
                self._cache_lutris_entry(gp, entry)
                lutris_id = entry.get("id")
            else:
                self._cache_lutris_entry(gp, None)
        icon = None
        for cand in ("icon.png", "logo.png", "icon.ico"):
            if (gp / cand).exists():
                icon = gp / cand
                break
        try:
            path = create_desktop_shortcut(
                "Among Us (Isam AU)", exe, gp,
                prefix=self.config.get_wine_prefix(),
                lutris_id=lutris_id, icon_source=icon)
            QMessageBox.information(
                self.window, "Info", f"Desktop shortcut created:\n{path}")
        except Exception as e:
            QMessageBox.warning(self.window, "Error", f"Failed: {e}")

    def _change_location(self, new_path):
        self._set_status("Verifying game files...", "info")
        result = FileManager.verify_game_folder(new_path)
        if not result["exe_found"]:
            self.config.set_game_path(new_path)
            self.config.set_version("Not Installed")
            self.current_version = "Not Installed"
            self._update_version_display()
            self._update_main_btn()
            self._set_status(f"Location set to {new_path}", "success")
            QMessageBox.information(self.window, "Info",
                                    f"Location: {new_path}\nClick INSTALL GAME to download.")
            return
        if result["missing"]:
            self._set_status("Some files missing", "warning")
            msg = (f"Some game files are missing:\n{', '.join(result['missing'])}\n\n"
                   f"Found {result['file_count']} files "
                   f"({FileManager.format_size(result['total_size'])}).\nContinue anyway?")
            if QMessageBox.question(
                self.window, "Confirm", msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            ) != QMessageBox.StandardButton.Yes:
                self._set_status("Ready")
                return
        self._set_status(
            f"Verified — {result['file_count']} files, "
            f"{FileManager.format_size(result['total_size'])}",
            "success",
        )
        old = self.config.get_game_path()
        if old and old.exists() and old != new_path:
            if QMessageBox.question(
                self.window, "Confirm", "Move existing game files to new location?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            ) == QMessageBox.StandardButton.Yes:
                self._set_status("Moving files...", "info")
                try:
                    shutil.move(str(old), str(new_path))
                    self._set_status("Files moved!", "success")
                except (PermissionError, OSError) as e:
                    self._set_status("Move failed", "danger")
                    QMessageBox.warning(self.window, "Error",
                                        f"Failed to move files: {e}")
                    return
        self.config.set_game_path(new_path)
        self._set_status("Location changed!", "success")
        QMessageBox.information(self.window, "Info", f"Location: {new_path}")

    def _verify_files(self):
        gp = self.config.get_game_path()
        if not gp:
            QMessageBox.warning(self.window, "Error", "Game not installed!")
            return
        self._set_status("Verifying...", "info")
        result = FileManager.verify_game_folder(gp)
        if result["valid"]:
            QMessageBox.information(
                self.window, "Info",
                f"All files verified.\n{result['file_count']} files, "
                f"{FileManager.format_size(result['total_size'])}",
            )
        elif result["exe_found"]:
            QMessageBox.warning(
                self.window, "Warning",
                f"Some files missing:\n{', '.join(result['missing'])}",
            )
        else:
            QMessageBox.warning(self.window, "Error", "Among Us.exe not found!")
        self._set_status("Ready")

    def _reinstall_game(self):
        reply = QMessageBox.question(
            self.window, "Confirm", "Delete and reinstall the game?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            gp = self.config.get_game_path()
            if gp:
                self._pending_install_path = gp
            if gp and gp.exists():
                FileManager.safe_delete(gp)
            self.current_version = "Not Installed"
            self._update_version_display()
            self._download_latest()

    def _uninstall_game(self):
        reply = QMessageBox.question(
            self.window, "Confirm",
            "Remove all game files and launcher data?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            gp = self.config.get_game_path()
            if gp and gp.exists():
                if FileManager.safe_delete(gp):
                    QMessageBox.information(self.window, "Info", "Game files removed")
                else:
                    QMessageBox.warning(self.window, "Error",
                                        "Failed to remove game files")
            reply2 = QMessageBox.question(
                self.window, "Confirm",
                "Also remove launcher settings and data?\nThe launcher will restart.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply2 == QMessageBox.StandardButton.Yes:
                import shutil as _shutil
                try:
                    _shutil.rmtree(str(self.config.appdata_dir), ignore_errors=True)
                except Exception:
                    pass
                os._exit(0)
            self.current_version = "Not Installed"
            self._update_version_display()
            self._update_main_btn()

    # ------------------------------------------------------------------ zip extractor
    def _cb_select_zip(self):
        path, _ = QFileDialog.getOpenFileName(
            self.window, "Select Zip File", "", "Zip Files (*.zip);;All Files (*)"
        )
        if not path:
            return
        self._selected_zip = Path(path)
        self._zip_path_label.setText(str(self._selected_zip))
        self._zip_path_label.setObjectName("statusText")
        self._zip_path_label.style().polish(self._zip_path_label)
        contents = list_contents(self._selected_zip)
        if contents:
            preview = contents[:15]
            more = f"\n... and {len(contents) - 15} more" if len(contents) > 15 else ""
            self._zip_contents_label.setText("Contents:\n" + "\n".join(preview) + more)
        else:
            self._zip_contents_label.setText("Could not read zip contents")

    def _cb_extract_zip(self):
        if not hasattr(self, "_selected_zip") or not self._selected_zip:
            QMessageBox.warning(self.window, "Error", "Select a zip file first!")
            return
        gp = self.config.get_game_path()
        if not gp:
            QMessageBox.warning(self.window, "Error", "Game not installed! Set a game location first.")
            return
        self._zip_progress.show()
        self._zip_progress.setValue(0)
        self._set_status("Extracting zip...", "info")

        def go():
            def prog(done, total):
                pct = int(done / total * 100) if total else 0
                self._invoke_main(lambda p=pct: self._zip_progress.setValue(p))
            ok = extract_to(self._selected_zip, gp, prog)
            self._invoke_main(lambda: self._zip_progress.hide())
            if ok:
                self._invoke_main(lambda: self._set_status("Zip extracted!", "success"))
                self._invoke_main(lambda: QMessageBox.information(
                    self.window, "Success", "Files extracted to game folder!"))
            else:
                self._invoke_main(lambda: self._set_status("Extraction failed", "danger"))
                self._invoke_main(lambda: QMessageBox.warning(
                    self.window, "Error", "Failed to extract zip file."))
        self._run(go)
