"""Real-time BepInEx log viewer with filtering and auto-scroll."""
import logging
import re
import time
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QFileSystemWatcher, Signal
from PySide6.QtGui import QTextCursor, QColor, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QLineEdit, QLabel, QFrame, QButtonGroup,
)

import gui_qt.theme as theme

log = logging.getLogger(__name__)

LEVEL_COLORS = {
    "Error": theme.DANGER,
    "Warning": theme.WARNING,
    "Message": theme.INFO,
    "Info": theme.TEXT_SECONDARY,
}

FILTER_TAGS = ["All", "AUAS", "AUAS-PICK", "AUAS-DUMP", "Errors"]
AUAS_PATTERNS = {
    "AUAS": re.compile(r"\[AUAS\]"),
    "AUAS-PICK": re.compile(r"\[AUAS-PICK\]"),
    "AUAS-DUMP": re.compile(r"\[AUAS-DUMP\]"),
}


class LogViewer(QWidget):
    def __init__(self, game_path_getter, parent=None):
        super().__init__(parent)
        self._game_path_getter = game_path_getter
        self._current_filter = "All"
        self._auto_scroll = True
        self._last_pos = 0
        self._watched_dir = None
        self._build_ui()
        self._setup_watcher()
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_log)
        self._poll_timer.start(500)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        self._filter_btns = {}
        self._btn_group = QButtonGroup(self)
        self._btn_group.setExclusive(True)
        for i, tag in enumerate(FILTER_TAGS):
            btn = QPushButton(tag)
            btn.setObjectName("toolBtn")
            btn.setCheckable(True)
            btn.setFixedHeight(28)
            if tag == "All":
                btn.setChecked(True)
            btn.clicked.connect(lambda checked, t=tag: self._set_filter(t))
            self._btn_group.addButton(btn, i)
            toolbar.addWidget(btn)
            self._filter_btns[tag] = btn

        toolbar.addStretch()

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search logs...")
        self._search.setFixedHeight(28)
        self._search.setMaximumWidth(200)
        self._search.textChanged.connect(self._apply_text_filter)
        toolbar.addWidget(self._search)

        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("toolBtn")
        clear_btn.setFixedHeight(28)
        clear_btn.clicked.connect(self._clear_log)
        toolbar.addWidget(clear_btn)

        layout.addLayout(toolbar)

        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setFont(QFont("Consolas, monospace", 9))
        self._text.verticalScrollBar().valueChanged.connect(self._on_scroll)
        layout.addWidget(self._text)

    def _setup_watcher(self):
        self._watcher = QFileSystemWatcher()
        self._watcher.directoryChanged.connect(self._on_dir_changed)

    def _update_watcher(self):
        gp = self._game_path_getter()
        if not gp:
            return
        bepinex = gp / "BepInEx"
        if bepinex.exists() and str(bepinex) != self._watched_dir:
            if self._watched_dir:
                self._watcher.removePath(self._watched_dir)
            self._watcher.addPath(str(bepinex))
            self._watched_dir = str(bepinex)

    def _on_dir_changed(self, path):
        self._poll_log()

    def _poll_log(self):
        gp = self._game_path_getter()
        if not gp:
            return
        self._update_watcher()
        bepinex = gp / "BepInEx"
        log_file = bepinex / "LogOutput.log"
        if not log_file.exists():
            return
        try:
            size = log_file.stat().st_size
            if size <= self._last_pos:
                return
            with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                f.seek(self._last_pos)
                new_lines = f.read()
                self._last_pos = f.tell()
            if new_lines:
                self._append_lines(new_lines)
        except Exception:
            pass

    def _append_lines(self, text):
        for line in text.splitlines():
            if not line.strip():
                continue
            if not self._matches_filter(line):
                continue
            search = self._search.text().strip().lower()
            if search and search not in line.lower():
                continue
            colored = self._colorize(line)
            self._text.append(colored)
        if self._auto_scroll:
            cursor = self._text.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self._text.setTextCursor(cursor)

    def _colorize(self, line: str) -> str:
        for level, color in LEVEL_COLORS.items():
            if f"[{level}" in line:
                return f'<span style="color:{color}">{self._escape(line)}</span>'
        if "[AUAS" in line:
            return f'<span style="color:{theme.INFO}">{self._escape(line)}</span>'
        return f'<span style="color:{theme.TEXT_PRIMARY}">{self._escape(line)}</span>'

    def _escape(self, text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def _matches_filter(self, line: str) -> bool:
        if self._current_filter == "All":
            return True
        if self._current_filter == "Errors":
            return "[Error" in line or "[Warning" in line
        pattern = AUAS_PATTERNS.get(self._current_filter)
        return bool(pattern and pattern.search(line))

    def _set_filter(self, tag: str):
        self._current_filter = tag
        self._rebuild_display()

    def _apply_text_filter(self):
        self._rebuild_display()

    def _rebuild_display(self):
        gp = self._game_path_getter()
        if not gp:
            return
        log_file = gp / "BepInEx" / "LogOutput.log"
        if not log_file.exists():
            return
        try:
            text = log_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return
        self._text.clear()
        self._last_pos = 0
        self._append_lines(text)
        self._last_pos = log_file.stat().st_size

    def _on_scroll(self, value):
        max_val = self._text.verticalScrollBar().maximum()
        self._auto_scroll = (value >= max_val - 5)

    def _clear_log(self):
        self._text.clear()

    def start(self):
        self._last_pos = 0
        self._rebuild_display()

    def stop(self):
        self._poll_timer.stop()
