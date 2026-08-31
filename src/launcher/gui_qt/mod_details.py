"""
Mod Info Dialog — shows detailed info about a single mod DLL.
"""

import json
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QGridLayout, QTextBrowser, QListWidget, QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from mod_inspector import _read_dll_metadata
from .theme import (
    BG_SURFACE, BG_ELEVATED, BORDER_SUBTLE,
    ACCENT, ACCENT_2, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
)


class ModInfoDialog(QDialog):
    def __init__(self, dll_path: Path, profile_dir: Path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mod Info")
        self.setMinimumSize(460, 420)
        self.setMaximumSize(520, 520)
        self.setObjectName("modInfoDialog")
        self.setStyleSheet(f"""
            #modInfoDialog {{
                background-color: {BG_SURFACE};
                border: 1px solid {BORDER_SUBTLE};
                border-radius: 10px;
            }}
            QLabel {{ background: transparent; }}
            QGridLayout QLabel {{ font-size: 12px; }}
            QTextBrowser {{
                background-color: {BG_ELEVATED};
                border: 1px solid {BORDER_SUBTLE};
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
                color: {TEXT_PRIMARY};
            }}
            QListWidget {{
                background-color: {BG_ELEVATED};
                border: 1px solid {BORDER_SUBTLE};
                border-radius: 6px;
                padding: 4px;
                font-size: 12px;
            }}
            QListWidget::item {{
                padding: 4px 8px;
                color: {TEXT_PRIMARY};
            }}
        """)

        mod = _read_dll_metadata(dll_path)
        display_name = mod.name if mod.name else dll_path.stem
        file_size = self._format_size(dll_path.stat().st_size)
        last_modified = self._format_date(dll_path)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(18, 16, 18, 16)

        # Header: name + version
        name_label = QLabel(display_name)
        name_label.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        name_label.setStyleSheet(f"color: #ffffff;")
        layout.addWidget(name_label)

        # Version + size badge row
        badge_row = QHBoxLayout()
        badge_row.setSpacing(8)
        if mod.version:
            ver = QLabel(f"v{mod.version}")
            ver.setStyleSheet(f"""
                background-color: {ACCENT};
                color: #ffffff;
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: 600;
            """)
            badge_row.addWidget(ver)

        size_badge = QLabel(file_size)
        size_badge.setStyleSheet(f"""
            background-color: {BG_ELEVATED};
            color: {TEXT_SECONDARY};
            border: 1px solid {BORDER_SUBTLE};
            border-radius: 4px;
            padding: 2px 8px;
            font-size: 11px;
        """)
        badge_row.addWidget(size_badge)
        badge_row.addStretch()
        layout.addLayout(badge_row)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background-color: {BORDER_SUBTLE}; max-height: 1px;")
        layout.addWidget(sep)

        # Metadata grid
        grid = QGridLayout()
        grid.setSpacing(6)
        fields = [
            ("Filename", dll_path.name),
            ("Plugin GUID", mod.guid if mod.guid else "Not detected"),
            ("Last Modified", last_modified),
        ]
        for i, (label_text, value) in enumerate(fields):
            lbl = QLabel(label_text)
            lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; font-weight: 600;")
            val = QLabel(value)
            val.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 12px;")
            val.setWordWrap(True)
            grid.addWidget(lbl, i, 0)
            grid.addWidget(val, i, 1)
        layout.addLayout(grid)

        # Description (from sidecar JSON or fallback)
        desc_text = self._load_description(dll_path, profile_dir)
        desc_label = QLabel("Description")
        desc_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; font-weight: 600;")
        layout.addWidget(desc_label)

        desc_box = QTextBrowser()
        desc_box.setPlainText(desc_text)
        desc_box.setOpenExternalLinks(True)
        desc_box.setFixedHeight(80)
        layout.addWidget(desc_box)

        # Dependencies
        if mod.dependencies:
            dep_label = QLabel("Dependencies")
            dep_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; font-weight: 600;")
            layout.addWidget(dep_label)

            dep_list = QListWidget()
            for dep in mod.dependencies:
                dep_list.addItem(dep)
            dep_list.setFixedHeight(min(len(mod.dependencies) * 28 + 8, 100))
            layout.addWidget(dep_list)

        # Incompatibilities
        if mod.incompatibilities:
            inc_label = QLabel("Incompatibilities")
            inc_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; font-weight: 600;")
            layout.addWidget(inc_label)

            inc_list = QListWidget()
            for inc in mod.incompatibilities:
                inc_list.addItem(inc)
            inc_list.setFixedHeight(min(len(mod.incompatibilities) * 28 + 8, 80))
            layout.addWidget(inc_list)

        layout.addStretch()

    @staticmethod
    def _load_description(dll_path: Path, profile_dir: Path) -> str:
        for name in ("info.json", "manifest.json"):
            sidecar = profile_dir / name
            if sidecar.exists():
                try:
                    data = json.loads(sidecar.read_text(encoding="utf-8", errors="replace"))
                    if isinstance(data, dict):
                        for key in ("description", "desc", "summary"):
                            if key in data and data[key]:
                                return str(data[key])
                except Exception:
                    pass
        return "No description available."

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"

    @staticmethod
    def _format_date(path: Path) -> str:
        import datetime
        try:
            ts = path.stat().st_mtime
            return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
        except Exception:
            return "Unknown"
