import sys
import logging
from pathlib import Path

from PySide6.QtWidgets import (
    QMessageBox, QInputDialog, QListWidgetItem, QFileDialog,
)
from PySide6.QtCore import Qt

from file_manager import FileManager
from gui_qt.theme import SUCCESS, INFO, WARNING, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED
from gui_qt.mod_details import ModInfoDialog


class ModManagerMixin:
    # ------------------------------------------------------------------ bep
    def _find_bepmods_zip(self):
        if getattr(sys, 'frozen', False):
            base = Path(sys.executable).parent
            zp = base / "_internal" / "bepmods.zip"
            if zp.exists():
                return zp
        else:
            zp = Path(__file__).parent.parent.parent.parent / "release" / "bepmods.zip"
            if zp.exists():
                return zp
        return None

    def _update_bep_status(self):
        gp = self.config.get_game_path()
        if not gp:
            self._bep_status.setText("Game not installed — set a game location first")
            self._bep_status.setStyleSheet(f"color: {TEXT_MUTED};")
            return False
        core_dll = gp / "BepInEx" / "core" / "BepInEx.dll"
        if core_dll.exists():
            self._bep_status.setText("BepInEx: Installed")
            self._bep_status.setStyleSheet(f"color: {SUCCESS};")
            return True
        self._bep_status.setText("BepInEx: Not installed")
        self._bep_status.setStyleSheet(f"color: {WARNING};")
        return False

    def _cb_setup_bepinex(self):
        gp = self.config.get_game_path()
        if not gp:
            QMessageBox.warning(self.window, "Error", "Game not installed! Set a game location first.")
            return
        zp = self._find_bepmods_zip()
        if not zp:
            QMessageBox.warning(self.window, "Error", "bepmods.zip not found in launcher files.")
            return
        if (gp / "BepInEx" / "core" / "BepInEx.dll").exists():
            reply = QMessageBox.question(
                self.window, "Confirm",
                "BepInEx is already installed. Reinstall?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        def go():
            self._invoke_main(lambda: self._set_status("Installing BepInEx...", "info"))
            self._invoke_main(self._busy_on)
            ok = FileManager.extract_zip(zp, gp)
            if ok:
                self._invoke_main(lambda: self._set_status("BepInEx installed!", "success"))
                self._invoke_main(lambda: QMessageBox.information(
                    self.window, "Success", "BepInEx installed successfully!"))
                self._invoke_main(self._run_first_time_migration)
            else:
                self._invoke_main(lambda: self._set_status("BepInEx installation failed", "danger"))
                self._invoke_main(lambda: QMessageBox.warning(
                    self.window, "Error", "Failed to extract BepInEx files."))
            self._invoke_main(self._update_bep_status)
            self._invoke_main(self._busy_off)
        self._run(go)

    # ------------------------------------------------------------------ profiles
    def _refresh_profile_list(self):
        """Reload profile combo box and update active profile label."""
        self._profile_combo.blockSignals(True)
        self._profile_combo.clear()
        profiles = self.profile_mgr.list_profiles()
        self._profile_combo.addItems(profiles)
        active = self.config.get_active_profile()
        idx = self._profile_combo.findText(active)
        if idx >= 0:
            self._profile_combo.setCurrentIndex(idx)
        self._profile_combo.blockSignals(False)
        self._update_profile_label()
        self._cb_refresh_mods()

    def _update_profile_label(self):
        active = self.config.get_active_profile()
        self._profile_active_label.setText(f"Active profile: {active}")
        self._profile_active_label.setStyleSheet(f"color: {INFO}; font-weight: 600;")

    def _on_profile_selected(self, name):
        """When user selects a different profile in the combo (not the active one)."""
        if not name:
            return
        active = self.config.get_active_profile()
        if name != active:
            self._profile_active_label.setText(f"Selected: {name}  (click Switch to activate)")
            self._profile_active_label.setStyleSheet(f"color: {TEXT_SECONDARY};")
        else:
            self._update_profile_label()
        self._cb_refresh_mods()

    def _cb_create_profile(self):
        name, ok = QInputDialog.getText(self.window, "Create Profile", "Profile name:")
        if not ok or not name.strip():
            return
        name = name.strip()
        if not self.profile_mgr.create_profile(name):
            QMessageBox.warning(self.window, "Error", f"Could not create profile '{name}'.\nIt may already exist.")
            return
        self._refresh_profile_list()
        self.config.set_active_profile(name)
        gp = self.config.get_game_path()
        if gp:
            self.profile_mgr.switch_to(name, gp)
        self._refresh_profile_list()

    def _cb_rename_profile(self):
        name = self._profile_combo.currentText()
        if not name:
            return
        new_name, ok = QInputDialog.getText(self.window, "Rename Profile", "New name:", text=name)
        if not ok or not new_name.strip() or new_name.strip() == name:
            return
        new_name = new_name.strip()
        if not self.profile_mgr.rename_profile(name, new_name):
            QMessageBox.warning(self.window, "Error", f"Could not rename to '{new_name}'.\nName may already exist.")
            return
        active = self.config.get_active_profile()
        if active == name:
            self.config.set_active_profile(new_name)
            gp = self.config.get_game_path()
            if gp:
                self.profile_mgr.switch_to(new_name, gp)
        self._refresh_profile_list()

    def _cb_delete_profile(self):
        name = self._profile_combo.currentText()
        if not name:
            return
        active = self.config.get_active_profile()
        if name == active:
            QMessageBox.warning(self.window, "Error", "Cannot delete the active profile.\nSwitch to another profile first.")
            return
        reply = QMessageBox.question(
            self.window, "Confirm",
            f"Delete profile '{name}' and all its mods?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        if self.profile_mgr.delete_profile(name, active):
            self._refresh_profile_list()

    def _cb_switch_profile(self):
        name = self._profile_combo.currentText()
        if not name:
            return
        gp = self.config.get_game_path()
        if not gp:
            QMessageBox.warning(self.window, "Error", "Game not installed!")
            return
        if not (gp / "BepInEx" / "core" / "BepInEx.dll").exists():
            QMessageBox.warning(self.window, "Error", "BepInEx is not installed!\nSet it up first.")
            return
        if self.game.is_running:
            QMessageBox.warning(self.window, "Error", "Close Among Us before switching profiles!")
            return
        if not self.profile_mgr.switch_to(name, gp):
            QMessageBox.warning(self.window, "Error", f"Failed to switch to profile '{name}'.")
            return
        self.config.set_active_profile(name)
        self._refresh_profile_list()
        self._set_status(f"Switched to profile: {name}", "success")

    def _run_first_time_migration(self):
        """If no profiles exist yet, create defaults from existing plugins."""
        gp = self.config.get_game_path()
        if not gp:
            return
        profiles = self.profile_mgr.list_profiles()
        if profiles:
            return
        active = self.profile_mgr.ensure_first_profiles(gp)
        if active:
            self.config.set_active_profile(active)
            self._refresh_profile_list()

    # ------------------------------------------------------------------ mods in profile
    def _cb_refresh_mods(self):
        self._mods_list.clear()
        name = self._profile_combo.currentText()
        if not name:
            self._mods_status.setText("No profile selected")
            self._mods_status.setStyleSheet(f"color: {TEXT_MUTED};")
            return
        profile_dir = self.profile_mgr.profile_path(name)
        if not profile_dir.exists():
            self._mods_status.setText("Profile folder not found")
            self._mods_status.setStyleSheet(f"color: {TEXT_MUTED};")
            return
        dlls = sorted(profile_dir.glob("*.dll"), key=lambda f: f.name.lower())
        if not dlls:
            self._mods_status.setText("No mods in this profile")
            self._mods_status.setStyleSheet(f"color: {TEXT_MUTED};")
            return
        for dll in dlls:
            size = FileManager.format_size(dll.stat().st_size)
            item = QListWidgetItem(f"{dll.name}  ({size})")
            item.setData(Qt.ItemDataRole.UserRole, str(dll))
            self._mods_list.addItem(item)
        self._mods_status.setText(f"{len(dlls)} mod(s) in '{name}'")
        self._mods_status.setStyleSheet(f"color: {INFO};")

    def _cb_move_mods(self):
        selected = self._mods_list.selectedItems()
        if not selected:
            QMessageBox.information(self.window, "Info", "Select mod(s) to move first.")
            return
        current_profile = self._profile_combo.currentText()
        profiles = self.profile_mgr.list_profiles()
        others = [p for p in profiles if p != current_profile]
        if not others:
            QMessageBox.information(self.window, "Info", "No other profiles to move to.")
            return
        item, ok = QInputDialog.getItem(
            self.window, "Move Mods", "Move to profile:", others, 0, False,
        )
        if not ok:
            return
        names = [item.text().split("  ")[0] for item in selected]
        reply = QMessageBox.question(
            self.window, "Confirm",
            f"Move {len(names)} mod(s) to '{item}'?\n" + "\n".join(names),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        moved = self.profile_mgr.move_mods(current_profile, item, names)
        self._mods_status.setText(f"Moved {moved} mod(s) to '{item}'")
        self._mods_status.setStyleSheet(f"color: {SUCCESS};")
        self._cb_refresh_mods()

    def _cb_remove_mods(self):
        selected = self._mods_list.selectedItems()
        if not selected:
            QMessageBox.information(self.window, "Info", "Select mod(s) to remove first.")
            return
        names = [item.text().split("  ")[0] for item in selected]
        reply = QMessageBox.question(
            self.window, "Confirm",
            f"Remove {len(names)} mod(s)?\n" + "\n".join(names),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        removed = 0
        for item in selected:
            dll_path = Path(item.data(Qt.ItemDataRole.UserRole))
            try:
                dll_path.unlink()
                removed += 1
            except OSError as e:
                logging.error(f"Failed to remove mod {dll_path}: {e}")
        self._mods_status.setText(f"Removed {removed} mod(s)")
        self._mods_status.setStyleSheet(f"color: {SUCCESS};")
        self._cb_refresh_mods()

    def _cb_mod_info(self):
        selected = self._mods_list.selectedItems()
        if not selected:
            QMessageBox.information(self.window, "Info", "Select a mod from the list first.")
            return
        item = selected[0]
        dll_path = Path(item.data(Qt.ItemDataRole.UserRole))
        name = self._profile_combo.currentText()
        profile_dir = self.profile_mgr.profile_path(name) if name else Path()
        dlg = ModInfoDialog(dll_path, profile_dir, parent=self.window)
        dlg.exec()

    def _cb_add_mods(self):
        name = self._profile_combo.currentText()
        if not name:
            QMessageBox.warning(self.window, "Error", "Select or create a profile first.")
            return
        gp = self.config.get_game_path()
        if not gp:
            QMessageBox.warning(self.window, "Error", "Game not installed! Set a game location first.")
            return
        if not (gp / "BepInEx" / "core" / "BepInEx.dll").exists():
            QMessageBox.warning(self.window, "Error",
                                "BepInEx is not installed!\nSet it up on the Mods page first.")
            return
        files, _ = QFileDialog.getOpenFileNames(
            self.window, "Select Mod Files", "", "DLL Files (*.dll);;All Files (*)"
        )
        if not files:
            return
        copied = self.profile_mgr.import_mods(name, [Path(f) for f in files])
        self._mods_status.setText(f"Added {copied} mod(s) to '{name}'")
        self._mods_status.setStyleSheet(f"color: {SUCCESS};")
        self._cb_refresh_mods()
