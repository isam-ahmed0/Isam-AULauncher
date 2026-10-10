"""Pack Info / Edit dialog — edits a pack's pack.json metadata."""
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit,
    QPlainTextEdit, QPushButton, QFrame, QFileDialog,
)

import gui_qt.theme as theme
from .models import PackMetadata


class PackInfoDialog(QDialog):
    def __init__(self, pack_name: str, meta: Optional[PackMetadata],
                 pack_path: Optional[Path] = None, parent=None):
        super().__init__(parent)
        self._pack_name = pack_name
        self._pack_path = pack_path

        meta = meta or PackMetadata(name=pack_name)
        if not meta.name:
            meta.name = pack_name

        self.setWindowTitle(f"Pack Info — {pack_name}")
        self.setMinimumWidth(460)
        self.setObjectName("packInfoDialog")
        self.setStyleSheet(f"""
            #packInfoDialog {{
                background-color: {theme.BG_SURFACE};
                border: 1px solid {theme.BORDER_SUBTLE};
                border-radius: 10px;
            }}
            QLabel {{ background: transparent; }}
            QLineEdit, QPlainTextEdit {{
                background-color: {theme.BG_ELEVATED};
                border: 1px solid {theme.BORDER_SUBTLE};
                border-radius: 6px;
                padding: 6px 8px;
                color: {theme.TEXT_PRIMARY};
                font-size: 13px;
            }}
            QLineEdit:focus, QPlainTextEdit:focus {{
                border-color: {theme.ACCENT};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        header = QLabel(f"Pack: {pack_name}")
        header.setStyleSheet(f"color: {theme.TEXT_BRIGHT}; font-size: 15px; font-weight: 700;")
        layout.addWidget(header)

        folder_lbl = QLabel(f"Folder: {pack_path}" if pack_path else "Folder: (unknown)")
        folder_lbl.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 11px;")
        folder_lbl.setWordWrap(True)
        layout.addWidget(folder_lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background-color: {theme.BORDER_SUBTLE}; max-height: 1px;")
        layout.addWidget(sep)

        form = QFormLayout()
        form.setSpacing(8)

        self._name_edit = QLineEdit(meta.name)
        form.addRow(self._lbl("Display name"), self._name_edit)

        self._author_edit = QLineEdit(meta.author)
        form.addRow(self._lbl("Author"), self._author_edit)

        self._version_edit = QLineEdit(meta.version)
        form.addRow(self._lbl("Version"), self._version_edit)

        thumb_row = QHBoxLayout()
        self._thumb_edit = QLineEdit(meta.thumbnail or "")
        self._thumb_edit.setPlaceholderText("Path or URL (optional)")
        thumb_row.addWidget(self._thumb_edit, 1)
        browse_btn = QPushButton("Browse")
        browse_btn.setObjectName("toolBtn")
        browse_btn.setFixedHeight(30)
        browse_btn.clicked.connect(self._cb_browse_thumb)
        thumb_row.addWidget(browse_btn)
        form.addRow(self._lbl("Thumbnail"), thumb_row)

        self._desc_edit = QPlainTextEdit(meta.description or "")
        self._desc_edit.setFixedHeight(96)
        form.addRow(self._lbl("Description"), self._desc_edit)

        layout.addLayout(form)

        self._preview = QLabel()
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setFixedHeight(1)
        layout.addWidget(self._preview)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("toolBtn")
        cancel_btn.setFixedHeight(34)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        save_btn = QPushButton("Save")
        save_btn.setObjectName("successBtn")
        save_btn.setFixedHeight(34)
        save_btn.clicked.connect(self.accept)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    @staticmethod
    def _lbl(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 12px; font-weight: 600;")
        return lbl

    def _cb_browse_thumb(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose Thumbnail", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp);;All Files (*)",
        )
        if path:
            self._thumb_edit.setText(path)
            self._show_preview(path)

    def _show_preview(self, path: str):
        pm = QPixmap(path)
        if pm.isNull():
            self._preview.setFixedHeight(1)
            return
        self._preview.setPixmap(pm.scaledToHeight(
            120, Qt.TransformationMode.SmoothTransformation))
        self._preview.setFixedHeight(124)

    def result_metadata(self) -> PackMetadata:
        return PackMetadata(
            name=self._name_edit.text().strip() or self._pack_name,
            author=self._author_edit.text().strip(),
            description=self._desc_edit.toPlainText().strip(),
            version=self._version_edit.text().strip() or "1.0.0",
            thumbnail=self._thumb_edit.text().strip() or None,
            created_at=None,
        )
