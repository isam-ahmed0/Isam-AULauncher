"""
ModStore — Thunderstore API integration and mod store page widget.
Fetches Among Us mods from thunderstore.io, displays them in a browsable
grid, and handles installation into BepInEx/plugins.
"""
import logging
import json
import zipfile
import tempfile
from pathlib import Path

import requests
from PySide6.QtCore import Qt, QThread, Signal, QObject
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QLineEdit, QGridLayout, QDialog,
    QTextBrowser, QMessageBox, QSizePolicy,
)
from PySide6.QtGui import QFont, QPixmap

from gui_qt.theme import (
    BG_BASE, BG_SURFACE, BG_ELEVATED, ACCENT, ACCENT_2,
    SUCCESS, DANGER, WARNING, TEXT_BRIGHT, TEXT_PRIMARY,
    TEXT_SECONDARY, TEXT_MUTED, BORDER_SUBTLE,
)

log = logging.getLogger(__name__)

THUNDERSTORE_API = "https://thunderstore.io/c/among-us/api/v1/package/"
THUNDERSTORE_CDN = "https://gcdn.thunderstore.io/community/"

RISK_COLORS = {
    "safe": SUCCESS,
    "warning": WARNING,
    "danger": DANGER,
}


# ---------------------------------------------------------------------------
# API layer
# ---------------------------------------------------------------------------
class ModStore(QObject):
    """Fetches mod data from Thunderstore. No local state."""

    mods_fetched = Signal(list)
    error = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._session = requests.Session()
        self._session.headers["Accept"] = "application/json"

    def fetch_mods(self):
        """Fetch all Among Us mods in a background thread."""
        def _do():
            try:
                r = self._session.get(THUNDERSTORE_API, timeout=20)
                r.raise_for_status()
                raw = r.json()
                mods = []
                for pkg in raw:
                    latest = pkg.get("versions", [{}])
                    latest = latest[0] if latest else {}
                    mods.append({
                        "uuid": pkg.get("uuid4", ""),
                        "name": pkg.get("name", "Unknown"),
                        "author": pkg.get("owner", "Unknown"),
                        "description": pkg.get("description", ""),
                        "icon": pkg.get("icon", ""),
                        "downloads": pkg.get("downloads", 0),
                        "rating": pkg.get("rating_score", 0),
                        "version": latest.get("version_number", ""),
                        "download_url": latest.get("download_url", ""),
                        "dependencies": latest.get("dependencies", []),
                        "date_updated": pkg.get("date_updated", ""),
                        "categories": pkg.get("categories", []),
                    })
                self.mods_fetched.emit(mods)
            except Exception as e:
                log.error(f"Failed to fetch mods: {e}")
                self.error.emit(str(e))

        t = QThread(target=_do)
        t.start()

    def install_mod(self, mod: dict, game_path: Path) -> bool:
        """Download and install a mod into BepInEx/plugins."""
        url = mod.get("download_url")
        if not url:
            return False

        plugins_dir = game_path / "BepInEx" / "plugins"
        plugins_dir.mkdir(parents=True, exist_ok=True)

        try:
            r = self._session.get(url, timeout=60, stream=True)
            r.raise_for_status()

            tmp = Path(tempfile.mktemp(suffix=".zip"))
            with open(tmp, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

            # Extract zip into plugins dir
            with zipfile.ZipFile(tmp, "r") as zf:
                zf.extractall(plugins_dir)

            tmp.unlink(missing_ok=True)
            return True
        except Exception as e:
            log.error(f"Failed to install mod {mod['name']}: {e}")
            return False


# ---------------------------------------------------------------------------
# Mod detail popup
# ---------------------------------------------------------------------------
class ModDetailDialog(QDialog):
    """Shows full mod details with an install button."""

    def __init__(self, mod: dict, game_path: Path, mod_store: ModStore, parent=None):
        super().__init__(parent)
        self.mod = mod
        self.game_path = game_path
        self.mod_store = mod_store
        self.setWindowTitle(mod["name"])
        self.setMinimumSize(500, 400)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        header.setSpacing(12)

        icon_label = QLabel()
        icon_label.setFixedSize(48, 48)
        icon_label.setStyleSheet("background-color: transparent;")
        if mod.get("icon"):
            try:
                r = requests.get(mod["icon"], timeout=10)
                if r.status_code == 200:
                    pix = QPixmap()
                    pix.loadFromData(r.content)
                    icon_label.setPixmap(pix.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio,
                                                     Qt.TransformationMode.SmoothTransformation))
            except Exception:
                pass
        header.addWidget(icon_label)

        info = QVBoxLayout()
        name_lbl = QLabel(mod["name"])
        name_lbl.setObjectName("profileName")
        info.addWidget(name_lbl)

        author_lbl = QLabel(f"by {mod['author']}")
        author_lbl.setStyleSheet(f"color: {TEXT_MUTED};")
        info.addWidget(author_lbl)
        header.addLayout(info)
        header.addStretch()
        layout.addLayout(header)

        # Stats row
        stats = QHBoxLayout()
        stats.setSpacing(16)
        for text in [
            f"Downloads: {mod['downloads']:,}",
            f"Rating: {mod['rating']}",
            f"Version: {mod['version']}",
        ]:
            lbl = QLabel(text)
            lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
            stats.addWidget(lbl)

        risk = mod.get("risk_level", "safe")
        risk_lbl = QLabel(risk.upper())
        risk_lbl.setStyleSheet(
            f"color: {RISK_COLORS.get(risk, TEXT_MUTED)}; font-size: 11px; font-weight: bold;"
        )
        stats.addWidget(risk_lbl)
        stats.addStretch()
        layout.addLayout(stats)

        layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine))

        # Description
        desc = QTextBrowser()
        desc.setOpenExternalLinks(True)
        desc.setHtml(f"<p style='color: {TEXT_PRIMARY}; font-size: 13px;'>{mod['description']}</p>")
        desc.setStyleSheet(f"background-color: transparent; border: none;")
        layout.addWidget(desc)

        # Install button
        self.install_btn = QPushButton("INSTALL MOD")
        self.install_btn.setObjectName("successBtn")
        self.install_btn.setFixedHeight(44)
        self.install_btn.clicked.connect(self._install)
        layout.addWidget(self.install_btn)

    def _install(self):
        if not self.game_path or not self.game_path.exists():
            QMessageBox.warning(self, "Error", "Game not installed!")
            return
        self.install_btn.setEnabled(False)
        self.install_btn.setText("Installing...")

        def go():
            ok = self.mod_store.install_mod(self.mod, self.game_path)
            if ok:
                self.install_btn.setText("INSTALLED")
                self.install_btn.setStyleSheet(f"background-color: {SUCCESS};")
            else:
                self.install_btn.setText("FAILED")
                self.install_btn.setStyleSheet(f"background-color: {DANGER};")
                self.install_btn.setEnabled(True)

        t = QThread(target=go)
        t.start()


# ---------------------------------------------------------------------------
# Mod card widget
# ---------------------------------------------------------------------------
class ModCard(QFrame):
    """Clickable card showing a single mod."""

    clicked = Signal(dict)

    def __init__(self, mod: dict, parent=None):
        super().__init__(parent)
        self.mod = mod
        self.setObjectName("modCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(100)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # Icon
        icon = QLabel()
        icon.setFixedSize(40, 40)
        icon.setStyleSheet("background-color: transparent;")
        if mod.get("icon"):
            try:
                r = requests.get(mod["icon"], timeout=5)
                if r.status_code == 200:
                    pix = QPixmap()
                    pix.loadFromData(r.content)
                    icon.setPixmap(pix.scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio,
                                               Qt.TransformationMode.SmoothTransformation))
            except Exception:
                pass
        layout.addWidget(icon)

        # Info
        info = QVBoxLayout()
        info.setSpacing(2)

        name = QLabel(mod["name"])
        name.setStyleSheet(f"color: {TEXT_BRIGHT}; font-size: 14px; font-weight: bold; background: transparent;")
        info.addWidget(name)

        author = QLabel(f"by {mod['author']}")
        author.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; background: transparent;")
        info.addWidget(author)

        desc = QLabel(mod["description"][:80] + ("..." if len(mod["description"]) > 80 else ""))
        desc.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px; background: transparent;")
        info.addWidget(desc)
        layout.addLayout(info, 1)

        # Stats
        stats = QVBoxLayout()
        stats.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        stats.setSpacing(4)

        dl = QLabel(f"{mod['downloads']:,}")
        dl.setStyleSheet(f"color: {ACCENT}; font-size: 12px; font-weight: bold; background: transparent;")
        dl.setAlignment(Qt.AlignmentFlag.AlignRight)
        stats.addWidget(dl)

        dl_label = QLabel("downloads")
        dl_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px; background: transparent;")
        dl_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        stats.addWidget(dl_label)

        layout.addLayout(stats)

    def mousePressEvent(self, event):
        self.clicked.emit(self.mod)
        super().mousePressEvent(event)


# ---------------------------------------------------------------------------
# Full mod store page
# ---------------------------------------------------------------------------
class ModStorePage(QWidget):
    """Browsable mod store with search and grid layout."""

    def __init__(self, mod_store: ModStore, config, parent=None):
        super().__init__(parent)
        self.mod_store = mod_store
        self.config = config
        self._all_mods = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header bar
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(28, 16, 28, 8)

        title = QLabel("MOD STORE")
        title.setStyleSheet(f"color: {TEXT_BRIGHT}; font-size: 16px; font-weight: bold; background: transparent;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setObjectName("toolBtn")
        self.refresh_btn.setFixedHeight(32)
        self.refresh_btn.clicked.connect(self._load_mods)
        header_layout.addWidget(self.refresh_btn)
        layout.addWidget(header)

        # Search bar
        search_widget = QWidget()
        search_layout = QHBoxLayout(search_widget)
        search_layout.setContentsMargins(28, 0, 28, 8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search mods...")
        self.search_input.setFixedHeight(36)
        self.search_input.textChanged.connect(self._filter_mods)
        search_layout.addWidget(self.search_input)
        layout.addWidget(search_widget)

        # Scroll area with mod grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.mods_container = QWidget()
        self.mods_grid = QGridLayout(self.mods_container)
        self.mods_grid.setContentsMargins(28, 8, 28, 28)
        self.mods_grid.setSpacing(12)
        scroll.setWidget(self.mods_container)
        layout.addWidget(scroll, 1)

        # Loading label
        self.loading_label = QLabel("Loading mods...")
        self.loading_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 14px;")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mods_grid.addWidget(self.loading_label, 0, 0, 1, 3)

        # Connect API signals
        self.mod_store.mods_fetched.connect(self._on_mods_loaded)
        self.mod_store.error.connect(self._on_error)

    def _load_mods(self):
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("Loading...")
        self.loading_label.show()
        self.loading_label.setText("Loading mods...")
        self.mod_store.fetch_mods()

    def _on_mods_loaded(self, mods: list):
        self._all_mods = mods
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("Refresh")
        self._populate_grid(mods)

    def _on_error(self, msg: str):
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("Refresh")
        self.loading_label.setText(f"Failed to load mods: {msg}")

    def _populate_grid(self, mods: list):
        # Clear existing cards
        while self.mods_grid.count():
            item = self.mods_grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not mods:
            self.loading_label.setText("No mods found.")
            self.loading_label.show()
            self.mods_grid.addWidget(self.loading_label, 0, 0, 1, 3)
            return

        self.loading_label.hide()
        cols = 2
        for i, mod in enumerate(mods):
            card = ModCard(mod)
            card.clicked.connect(self._show_detail)
            row, col = divmod(i, cols)
            self.mods_grid.addWidget(card, row, col)

    def _filter_mods(self, text: str):
        text = text.lower().strip()
        if not text:
            self._populate_grid(self._all_mods)
            return
        filtered = [
            m for m in self._all_mods
            if text in m["name"].lower() or text in m["author"].lower() or text in m["description"].lower()
        ]
        self._populate_grid(filtered)

    def _show_detail(self, mod: dict):
        gp = self.config.get_game_path()
        dialog = ModDetailDialog(mod, gp, self.mod_store, self.window())
        dialog.exec()
