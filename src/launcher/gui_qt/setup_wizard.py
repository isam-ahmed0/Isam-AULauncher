"""First-run Linux setup wizard (PySide6).

Walks the user through picking a GPU and a Wine build, then saves the choice.
Shown once on first Linux launch (and re-openable from Settings).
"""
import subprocess
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QComboBox,
    QPushButton, QStackedWidget, QWidget, QFileDialog, QMessageBox,
)

import gui_qt.theme as theme
import graphics


def _hline():
    return QFrame(frameShape=QFrame.Shape.HLine)


class SetupWizard(QDialog):
    """Modal setup wizard for Linux GPU + Wine selection."""

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("CrewLauncher Setup")
        self.setModal(True)
        self.setMinimumWidth(520)

        self._gpus = graphics.detect_gpus()
        self._wines = graphics.detect_wine_binaries()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 22, 28, 22)
        outer.setSpacing(12)

        title = QLabel("Finish setting up CrewLauncher")
        title.setObjectName("sectionTitle")
        outer.addWidget(title)
        outer.addWidget(_hline())

        self.stack = QStackedWidget()
        self.stack.addWidget(self._page_welcome())
        self.stack.addWidget(self._page_gpu())
        self.stack.addWidget(self._page_wine())
        self.stack.addWidget(self._page_summary())
        outer.addWidget(self.stack, 1)

        outer.addWidget(_hline())
        nav = QHBoxLayout()
        self.back_btn = QPushButton("Back")
        self.back_btn.setObjectName("smallBtn")
        self.back_btn.clicked.connect(self._back)
        nav.addWidget(self.back_btn)
        nav.addStretch()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("smallBtn")
        self.cancel_btn.clicked.connect(self.reject)
        nav.addWidget(self.cancel_btn)
        self.next_btn = QPushButton("Next")
        self.next_btn.setObjectName("toolBtn")
        self.next_btn.clicked.connect(self._next)
        nav.addWidget(self.next_btn)
        outer.addLayout(nav)

        self._update_nav()

    # ------------------------------------------------------------------ pages
    def _page_welcome(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 6, 0, 6)
        text = QLabel(
            "This wizard picks the GPU and Wine build Among Us runs with.\n\n"
            "You can change these later in Settings.")
        text.setObjectName("mutedText")
        text.setWordWrap(True)
        lay.addWidget(text)
        if not self._gpus:
            warn = QLabel(
                "No GPUs were detected (lspci unavailable). The game will use "
                "your system default GPU.")
            warn.setObjectName("mutedText")
            warn.setWordWrap(True)
            lay.addWidget(warn)
        lay.addStretch()
        return page

    def _page_gpu(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 6, 0, 6)
        lbl = QLabel("Graphics card")
        lbl.setObjectName("mutedText")
        lay.addWidget(lbl)
        self.gpu_combo = QComboBox()
        self.gpu_combo.addItem("System default", "")
        for g in self._gpus:
            label = g["name"]
            tag = "discrete" if g.get("discrete") else "integrated"
            self.gpu_combo.addItem(f"{label}  ({tag})", g["id"])
        idx = self.gpu_combo.findData(self.config.get_gpu())
        if idx >= 0:
            self.gpu_combo.setCurrentIndex(idx)
        elif self._gpus:
            for i, g in enumerate(self._gpus):
                if g.get("vendor") == graphics.VENDOR_NVIDIA:
                    self.gpu_combo.setCurrentIndex(i + 1)
                    break
        lay.addWidget(self.gpu_combo)
        desc = QLabel(
            "The launcher sets the right PRIME / render-offload variables so "
            "the game uses this GPU.")
        desc.setObjectName("mutedText")
        desc.setWordWrap(True)
        lay.addWidget(desc)
        lay.addStretch()
        return page

    def _page_wine(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 6, 0, 6)
        lbl = QLabel("Wine build")
        lbl.setObjectName("mutedText")
        lay.addWidget(lbl)
        row = QHBoxLayout()
        self.wine_combo = QComboBox()
        self.wine_combo.setEditable(True)
        self.wine_combo.addItem("Auto-detect", "")
        for w in self._wines:
            self.wine_combo.addItem(f"{w['name']} — {w['path']}", w["path"])
        cur = self.config.get_wine_binary()
        if cur:
            idx = self.wine_combo.findData(cur)
            if idx >= 0:
                self.wine_combo.setCurrentIndex(idx)
            else:
                self.wine_combo.setEditText(cur)
        row.addWidget(self.wine_combo, 1)
        browse = QPushButton("Browse\u2026")
        browse.setObjectName("smallBtn")
        browse.clicked.connect(self._browse_wine)
        row.addWidget(browse)
        lay.addLayout(row)
        if not self._wines:
            warn = QLabel(
                "Wine was not found on this system. Install Wine, or browse to "
                "a Wine / Proton-GE build.")
            warn.setObjectName("mutedText")
            warn.setWordWrap(True)
            lay.addWidget(warn)
        prefix = QLabel(f"Prefix: {self.config.get_wine_prefix()}")
        prefix.setObjectName("mutedText")
        prefix.setWordWrap(True)
        lay.addWidget(prefix)
        lay.addStretch()
        return page

    def _page_summary(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 6, 0, 6)
        lbl = QLabel("Summary")
        lbl.setObjectName("mutedText")
        lay.addWidget(lbl)
        self.summary_lbl = QLabel("")
        self.summary_lbl.setObjectName("infoText")
        self.summary_lbl.setWordWrap(True)
        lay.addWidget(self.summary_lbl)
        test = QPushButton("Test Wine")
        test.setObjectName("smallBtn")
        test.clicked.connect(self._test_wine)
        lay.addWidget(test, 0, Qt.AlignmentFlag.AlignLeft)
        lay.addStretch()
        return page

    # ------------------------------------------------------------------ nav
    def _current_index(self):
        return self.stack.currentIndex()

    def _update_nav(self):
        idx = self._current_index()
        self.back_btn.setEnabled(idx > 0)
        last = idx == self.stack.count() - 1
        self.next_btn.setText("Finish" if last else "Next")
        if last:
            self.summary_lbl.setText(self._summary_text())

    def _back(self):
        if self._current_index() > 0:
            self.stack.setCurrentIndex(self._current_index() - 1)
            self._update_nav()

    def _next(self):
        if self._current_index() == self.stack.count() - 1:
            self._finish()
            return
        self.stack.setCurrentIndex(self._current_index() + 1)
        self._update_nav()

    # ------------------------------------------------------------------ helpers
    def _selected_gpu_id(self):
        return self.gpu_combo.currentData() or ""

    def _selected_wine(self):
        data = self.wine_combo.currentData()
        if data:
            return data
        text = self.wine_combo.currentText().strip()
        if not text or text == "Auto-detect":
            return ""
        return text

    def _summary_text(self):
        gpu = graphics.describe_gpu(self._selected_gpu_id(), self._gpus)
        wine = self._selected_wine() or graphics.resolve_wine() or "Not found"
        return f"GPU: {gpu}\nWine: {wine}\nPrefix: {self.config.get_wine_prefix()}"

    def _browse_wine(self):
        start = "/usr/bin" if Path("/usr/bin").is_dir() else str(Path.home())
        path, _ = QFileDialog.getOpenFileName(
            self, "Select the Wine executable", start, "Executables (*)")
        if path:
            self.wine_combo.setCurrentIndex(-1)
            self.wine_combo.setEditText(path)

    def _test_wine(self):
        wine = self._selected_wine() or graphics.resolve_wine()
        if not wine:
            QMessageBox.warning(self, "Wine not found",
                                "No Wine binary is selected.")
            return
        try:
            from platform_utils import external_env
            out = subprocess.run(
                [wine, "--version"], capture_output=True, text=True,
                timeout=15, env=external_env())
            text = (out.stdout or out.stderr or "").strip() or "No output"
            QMessageBox.information(self, "Wine test", text)
        except Exception as e:
            QMessageBox.warning(self, "Wine test failed", str(e))

    def _finish(self):
        self.config.set_gpu(self._selected_gpu_id())
        self.config.set_wine_binary(self._selected_wine())
        self.config.set_linux_setup_complete(True)
        self.accept()
