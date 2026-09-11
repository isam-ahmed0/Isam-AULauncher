"""Assets Manager tab — profile switching + read-only asset list + pack I/O."""
import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame,
    QComboBox, QTextEdit, QFileDialog, QInputDialog, QMessageBox,
)

from .profile_manager import AUASProfileManager, ASSET_SUBFOLDERS
from .pack_io import export_pack, import_pack

import gui_qt.theme as theme

log = logging.getLogger(__name__)


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

        # Header: ASSETS MANAGER label
        title = QLabel("ASSETS MANAGER")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine))

        # Profile bar
        prof_row = QHBoxLayout()
        prof_row.setSpacing(8)

        prof_label = QLabel("Profile:")
        prof_label.setObjectName("bodyText")
        prof_row.addWidget(prof_label)

        self._profile_combo = QComboBox()
        self._profile_combo.setFixedHeight(32)
        self._profile_combo.setMinimumWidth(160)
        self._profile_combo.currentTextChanged.connect(self._on_profile_changed)
        prof_row.addWidget(self._profile_combo)

        create_btn = QPushButton("New")
        create_btn.setObjectName("toolBtn")
        create_btn.setFixedHeight(32)
        create_btn.clicked.connect(self._cb_create_profile)
        prof_row.addWidget(create_btn)

        rename_btn = QPushButton("Rename")
        rename_btn.setObjectName("toolBtn")
        rename_btn.setFixedHeight(32)
        rename_btn.clicked.connect(self._cb_rename_profile)
        prof_row.addWidget(rename_btn)

        delete_btn = QPushButton("Delete")
        delete_btn.setObjectName("dangerBtn")
        delete_btn.setFixedHeight(32)
        delete_btn.clicked.connect(self._cb_delete_profile)
        prof_row.addWidget(delete_btn)

        activate_btn = QPushButton("Activate")
        activate_btn.setObjectName("successBtn")
        activate_btn.setFixedHeight(32)
        activate_btn.clicked.connect(self._cb_activate_profile)
        prof_row.addWidget(activate_btn)

        prof_row.addStretch()
        layout.addLayout(prof_row)

        layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine))

        # Read-only asset list
        self._asset_list = QTextEdit()
        self._asset_list.setReadOnly(True)
        self._asset_list.setFont(QFont("Consolas, monospace", 9))
        self._asset_list.setMinimumHeight(200)
        layout.addWidget(self._asset_list, 1)

        layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine))

        # Pack I/O
        pack_row = QHBoxLayout()
        pack_row.setSpacing(8)

        import_btn = QPushButton("Import .aupack")
        import_btn.setObjectName("toolBtn")
        import_btn.setFixedHeight(32)
        import_btn.clicked.connect(self._cb_import_pack)
        pack_row.addWidget(import_btn)

        export_btn = QPushButton("Export .aupack")
        export_btn.setObjectName("toolBtn")
        export_btn.setFixedHeight(32)
        export_btn.clicked.connect(self._cb_export_pack)
        pack_row.addWidget(export_btn)

        pack_row.addStretch()
        layout.addLayout(pack_row)

        # Status bar
        self._status_bar = QLabel("Profile: None | Replacements: 0")
        self._status_bar.setObjectName("statusText")
        layout.addWidget(self._status_bar)

    # ---- Profile management ----

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
        self._refresh_asset_list()
        self._update_status()

    def _cb_create_profile(self):
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

    # ---- Asset list (read-only) ----

    def _refresh_asset_list(self):
        name = self._profile_combo.currentText()
        if not name:
            self._asset_list.clear()
            return
        profile_path = self._profile_mgr.profile_path(name)
        if not profile_path.exists():
            self._asset_list.clear()
            return
        lines = []
        for sub in ASSET_SUBFOLDERS:
            sub_path = profile_path / sub
            if not sub_path.exists():
                continue
            files = sorted(f for f in sub_path.iterdir() if f.is_file())
            if not files:
                continue
            lines.append(f"{sub}/ ({len(files)} files)")
            for f in files:
                size = f.stat().st_size
                if size >= 1024 * 1024:
                    size_str = f"{size / (1024 * 1024):.1f} MB"
                elif size >= 1024:
                    size_str = f"{size / 1024:.0f} KB"
                else:
                    size_str = f"{size} B"
                lines.append(f"  {f.name}  ({size_str})")
            lines.append("")
        if not lines:
            self._asset_list.setText("Empty profile — no asset files found.")
        else:
            self._asset_list.setText("\n".join(lines))

    # ---- Pack I/O ----

    def _cb_import_pack(self):
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

    # ---- Status ----

    def _update_status(self):
        name = self._profile_combo.currentText()
        count = self._profile_mgr.get_profile_count(name) if name else 0
        gp = self._game_path_getter()
        game_str = str(gp) if gp else "Not set"
        self._status_bar.setText(f"Profile: {name or 'None'} | Replacements: {count} | Game: {game_str}")

    def refresh(self):
        self._refresh_profiles()
        self._update_status()
