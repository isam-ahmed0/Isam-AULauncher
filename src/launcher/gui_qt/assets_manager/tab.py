"""Main Assets Manager tab — combines all sub-components."""
import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QPushButton,
    QLabel, QFrame, QComboBox, QSplitter, QStatusBar,
)

from .profile_manager import AUASProfileManager
from .asset_discovery import discover_all
from .log_viewer import LogViewer
from .config_panel import ConfigPanel
from .pack_browser import PackBrowser
from .preview import AssetPreview
from .pack_io import export_pack, import_pack

import gui_qt.theme as theme

log = logging.getLogger(__name__)

TAB_LABELS = ["Pack Browser", "Asset Browser", "Log Viewer", "Config", "Profiles"]


class AssetsManagerTab(QWidget):
    def __init__(self, profile_mgr: AUASProfileManager, game_path_getter, parent=None):
        super().__init__(parent)
        self._profile_mgr = profile_mgr
        self._game_path_getter = game_path_getter
        self._build_ui()
        self._refresh_profiles()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 20, 28, 20)
        layout.setSpacing(12)

        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        title = QLabel("ASSETS MANAGER")
        title.setObjectName("sectionTitle")
        header_row.addWidget(title)
        header_row.addStretch()

        self._profile_combo = QComboBox()
        self._profile_combo.setFixedHeight(32)
        self._profile_combo.setMinimumWidth(160)
        self._profile_combo.currentTextChanged.connect(self._on_profile_changed)
        header_row.addWidget(self._profile_combo)

        create_btn = QPushButton("New")
        create_btn.setObjectName("toolBtn")
        create_btn.setFixedHeight(32)
        create_btn.clicked.connect(self._cb_create_profile)
        header_row.addWidget(create_btn)

        delete_btn = QPushButton("Delete")
        delete_btn.setObjectName("dangerBtn")
        delete_btn.setFixedHeight(32)
        delete_btn.clicked.connect(self._cb_delete_profile)
        header_row.addWidget(delete_btn)

        rename_btn = QPushButton("Rename")
        rename_btn.setObjectName("toolBtn")
        rename_btn.setFixedHeight(32)
        rename_btn.clicked.connect(self._cb_rename_profile)
        header_row.addWidget(rename_btn)

        activate_btn = QPushButton("Activate")
        activate_btn.setObjectName("successBtn")
        activate_btn.setFixedHeight(32)
        activate_btn.clicked.connect(self._cb_activate_profile)
        header_row.addWidget(activate_btn)

        layout.addLayout(header_row)

        layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine))

        tab_row = QHBoxLayout()
        tab_row.setSpacing(4)
        self._tab_btns = {}
        for i, label in enumerate(TAB_LABELS):
            btn = QPushButton(label)
            btn.setObjectName("toolBtn")
            btn.setCheckable(True)
            btn.setFixedHeight(32)
            btn.clicked.connect(lambda checked, idx=i: self._switch_tab(idx))
            tab_row.addWidget(btn)
            self._tab_btns[label] = btn
        tab_row.addStretch()
        layout.addLayout(tab_row)

        self._pages = QStackedWidget()

        self._pack_browser = PackBrowser(self._profile_mgr, self._game_path_getter)
        self._pack_browser.file_selected.connect(self._on_file_selected)
        self._pages.addWidget(self._pack_browser)

        asset_page = self._build_asset_browser()
        self._pages.addWidget(asset_page)

        self._log_viewer = LogViewer(self._game_path_getter)
        self._pages.addWidget(self._log_viewer)

        self._config_panel = ConfigPanel(self._game_path_getter)
        self._pages.addWidget(self._config_panel)

        profiles_page = self._build_profiles_page()
        self._pages.addWidget(profiles_page)

        layout.addWidget(self._pages, 1)

        self._status_bar = QLabel("Profile: None | Replacements: 0")
        self._status_bar.setObjectName("statusText")
        layout.addWidget(self._status_bar)

        self._tab_btns["Pack Browser"].setChecked(True)

    def _build_asset_browser(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._asset_list_label = QLabel("DISCOVERED ASSETS")
        self._asset_list_label.setObjectName("sectionTitle")
        layout.addWidget(self._asset_list_label)

        from PySide6.QtWidgets import QTextEdit
        self._asset_display = QTextEdit()
        self._asset_display.setReadOnly(True)
        self._asset_display.setFont(QFont("Consolas, monospace", 9))
        layout.addWidget(self._asset_display)

        btn_row = QHBoxLayout()
        scan_btn = QPushButton("Scan Assets")
        scan_btn.setObjectName("primaryBtn")
        scan_btn.setFixedHeight(32)
        scan_btn.clicked.connect(self._cb_scan_assets)
        btn_row.addWidget(scan_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        return page

    def _build_profiles_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        layout.addWidget(QLabel("PACK PROFILES"))
        layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine))

        self._profiles_display = QLabel("Select a profile above to manage it.")
        self._profiles_display.setObjectName("bodyText")
        self._profiles_display.setWordWrap(True)
        layout.addWidget(self._profiles_display)

        btn_row = QHBoxLayout()
        import_btn = QPushButton("Import .aupack")
        import_btn.setObjectName("toolBtn")
        import_btn.setFixedHeight(32)
        import_btn.clicked.connect(self._cb_import_pack)
        btn_row.addWidget(import_btn)

        export_btn = QPushButton("Export .aupack")
        export_btn.setObjectName("toolBtn")
        export_btn.setFixedHeight(32)
        export_btn.clicked.connect(self._cb_export_pack)
        btn_row.addWidget(export_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        layout.addStretch()
        return page

    def _switch_tab(self, idx: int):
        self._pages.setCurrentIndex(idx)
        for i, (label, btn) in enumerate(self._tab_btns.items()):
            btn.setChecked(i == idx)
        if idx == 2:
            self._log_viewer.start()
        elif idx == 3:
            self._config_panel.refresh()
        elif idx == 4:
            self._refresh_profiles_display()

    def _refresh_profiles(self):
        self._profile_combo.blockSignals(True)
        self._profile_combo.clear()
        for name in self._profile_mgr.list_profiles():
            self._profile_combo.addItem(name)
        self._profile_combo.blockSignals(False)
        if self._profile_combo.count() > 0:
            self._profile_combo.setCurrentIndex(0)
            self._on_profile_changed(self._profile_combo.currentText())

    def _on_profile_changed(self, name: str):
        self._pack_browser.set_profile(name)
        self._update_status()

    def _on_file_selected(self, path: Path):
        if hasattr(self, '_preview'):
            self._preview.preview_file(path)

    def _cb_create_profile(self):
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "New Profile", "Profile name:")
        if ok and name:
            if self._profile_mgr.create_profile(name):
                self._refresh_profiles()
                idx = self._profile_combo.findText(name)
                if idx >= 0:
                    self._profile_combo.setCurrentIndex(idx)

    def _cb_delete_profile(self):
        name = self._profile_combo.currentText()
        if not name:
            return
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "Delete Profile",
            f'Delete profile "{name}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._profile_mgr.delete_profile(name)
            self._refresh_profiles()

    def _cb_rename_profile(self):
        old = self._profile_combo.currentText()
        if not old:
            return
        from PySide6.QtWidgets import QInputDialog
        new, ok = QInputDialog.getText(self, "Rename Profile", "New name:", text=old)
        if ok and new and new != old:
            if self._profile_mgr.rename_profile(old, new):
                self._refresh_profiles()

    def _cb_activate_profile(self):
        name = self._profile_combo.currentText()
        gp = self._game_path_getter()
        if not name or not gp:
            return
        if self._profile_mgr.activate_profile(name, gp):
            self._status_bar.setText(f"Profile '{name}' activated")
            self._status_bar.setObjectName("successText")
        else:
            self._status_bar.setText(f"Failed to activate '{name}'")
            self._status_bar.setObjectName("dangerText")
        self._status_bar.style().polish(self._status_bar)

    def _cb_scan_assets(self):
        gp = self._game_path_getter()
        if not gp:
            self._asset_display.setText("No game path set. Install or locate the game first.")
            return
        self._asset_display.setText("Scanning...")
        entries = discover_all(gp)
        if not entries:
            self._asset_display.setText("No assets discovered. Ensure BepInEx is installed.")
            return
        lines = [f"Found {len(entries)} asset(s):\n"]
        by_type = {}
        for e in entries:
            by_type.setdefault(e.asset_type, []).append(e)
        for asset_type, items in sorted(by_type.items()):
            lines.append(f"── {asset_type} ({len(items)}) ──")
            for item in items[:50]:
                extra = ""
                if item.width and item.height:
                    extra = f" [{item.width}x{item.height}]"
                dll = f" ({item.dll_source})" if item.dll_source else ""
                lines.append(f"  {item.name}{extra}{dll}")
            if len(items) > 50:
                lines.append(f"  ... and {len(items) - 50} more")
            lines.append("")
        self._asset_display.setText("\n".join(lines))

    def _cb_import_pack(self):
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Pack", "", "AU Asset Pack (*.aupack);;All (*)",
        )
        if path:
            name = import_pack(self._profile_mgr, Path(path), parent=self)
            if name:
                self._refresh_profiles()
                idx = self._profile_combo.findText(name)
                if idx >= 0:
                    self._profile_combo.setCurrentIndex(idx)

    def _cb_export_pack(self):
        name = self._profile_combo.currentText()
        if name:
            export_pack(self._profile_mgr, name, parent=self)

    def _refresh_profiles_display(self):
        profiles = self._profile_mgr.list_pack_profiles()
        if not profiles:
            self._profiles_display.setText("No packs created yet.")
            return
        lines = []
        for p in profiles:
            cats = ", ".join(p.categories) if p.categories else "Empty"
            lines.append(f"  {p.name}: {p.asset_count} assets [{cats}]")
        self._profiles_display.setText("Profiles:\n" + "\n".join(lines))

    def _update_status(self):
        name = self._profile_combo.currentText()
        count = self._profile_mgr.get_profile_count(name) if name else 0
        gp = self._game_path_getter()
        game_str = str(gp) if gp else "Not set"
        self._status_bar.setText(f"Profile: {name or 'None'} | Replacements: {count} | Game: {game_str}")

    def refresh(self):
        self._refresh_profiles()
        self._update_status()
        self._config_panel.refresh()

    def start_log(self):
        self._log_viewer.start()

    def stop_log(self):
        self._log_viewer.stop()
