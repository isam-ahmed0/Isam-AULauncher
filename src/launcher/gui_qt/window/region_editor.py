from PySide6.QtWidgets import (
    QMessageBox, QInputDialog, QListWidgetItem,
)
from PySide6.QtCore import Qt

import gui_qt.theme as theme


class RegionEditorMixin:
    def _load_region_list(self):
        self.region_mgr.load()
        self._region_list.clear()
        for i, r in enumerate(self.region_mgr.regions):
            label = r["Name"]
            if i == self.region_mgr.active_index:
                label = f"  ●  {label}  (active)"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, i)
            self._region_list.addItem(item)
        if self.region_mgr.active_index < self._region_list.count():
            self._region_list.setCurrentRow(self.region_mgr.active_index)

    def _cb_add_region(self):
        name, ok = QInputDialog.getText(self.window, "Add Region", "Region name:")
        if not ok or not name.strip():
            return
        ip, ok = QInputDialog.getText(self.window, "Add Region", "Server URL (e.g. https://play.skeld.net):")
        if not ok or not ip.strip():
            return
        port, ok = QInputDialog.getInt(self.window, "Add Region", "Port:", 443, 1, 65535)
        if not ok:
            return
        ping, ok = QInputDialog.getText(
            self.window, "Add Region",
            "Ping Server (IP/hostname, e.g. 159.223.173.35)\nLeave empty to use server URL:",
        )
        if not ok:
            return
        ping = ping.strip() or ip.strip()
        if self.region_mgr.add(name.strip(), ping, ip.strip(), port):
            self.region_mgr.save()
            self._load_region_list()
            self._region_status.setText(f"Added region: {name.strip()}")
            self._region_status.setStyleSheet(f"color: {theme.SUCCESS};")
        else:
            self._region_status.setText(f"Region '{name.strip()}' already exists")
            self._region_status.setStyleSheet(f"color: {theme.WARNING};")

    def _cb_remove_region(self):
        item = self._region_list.currentItem()
        if not item:
            return
        idx = item.data(Qt.ItemDataRole.UserRole)
        name = self.region_mgr.regions[idx]["Name"]
        reply = QMessageBox.question(
            self.window, "Remove Region",
            f"Remove '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.region_mgr.remove(idx)
            self.region_mgr.save()
            self._load_region_list()
            self._region_status.setText(f"Removed: {name}")
            self._region_status.setStyleSheet(f"color: {theme.INFO};")

    def _cb_apply_region(self):
        item = self._region_list.currentItem()
        if not item:
            return
        idx = item.data(Qt.ItemDataRole.UserRole)
        self.region_mgr.active_index = idx
        if self.region_mgr.save():
            name = self.region_mgr.regions[idx]["Name"]
            self._region_status.setText(f"Active region set to: {name}")
            self._region_status.setStyleSheet(f"color: {theme.SUCCESS};")
            self._load_region_list()
        else:
            self._region_status.setText("Failed to save region settings")
            self._region_status.setStyleSheet(f"color: {theme.DANGER};")

    def _cb_reset_regions(self):
        reply = QMessageBox.question(
            self.window, "Reset Regions",
            "Reset to official Innersloth servers? Custom regions will be removed.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.region_mgr.reset_official()
            self.region_mgr.save()
            self._load_region_list()
            self._region_status.setText("Reset to official regions")
            self._region_status.setStyleSheet(f"color: {theme.INFO};")
