"""BepInEx Config Manager — read/write plugin .cfg toggles."""
import logging
import re
from pathlib import Path
from typing import Dict, Optional, List, Tuple

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox,
    QPushButton, QFrame, QScrollArea, QGroupBox,
)

import gui_qt.theme as theme

log = logging.getLogger(__name__)

CONFIG_FILE = "com.auassetsswapper.plugin.cfg"

SETTINGS = [
    ("DumpAllAssets", "General", "Log all loaded asset names to the BepInEx console", True),
    ("Sprites", "Swappers", "Enable sprite/texture swapping", True),
    ("Textures", "Swappers", "Enable raw Texture2D swapping", True),
    ("Audio", "Swappers", "Enable audio clip swapping", True),
    ("Fonts", "Swappers", "Enable font swapping", True),
    ("Shaders", "Swappers", "Enable shader swapping", True),
    ("Materials", "Swappers", "Enable material swapping", True),
    ("Prefabs", "Swappers", "Enable prefab/gameobject swapping", True),
]


class ConfigPanel(QWidget):
    def __init__(self, game_path_getter, parent=None):
        super().__init__(parent)
        self._game_path_getter = game_path_getter
        self._checkboxes: Dict[str, QCheckBox] = {}
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        header = QLabel("PLUGIN CONFIGURATION")
        header.setObjectName("sectionTitle")
        layout.addWidget(header)

        desc = QLabel("Toggle AU Assets Swapper plugin features. Changes save to BepInEx config.")
        desc.setObjectName("bodyText")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine))

        self._config_missing = QLabel("Config file not found. Launch the game once to generate it.")
        self._config_missing.setObjectName("warningText")
        self._config_missing.hide()
        layout.addWidget(self._config_missing)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_widget = QWidget()
        self._checks_layout = QVBoxLayout(scroll_widget)
        self._checks_layout.setContentsMargins(0, 0, 0, 0)
        self._checks_layout.setSpacing(4)

        current_section = ""
        for key, section, desc_text, default in SETTINGS:
            if section != current_section:
                if current_section:
                    self._checks_layout.addSpacing(8)
                sec_label = QLabel(section.upper())
                sec_label.setObjectName("sectionTitle")
                self._checks_layout.addWidget(sec_label)
                current_section = section
            cb = QCheckBox(key)
            cb.setChecked(default)
            cb.setToolTip(desc_text)
            cb.stateChanged.connect(self._on_changed)
            self._checkboxes[key] = cb
            self._checks_layout.addWidget(cb)

        self._checks_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        btn_row = QHBoxLayout()
        self._save_btn = QPushButton("Save")
        self._save_btn.setObjectName("successBtn")
        self._save_btn.setFixedHeight(36)
        self._save_btn.clicked.connect(self._save_config)
        btn_row.addWidget(self._save_btn)

        self._reset_btn = QPushButton("Reset to Defaults")
        self._reset_btn.setObjectName("toolBtn")
        self._reset_btn.setFixedHeight(36)
        self._reset_btn.clicked.connect(self._reset_defaults)
        btn_row.addWidget(self._reset_btn)
        btn_row.addStretch()

        layout.addLayout(btn_row)

        self._status = QLabel("")
        self._status.setObjectName("statusText")
        layout.addWidget(self._status)

    def _config_path(self) -> Optional[Path]:
        gp = self._game_path_getter()
        if not gp:
            return None
        p = gp / "BepInEx" / "config" / CONFIG_FILE
        return p if p.exists() else None

    def refresh(self):
        path = self._config_path()
        if not path:
            self._config_missing.show()
            return
        self._config_missing.hide()
        values = self._parse_config(path)
        for key, cb in self._checkboxes.items():
            if key in values:
                cb.setChecked(values[key].lower() == "true")

    def _parse_config(self, path: Path) -> Dict[str, str]:
        values: Dict[str, str] = {}
        try:
            for line in path.read_text(encoding="utf-8-sig").splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or stripped.startswith("["):
                    continue
                if "=" in stripped:
                    key, _, val = stripped.partition("=")
                    values[key.strip()] = val.strip()
        except Exception as e:
            log.error(f"Failed to parse config: {e}")
        return values

    def _save_config(self):
        path = self._config_path()
        if not path:
            gp = self._game_path_getter()
            if not gp:
                self._status.setText("No game path set")
                return
            config_dir = gp / "BepInEx" / "config"
            config_dir.mkdir(parents=True, exist_ok=True)
            path = config_dir / CONFIG_FILE
        try:
            lines = []
            if path.exists():
                lines = path.read_text(encoding="utf-8-sig").splitlines()
            new_lines = []
            replaced = set()
            for line in lines:
                stripped = line.strip()
                if "=" in stripped and not stripped.startswith("#") and not stripped.startswith("["):
                    key, _, _ = stripped.partition("=")
                    key = key.strip()
                    if key in self._checkboxes:
                        val = "true" if self._checkboxes[key].isChecked() else "false"
                        new_lines.append(f"{key} = {val}")
                        replaced.add(key)
                        continue
                new_lines.append(line)
            for key, cb in self._checkboxes.items():
                if key not in replaced:
                    val = "true" if cb.isChecked() else "false"
                    new_lines.append(f"{key} = {val}")
            path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            self._status.setText("Config saved")
            self._status.setObjectName("successText")
        except Exception as e:
            log.error(f"Failed to save config: {e}")
            self._status.setText(f"Error: {e}")
            self._status.setObjectName("dangerText")
        self._status.style().polish(self._status)

    def _reset_defaults(self):
        for key, _, _, default in SETTINGS:
            if key in self._checkboxes:
                self._checkboxes[key].setChecked(default)

    def _on_changed(self, state):
        pass
