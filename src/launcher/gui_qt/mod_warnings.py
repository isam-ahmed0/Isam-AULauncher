"""
Mod Warning Dialog — shows pre-launch warnings for mod conflicts.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QPushButton, QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from .theme import (
    BG_BASE, BG_SURFACE, BG_ELEVATED, BORDER_SUBTLE,
    ACCENT, ACCENT_2, DANGER, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_BRIGHT,
)

_KIND_STYLES = {
    "duplicate":   DANGER,
    "missing_dep": "#f59e0b",
    "conflict":    "#f59e0b",
}


class ModWarningDialog(QDialog):
    def __init__(self, issues, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mod Warnings Detected")
        self.setMinimumSize(520, 380)
        self.setMaximumSize(620, 500)
        self.setObjectName("modWarningDialog")
        self.setStyleSheet(f"""
            #modWarningDialog {{
                background-color: {BG_SURFACE};
                border: 1px solid {BORDER_SUBTLE};
                border-radius: 10px;
            }}
            QLabel {{
                background: transparent;
            }}
            QListWidget {{
                background-color: {BG_ELEVATED};
                border: 1px solid {BORDER_SUBTLE};
                border-radius: 6px;
                padding: 4px;
                font-size: 12px;
            }}
            QListWidget::item {{
                padding: 8px 10px;
                border-bottom: 1px solid {BORDER_SUBTLE};
                color: {TEXT_PRIMARY};
            }}
            QListWidget::item:last {{
                border-bottom: none;
            }}
            QListWidget::item:selected {{
                background-color: {BG_BASE};
            }}
            QPushButton {{
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: 600;
                font-size: 13px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 18, 20, 18)

        # Header
        header = QLabel("Mod Warnings Detected")
        header.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {DANGER};")
        layout.addWidget(header)

        # Subtext
        sub = QLabel(
            "We found potential issues with your active mod profile. "
            "The game may crash or behave unexpectedly."
        )
        sub.setWordWrap(True)
        sub.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
        layout.addWidget(sub)

        # Issue list
        issue_list = QListWidget()
        issue_list.setAlternatingRowColors(False)
        for issue in issues:
            color = _KIND_STYLES.get(issue.kind, TEXT_SECONDARY)
            tag = issue.kind.upper().replace("_", " ")
            item = QListWidgetItem(f"  {tag}   {issue.description}")
            item.setForeground(Qt.GlobalColor.white)
            issue_list.addItem(item)
        layout.addWidget(issue_list, 1)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background-color: {BORDER_SUBTLE}; max-height: 1px;")
        layout.addWidget(sep)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumWidth(120)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {BG_ELEVATED};
                color: {TEXT_SECONDARY};
                border: 1px solid {BORDER_SUBTLE};
            }}
            QPushButton:hover {{
                background-color: {BG_BASE};
                color: {TEXT_PRIMARY};
            }}
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        launch_btn = QPushButton("Launch Anyway")
        launch_btn.setMinimumWidth(140)
        launch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        launch_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ACCENT_2};
                color: #000000;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: #10b981;
            }}
        """)
        launch_btn.clicked.connect(self.accept)
        btn_row.addWidget(launch_btn)

        layout.addLayout(btn_row)
