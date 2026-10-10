"""Assets Manager page — AU-Assets-Swapper resource pack manager."""
import logging
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame,
    QComboBox, QTreeWidget, QTreeWidgetItem, QFileDialog, QInputDialog,
    QMessageBox, QScrollArea, QDialog, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView,
)

import gui_qt.theme as theme
from .manager import AUASManager, ASSET_CATEGORIES
from .pack_info import PackInfoDialog

log = logging.getLogger(__name__)


def _fmt_size(size: int) -> str:
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    if size >= 1024:
        return f"{size / 1024:.0f} KB"
    return f"{size} B"


class _AddAssetsDialog(QDialog):
    """Pick a target category for each file before copying."""

    def __init__(self, files: List[Path], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Assets")
        self.setMinimumSize(520, 380)
        self._files = list(files)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(10)

        info = QLabel(
            "Choose the destination folder for each file. "
            "Files with no known type default to Sprites.")
        info.setObjectName("bodyText")
        info.setWordWrap(True)
        layout.addWidget(info)

        self._table = QTableWidget(len(self._files), 2)
        self._table.setHorizontalHeaderLabels(["File", "Category"])
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        for row, f in enumerate(self._files):
            name_item = QTableWidgetItem(f.name)
            name_item.setToolTip(str(f))
            self._table.setItem(row, 0, name_item)

            combo = QComboBox()
            combo.addItems(ASSET_CATEGORIES)
            guess = AUASManager.guess_category(f.name) or "Sprites"
            idx = combo.findText(guess)
            if idx >= 0:
                combo.setCurrentIndex(idx)
            self._table.setCellWidget(row, 1, combo)
        layout.addWidget(self._table, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("toolBtn")
        cancel_btn.setFixedHeight(34)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        add_btn = QPushButton("Add")
        add_btn.setObjectName("successBtn")
        add_btn.setFixedHeight(34)
        add_btn.clicked.connect(self.accept)
        btn_row.addWidget(add_btn)
        layout.addLayout(btn_row)

    def items(self) -> List[Tuple[Path, str]]:
        out: List[Tuple[Path, str]] = []
        for row, f in enumerate(self._files):
            combo = self._table.cellWidget(row, 1)
            category = combo.currentText() if combo else "Sprites"
            out.append((f, category))
        return out


class AssetsManagerPage(QWidget):
    def __init__(self, game_path_getter: Callable[[], Optional[Path]],
                 game_running_getter: Optional[Callable[[], bool]] = None,
                 parent=None):
        super().__init__(parent)
        self._game_path_getter = game_path_getter
        self._game_running_getter = game_running_getter or (lambda: False)
        self._mgr = AUASManager(game_path_getter())
        self._build_ui()
        self.refresh()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        page = QVBoxLayout(self)
        page.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(32, 20, 32, 20)
        layout.setSpacing(14)

        title = QLabel("ASSETS")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        desc = QLabel(
            "Manage AU-Assets-Swapper resource packs in your game's AUAS_Data "
            "folder.\nEach pack holds replacement Sprites, Textures, Audio, Fonts, "
            "Shaders, Materials, Prefabs and TextAssets.")
        desc.setObjectName("bodyText")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine))

        # ---- pack selection row ----
        prof_title = QLabel("PACK")
        prof_title.setObjectName("sectionTitle")
        layout.addWidget(prof_title)

        sel_row = QHBoxLayout()
        sel_row.setSpacing(10)

        self._pack_combo = QComboBox()
        self._pack_combo.setFixedHeight(38)
        self._pack_combo.setMinimumWidth(220)
        self._pack_combo.currentTextChanged.connect(self._on_pack_changed)
        sel_row.addWidget(self._pack_combo)

        create_btn = QPushButton("Create")
        create_btn.setObjectName("toolBtn")
        create_btn.setFixedHeight(38)
        create_btn.clicked.connect(self._cb_create)
        sel_row.addWidget(create_btn)

        rename_btn = QPushButton("Rename")
        rename_btn.setObjectName("toolBtn")
        rename_btn.setFixedHeight(38)
        rename_btn.clicked.connect(self._cb_rename)
        sel_row.addWidget(rename_btn)

        delete_btn = QPushButton("Delete")
        delete_btn.setObjectName("dangerBtn")
        delete_btn.setFixedHeight(38)
        delete_btn.clicked.connect(self._cb_delete)
        sel_row.addWidget(delete_btn)

        sel_row.addStretch()
        layout.addLayout(sel_row)

        self._active_label = QLabel("")
        self._active_label.setObjectName("statusText")
        layout.addWidget(self._active_label)

        switch_row = QHBoxLayout()
        switch_row.setSpacing(8)

        self._activate_btn = QPushButton("Set Active Pack")
        self._activate_btn.setObjectName("primaryBtn")
        self._activate_btn.setFixedHeight(38)
        self._activate_btn.clicked.connect(self._cb_activate)
        switch_row.addWidget(self._activate_btn)

        clear_btn = QPushButton("Disable (Vanilla)")
        clear_btn.setObjectName("toolBtn")
        clear_btn.setFixedHeight(38)
        clear_btn.clicked.connect(self._cb_clear_active)
        switch_row.addWidget(clear_btn)

        switch_row.addStretch()
        layout.addLayout(switch_row)

        layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine))

        # ---- assets in selected pack ----
        assets_title = QLabel("ASSETS IN PACK")
        assets_title.setObjectName("sectionTitle")
        layout.addWidget(assets_title)

        self._tree = QTreeWidget()
        self._tree.setColumnCount(2)
        self._tree.setHeaderLabels(["Name", "Size"])
        self._tree.setMinimumHeight(180)
        self._tree.setRootIsDecorated(True)
        self._tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self._tree)

        asset_btn_row = QHBoxLayout()
        asset_btn_row.setSpacing(10)

        add_btn = QPushButton("Add Files")
        add_btn.setObjectName("successBtn")
        add_btn.setFixedHeight(38)
        add_btn.clicked.connect(self._cb_add_files)
        asset_btn_row.addWidget(add_btn)

        remove_btn = QPushButton("Remove Selected")
        remove_btn.setObjectName("dangerBtn")
        remove_btn.setFixedHeight(38)
        remove_btn.clicked.connect(self._cb_remove_selected)
        asset_btn_row.addWidget(remove_btn)

        open_btn = QPushButton("Open Pack Folder")
        open_btn.setObjectName("toolBtn")
        open_btn.setFixedHeight(38)
        open_btn.clicked.connect(self._cb_open_folder)
        asset_btn_row.addWidget(open_btn)

        edit_btn = QPushButton("Edit Info")
        edit_btn.setObjectName("toolBtn")
        edit_btn.setFixedHeight(38)
        edit_btn.clicked.connect(self._cb_edit_info)
        asset_btn_row.addWidget(edit_btn)

        asset_btn_row.addStretch()
        layout.addLayout(asset_btn_row)

        layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine))

        # ---- pack import / export ----
        io_title = QLabel("PACK FILE")
        io_title.setObjectName("sectionTitle")
        layout.addWidget(io_title)

        io_row = QHBoxLayout()
        io_row.setSpacing(10)
        import_btn = QPushButton("Import Pack (.zip)")
        import_btn.setObjectName("toolBtn")
        import_btn.setFixedHeight(38)
        import_btn.clicked.connect(self._cb_import)
        io_row.addWidget(import_btn)
        export_btn = QPushButton("Export Pack (.aupack)")
        export_btn.setObjectName("toolBtn")
        export_btn.setFixedHeight(38)
        export_btn.clicked.connect(self._cb_export)
        io_row.addWidget(export_btn)
        io_row.addStretch()
        layout.addLayout(io_row)

        layout.addStretch()

        self._status = QLabel("")
        self._status.setObjectName("statusText")
        layout.addWidget(self._status)

        scroll.setWidget(content)
        page.addWidget(scroll)

    # ------------------------------------------------------------------ state
    def _selected_pack(self) -> Optional[str]:
        return self._pack_combo.currentText() or None

    def _set_status(self, text: str, kind: str = "muted"):
        self._status.setText(text)
        self._status.setObjectName({
            "muted": "mutedText", "info": "infoText",
            "success": "successText", "danger": "dangerText",
            "warning": "warningText",
        }.get(kind, "statusText"))
        self._status.style().polish(self._status)

    def _game_running(self) -> bool:
        try:
            return bool(self._game_running_getter())
        except Exception:
            return False

    def _warn_game_running(self) -> bool:
        if self._game_running():
            QMessageBox.warning(
                self, "Game Running",
                "Close Among Us before changing packs.\n"
                "In-game you can also press F6 to switch packs.")
            return True
        return False

    # ------------------------------------------------------------------ refresh
    def refresh(self):
        gp = self._game_path_getter()
        self._mgr.game_path = Path(gp) if gp else None
        active = self._mgr.get_active_pack()
        current = self._pack_combo.currentText()

        self._pack_combo.blockSignals(True)
        self._pack_combo.clear()
        packs = self._mgr.list_packs()
        self._pack_combo.addItems(packs)
        if current in packs:
            self._pack_combo.setCurrentText(current)
        elif active in packs:
            self._pack_combo.setCurrentText(active)
        self._pack_combo.blockSignals(False)

        self._update_active_label(active)
        self._refresh_assets()

    def _on_pack_changed(self, _name: str):
        self._refresh_assets()

    def _update_active_label(self, active: Optional[str]):
        if not self._mgr.game_path:
            self._active_label.setText("Game location not set — set it on the Home page.")
            self._active_label.setObjectName("warningText")
        elif active:
            self._active_label.setText(f"Active pack: {active}   (F6 in-game to cycle)")
            self._active_label.setObjectName("successText")
        else:
            self._active_label.setText("Active pack: none (game uses vanilla assets)")
            self._active_label.setObjectName("statusText")
        self._active_label.style().polish(self._active_label)

    def _refresh_assets(self):
        self._tree.clear()
        name = self._selected_pack()
        if not name:
            self._set_status(
                "No packs yet. Use Create to make one.", "muted")
            return
        assets = self._mgr.list_assets(name)
        total = 0
        for cat in ASSET_CATEGORIES:
            files = assets.get(cat, [])
            cat_item = QTreeWidgetItem([f"{cat}  ({len(files)})", ""])
            self._tree.addTopLevelItem(cat_item)
            for rel, size in files:
                child = QTreeWidgetItem([rel, _fmt_size(size)])
                child.setData(0, Qt.ItemDataRole.UserRole, (cat, rel))
                cat_item.addChild(child)
                total += 1
            cat_item.setExpanded(total <= 60)
        if total == 0:
            self._set_status(f"'{name}' is empty. Use Add Files to add replacements.", "muted")
        else:
            self._set_status(f"{total} asset(s) in '{name}'.", "info")

    # ------------------------------------------------------------------ pack ops
    def _cb_create(self):
        if not self._mgr.game_path:
            QMessageBox.warning(self, "No Game", "Set the game location on the Home page first.")
            return
        name, ok = QInputDialog.getText(self, "Create Pack", "Pack name:")
        if not ok or not name.strip():
            return
        name = name.strip()
        if not self._mgr.is_valid_name(name):
            QMessageBox.warning(self, "Invalid Name", "'" + name + "' is not a valid pack name.")
            return
        if not self._mgr.create_pack(name):
            QMessageBox.warning(self, "Error", f"Could not create pack '{name}'.\nIt may already exist.")
            return
        self.refresh()
        self._pack_combo.setCurrentText(name)
        self._set_status(f"Created pack '{name}'.", "success")

    def _cb_rename(self):
        name = self._selected_pack()
        if not name:
            return
        new, ok = QInputDialog.getText(self, "Rename Pack", "New name:", text=name)
        if not ok or not new.strip() or new.strip() == name:
            return
        new = new.strip()
        if not self._mgr.rename_pack(name, new):
            QMessageBox.warning(self, "Error", f"Could not rename to '{new}'.\nName may be invalid or already exists.")
            return
        self.refresh()
        self._pack_combo.setCurrentText(new)
        self._set_status(f"Renamed '{name}' to '{new}'.", "success")

    def _cb_delete(self):
        name = self._selected_pack()
        if not name:
            return
        reply = QMessageBox.question(
            self, "Delete Pack",
            f"Delete pack '{name}' and all of its assets?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        if self._mgr.delete_pack(name):
            self.refresh()
            self._set_status(f"Deleted pack '{name}'.", "success")
        else:
            self._set_status(f"Failed to delete '{name}'.", "danger")

    def _cb_activate(self):
        name = self._selected_pack()
        if not name:
            return
        if not self._mgr.game_path:
            QMessageBox.warning(self, "No Game", "Set the game location on the Home page first.")
            return
        if self._mgr.set_active_pack(name):
            self._update_active_label(name)
            self._set_status(
                f"Active pack set to '{name}'. F5 in-game to reload.", "success")
        else:
            self._set_status("Failed to write AUAS config.", "danger")

    def _cb_clear_active(self):
        if self._mgr.set_active_pack(None):
            self._update_active_label(None)
            self._set_status("Active pack cleared — game will use vanilla assets.", "success")
        else:
            self._set_status("Failed to write AUAS config.", "danger")

    # ------------------------------------------------------------------ assets
    def _cb_add_files(self):
        name = self._selected_pack()
        if not name:
            QMessageBox.warning(self, "No Pack", "Select or create a pack first.")
            return
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Asset Files", "",
            "All Files (*)")
        if not files:
            return
        dlg = _AddAssetsDialog([Path(f) for f in files], parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        copied, errors = self._mgr.copy_assets(name, dlg.items())
        self._refresh_assets()
        if errors:
            QMessageBox.warning(
                self, "Some Files Skipped",
                f"Added {copied} file(s) to '{name}'.\n\n" + "\n".join(errors[:10]))
        self._set_status(f"Added {copied} file(s) to '{name}'.", "success")

    def _cb_remove_selected(self):
        name = self._selected_pack()
        items = self._tree.selectedItems()
        targets = []
        for it in items:
            data = it.data(0, Qt.ItemDataRole.UserRole)
            if data:
                targets.append(data)
        if not name or not targets:
            QMessageBox.information(self, "Info", "Select file(s) in the tree to remove.")
            return
        reply = QMessageBox.question(
            self, "Remove Assets",
            f"Remove {len(targets)} file(s) from '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        removed = sum(1 for cat, rel in targets if self._mgr.remove_asset(name, cat, rel))
        self._refresh_assets()
        self._set_status(f"Removed {removed} file(s).", "success")

    def _cb_open_folder(self):
        from platform_utils import open_local_path
        name = self._selected_pack()
        path = self._mgr.pack_path(name) if name else self._mgr.auas_dir
        if path and path.exists():
            open_local_path(path)
        else:
            QMessageBox.information(self, "Info", "Folder does not exist yet.")

    def _cb_edit_info(self):
        name = self._selected_pack()
        if not name:
            return
        meta = self._mgr.get_metadata(name)
        dlg = PackInfoDialog(name, meta, self._mgr.pack_path(name), parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_meta = dlg.result_metadata()
            old_meta = meta or self._mgr.get_metadata(name)
            if old_meta and old_meta.created_at:
                new_meta.created_at = old_meta.created_at
            self._mgr.save_metadata(name, new_meta)
            self._set_status(f"Saved pack info for '{name}'.", "success")

    # ------------------------------------------------------------------ pack I/O
    def _cb_import(self):
        if not self._mgr.game_path:
            QMessageBox.warning(self, "No Game", "Set the game location on the Home page first.")
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Pack", "", "AU Asset Pack (*.aupack *.zip);;All Files (*)")
        if not path:
            return
        src = Path(path)
        meta = AUASManager.read_zip_meta(src)
        suggested = (meta.name if meta and meta.name else src.stem)
        name, ok = QInputDialog.getText(self, "Import Pack", "New pack name:", text=suggested)
        if not ok or not name.strip():
            return
        name = name.strip()
        if name in self._mgr.list_packs():
            reply = QMessageBox.question(
                self, "Overwrite",
                f"Pack '{name}' already exists. Overwrite it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                return
        result = self._mgr.import_pack(src, name)
        if result:
            self.refresh()
            self._pack_combo.setCurrentText(result)
            self._set_status(f"Imported pack '{result}'.", "success")
        else:
            QMessageBox.warning(self, "Import Failed",
                                "Could not import the pack. Is it a valid .aupack/.zip?")

    def _cb_export(self):
        name = self._selected_pack()
        if not name:
            return
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Export Pack", f"{name}.aupack",
            "AU Asset Pack (*.aupack);;Zip (*.zip);;All Files (*)")
        if not save_path:
            return
        if self._mgr.export_pack(name, Path(save_path)):
            self._set_status(f"Exported '{name}'.", "success")
        else:
            self._set_status("Export failed.", "danger")
