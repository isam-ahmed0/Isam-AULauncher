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
from gui_qt.theme import (
    SUCCESS, INFO, DANGER, WARNING,
    TEXT_PRIMARY, TEXT_MUTED,
)
from gui_qt.zipextract import list_contents, extract_to


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
            os.startfile(str(gp))
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
        from .mod_warnings import ModWarningDialog
        from PySide6.QtWidgets import QDialog

        profile_name = self.config.get_active_profile()
        profile_path = self.profile_mgr.profile_path(profile_name)
        _, issues = inspect_profile_dlls(profile_path)
        if issues:
            dlg = ModWarningDialog(issues, parent=self.window)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return
        ok = self.game.launch()
        if ok:
            self._update_main_btn()

    def _create_shortcut(self):
        gp = self.config.get_game_path()
        if not gp:
            QMessageBox.warning(self.window, "Error", "Game not installed!")
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
        self._zip_path_label.setStyleSheet(f"color: {TEXT_PRIMARY};")
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
