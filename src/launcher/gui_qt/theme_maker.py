"""Theme Maker — full visual editor for creating custom themes."""
import random
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QRegularExpression
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QColorDialog, QFrame, QWidget, QScrollArea,
    QGridLayout, QGroupBox, QSizePolicy,
)
import gui_qt.theme as theme
from gui_qt.themes import save_custom_theme, BUILTIN


# Palette key definitions grouped by section
_SECTIONS = [
    ("Background", [
        ("bg_base", "Base"),
        ("bg_surface", "Surface"),
        ("bg_elevated", "Elevated"),
        ("bg_hover", "Hover"),
        ("bg_active", "Active"),
        ("bg_sidebar", "Sidebar"),
    ]),
    ("Border", [
        ("border_subtle", "Subtle"),
        ("border_default", "Default"),
        ("border_focus", "Focus"),
    ]),
    ("Accent", [
        ("accent", "Primary"),
        ("accent_hover", "Hover"),
        ("accent_muted", "Muted"),
        ("accent_2", "Secondary"),
    ]),
    ("Semantic", [
        ("success", "Success"),
        ("success_hover", "Success Hover"),
        ("info", "Info"),
        ("warning", "Warning"),
        ("danger", "Danger"),
        ("danger_hover", "Danger Hover"),
    ]),
    ("Text", [
        ("text_primary", "Primary"),
        ("text_secondary", "Secondary"),
        ("text_muted", "Muted"),
        ("text_bright", "Bright"),
    ]),
    ("Button", [
        ("btn_disabled_bg", "Disabled BG"),
        ("btn_disabled_text", "Disabled Text"),
    ]),
    ("Scrollbar", [
        ("scrollbar_handle", "Handle"),
        ("scrollbar_hover", "Hover"),
    ]),
    ("Checkbox", [
        ("checkbox_border", "Border"),
    ]),
]


def _random_hex():
    return f"#{random.randint(0, 0xFFFFFF):06x}"


def _random_palette():
    """Generate a random but cohesive dark palette."""
    hue = random.randint(0, 360)
    accent = QColor.fromHsv(hue, 200, 220)
    accent2 = QColor.fromHsv((hue + 40) % 360, 180, 200)
    success = QColor.fromHsv(145, 180, 180)
    danger = QColor.fromHsv(0, 180, 220)
    info = QColor.fromHsv(210, 160, 200)
    warning = QColor.fromHsv(45, 200, 220)

    def h(c):
        return c.name()

    return {
        "bg_base": "#0d0d0e",
        "bg_surface": "#151516",
        "bg_elevated": "#1c1c1e",
        "bg_hover": "#242426",
        "bg_active": "#2c2c2f",
        "bg_sidebar": "#0a0a0b",
        "border_subtle": "#1f1f21",
        "border_default": "#2a2a2d",
        "border_focus": h(accent),
        "accent": h(accent),
        "accent_hover": h(accent.lighter(115)),
        "accent_muted": h(accent.darker(200)),
        "accent_2": h(accent2),
        "success": h(success),
        "success_hover": h(success.lighter(115)),
        "info": h(info),
        "warning": h(warning),
        "danger": h(danger),
        "danger_hover": h(danger.lighter(115)),
        "text_primary": "#f0efed",
        "text_secondary": "#a3a09c",
        "text_muted": "#68655f",
        "text_bright": "#ffffff",
        "btn_disabled_bg": "#1f1f21",
        "btn_disabled_text": "#57544f",
        "scrollbar_handle": "#2a2a2d",
        "scrollbar_hover": "#3a3a3d",
        "checkbox_border": "#3a3a3d",
    }


class _ColorRow(QWidget):
    """A single row: label + hex input + swatch + pick button."""
    color_changed = Signal(str, str)  # key, hex value

    def __init__(self, key: str, label: str, hex_val: str, parent=None):
        super().__init__(parent)
        self._key = key
        self._color = QColor(hex_val)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        lbl = QLabel(label)
        lbl.setFixedWidth(110)
        lbl.setObjectName("mutedText")
        layout.addWidget(lbl)

        self._hex_input = QLineEdit(hex_val)
        self._hex_input.setFixedWidth(80)
        self._hex_input.setMaxLength(7)
        self._hex_input.textChanged.connect(self._on_hex_input)
        layout.addWidget(self._hex_input)

        self._swatch = QFrame()
        self._swatch.setFixedSize(24, 24)
        self._swatch.setStyleSheet(
            f"background-color: {hex_val}; border: 1px solid #555; border-radius: 4px;"
        )
        layout.addWidget(self._swatch)

        pick_btn = QPushButton("\u25ab")
        pick_btn.setFixedSize(28, 28)
        pick_btn.setToolTip("Pick color")
        pick_btn.clicked.connect(self._pick_color)
        layout.addWidget(pick_btn)

        layout.addStretch()

    def _on_hex_input(self, text):
        if len(text) == 7 and text.startswith("#"):
            c = QColor(text)
            if c.isValid():
                self._color = c
                self._swatch.setStyleSheet(
                    f"background-color: {text}; border: 1px solid #555; border-radius: 4px;"
                )
                self.color_changed.emit(self._key, text)

    def _pick_color(self):
        dialog = QColorDialog(self._color, self)
        dialog.setOption(QColorDialog.ColorDialogOption.ShowAlphaChannel, False)
        if dialog.exec() == QColorDialog.DialogCode.Accepted:
            c = dialog.currentColor()
            hex_val = c.name()
            self._hex_input.setText(hex_val)

    def get_value(self):
        return self._color.name()

    def set_value(self, hex_val):
        self._hex_input.setText(hex_val)


class ThemeMakerDialog(QDialog):
    """Full visual theme editor dialog."""
    theme_saved = Signal(str)  # emitted with theme name on save

    def __init__(self, base_palette=None, theme_name="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Theme Maker")
        self.setMinimumSize(620, 700)
        self.resize(620, 700)
        self._palette = dict(base_palette or theme.get_palette_dict())
        self._original_name = theme_name
        self._rows = {}  # key -> _ColorRow
        self._setup_ui()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        title = QLabel("Theme Maker")
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch()

        randomize_btn = QPushButton("Randomize")
        randomize_btn.setObjectName("toolBtn")
        randomize_btn.setFixedHeight(32)
        randomize_btn.clicked.connect(self._randomize)
        header.addWidget(randomize_btn)
        layout.addLayout(header)

        layout.addSpacing(4)

        # Theme name
        name_row = QHBoxLayout()
        name_lbl = QLabel("Theme Name:")
        name_lbl.setObjectName("mutedText")
        name_row.addWidget(name_lbl)
        self._name_input = QLineEdit(self._original_name)
        self._name_input.setPlaceholderText("My Custom Theme")
        self._name_input.setFixedWidth(250)
        name_row.addWidget(self._name_input)
        name_row.addStretch()
        layout.addLayout(name_row)

        layout.addSpacing(4)

        # Palette sections
        for section_name, keys in _SECTIONS:
            group = QGroupBox(section_name)
            group_layout = QGridLayout(group)
            group_layout.setSpacing(6)
            for row_idx, (key, label) in enumerate(keys):
                hex_val = self._palette.get(key, "#888888")
                row = _ColorRow(key, label, hex_val)
                row.color_changed.connect(self._on_color_changed)
                self._rows[key] = row
                group_layout.addWidget(row, row_idx, 0)
            layout.addWidget(group)

        # Live preview
        layout.addSpacing(8)
        preview_label = QLabel("Live Preview")
        preview_label.setObjectName("sectionTitle")
        layout.addWidget(preview_label)

        self._preview_frame = QFrame()
        self._preview_frame.setMinimumHeight(120)
        self._preview_frame.setStyleSheet(
            f"background-color: {self._palette.get('bg_surface', '#151516')}; "
            f"border: 1px solid {self._palette.get('border_subtle', '#1f1f21')}; "
            f"border-radius: 8px;"
        )
        preview_layout = QVBoxLayout(self._preview_frame)

        preview_hero = QLabel("Isam AULauncher")
        preview_hero.setStyleSheet(
            f"color: {self._palette.get('text_bright', '#ffffff')}; font-size: 20px; font-weight: bold; background: transparent;"
        )
        preview_layout.addWidget(preview_hero)

        btn_row = QHBoxLayout()
        for btn_name, obj_name, text in [
            ("success_btn", "successBtn", "Launch"),
            ("primary_btn", "primaryBtn", "Update"),
            ("danger_btn", "dangerBtn", "Stop"),
            ("tool_btn", "toolBtn", "Browse"),
        ]:
            btn = QPushButton(text)
            btn.setObjectName(obj_name)
            btn.setFixedHeight(32)
            btn_row.addWidget(btn)
        preview_layout.addLayout(btn_row)

        layout.addWidget(self._preview_frame)

        # Buttons
        layout.addSpacing(8)
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("toolBtn")
        cancel_btn.setFixedHeight(38)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        reset_btn = QPushButton("Reset")
        reset_btn.setObjectName("toolBtn")
        reset_btn.setFixedHeight(38)
        reset_btn.clicked.connect(self._reset)
        btn_row.addWidget(reset_btn)

        save_btn = QPushButton("Save Theme")
        save_btn.setObjectName("successBtn")
        save_btn.setFixedHeight(38)
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)

        layout.addLayout(btn_row)
        layout.addStretch()

        scroll.setWidget(container)

    def _on_color_changed(self, key, hex_val):
        self._palette[key] = hex_val
        self._update_preview()

    def _update_preview(self):
        p = self._palette
        self._preview_frame.setStyleSheet(
            f"background-color: {p.get('bg_surface', '#151516')}; "
            f"border: 1px solid {p.get('border_subtle', '#1f1f21')}; "
            f"border-radius: 8px;"
        )
        # Update preview buttons via main window
        from PySide6.QtWidgets import QApplication
        from gui_qt.themes import THEMES
        app = QApplication.instance()
        if app:
            THEMES["__preview__"] = p
            theme.set_theme(app, "__preview__")

    def _randomize(self):
        palette = _random_palette()
        self._palette = palette
        for key, row in self._rows.items():
            row.set_value(palette.get(key, "#888888"))
        self._update_preview()

    def _reset(self):
        base = theme.get_palette_dict()
        self._palette = dict(base)
        for key, row in self._rows.items():
            row.set_value(base.get(key, "#888888"))
        self._update_preview()

    def _save(self):
        name = self._name_input.text().strip()
        if not name:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Theme Maker", "Please enter a theme name.")
            return
        if name in BUILTIN:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Theme Maker", f'Cannot overwrite built-in theme "{name}".')
            return

        # Collect final palette
        palette = {}
        for key, row in self._rows.items():
            palette[key] = row.get_value()

        if save_custom_theme(name, palette):
            self.theme_saved.emit(name)
            self.accept()
        else:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Theme Maker", "Failed to save theme.")
