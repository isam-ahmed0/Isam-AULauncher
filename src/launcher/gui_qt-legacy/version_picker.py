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
    version_selected = Signal(str)
    retry_requested = Signal(object)  # emits callback(versions, error)

    def __init__(self, releases, current_version="", latest_version="",
                 error_message=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Choose Version")
        self.setMinimumSize(420, 500)
        self.resize(420, 500)
        self._releases = releases
        self._current_version = current_version
        self._latest_version = latest_version
        self._error_message = error_message
        self._selected_tag = latest_version or (releases[0].version if releases else "")
        self._rows = []
        self._version_list_layout = None
        self._count_label = None
        self._empty_label = None
        self._setup_ui()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # Header with refresh button
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 16, 20, 8)
        title = QLabel("Choose Version")
        title.setObjectName("sectionTitle")
        header_layout.addWidget(title)
        header_layout.addStretch()

        self._refresh_btn = QPushButton("Refresh")
        self._refresh_btn.setObjectName("toolBtn")
        self._refresh_btn.setFixedHeight(30)
        self._refresh_btn.clicked.connect(self._on_refresh)
        header_layout.addWidget(self._refresh_btn)
        outer.addWidget(header)

        # Version count / error
        self._count_label = QLabel("")
        self._count_label.setObjectName("mutedText")
        self._count_label.setContentsMargins(20, 0, 20, 8)
        outer.addWidget(self._count_label)
        self._update_count_label()

        # Scrollable version list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        list_widget = QWidget()
        self._version_list_layout = QVBoxLayout(list_widget)
        self._version_list_layout.setContentsMargins(12, 0, 12, 0)
        self._version_list_layout.setSpacing(4)

        self._populate_list()

        self._version_list_layout.addStretch()
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
        self._download_btn.setEnabled(bool(self._selected_tag and self._releases))
        self._download_btn.clicked.connect(self._on_download)
        btn_layout.addWidget(self._download_btn)

        outer.addWidget(btn_row)

    def _update_count_label(self):
        if self._error_message:
            self._count_label.setText(self._error_message)
            self._count_label.setStyleSheet(f"color: {theme.DANGER};")
        elif self._releases:
            self._count_label.setText(f"{len(self._releases)} versions available")
            self._count_label.setStyleSheet("")
        else:
            self._count_label.setText("No versions found")
            self._count_label.setStyleSheet("")

    def _populate_list(self):
        # Clear existing rows
        while self._version_list_layout.count():
            item = self._version_list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._rows.clear()

        if self._releases:
            for release in self._releases:
                tag = release.version
                is_latest = tag == self._latest_version
                is_installed = tag == self._current_version
                is_selected = tag == self._selected_tag
                row = _VersionRow(tag, is_latest, is_installed, is_selected)
                row.clicked.connect(self._on_row_clicked)
                self._version_list_layout.addWidget(row)
                self._rows.append(row)
        else:
            # Empty state with retry button
            self._empty_label = QLabel(
                self._error_message or "No game versions found."
            )
            self._empty_label.setObjectName("mutedText")
            self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._empty_label.setWordWrap(True)
            self._version_list_layout.addWidget(self._empty_label)

            retry_btn = QPushButton("Try Again")
            retry_btn.setObjectName("toolBtn")
            retry_btn.setFixedHeight(34)
            retry_btn.clicked.connect(self._on_refresh)
            self._version_list_layout.addWidget(retry_btn)

    def _on_row_clicked(self, tag: str):
        self._selected_tag = tag
        for row in self._rows:
            row.set_selected(row._tag == tag)
        self._download_btn.setEnabled(True)

    def _on_download(self):
        if self._selected_tag:
            self.version_selected.emit(self._selected_tag)
            self.accept()

    def _on_refresh(self):
        self._refresh_btn.setEnabled(False)
        self._refresh_btn.setText("Loading...")
        self.retry_requested.emit(self._on_refresh_done)

    def _on_refresh_done(self, versions, error):
        self._releases = versions
        self._error_message = error
        self._selected_tag = self._latest_version or (versions[0].version if versions else "")
        self._update_count_label()
        self._populate_list()
        self._download_btn.setEnabled(bool(self._selected_tag and self._releases))
        self._refresh_btn.setEnabled(True)
        self._refresh_btn.setText("Refresh")
