"""Version Picker — dialog for selecting a game version to install."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QWidget, QScrollArea, QSizePolicy,
)
import gui_qt.theme as theme


class _VersionRow(QFrame):
    """Clickable row representing a single game version."""
    clicked = Signal(str)

    def __init__(self, tag: str, is_latest: bool = False, is_installed: bool = False,
                 is_selected: bool = False, parent=None):
        super().__init__(parent)
        self._tag = tag
        self._is_latest = is_latest
        self._is_installed = is_installed
        self._selected = is_selected

        self.setFixedHeight(44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style()

    def set_selected(self, val: bool):
        self._selected = val
        self._update_style()

    def _update_style(self):
        if self._selected:
            border = theme.ACCENT
            bg = theme.BG_HOVER
        else:
            border = "transparent"
            bg = "transparent"
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 6px;
            }}
            QFrame:hover {{
                background-color: {theme.BG_HOVER};
                border: 1px solid {theme.BORDER_SUBTLE};
            }}
        """)

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter
        from PySide6.QtCore import Qt as Qt2
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Version tag
        p.setPen(QColor(theme.TEXT_BRIGHT))
        f = QFont("Segoe UI", 13)
        f.setBold(True)
        p.setFont(f)
        p.drawText(16, 0, w - 100, h, Qt2.AlignmentFlag.AlignVCenter, self._tag)

        # Badges
        badge_x = w - 16
        if self._is_installed:
            badge_text = "Installed"
            badge_bg = theme.SUCCESS
            badge_fg = theme.TEXT_BRIGHT
            badge_x -= self._draw_badge(p, badge_x, h, badge_text, badge_bg, badge_fg)
        if self._is_latest:
            badge_text = "Latest"
            badge_bg = theme.ACCENT
            badge_fg = theme.TEXT_BRIGHT
            badge_x -= self._draw_badge(p, badge_x, h, badge_text, badge_bg, badge_fg)

        p.end()

    def _draw_badge(self, p, x, h, text, bg, fg):
        from PySide6.QtGui import QFontMetrics
        f = QFont("Segoe UI", 10)
        f.setBold(True)
        p.setFont(f)
        fm = QFontMetrics(f)
        tw = fm.horizontalAdvance(text) + 14
        bx = x - tw
        by = (h - 20) // 2
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(bg))
        p.drawRoundedRect(bx, by, tw, 20, 10, 10)
        p.setPen(QColor(fg))
        p.drawText(bx, by, tw, 20, Qt.AlignmentFlag.AlignCenter, text)
        return tw + 6

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._tag)
        super().mousePressEvent(event)


class VersionPickerDialog(QDialog):
    """Version picker dialog for selecting a game version."""
    version_selected = Signal(str)  # emitted with selected version tag

    def __init__(self, releases, current_version="", latest_version="",
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle("Choose Version")
        self.setMinimumSize(420, 500)
        self.resize(420, 500)
        self._releases = releases  # list of GameVersion objects
        self._current_version = current_version
        self._latest_version = latest_version
        self._selected_tag = latest_version or (releases[0].version if releases else "")
        self._rows = []
        self._setup_ui()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # Header
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 16, 20, 8)
        title = QLabel("Choose Version")
        title.setObjectName("sectionTitle")
        header_layout.addWidget(title)
        header_layout.addStretch()
        outer.addWidget(header)

        # Version count
        count_label = QLabel(f"{len(self._releases)} versions available")
        count_label.setObjectName("mutedText")
        count_label.setContentsMargins(20, 0, 20, 8)
        outer.addWidget(count_label)

        # Scrollable version list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        list_widget = QWidget()
        list_layout = QVBoxLayout(list_widget)
        list_layout.setContentsMargins(12, 0, 12, 0)
        list_layout.setSpacing(4)

        for release in self._releases:
            tag = release.version
            is_latest = tag == self._latest_version
            is_installed = tag == self._current_version
            is_selected = tag == self._selected_tag
            row = _VersionRow(tag, is_latest, is_installed, is_selected)
            row.clicked.connect(self._on_row_clicked)
            list_layout.addWidget(row)
            self._rows.append(row)

        list_layout.addStretch()
        scroll.setWidget(list_widget)

        # Buttons
        btn_row = QWidget()
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(20, 12, 20, 16)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("toolBtn")
        cancel_btn.setFixedHeight(38)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        btn_layout.addStretch()

        self._download_btn = QPushButton("Download")
        self._download_btn.setObjectName("successBtn")
        self._download_btn.setFixedHeight(38)
        self._download_btn.setEnabled(bool(self._selected_tag))
        self._download_btn.clicked.connect(self._on_download)
        btn_layout.addWidget(self._download_btn)

        outer.addWidget(btn_row)

    def _on_row_clicked(self, tag: str):
        self._selected_tag = tag
        for row in self._rows:
            row.set_selected(row._tag == tag)
        self._download_btn.setEnabled(True)

    def _on_download(self):
        if self._selected_tag:
            self.version_selected.emit(self._selected_tag)
            self.accept()
