"""
Mod Warning Dialog — shows pre-launch warnings for mod conflicts.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QPushButton, QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

import gui_qt.theme as theme

_KIND_STYLES = lambda: {
    "duplicate":   theme.DANGER,
    "missing_dep": "#f59e0b",
    "conflict":    "#f59e0b",
}


class ModWarningDialog(QDialog):
    def __init__(self, issues, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mod Warnings Detected")
        self.setFixedSize(520, 400)
        self.setObjectName("modWarningDialog")
        self.setStyleSheet(f"""
            #modWarningDialog {{
                background-color: {theme.BG_SURFACE};
                border: 1px solid {theme.BORDER_SUBTLE};
                border-radius: 10px;
            }}
            QLabel {{
                background: transparent;
            }}
            QListWidget {{
                background-color: {theme.BG_ELEVATED};
                border: 1px solid {theme.BORDER_SUBTLE};
                border-radius: 6px;
                padding: 4px;
                font-size: 12px;
            }}
            QListWidget::item {{
                padding: 8px 10px;
                border-bottom: 1px solid {theme.BORDER_SUBTLE};
                color: {theme.TEXT_PRIMARY};
            }}
            QListWidget::item:last {{
                border-bottom: none;
            }}
            QListWidget::item:selected {{
                background-color: {theme.BG_BASE};
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
        header.setStyleSheet(f"color: {theme.DANGER};")
        layout.addWidget(header)

        # Subtext
        sub = QLabel(
            "We found potential issues with your active mod profile. "
            "The game may crash or behave unexpectedly."
        )
        sub.setWordWrap(True)
        sub.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 12px;")
        layout.addWidget(sub)

        # Issue list
        issue_list = QListWidget()
        issue_list.setAlternatingRowColors(False)
        for issue in issues:
            color = _KIND_STYLES().get(issue.kind, theme.TEXT_SECONDARY)
            tag = issue.kind.upper().replace("_", " ")
            item = QListWidgetItem(f"  {tag}   {issue.description}")
            item.setForeground(Qt.GlobalColor.white)
            issue_list.addItem(item)
        layout.addWidget(issue_list, 1)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background-color: {theme.BORDER_SUBTLE}; max-height: 1px;")
        layout.addWidget(sep)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("modalSecondary")
        cancel_btn.setFixedHeight(36)
        cancel_btn.setMinimumWidth(120)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        launch_btn = QPushButton("Launch Anyway")
        launch_btn.setObjectName("modalDanger")
        launch_btn.setFixedHeight(36)
        launch_btn.setMinimumWidth(140)
        launch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        launch_btn.clicked.connect(self.accept)
        btn_row.addWidget(launch_btn)

        layout.addLayout(btn_row)
