"""Mod Browser page — browse the remote catalog and install mods into a profile."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget,
    QListWidgetItem, QScrollArea, QFrame, QProgressBar, QComboBox, QLineEdit,
)

import gui_qt.theme as theme

_STATE_LABEL = {
    "install": "Not installed",
    "installed": "Installed",
    "update": "Update available",
    "unknown": "Installed (not in catalog)",
}

_STATE_STYLE = {
    "install": theme.TEXT_SECONDARY,
    "installed": theme.SUCCESS,
    "update": theme.WARNING,
    "unknown": theme.INFO,
}


class ModBrowserPage(QWidget):
    """Read-only view of the catalog; actions are emitted as signals."""

    install_requested = Signal(object)   # ModEntry
    remove_requested = Signal(object)    # ModEntry
    refresh_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries = {}
        self._states = {}
        self._profile = ""
        self._build()

    # ------------------------------------------------------------------ build
    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 20, 32, 20)
        outer.setSpacing(14)

        header = QHBoxLayout()
        title = QLabel("MOD BROWSER")
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch()
        self._profile_label = QLabel("")
        self._profile_label.setObjectName("mutedText")
        header.addWidget(self._profile_label)
        refresh = QPushButton("Refresh Catalog")
        refresh.setObjectName("toolBtn")
        refresh.setFixedHeight(36)
        refresh.clicked.connect(self.refresh_requested.emit)
        header.addWidget(refresh)
        outer.addLayout(header)

        intro = QLabel(
            "Download community mods from the remote catalog. Mods are installed "
            "into the active profile; close the game before installing or removing."
        )
        intro.setObjectName("bodyText")
        intro.setWordWrap(True)
        outer.addWidget(intro)

        filters = QHBoxLayout()
        filters.setSpacing(10)
        self._search = QLineEdit()
        self._search.setObjectName("modBrowserSearch")
        self._search.setPlaceholderText("Search mods...")
        self._search.setFixedHeight(36)
        self._search.textChanged.connect(self._apply_filter)
        filters.addWidget(self._search, 2)
        self._category = QComboBox()
        self._category.setObjectName("toolBtn")
        self._category.setFixedHeight(36)
        self._category.addItem("All categories")
        self._category.currentIndexChanged.connect(self._apply_filter)
        filters.addWidget(self._category, 1)
        outer.addLayout(filters)

        body = QHBoxLayout()
        body.setSpacing(14)

        self._list = QListWidget()
        self._list.setObjectName("modBrowserList")
        self._list.setMinimumWidth(300)
        self._list.currentItemChanged.connect(self._on_selection_changed)
        body.addWidget(self._list, 1)

        detail_card = QFrame()
        detail_card.setObjectName("modBrowserCard")
        detail_card.setMinimumWidth(340)
        detail = QVBoxLayout(detail_card)
        detail.setContentsMargins(20, 18, 20, 18)
        detail.setSpacing(10)

        self._detail_name = QLabel("Select a mod to see details")
        self._detail_name.setObjectName("modBrowserTitle")
        self._detail_name.setWordWrap(True)
        detail.addWidget(self._detail_name)

        self._detail_meta = QLabel("")
        self._detail_meta.setObjectName("modBrowserMeta")
        self._detail_meta.setWordWrap(True)
        detail.addWidget(self._detail_meta)

        self._detail_status = QLabel("")
        detail.addWidget(self._detail_status)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        detail.addWidget(line)

        self._detail_desc = QLabel("")
        self._detail_desc.setObjectName("bodyText")
        self._detail_desc.setWordWrap(True)
        self._detail_desc.setAlignment(Qt.AlignmentFlag.AlignTop)
        detail.addWidget(self._detail_desc, 1)

        self._detail_deps = QLabel("")
        self._detail_deps.setObjectName("mutedText")
        self._detail_deps.setWordWrap(True)
        detail.addWidget(self._detail_deps)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(detail_card)
        body.addWidget(scroll, 1)
        outer.addLayout(body, 1)

        footer = QHBoxLayout()
        self._status = QLabel("")
        self._status.setObjectName("mutedText")
        footer.addWidget(self._status, 1)
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setFixedWidth(140)
        self._progress.setFixedHeight(14)
        self._progress.hide()
        footer.addWidget(self._progress)

        self._remove_btn = QPushButton("Remove")
        self._remove_btn.setObjectName("dangerSoftBtn")
        self._remove_btn.setFixedHeight(36)
        self._remove_btn.setEnabled(False)
        self._remove_btn.clicked.connect(self._on_remove)
        footer.addWidget(self._remove_btn)

        self._install_btn = QPushButton("Install")
        self._install_btn.setObjectName("successBtn")
        self._install_btn.setFixedHeight(36)
        self._install_btn.setEnabled(False)
        self._install_btn.clicked.connect(self._on_install)
        footer.addWidget(self._install_btn)
        outer.addLayout(footer)

    # ------------------------------------------------------------------ model
    def set_catalog(self, catalog, states: dict, profile_name: str):
        """Render a catalog, preserving the current selection where possible."""
        selected_id = self.selected_id()
        self._entries.clear()
        self._states = dict(states or {})
        self._profile = profile_name or ""
        self._profile_label.setText(f"Active profile: {self._profile or 'none'}")

        categories = set()
        for entry in (catalog.mods if catalog else []):
            self._entries[entry.id] = entry
            if entry.category:
                categories.add(entry.category)

        current_category = self._category.currentText()
        self._category.blockSignals(True)
        self._category.clear()
        self._category.addItem("All categories")
        self._category.addItems(sorted(categories, key=str.lower))
        idx = self._category.findText(current_category)
        if idx >= 0:
            self._category.setCurrentIndex(idx)
        self._category.blockSignals(False)

        self._list.clear()
        for entry in sorted((catalog.mods if catalog else []), key=lambda m: m.name.lower()):
            state = self._states.get(entry.id, "install")
            item = QListWidgetItem(f"{entry.name}  ·  v{entry.version}  ·  {_STATE_LABEL.get(state, state)}")
            item.setData(Qt.ItemDataRole.UserRole, entry.id)
            item.setToolTip(entry.description[:300])
            self._list.addItem(item)

        if selected_id:
            items = self._list.findItems("", Qt.MatchFlag.MatchContains)
            for item in items:
                if item.data(Qt.ItemDataRole.UserRole) == selected_id:
                    self._list.setCurrentItem(item)
                    break
        self._apply_filter()
        if self._list.count() and not self._list.currentItem():
            self._list.setCurrentRow(0)
        self._on_selection_changed()

    def set_status(self, text: str, kind: str = ""):
        self._status.setText(text or "")
        color = {
            "success": theme.SUCCESS, "warning": theme.WARNING,
            "danger": theme.DANGER, "info": theme.INFO,
        }.get(kind)
        self._status.setStyleSheet(f"color: {color};" if color else "")

    def set_busy(self, busy: bool):
        self._install_btn.setEnabled(not busy and self.selected_entry() is not None)
        self._remove_btn.setEnabled(not busy and self.selected_status() in ("installed", "update", "unknown"))
        self._progress.setVisible(busy)
        if busy:
            self._progress.setValue(0)

    def set_progress(self, pct: float):
        self._progress.setValue(int(max(0, min(100, pct))))

    # ------------------------------------------------------------------ helpers
    def selected_id(self) -> str:
        item = self._list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else ""

    def selected_entry(self):
        return self._entries.get(self.selected_id())

    def selected_status(self) -> str:
        return self._states.get(self.selected_id(), "")

    def _apply_filter(self, *args):
        term = self._search.text().strip().lower()
        category = self._category.currentText()
        for i in range(self._list.count()):
            item = self._list.item(i)
            entry = self._entries.get(item.data(Qt.ItemDataRole.UserRole))
            if not entry:
                continue
            matches_term = not term or term in entry.name.lower() or term in entry.description.lower()
            matches_cat = category in ("", "All categories") or entry.category == category
            item.setHidden(not (matches_term and matches_cat))

    def _on_selection_changed(self, *args):
        entry = self.selected_entry()
        if not entry:
            self._detail_name.setText("Select a mod to see details")
            self._detail_meta.clear()
            self._detail_status.clear()
            self._detail_desc.clear()
            self._detail_deps.clear()
            self._install_btn.setEnabled(False)
            self._remove_btn.setEnabled(False)
            return

        self._detail_name.setText(entry.name)
        bits = [f"v{entry.version}" if entry.version else "", entry.author, entry.category]
        self._detail_meta.setText("  ·  ".join(b for b in bits if b))
        state = self.selected_status()
        self._detail_status.setText(_STATE_LABEL.get(state, state))
        self._detail_status.setStyleSheet(f"color: {_STATE_STYLE.get(state, theme.TEXT_SECONDARY)}; font-weight: 600;")
        self._detail_desc.setText(entry.description or "No description provided.")

        deps = []
        if entry.dependencies:
            deps.append("Requires: " + ", ".join(entry.dependencies))
        if entry.incompatibilities:
            deps.append("Conflicts with: " + ", ".join(entry.incompatibilities))
        if entry.game_version:
            deps.append(f"Game version: {entry.game_version}")
        self._detail_deps.setText("\n".join(deps))

        self._install_btn.setText("Update" if state == "update" else "Install")
        self._install_btn.setEnabled(True)
        self._remove_btn.setEnabled(state in ("installed", "update", "unknown"))

    def _on_install(self):
        entry = self.selected_entry()
        if entry:
            self.install_requested.emit(entry)

    def _on_remove(self):
        entry = self.selected_entry()
        if entry:
            self.remove_requested.emit(entry)
