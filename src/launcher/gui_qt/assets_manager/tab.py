"""Assets Manager page — AU-Assets-Swapper resource pack manager."""
import logging
from collections import Counter
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from PySide6.QtCore import Qt, QRect, QSize, QPoint
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QLabel,
    QFrame, QComboBox, QTreeWidget, QTreeWidgetItem, QFileDialog,
    QInputDialog, QMessageBox, QDialog, QListWidget, QListWidgetItem,
    QSplitter, QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox,
    QAbstractItemView, QLayout, QSizePolicy,
)

from .manager import AUASManager, ASSET_CATEGORIES
from .pack_info import PackInfoDialog

log = logging.getLogger(__name__)

_NAME_ROLE = Qt.ItemDataRole.UserRole
_BASE_ROLE = Qt.ItemDataRole.UserRole + 1
_ASSET_ROLE = Qt.ItemDataRole.UserRole + 2
_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tga"}
_ALL_PILL = "All categories"


def _fmt_size(size: int) -> str:
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    if size >= 1024:
        return f"{size / 1024:.0f} KB"
    return f"{size} B"


class FlowLayout(QLayout):
    """A simple left-to-right layout that wraps onto new lines."""

    def __init__(self, parent=None, margin: int = 0,
                 hspacing: int = 8, vspacing: int = 8):
        super().__init__(parent)
        self._items: List = []
        self._hspace = hspacing
        self._vspace = vspacing
        self.setContentsMargins(margin, margin, margin, margin)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        size += QSize(m.left() + m.right(), m.top() + m.bottom())
        return size

    def _do_layout(self, rect: QRect, test_only: bool):
        m = self.contentsMargins()
        effective = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        x, y = effective.x(), effective.y()
        line_height = 0
        for item in self._items:
            hint = item.sizeHint()
            next_x = x + hint.width() + self._hspace
            if next_x - self._hspace > effective.right() and line_height > 0:
                x = effective.x()
                y = y + line_height + self._vspace
                next_x = x + hint.width() + self._hspace
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), hint))
            x = next_x
            line_height = max(line_height, hint.height())
        return y + line_height - rect.y() + m.bottom()


class _AddAssetsDialog(QDialog):
    """Confirm category per file and the overwrite policy before copying."""

    def __init__(self, files: List[Path], conflicts: List[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Assets")
        self.setMinimumSize(540, 400)
        self._files = list(files)
        self._conflicts = set(conflicts)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(10)

        unknown = sum(1 for f in self._files
                      if AUASManager.guess_category(f.name) is None)
        if unknown:
            text = (f"{unknown} file(s) have an unknown type. "
                    "Choose a destination folder for each.")
        else:
            text = "Adjust the destination folder for any file, then click Add."
        info = QLabel(text)
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
            guess = AUASManager.guess_category(f.name)
            label = f.name if guess else f"{f.name}   (unknown type)"
            name_item = QTableWidgetItem(label)
            name_item.setToolTip(str(f))
            self._table.setItem(row, 0, name_item)

            combo = QComboBox()
            combo.addItems(ASSET_CATEGORIES)
            idx = combo.findText(guess or "Sprites")
            if idx >= 0:
                combo.setCurrentIndex(idx)
            self._table.setCellWidget(row, 1, combo)
        layout.addWidget(self._table, 1)

        self._replace_chk = QCheckBox("Replace existing files (uncheck to keep both)")
        self._replace_chk.setChecked(True)
        if self._conflicts:
            self._replace_chk.setText(
                f"Replace {len(self._conflicts)} existing file(s) "
                "(uncheck to keep both)")
            layout.addWidget(self._replace_chk)
        else:
            self._replace_chk.hide()

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("toolBtn")
        cancel_btn.setMinimumHeight(36)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        add_btn = QPushButton("Add")
        add_btn.setObjectName("successBtn")
        add_btn.setMinimumHeight(36)
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

    def overwrite(self) -> bool:
        return self._replace_chk.isChecked()


class AssetsManagerPage(QWidget):
    def __init__(self, game_path_getter: Callable[[], Optional[Path]],
                 game_running_getter: Optional[Callable[[], bool]] = None,
                 parent=None):
        super().__init__(parent)
        self._game_path_getter = game_path_getter
        self._game_running_getter = game_running_getter or (lambda: False)
        self._mgr = AUASManager(game_path_getter())
        self._loading = False
        self._current_pack: Optional[str] = None
        self._assets: Dict[str, List[Tuple[str, int]]] = {}
        self._active_cat: Optional[str] = None
        self.setAcceptDrops(True)
        self._build_ui()
        self.refresh()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._build_left_pane())
        splitter.addWidget(self._build_right_pane())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([300, 800])
        root.addWidget(splitter)

    # ---- left: pack list + actions (two separate cards)
    def _build_left_pane(self) -> QWidget:
        left = QWidget()
        left.setMinimumWidth(270)
        left.setMaximumWidth(390)
        ll = QVBoxLayout(left)
        ll.setContentsMargins(20, 20, 10, 20)
        ll.setSpacing(12)

        title = QLabel("PACKS")
        title.setObjectName("assetsSectionLabel")
        ll.addWidget(title)

        list_card = QFrame()
        list_card.setObjectName("assetsPanelCard")
        lc = QVBoxLayout(list_card)
        lc.setContentsMargins(12, 12, 12, 12)
        lc.setSpacing(8)
        self._pack_list = QListWidget()
        self._pack_list.currentItemChanged.connect(self._on_pack_selected)
        lc.addWidget(self._pack_list)
        ll.addWidget(list_card, 1)

        actions_card = QFrame()
        actions_card.setObjectName("assetsPanelCard")
        ac = QVBoxLayout(actions_card)
        ac.setContentsMargins(12, 12, 12, 12)
        ac.setSpacing(8)
        manage = QLabel("MANAGE")
        manage.setObjectName("assetsSectionLabel")
        ac.addWidget(manage)

        grid = QGridLayout()
        grid.setSpacing(8)
        self._new_btn = self._left_button("New Pack", "successBtn", self._cb_create)
        self._import_btn = self._left_button("Import Pack", "toolBtn", self._cb_import)
        self._dup_btn = self._left_button("Duplicate", "toolBtn", self._cb_duplicate)
        self._rename_btn = self._left_button("Rename", "toolBtn", self._cb_rename)
        self._delete_btn = self._left_button("Delete Pack", "dangerSoftBtn", self._cb_delete)
        grid.addWidget(self._new_btn, 0, 0)
        grid.addWidget(self._import_btn, 0, 1)
        grid.addWidget(self._dup_btn, 1, 0)
        grid.addWidget(self._rename_btn, 1, 1)
        grid.addWidget(self._delete_btn, 2, 0, 1, 2)
        ac.addLayout(grid)
        ll.addWidget(actions_card)

        hint = QLabel("Click a pack to make it active.")
        hint.setObjectName("mutedText")
        hint.setWordWrap(True)
        ll.addWidget(hint)
        return left

    @staticmethod
    def _left_button(text: str, object_name: str, slot) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName(object_name)
        btn.setMinimumHeight(40)
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        btn.clicked.connect(slot)
        return btn

    # ---- right: info card + files + toolbars
    def _build_right_pane(self) -> QWidget:
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(16, 20, 24, 20)
        rl.setSpacing(14)

        title = QLabel("Assets")
        title.setObjectName("assetsPageTitle")
        rl.addWidget(title)

        banner = QLabel(
            "Click a pack on the left to activate it. Press F5 in-game to apply "
            "and F6 to cycle packs. Drag & drop files or folders here to add them.")
        banner.setObjectName("bodyText")
        banner.setWordWrap(True)
        rl.addWidget(banner)

        rl.addWidget(self._build_info_card())
        rl.addWidget(self._build_files_section(), 1)
        rl.addWidget(self._build_asset_toolbars())

        self._status = QLabel("")
        self._status.setObjectName("statusText")
        self._status.setWordWrap(True)
        rl.addWidget(self._status)
        return right

    def _build_info_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("assetsPanelCard")
        outer = QVBoxLayout(card)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(14)

        top = QHBoxLayout()
        top.setSpacing(16)

        self._thumb = QLabel("")
        self._thumb.setObjectName("assetsCover")
        self._thumb.setFixedSize(108, 108)
        self._thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cover_font = self._thumb.font()
        cover_font.setPointSize(30)
        cover_font.setBold(True)
        self._thumb.setFont(cover_font)
        top.addWidget(self._thumb, 0, Qt.AlignmentFlag.AlignTop)

        info = QVBoxLayout()
        info.setSpacing(4)
        head = QHBoxLayout()
        head.setSpacing(10)
        self._name_label = QLabel("")
        self._name_label.setObjectName("assetsCardTitle")
        head.addWidget(self._name_label, 1)
        self._edit_btn = QPushButton("Edit Info")
        self._edit_btn.setObjectName("toolBtn")
        self._edit_btn.setMinimumHeight(40)
        self._edit_btn.setMinimumWidth(110)
        self._edit_btn.clicked.connect(self._cb_edit_info)
        head.addWidget(self._edit_btn, 0, Qt.AlignmentFlag.AlignTop)
        info.addLayout(head)

        self._detail_label = QLabel("")
        self._detail_label.setObjectName("profileDetail")
        self._detail_label.setWordWrap(True)
        info.addWidget(self._detail_label)

        self._desc_label = QLabel("")
        self._desc_label.setObjectName("bodyText")
        self._desc_label.setWordWrap(True)
        info.addWidget(self._desc_label)
        info.addStretch()
        top.addLayout(info, 1)
        outer.addLayout(top)

        pills_label = QLabel("CATEGORIES")
        pills_label.setObjectName("assetsSectionLabel")
        outer.addWidget(pills_label)

        self._pills_host = QWidget()
        self._pills_layout = FlowLayout(self._pills_host, hspacing=8, vspacing=8)
        outer.addWidget(self._pills_host)
        return card

    def _build_files_section(self) -> QWidget:
        section = QWidget()
        sv = QVBoxLayout(section)
        sv.setContentsMargins(0, 0, 0, 0)
        sv.setSpacing(10)

        head = QHBoxLayout()
        head.setSpacing(10)
        label = QLabel("FILES")
        label.setObjectName("assetsSectionLabel")
        head.addWidget(label)
        self._count_label = QLabel("")
        self._count_label.setObjectName("mutedText")
        head.addWidget(self._count_label)
        head.addStretch()
        self._list_toggle = QPushButton("Show file list")
        self._list_toggle.setObjectName("toolBtn")
        self._list_toggle.setCheckable(True)
        self._list_toggle.setMinimumHeight(40)
        self._list_toggle.setMinimumWidth(150)
        self._list_toggle.toggled.connect(self._on_toggle_list)
        head.addWidget(self._list_toggle)
        sv.addLayout(head)

        self._tree = QTreeWidget()
        self._tree.setObjectName("assetsFileTree")
        self._tree.setColumnCount(2)
        self._tree.setHeaderLabels(["Name", "Size"])
        self._tree.setMinimumHeight(160)
        self._tree.setRootIsDecorated(True)
        self._tree.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection)
        self._tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._tree.currentItemChanged.connect(self._on_asset_selected)
        self._tree.setVisible(False)
        sv.addWidget(self._tree, 1)

        self._preview_frame = QFrame()
        self._preview_frame.setObjectName("assetsPanelCard")
        pv = QVBoxLayout(self._preview_frame)
        pv.setContentsMargins(12, 12, 12, 12)
        self._preview = QLabel("")
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setMinimumHeight(140)
        pv.addWidget(self._preview)
        self._preview_frame.setVisible(False)
        sv.addWidget(self._preview_frame)
        return section

    def _build_asset_toolbars(self) -> QWidget:
        wrap = QWidget()
        wv = QVBoxLayout(wrap)
        wv.setContentsMargins(0, 0, 0, 0)
        wv.setSpacing(8)

        row1 = QHBoxLayout()
        row1.setSpacing(10)
        self._add_btn = QPushButton("Add Files")
        self._add_btn.setObjectName("successBtn")
        self._add_btn.setMinimumHeight(40)
        self._add_btn.setMinimumWidth(120)
        self._add_btn.clicked.connect(self._cb_add_files)
        self._add_folder_btn = QPushButton("Add Folder")
        self._add_folder_btn.setObjectName("successBtn")
        self._add_folder_btn.setMinimumHeight(40)
        self._add_folder_btn.setMinimumWidth(120)
        self._add_folder_btn.clicked.connect(self._cb_add_folder)
        row1.addWidget(self._add_btn)
        row1.addWidget(self._add_folder_btn)
        row1.addStretch()
        wv.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(10)
        self._remove_btn = QPushButton("Remove Selected")
        self._remove_btn.setObjectName("dangerSoftBtn")
        self._remove_btn.setMinimumHeight(40)
        self._remove_btn.setMinimumWidth(160)
        self._remove_btn.clicked.connect(self._cb_remove_selected)
        self._open_btn = QPushButton("Open Folder")
        self._open_btn.setObjectName("toolBtn")
        self._open_btn.setMinimumHeight(40)
        self._open_btn.setMinimumWidth(120)
        self._open_btn.clicked.connect(self._cb_open_folder)
        self._export_btn = QPushButton("Export .zip")
        self._export_btn.setObjectName("toolBtn")
        self._export_btn.setMinimumHeight(40)
        self._export_btn.setMinimumWidth(120)
        self._export_btn.clicked.connect(self._cb_export)
        row2.addWidget(self._remove_btn)
        row2.addWidget(self._open_btn)
        row2.addStretch()
        row2.addWidget(self._export_btn)
        wv.addLayout(row2)
        return wrap

    # ------------------------------------------------------------------ state
    def _set_status(self, text: str, kind: str = "muted"):
        self._status.setText(text)
        self._status.setObjectName({
            "muted": "mutedText", "info": "infoText",
            "success": "successText", "danger": "dangerText",
            "warning": "warningText",
        }.get(kind, "statusText"))
        self._status.style().polish(self._status)

    # ------------------------------------------------------------------ refresh
    def refresh(self):
        gp = self._game_path_getter()
        self._mgr.game_path = Path(gp) if gp else None
        active = self._mgr.get_active_pack()
        packs = self._mgr.list_packs()

        self._loading = True
        self._pack_list.clear()
        vanilla = QListWidgetItem("None (Vanilla)")
        vanilla.setData(_NAME_ROLE, None)
        vanilla.setData(_BASE_ROLE, "None (Vanilla)")
        self._pack_list.addItem(vanilla)
        for name in packs:
            total = self._mgr.pack_stats(name)[0]
            base = f"{name}    ({total})"
            item = QListWidgetItem(base)
            item.setData(_NAME_ROLE, name)
            item.setData(_BASE_ROLE, base)
            self._pack_list.addItem(item)

        target = self._current_pack if self._current_pack in packs else active
        row = packs.index(target) + 1 if target in packs else 0
        self._pack_list.setCurrentRow(row)
        self._loading = False

        self._current_pack = target
        self._apply_active_highlight(active)
        self._refresh_details()

    def _on_pack_selected(self, current: Optional[QListWidgetItem], _prev=None):
        if self._loading or current is None:
            return
        name = current.data(_NAME_ROLE)
        self._current_pack = name
        self._active_cat = None
        if name is None:
            ok = self._mgr.set_active_pack(None)
            self._set_status(
                "Active pack cleared — the game uses vanilla assets.",
                "success" if ok else "danger")
        else:
            ok = self._mgr.set_active_pack(name)
            if ok:
                self._set_status(
                    f"Active pack: {name} — press F5 in-game to apply.", "success")
            else:
                self._set_status("Failed to write AUAS config.", "danger")
        self._apply_active_highlight(self._mgr.get_active_pack())
        self._refresh_details()

    def _apply_active_highlight(self, active: Optional[str]):
        for i in range(self._pack_list.count()):
            item = self._pack_list.item(i)
            name = item.data(_NAME_ROLE)
            is_active = (name == active) if active else (name is None)
            base = item.data(_BASE_ROLE) or ""
            item.setText(("● " if is_active else "   ") + base)
            font = item.font()
            font.setBold(is_active)
            item.setFont(font)

    def _refresh_details(self):
        name = self._current_pack
        has_pack = bool(name) and bool(self._mgr.game_path)

        for w in (self._add_btn, self._add_folder_btn, self._open_btn,
                  self._edit_btn, self._export_btn, self._list_toggle):
            w.setEnabled(has_pack)

        self._tree.clear()
        self._preview_frame.setVisible(False)

        if not self._mgr.game_path:
            self._name_label.setText("Game location not set")
            self._detail_label.setText("")
            self._desc_label.setText("Set the game folder on the Home page first.")
            self._thumb.setPixmap(QPixmap())
            self._thumb.setText("?")
            self._count_label.setText("")
            self._clear_pills()
            self._set_status("Game location not set.", "warning")
            self._update_action_states()
            return

        if not name:
            self._name_label.setText("No pack selected")
            self._detail_label.setText("")
            self._desc_label.setText("Create or select a pack on the left.")
            self._thumb.setPixmap(QPixmap())
            self._thumb.setText("?")
            self._count_label.setText("")
            self._clear_pills()
            self._set_status("No packs yet. Use New Pack to create one.", "muted")
            self._update_action_states()
            return

        meta = self._mgr.get_metadata(name)
        display = (meta.name if meta and meta.name else name)
        self._name_label.setText(display)
        bits = [f"folder: {name}"]
        if meta and meta.author:
            bits.append(f"by {meta.author}")
        if meta and meta.version:
            bits.append(f"v{meta.version}")
        self._detail_label.setText("  ·  ".join(bits))
        if meta and meta.description:
            self._desc_label.setText(meta.description)
        else:
            self._desc_label.setText("No description — click Edit Info to add one.")
        self._load_thumbnail(name)

        self._assets = self._mgr.list_assets(name)
        cats = [c for c in ASSET_CATEGORIES if self._assets.get(c)]
        total = sum(len(v) for v in self._assets.values())
        if total:
            plural = "y" if len(cats) == 1 else "ies"
            self._count_label.setText(
                f"{total} file(s) · {len(cats)} categor{plural}")
        else:
            self._count_label.setText("no files yet")
        self._populate_pills(cats)
        self._populate_tree()

        if total == 0:
            self._set_status(
                f"'{name}' is empty — drag files here or use Add Files.", "muted")
        else:
            self._set_status(f"Active pack: {name}. {total} asset(s).", "info")
        self._update_action_states()

    def _load_thumbnail(self, name: str):
        meta = self._mgr.get_metadata(name)
        thumb = getattr(meta, "thumbnail", None) if meta else None
        placeholder = (name[:1] or "?").upper()
        pix = QPixmap()
        if thumb:
            p = Path(thumb)
            if not p.is_absolute():
                base = self._mgr.pack_path(name)
                p = (base / thumb) if base else p
            if p.exists():
                pix = QPixmap(str(p))
        if pix.isNull():
            self._thumb.setPixmap(QPixmap())
            self._thumb.setText(placeholder)
        else:
            self._thumb.setText("")
            self._thumb.setPixmap(pix.scaled(
                108, 108, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))

    # ---- category pills
    def _clear_pills(self):
        while self._pills_layout.count():
            item = self._pills_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _add_pill(self, label: str, category: Optional[str], checked: bool):
        btn = QPushButton(label)
        btn.setObjectName("pillBtn")
        btn.setCheckable(True)
        btn.setAutoExclusive(True)
        btn.setProperty("cat", _ALL_PILL if category is None else category)
        btn.setChecked(checked)
        btn.clicked.connect(self._on_pill_clicked)
        self._pills_layout.addWidget(btn)

    def _populate_pills(self, cats: List[str]):
        self._clear_pills()
        if self._active_cat not in cats:
            self._active_cat = None
        self._add_pill(_ALL_PILL, None, checked=self._active_cat is None)
        for cat in ASSET_CATEGORIES:
            if cat in cats:
                self._add_pill(f"{cat} {len(self._assets.get(cat, []))}",
                               cat, checked=self._active_cat == cat)

    def _on_pill_clicked(self):
        sender = self.sender()
        category = sender.property("cat") if sender else _ALL_PILL
        self._active_cat = None if category == _ALL_PILL else category
        self._populate_tree()

    def _populate_tree(self):
        self._tree.clear()
        for cat in ASSET_CATEGORIES:
            files = self._assets.get(cat, [])
            if not files:
                continue
            if self._active_cat and cat != self._active_cat:
                continue
            cat_item = QTreeWidgetItem([f"{cat}  ({len(files)})", ""])
            font = cat_item.font(0)
            font.setBold(True)
            cat_item.setFont(0, font)
            self._tree.addTopLevelItem(cat_item)
            for rel, size in files:
                child = QTreeWidgetItem([rel, _fmt_size(size)])
                child.setData(0, _ASSET_ROLE, (cat, rel))
                cat_item.addChild(child)
            cat_item.setExpanded(True)

    def _on_toggle_list(self, checked: bool):
        self._list_toggle.setText("Hide file list" if checked else "Show file list")
        self._tree.setVisible(checked)
        if not checked:
            self._preview_frame.setVisible(False)

    def _on_asset_selected(self, current: Optional[QTreeWidgetItem], _prev=None):
        data = current.data(0, _ASSET_ROLE) if current else None
        if not data or not self._current_pack or not self._mgr.game_path:
            self._preview_frame.setVisible(False)
            self._update_action_states()
            return
        cat, rel = data
        if Path(rel).suffix.lower() not in _IMAGE_EXTS:
            self._preview_frame.setVisible(False)
            self._update_action_states()
            return
        path = self._mgr.pack_path(self._current_pack) / cat / rel
        pix = QPixmap(str(path))
        if pix.isNull():
            self._preview_frame.setVisible(False)
        else:
            self._preview.setPixmap(pix.scaled(
                320, 200, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))
            self._preview_frame.setVisible(True)
        self._update_action_states()

    def _update_action_states(self):
        has_pack = bool(self._current_pack) and bool(self._mgr.game_path)
        self._remove_btn.setEnabled(has_pack and bool(self._selected_assets()))

    def _selected_assets(self) -> List[Tuple[str, str]]:
        targets = []
        for it in self._tree.selectedItems():
            data = it.data(0, _ASSET_ROLE)
            if data:
                targets.append(data)
        return targets

    # ------------------------------------------------------------------ pack ops
    def _cb_create(self):
        if not self._mgr.game_path:
            QMessageBox.warning(self, "No Game",
                                "Set the game location on the Home page first.")
            return
        name, ok = QInputDialog.getText(self, "New Pack", "Pack name:")
        if not ok or not name.strip():
            return
        name = name.strip()
        if not self._mgr.is_valid_name(name):
            QMessageBox.warning(self, "Invalid Name",
                                f"'{name}' is not a valid pack name.")
            return
        if not self._mgr.create_pack(name):
            QMessageBox.warning(self, "Error",
                                f"Could not create pack '{name}'.\nIt may already exist.")
            return
        self._current_pack = name
        self._mgr.set_active_pack(name)
        self.refresh()
        self._set_status(f"Created and activated '{name}'.", "success")

    def _cb_duplicate(self):
        name = self._current_pack
        if not name:
            QMessageBox.information(self, "No Pack", "Select a pack to duplicate.")
            return
        new, ok = QInputDialog.getText(
            self, "Duplicate Pack", "New pack name:", text=f"{name} copy")
        if not ok or not new.strip() or new.strip() == name:
            return
        new = new.strip()
        if not self._mgr.duplicate_pack(name, new):
            QMessageBox.warning(self, "Error",
                                f"Could not duplicate to '{new}'.\n"
                                "Name may be invalid or already exists.")
            return
        self._current_pack = new
        self.refresh()
        self._set_status(f"Duplicated '{name}' to '{new}'.", "success")

    def _cb_rename(self):
        name = self._current_pack
        if not name:
            return
        new, ok = QInputDialog.getText(self, "Rename Pack", "New name:", text=name)
        if not ok or not new.strip() or new.strip() == name:
            return
        new = new.strip()
        if not self._mgr.rename_pack(name, new):
            QMessageBox.warning(self, "Error",
                                f"Could not rename to '{new}'.\n"
                                "Name may be invalid or already exists.")
            return
        self._current_pack = new
        self.refresh()
        self._set_status(f"Renamed '{name}' to '{new}'.", "success")

    def _cb_delete(self):
        name = self._current_pack
        if not name:
            return
        reply = QMessageBox.question(
            self, "Delete Pack",
            f"Delete pack '{name}' and all of its assets?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        if self._mgr.delete_pack(name):
            self._current_pack = None
            self.refresh()
            self._set_status(f"Deleted pack '{name}'.", "success")
        else:
            self._set_status(f"Failed to delete '{name}'.", "danger")

    # ------------------------------------------------------------------ assets
    @staticmethod
    def _collect_files(paths: List[Path]) -> List[Path]:
        files: List[Path] = []
        for p in paths:
            p = Path(p)
            try:
                if p.is_dir():
                    files.extend(f for f in p.rglob("*") if f.is_file())
                elif p.is_file():
                    files.append(p)
            except OSError:
                continue
        return files

    def _cb_add_files(self):
        if not self._require_pack():
            return
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Asset Files", "", "All Files (*)")
        if files:
            self._add_paths([Path(f) for f in files])

    def _cb_add_folder(self):
        if not self._require_pack():
            return
        folder = QFileDialog.getExistingDirectory(self, "Select Asset Folder")
        if folder:
            self._add_paths([Path(folder)])

    def _require_pack(self) -> bool:
        if not self._current_pack:
            QMessageBox.warning(self, "No Pack", "Select or create a pack first.")
            return False
        return True

    def _add_paths(self, paths: List[Path]):
        name = self._current_pack
        if not name:
            QMessageBox.warning(self, "No Pack", "Select or create a pack first.")
            return
        files = self._collect_files(paths)
        if not files:
            self._set_status("No files found to add.", "warning")
            return

        routed = [(f, AUASManager.guess_category(f.name) or "Sprites")
                  for f in files]
        unknown = [f for f in files if AUASManager.guess_category(f.name) is None]
        conflicts = self._mgr.find_conflicts(name, routed)

        if unknown or conflicts:
            dlg = _AddAssetsDialog(files, conflicts, parent=self)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return
            items = dlg.items()
            overwrite = dlg.overwrite()
        else:
            items = routed
            overwrite = True

        copied, _skipped, errors = self._mgr.copy_assets(
            name, items, overwrite=overwrite)
        self.refresh()

        if copied:
            counts = Counter(cat for _f, cat in items)
            summary = ", ".join(f"{c} {n}" for c, n in counts.most_common())
            self._set_status(f"Added {copied} file(s) to '{name}' ({summary}).",
                             "success")
        else:
            self._set_status(f"No files were added to '{name}'.", "warning")
        if errors:
            QMessageBox.warning(
                self, "Some Files Skipped",
                f"Added {copied} file(s).\n\n" + "\n".join(errors[:10]))

    def _cb_remove_selected(self):
        name = self._current_pack
        targets = self._selected_assets()
        if not name or not targets:
            QMessageBox.information(self, "Info",
                                    "Select file(s) in the list to remove.")
            return
        reply = QMessageBox.question(
            self, "Remove Assets",
            f"Remove {len(targets)} file(s) from '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        removed = sum(1 for cat, rel in targets
                      if self._mgr.remove_asset(name, cat, rel))
        self.refresh()
        self._set_status(f"Removed {removed} file(s).", "success")

    def _cb_open_folder(self):
        from platform_utils import open_local_path
        path = self._mgr.pack_path(self._current_pack) if self._current_pack \
            else self._mgr.auas_dir
        if path and path.exists():
            open_local_path(path)
        else:
            QMessageBox.information(self, "Info", "Folder does not exist yet.")

    def _cb_edit_info(self):
        name = self._current_pack
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
            self.refresh()
            self._set_status(f"Saved pack info for '{name}'.", "success")

    # ------------------------------------------------------------------ pack I/O
    def _cb_import(self):
        if not self._mgr.game_path:
            QMessageBox.warning(self, "No Game",
                                "Set the game location on the Home page first.")
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Pack", "",
            "AU Asset Pack (*.zip *.aupack);;All Files (*)")
        if not path:
            return
        src = Path(path)
        meta = AUASManager.read_zip_meta(src)
        suggested = meta.name if meta and meta.name else src.stem
        name, ok = QInputDialog.getText(
            self, "Import Pack", "New pack name:", text=suggested)
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
            self._current_pack = result
            self.refresh()
            self._set_status(f"Imported pack '{result}'.", "success")
        else:
            QMessageBox.warning(self, "Import Failed",
                                "Could not import the pack. Is it a valid .zip/.aupack?")

    def _cb_export(self):
        name = self._current_pack
        if not name:
            return
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Export Pack", f"{name}.zip", "Zip Archive (*.zip)")
        if not save_path:
            return
        dest = Path(save_path)
        if dest.suffix.lower() != ".zip":
            dest = dest.with_name(dest.stem + ".zip")
        if self._mgr.export_pack(name, dest):
            self._set_status(f"Exported '{name}' to {dest.name}.", "success")
        else:
            self._set_status("Export failed.", "danger")

    # ------------------------------------------------------------------ drag & drop
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and self._current_pack:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls() and self._current_pack:
            event.acceptProposedAction()

    def dropEvent(self, event):
        if not self._current_pack:
            event.ignore()
            return
        paths = [Path(u.toLocalFile()) for u in event.mimeData().urls()
                 if u.toLocalFile()]
        if paths:
            self._add_paths(paths)
            event.acceptProposedAction()
