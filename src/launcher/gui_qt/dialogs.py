import webbrowser

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics, QColor
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QCheckBox,
    QPushButton, QMessageBox, QGridLayout, QWidget,
)

from config import APP_NAME, LAUNCHER_VERSION, MAKER, DISCORD_INVITE, YOUTUBE_CHANNEL, SOURCE_CODE_URL
from file_manager import FileManager
import gui_qt.theme as theme
from gui_qt.themes import THEMES


_THEME_ORDER = ["Indigo", "Amber", "Crimson", "Forest", "Light", "Mint"]


class _ThemeCard(QFrame):
    """Clickable card representing a single theme preset."""

    def __init__(self, name: str, palette: dict, is_selected: bool, parent=None):
        super().__init__(parent)
        self._name = name
        self._palette = palette
        self._selected = is_selected

        self.setFixedSize(130, 72)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style()

    def set_selected(self, val: bool):
        self._selected = val
        self._update_style()

    def _update_style(self):
        accent = self._palette["accent"]
        bg = self._palette["bg_surface"]
        border = accent if self._selected else self._palette.get("border_subtle", "#282c38")
        border_w = "2px" if self._selected else "1px"
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border: {border_w} solid {border};
                border-radius: 8px;
            }}
            QFrame:hover {{
                border: 2px solid {accent};
            }}
        """)

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QColor, QLinearGradient
        from PySide6.QtCore import Qt as Qt2
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        accent = QColor(self._palette["accent"])
        accent2 = QColor(self._palette["accent_2"])

        # Accent color bar at top
        grad = QLinearGradient(0, 0, w, 0)
        grad.setColorAt(0, accent)
        grad.setColorAt(1, accent2)
        p.setPen(Qt2.PenStyle.NoPen)
        from PySide6.QtGui import QBrush
        p.setBrush(QBrush(grad))
        p.drawRoundedRect(0, 0, w, 4, 8, 8)

        # Theme name
        from PySide6.QtGui import QFont
        p.setPen(QColor(self._palette["text_bright"]))
        f = QFont("Segoe UI", 11)
        f.setBold(True)
        p.setFont(f)
        p.drawText(0, 22, w, 20, Qt2.AlignmentFlag.AlignHCenter, self._name)

        # Accent color label
        p.setPen(QColor(self._palette["text_muted"]))
        f2 = QFont("Segoe UI", 9)
        p.setFont(f2)
        p.drawText(0, 42, w, 16, Qt2.AlignmentFlag.AlignHCenter, accent.name())

        p.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            parent = self.parent()
            while parent and not isinstance(parent, SettingsDialog):
                parent = parent.parent()
            if parent:
                parent._select_theme(self._name)
        super().mousePressEvent(event)


class SettingsDialog(QDialog):
    def __init__(self, config, discord, profile_mgr, parent=None):
        super().__init__(parent)
        self.config = config
        self.discord = discord
        self.profile_mgr = profile_mgr

        self.setWindowTitle("Settings")
        self.setFixedSize(480, 560)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)

        title = QLabel("Settings")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        layout.addSpacing(4)
        layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine))
        layout.addSpacing(12)

        settings = self.config.settings

        cb_rpc = QCheckBox("Discord Rich Presence")
        cb_rpc.setChecked(settings.get("discord_rpc", True))
        layout.addWidget(cb_rpc)
        desc1 = QLabel("  Show your activity on Discord")
        desc1.setObjectName("mutedText")
        layout.addWidget(desc1)
        layout.addSpacing(12)

        cb_auto = QCheckBox("Auto-update game")
        cb_auto.setChecked(settings.get("auto_update", True))
        layout.addWidget(cb_auto)
        desc2 = QLabel("  Download game updates automatically")
        desc2.setObjectName("mutedText")
        layout.addWidget(desc2)
        layout.addSpacing(12)

        layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine))
        layout.addSpacing(8)

        # --- Theme section ---
        theme_title = QLabel("Theme")
        theme_title.setObjectName("sectionTitle")
        layout.addWidget(theme_title)
        layout.addSpacing(6)

        self._theme_cards = {}
        self._selected_theme = settings.get("theme", "Indigo")

        grid = QGridLayout()
        grid.setSpacing(8)
        for idx, name in enumerate(_THEME_ORDER):
            pal = THEMES[name]
            card = _ThemeCard(name, pal, name == self._selected_theme)
            row, col = divmod(idx, 3)
            grid.addWidget(card, row, col)
            self._theme_cards[name] = card
        layout.addLayout(grid)
        layout.addSpacing(8)

        layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine))
        layout.addSpacing(8)

        # --- Game Info section ---
        info_title = QLabel("Game Info")
        info_title.setObjectName("sectionTitle")
        layout.addWidget(info_title)
        layout.addSpacing(6)

        gp = self.config.get_game_path()
        version = self.config.get_version() or "Not installed"
        install_path = str(gp) if gp else "Not set"
        bepinstalled = bool(gp and (gp / "BepInEx" / "core" / "BepInEx.dll").exists())
        active_profile = self.config.get_active_profile()

        mod_count = 0
        if gp and bepinstalled:
            profile_dir = self.profile_mgr.profile_path(active_profile)
            if profile_dir.exists():
                mod_count = len(list(profile_dir.glob("*.dll")))

        disk_usage = ""
        if gp and gp.exists():
            try:
                total = sum(f.stat().st_size for f in gp.rglob("*") if f.is_file())
                disk_usage = FileManager.format_size(total)
            except Exception:
                disk_usage = "Unknown"
        else:
            disk_usage = "N/A"

        bep_text = "Installed" if bepinstalled else "Not installed"
        bep_color = theme.SUCCESS if bepinstalled else theme.TEXT_MUTED

        fields = [
            ("Version:", version, theme.TEXT_BRIGHT),
            ("Install Path:", install_path, theme.TEXT_BRIGHT),
            ("BepInEx:", bep_text, bep_color),
            ("Active Profile:", active_profile, theme.TEXT_BRIGHT),
            ("Mods Installed:", str(mod_count), theme.TEXT_BRIGHT),
            ("Disk Usage:", disk_usage or "N/A", theme.TEXT_BRIGHT),
        ]

        for row, (label, value, color) in enumerate(fields):
            row_layout = QHBoxLayout()
            row_layout.setContentsMargins(8, 0, 8, 0)
            lbl = QLabel(label)
            lbl.setObjectName("mutedText")
            lbl.setFixedWidth(120)
            row_layout.addWidget(lbl)
            val = QLabel(value)
            val.setStyleSheet(f"color: {color};")
            val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            val.setWordWrap(False)
            val.setMaximumWidth(300)
            fm = QFontMetrics(val.font())
            elided = fm.elidedText(value, Qt.TextElideMode.ElideRight, 300)
            val.setText(elided)
            val.setToolTip(value)
            row_layout.addWidget(val)
            row_layout.addStretch()
            layout.addLayout(row_layout)

        layout.addSpacing(16)
        layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine))
        layout.addSpacing(12)

        def save():
            settings["discord_rpc"] = cb_rpc.isChecked()
            settings["auto_update"] = cb_auto.isChecked()
            settings["theme"] = self._selected_theme
            self.config.save_settings()
            if settings["discord_rpc"] and not self.discord.connected:
                self.discord.connect()
            elif not settings["discord_rpc"] and self.discord.connected:
                self.discord.disconnect()
            self.accept()

        save_btn = QPushButton("Save")
        save_btn.setObjectName("modalPrimary")
        save_btn.setFixedHeight(36)
        save_btn.clicked.connect(save)
        layout.addWidget(save_btn)

    def _select_theme(self, name: str):
        self._selected_theme = name
        for tname, card in self._theme_cards.items():
            card.set_selected(tname == name)
        # Live preview
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            theme.set_theme(app, name)
            # Repaint custom-painted widgets (HeroBanner)
            from gui_qt.widgets import HeroBanner
            for w in app.topLevelWidgets():
                for banner in w.findChildren(HeroBanner):
                    banner.update()

    def done(self, result):
        # Revert theme if cancelled
        if result != QDialog.DialogCode.Accepted:
            current = self.config.settings.get("theme", "Indigo")
            if current != self._selected_theme:
                from PySide6.QtWidgets import QApplication
                app = QApplication.instance()
                if app:
                    theme.set_theme(app, current)
        super().done(result)


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About")
        self.setFixedSize(460, 340)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)

        title = QLabel("About")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        layout.addSpacing(4)
        layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine))
        layout.addSpacing(12)

        name = QLabel(APP_NAME)
        name.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {theme.TEXT_BRIGHT};")
        layout.addWidget(name)
        ver = QLabel(f"Version {LAUNCHER_VERSION}")
        ver.setObjectName("statusText")
        layout.addWidget(ver)
        maker = QLabel(f"Made by {MAKER}")
        maker.setObjectName("mutedText")
        layout.addWidget(maker)
        layout.addSpacing(8)
        desc = QLabel("A premium launcher for Among Us\nwith auto-updates and mod support.")
        desc.setObjectName("statusText")
        layout.addWidget(desc)
        layout.addSpacing(16)
        layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine))
        layout.addSpacing(12)

        # Links row
        links_row = QHBoxLayout()
        if DISCORD_INVITE:
            discord_btn = QPushButton("Discord")
            discord_btn.setObjectName("toolBtn")
            discord_btn.setFixedHeight(36)
            discord_btn.clicked.connect(lambda: webbrowser.open(DISCORD_INVITE))
            links_row.addWidget(discord_btn)
        else:
            discord_btn = QPushButton("Discord (Coming soon)")
            discord_btn.setObjectName("toolBtn")
            discord_btn.setFixedHeight(36)
            discord_btn.clicked.connect(self._cb_coming_soon)
            links_row.addWidget(discord_btn)

        yt_btn = QPushButton("YouTube")
        yt_btn.setObjectName("toolBtn")
        yt_btn.setFixedHeight(36)
        yt_btn.clicked.connect(lambda: webbrowser.open(YOUTUBE_CHANNEL))
        links_row.addWidget(yt_btn)

        src_btn = QPushButton("Source Code")
        src_btn.setObjectName("toolBtn")
        src_btn.setFixedHeight(36)
        src_btn.clicked.connect(lambda: webbrowser.open(SOURCE_CODE_URL))
        links_row.addWidget(src_btn)
        layout.addLayout(links_row)

        layout.addSpacing(20)
        layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine))
        layout.addSpacing(8)

        ok_btn = QPushButton("OK")
        ok_btn.setObjectName("modalPrimary")
        ok_btn.setFixedHeight(36)
        ok_btn.clicked.connect(self.accept)
        layout.addWidget(ok_btn)

    def _cb_coming_soon(self):
        QMessageBox.information(self, "Discord", "Discord server coming soon!")
