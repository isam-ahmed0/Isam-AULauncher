import webbrowser

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics, QColor, QPainter, QLinearGradient, QBrush, QFont
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QFrame, QCheckBox,
    QPushButton, QMessageBox, QGridLayout, QWidget, QScrollArea,
)

from config import APP_NAME, LAUNCHER_VERSION, MAKER, DISCORD_INVITE, YOUTUBE_CHANNEL, SOURCE_CODE_URL
from file_manager import FileManager
import gui_qt.theme as theme
from gui_qt.themes import THEMES, is_custom_theme, delete_custom_theme


_THEME_ORDER = ["Forest", "Violet", "Coral", "Slate", "Ember", "Plum", "Mono"]


class _ThemeCard(QFrame):
    """Clickable card representing a single theme preset."""

    def __init__(self, name: str, palette: dict, is_selected: bool,
                 is_custom: bool = False, parent=None):
        super().__init__(parent)
        self._name = name
        self._palette = palette
        self._selected = is_selected
        self._is_custom = is_custom

        self.setFixedSize(140, 78)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style()

    def set_selected(self, val: bool):
        self._selected = val
        self._update_style()

    def _update_style(self):
        accent = self._palette["accent"]
        bg = self._palette["bg_surface"]
        border = accent if self._selected else self._palette["border_subtle"]
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border: 2px solid {border};
                border-radius: 8px;
            }}
            QFrame:hover {{
                border: 2px solid {accent};
            }}
        """)

    def paintEvent(self, event):
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
        p.setBrush(QBrush(grad))
        p.drawRoundedRect(0, 0, w, 4, 8, 8)

        # Theme name
        p.setPen(QColor(self._palette["text_bright"]))
        f = QFont("Segoe UI", 12)
        f.setBold(True)
        p.setFont(f)
        p.drawText(0, 24, w, 20, Qt2.AlignmentFlag.AlignHCenter, self._name)

        # Accent color label
        p.setPen(QColor(self._palette["text_muted"]))
        f2 = QFont("Segoe UI", 10)
        p.setFont(f2)
        p.drawText(0, 46, w, 16, Qt2.AlignmentFlag.AlignHCenter, accent.name())

        # Delete X for custom themes
        if self._is_custom:
            p.setPen(QColor(self._palette.get("text_muted", "#666")))
            xf = QFont("Segoe UI", 11)
            xf.setBold(True)
            p.setFont(xf)
            p.drawText(w - 20, 16, 16, 16, Qt2.AlignmentFlag.AlignCenter, "\u00d7")

        p.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Check if click is on the delete X (top-right corner for custom themes)
            if self._is_custom and event.position().x() > self.width() - 22 and event.position().y() < 20:
                parent = self.parent()
                while parent and not isinstance(parent, SettingsPage):
                    parent = parent.parent()
                if parent:
                    parent._delete_theme(self._name)
                return
            # Walk up to find SettingsPage widget
            parent = self.parent()
            while parent and not isinstance(parent, SettingsPage):
                parent = parent.parent()
            if parent:
                parent._select_theme(self._name)
        super().mousePressEvent(event)


class SettingsPage(QWidget):
    """Settings page widget (embedded in stacked widget, not a dialog)."""

    def __init__(self, config, discord, profile_mgr, parent=None):
        super().__init__(parent)
        self.config = config
        self.discord = discord
        self.profile_mgr = profile_mgr
        self._selected_theme = config.settings.get("theme", "Forest")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(32, 20, 32, 20)
        layout.setSpacing(12)

        title = QLabel("Settings")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        layout.addSpacing(8)
        layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine))
        layout.addSpacing(12)

        settings = self.config.settings

        cb_rpc = QCheckBox("Discord Rich Presence")
        cb_rpc.setChecked(settings.get("discord_rpc", True))
        cb_rpc.stateChanged.connect(lambda: self._save_setting("discord_rpc", cb_rpc.isChecked()))
        layout.addWidget(cb_rpc)
        desc1 = QLabel("Show your activity on Discord")
        desc1.setObjectName("mutedText")
        desc1.setContentsMargins(26, 0, 0, 0)
        layout.addWidget(desc1)
        layout.addSpacing(12)

        cb_auto = QCheckBox("Auto-update game")
        cb_auto.setChecked(settings.get("auto_update", True))
        cb_auto.stateChanged.connect(lambda: self._save_setting("auto_update", cb_auto.isChecked()))
        layout.addWidget(cb_auto)
        desc2 = QLabel("Download game updates automatically")
        desc2.setObjectName("mutedText")
        desc2.setContentsMargins(26, 0, 0, 0)
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

        self._theme_grid = QGridLayout()
        self._theme_grid.setSpacing(10)
        grid = self._theme_grid
        # Built-in themes
        for idx, name in enumerate(_THEME_ORDER):
            pal = THEMES[name]
            card = _ThemeCard(name, pal, name == self._selected_theme, is_custom=False)
            row, col = divmod(idx, 3)
            grid.addWidget(card, row, col)
            self._theme_cards[name] = card
        # Custom themes
        custom_names = [n for n in THEMES if n not in _THEME_ORDER]
        for idx, name in enumerate(custom_names):
            pal = THEMES[name]
            card = _ThemeCard(name, pal, name == self._selected_theme, is_custom=True)
            total = len(_THEME_ORDER) + idx
            row, col = divmod(total, 3)
            grid.addWidget(card, row, col)
            self._theme_cards[name] = card
        layout.addLayout(grid)
        layout.addSpacing(4)

        # Create Theme button
        create_btn = QPushButton("+ Create Theme")
        create_btn.setObjectName("toolBtn")
        create_btn.setFixedHeight(38)
        create_btn.clicked.connect(self._open_theme_maker)
        layout.addWidget(create_btn)
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
        bep_obj = "successText" if bepinstalled else "mutedText"

        fields = [
            ("Version:", version, "gameInfoLabel"),
            ("Install Path:", install_path, "gameInfoLabel"),
            ("BepInEx:", bep_text, bep_obj),
            ("Active Profile:", active_profile, "gameInfoLabel"),
            ("Mods Installed:", str(mod_count), "gameInfoLabel"),
            ("Disk Usage:", disk_usage or "N/A", "gameInfoLabel"),
        ]

        for row, (label, value, obj_name) in enumerate(fields):
            row_layout = QHBoxLayout()
            row_layout.setContentsMargins(8, 0, 8, 0)
            lbl = QLabel(label)
            lbl.setObjectName("mutedText")
            lbl.setFixedWidth(120)
            row_layout.addWidget(lbl)
            val = QLabel(value)
            val.setObjectName(obj_name)
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

        layout.addStretch()
        scroll.setWidget(container)

    def _save_setting(self, key, value):
        self.config.settings[key] = value
        self.config.save_settings()
        if key == "discord_rpc":
            if value and not self.discord.connected:
                self.discord.connect()
            elif not value and self.discord.connected:
                self.discord.disconnect()

    def _select_theme(self, name: str):
        self._selected_theme = name
        for tname, card in self._theme_cards.items():
            card.set_selected(tname == name)
        self.config.settings["theme"] = name
        self.config.save_settings()
        # Live preview
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            theme.set_theme(app, name)
            from gui_qt.widgets import HeroBanner, enable_hover_glow
            for w in app.topLevelWidgets():
                for banner in w.findChildren(HeroBanner):
                    banner.update()
            # Refresh sidebar nav button glow colors
            main_win = None
            for w in app.topLevelWidgets():
                if hasattr(w, 'nav_buttons'):
                    main_win = w
                    break
            if main_win:
                for btn in main_win.nav_buttons.values():
                    enable_hover_glow(btn)
                # Restart playing pulse if game is running
                if hasattr(main_win, 'game') and main_win.game.is_running:
                    from gui_qt.widgets import start_playing_pulse
                    start_playing_pulse(main_win.main_action_btn, color=theme.DANGER)

    def _open_theme_maker(self):
        from gui_qt.theme_maker import ThemeMakerDialog
        base = theme.get_palette_dict()
        dlg = ThemeMakerDialog(base_palette=base, parent=self)
        dlg.theme_saved.connect(self._on_theme_saved)
        dlg.exec()

    def _on_theme_saved(self, name: str):
        self.config.settings["theme"] = name
        self.config.save_settings()
        self._selected_theme = name
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            theme.set_theme(app, name)
        self._refresh_theme_grid()

    def _delete_theme(self, name: str):
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "Delete Theme",
            f'Delete custom theme "{name}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            delete_custom_theme(name)
            if self._selected_theme == name:
                self._selected_theme = "Forest"
                self.config.settings["theme"] = "Forest"
                self.config.save_settings()
                from PySide6.QtWidgets import QApplication
                app = QApplication.instance()
                if app:
                    theme.set_theme(app, "Forest")
            self._refresh_theme_grid()

    def _refresh_theme_grid(self):
        """Rebuild just the theme cards grid."""
        # Clear existing cards from the grid layout
        grid = self._theme_grid
        while grid.count():
            item = grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._theme_cards.clear()
        # Re-add built-in themes
        for idx, name in enumerate(_THEME_ORDER):
            pal = THEMES[name]
            card = _ThemeCard(name, pal, name == self._selected_theme, is_custom=False)
            row, col = divmod(idx, 3)
            grid.addWidget(card, row, col)
            self._theme_cards[name] = card
        # Re-add custom themes
        custom_names = [n for n in THEMES if n not in _THEME_ORDER]
        for idx, name in enumerate(custom_names):
            pal = THEMES[name]
            card = _ThemeCard(name, pal, name == self._selected_theme, is_custom=True)
            total = len(_THEME_ORDER) + idx
            row, col = divmod(total, 3)
            grid.addWidget(card, row, col)
            self._theme_cards[name] = card


class AboutPage(QWidget):
    """About page widget (embedded in stacked widget, not a dialog)."""

    def __init__(self, parent=None):
        super().__init__(parent)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(32, 20, 32, 20)
        layout.setSpacing(12)

        title = QLabel("About")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        layout.addSpacing(8)
        layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine))
        layout.addSpacing(12)

        name = QLabel(APP_NAME)
        name.setObjectName("profileName")
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
        links_row.setSpacing(10)
        if DISCORD_INVITE:
            discord_btn = QPushButton("Discord")
            discord_btn.setObjectName("toolBtn")
            discord_btn.setFixedHeight(38)
            discord_btn.clicked.connect(lambda: webbrowser.open(DISCORD_INVITE))
            links_row.addWidget(discord_btn)
        else:
            discord_btn = QPushButton("Discord (Coming soon)")
            discord_btn.setObjectName("toolBtn")
            discord_btn.setFixedHeight(38)
            discord_btn.clicked.connect(self._cb_coming_soon)
            links_row.addWidget(discord_btn)

        yt_btn = QPushButton("YouTube")
        yt_btn.setObjectName("toolBtn")
        yt_btn.setFixedHeight(38)
        yt_btn.clicked.connect(lambda: webbrowser.open(YOUTUBE_CHANNEL))
        links_row.addWidget(yt_btn)

        src_btn = QPushButton("Source Code")
        src_btn.setObjectName("toolBtn")
        src_btn.setFixedHeight(38)
        src_btn.clicked.connect(lambda: webbrowser.open(SOURCE_CODE_URL))
        links_row.addWidget(src_btn)
        layout.addLayout(links_row)

        layout.addStretch()
        scroll.setWidget(container)

    def _cb_coming_soon(self):
        QMessageBox.information(self, "Discord", "Discord server coming soon!")
