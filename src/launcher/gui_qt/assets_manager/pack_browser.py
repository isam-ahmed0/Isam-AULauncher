"""Pack Browser — folder tree + file list for AUAS profile assets."""
import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QListWidget, QListWidgetItem, QPushButton, QLabel, QSplitter,
    QFileDialog, QMenu, QInputDialog,
)

from .profile_manager import AUASProfileManager, ASSET_SUBFOLDERS
import gui_qt.theme as theme

log = logging.getLogger(__name__)

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tga", ".gif", ".ico"}
AUDIO_EXTS = {".ogg", ".wav", ".mp3", ".m4a"}


class PackBrowser(QWidget):
    file_selected = Signal(Path)
    profile_changed = Signal(str)

    def __init__(self, profile_mgr: AUASProfileManager, game_path_getter, parent=None):
        super().__init__(parent)
        self._profile_mgr = profile_mgr
        self._game_path_getter = game_path_getter
        self._current_profile = ""
        self._current_folder = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        profile_label = QLabel("Profile:")
        profile_label.setObjectName("sectionTitle")
        toolbar.addWidget(profile_label)

        self._profile_label = QLabel("None")
        self._profile_label.setObjectName("statusText")
        toolbar.addWidget(self._profile_label)

        toolbar.addStretch()

        self._add_files_btn = QPushButton("Add Files")
        self._add_files_btn.setObjectName("toolBtn")
        self._add_files_btn.setFixedHeight(28)
        self._add_files_btn.clicked.connect(self._add_files)
        toolbar.addWidget(self._add_files_btn)

        self._remove_btn = QPushButton("Remove")
        self._remove_btn.setObjectName("dangerBtn")
        self._remove_btn.setFixedHeight(28)
        self._remove_btn.clicked.connect(self._remove_selected)
        toolbar.addWidget(self._remove_btn)

        layout.addLayout(toolbar)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self._tree = QTreeWidget()
        self._tree.setHeaderLabel("Folders")
        self._tree.setMinimumWidth(140)
        self._tree.setMaximumWidth(220)
        self._tree.currentItemChanged.connect(self._on_tree_select)
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._tree_context)
        splitter.addWidget(self._tree)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(4)

        self._file_list = QListWidget()
        self._file_list.setIconSize(self._file_list.iconSize())
        self._file_list.currentItemChanged.connect(self._on_file_select)
        self._file_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._file_list.customContextMenuRequested.connect(self._file_context)
        right_layout.addWidget(self._file_list)

        self._file_count = QLabel("0 files")
        self._file_count.setObjectName("mutedText")
        right_layout.addWidget(self._file_count)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter)

    def set_profile(self, name: str):
        self._current_profile = name
        self._profile_label.setText(name or "None")
        self._refresh_tree()

    def _refresh_tree(self):
        self._tree.clear()
        if not self._current_profile:
            return
        profile_path = self._profile_mgr.profile_path(self._current_profile)
        if not profile_path.exists():
            return
        root = QTreeWidgetItem(self._tree, [self._current_profile])
        root.setExpanded(True)
        for sub in ASSET_SUBFOLDERS:
            sub_path = profile_path / sub
            item = QTreeWidgetItem(root, [sub])
            if sub_path.exists() and any(sub_path.iterdir()):
                item.setForeground(0, self._tree.palette().text())
            else:
                item.setForeground(0, self._tree.palette().mid())
            count = sum(1 for _ in sub_path.iterdir()) if sub_path.exists() else 0
            item.setText(0, f"{sub} ({count})")

    def _on_tree_select(self, item, prev):
        if not item:
            return
        name = item.text(0).split(" (")[0]
        if name == self._current_profile:
            self._current_folder = None
            self._refresh_file_list()
            return
        self._current_folder = name
        self._refresh_file_list()

    def _refresh_file_list(self):
        self._file_list.clear()
        if not self._current_profile or not self._current_folder:
            self._file_count.setText("0 files")
            return
        profile_path = self._profile_mgr.profile_path(self._current_profile)
        folder = profile_path / self._current_folder
        if not folder.exists():
            self._file_count.setText("0 files")
            return
        files = sorted(folder.iterdir())
        count = 0
        for f in files:
            if f.is_file():
                size_kb = f.stat().st_size / 1024
                if size_kb >= 1024:
                    size_str = f"{size_kb / 1024:.1f} MB"
                else:
                    size_str = f"{size_kb:.0f} KB"
                item = QListWidgetItem(f"{f.name}  ({size_str})")
                item.setData(Qt.ItemDataRole.UserRole, str(f))
                self._file_list.addItem(item)
                count += 1
        self._file_count.setText(f"{count} file{'s' if count != 1 else ''}")

    def _on_file_select(self, item, prev):
        if not item:
            return
        path_str = item.data(Qt.ItemDataRole.UserRole)
        if path_str:
            self.file_selected.emit(Path(path_str))

    def _add_files(self):
        if not self._current_profile or not self._current_folder:
            return
        files, _ = QFileDialog.getOpenFileNames(
            self, "Add Asset Files", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tga *.gif *.ico);;Audio (*.ogg *.wav *.mp3 *.m4a);;All (*)",
        )
        if not files:
            return
        import shutil
        target = self._profile_mgr.profile_path(self._current_profile) / self._current_folder
        target.mkdir(parents=True, exist_ok=True)
        for f in files:
            src = Path(f)
            try:
                shutil.copy2(str(src), str(target / src.name))
            except Exception as e:
                log.error(f"Failed to copy {src}: {e}")
        self._refresh_tree()
        self._refresh_file_list()

    def _remove_selected(self):
        item = self._file_list.currentItem()
        if not item:
            return
        path_str = item.data(Qt.ItemDataRole.UserRole)
        if not path_str:
            return
        p = Path(path_str)
        try:
            p.unlink()
        except Exception as e:
            log.error(f"Failed to remove {p}: {e}")
        self._refresh_tree()
        self._refresh_file_list()

    def _tree_context(self, pos):
        item = self._tree.itemAt(pos)
        if not item:
            return
        name = item.text(0).split(" (")[0]
        if name == self._current_profile:
            return
        menu = QMenu(self)
        add_action = menu.addAction("Add Files...")
        add_action.triggered.connect(self._add_files)
        delete_action = menu.addAction("Delete All")
        delete_action.triggered.connect(lambda: self._delete_folder(name))
        menu.exec(self._tree.viewport().mapToGlobal(pos))

    def _file_context(self, pos):
        item = self._file_list.itemAt(pos)
        if not item:
            return
        menu = QMenu(self)
        remove_action = menu.addAction("Remove")
        remove_action.triggered.connect(self._remove_selected)
        menu.exec(self._file_list.viewport().mapToGlobal(pos))

    def _delete_folder(self, name: str):
        import shutil
        target = self._profile_mgr.profile_path(self._current_profile) / name
        if target.exists():
            shutil.rmtree(str(target))
            target.mkdir(exist_ok=True)
        self._refresh_tree()
        self._refresh_file_list()

    def refresh(self):
        self._refresh_tree()
        self._refresh_file_list()
