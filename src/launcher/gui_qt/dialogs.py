import sys
import webbrowser
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics, QColor, QPainter, QLinearGradient, QBrush, QFont
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QFrame, QCheckBox,
    QPushButton, QMessageBox, QGridLayout, QWidget, QScrollArea, QComboBox,
    QFileDialog, QInputDialog,
)

from config import (
    APP_NAME, LAUNCHER_VERSION, MAKER, DISCORD_INVITE, YOUTUBE_CHANNEL,
    SOURCE_CODE_URL, LINUX_DOC_URL, WINE_DOC_URL,
)
from file_manager import FileManager
import gui_qt.theme as theme
from gui_qt.themes import THEMES, is_custom_theme, delete_custom_theme
import ui_registry


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

        # --- Interface section ---
        layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine))
        layout.addSpacing(8)
        ui_title = QLabel("Interface")
        ui_title.setObjectName("sectionTitle")
        layout.addWidget(ui_title)
        layout.addSpacing(6)

        self._ui_guis = ui_registry.list_guis(self.config)
        ui_row = QHBoxLayout()
        ui_row.setContentsMargins(8, 0, 8, 0)
        ui_lbl = QLabel("User interface")
        ui_lbl.setObjectName("mutedText")
        ui_lbl.setFixedWidth(140)
        ui_row.addWidget(ui_lbl)
        self.ui_combo = QComboBox()
        self._fill_ui_combo()
        self.ui_combo.currentIndexChanged.connect(self._save_ui_mode)
        ui_row.addWidget(self.ui_combo, 1)
        layout.addLayout(ui_row)

        from platform_utils import IS_LINUX
        if IS_LINUX:
            disp_row = QHBoxLayout()
            disp_row.setContentsMargins(8, 0, 8, 0)
            disp_lbl = QLabel("Display backend")
            disp_lbl.setObjectName("mutedText")
            disp_lbl.setFixedWidth(140)
            disp_row.addWidget(disp_lbl)
            self.display_combo = QComboBox()
            self.display_combo.addItem("Auto (recommended)", "")
            self.display_combo.addItem("X11 (xcb)", "x11")
            self.display_combo.addItem("Wayland", "wayland")
            didx = self.display_combo.findData(self.config.get_display_backend())
            if didx >= 0:
                self.display_combo.setCurrentIndex(didx)
            self.display_combo.currentIndexChanged.connect(self._save_display_backend)
            disp_row.addWidget(self.display_combo, 1)
            layout.addLayout(disp_row)

            disp_desc = QLabel("X11 is the safest choice for most users.")
            disp_desc.setObjectName("mutedText")
            disp_desc.setContentsMargins(148, 0, 0, 0)
            layout.addWidget(disp_desc)

        ui_desc = QLabel("Changing the interface or display backend needs a restart.")
        ui_desc.setObjectName("mutedText")
        ui_desc.setContentsMargins(148, 0, 0, 0)
        layout.addWidget(ui_desc)

        ui_btns = QHBoxLayout()
        ui_btns.setContentsMargins(148, 4, 0, 0)
        open_guis_btn = QPushButton("Open GUI folder")
        open_guis_btn.setObjectName("smallBtn")
        open_guis_btn.clicked.connect(self._open_guis_folder)
        ui_btns.addWidget(open_guis_btn)
        create_gui_btn = QPushButton("Create Custom GUI")
        create_gui_btn.setObjectName("smallBtn")
        create_gui_btn.clicked.connect(self._create_custom_gui)
        ui_btns.addWidget(create_gui_btn)
        edit_gui_btn = QPushButton("Edit Custom GUI")
        edit_gui_btn.setObjectName("smallBtn")
        edit_gui_btn.clicked.connect(self._edit_custom_gui)
        ui_btns.addWidget(edit_gui_btn)
        ui_btns.addStretch()
        restart_btn = QPushButton("Restart now")
        restart_btn.setObjectName("smallBtn")
        restart_btn.clicked.connect(self._restart_now)
        ui_btns.addWidget(restart_btn)
        layout.addLayout(ui_btns)
        layout.addSpacing(12)

        if IS_LINUX:
            import graphics
            layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine))
            layout.addSpacing(8)
            gfx_title = QLabel("Graphics")
            gfx_title.setObjectName("sectionTitle")
            layout.addWidget(gfx_title)
            layout.addSpacing(6)

            self._gpus = graphics.detect_gpus()
            row = QHBoxLayout()
            row.setContentsMargins(8, 0, 8, 0)
            gpu_lbl = QLabel("GPU")
            gpu_lbl.setObjectName("mutedText")
            gpu_lbl.setFixedWidth(140)
            row.addWidget(gpu_lbl)
            self.gpu_combo = QComboBox()
            self.gpu_combo.addItem("System default", "")
            for g in self._gpus:
                tag = "discrete" if g.get("discrete") else "integrated"
                self.gpu_combo.addItem(f"{g['name']}  ({tag})", g["id"])
            idx = self.gpu_combo.findData(self.config.get_gpu())
            if idx >= 0:
                self.gpu_combo.setCurrentIndex(idx)
            self.gpu_combo.currentIndexChanged.connect(
                lambda: self._save_setting("gpu_id", self.gpu_combo.currentData() or ""))
            row.addWidget(self.gpu_combo, 1)
            gpu_refresh = QPushButton("Refresh")
            gpu_refresh.setObjectName("smallBtn")
            gpu_refresh.clicked.connect(self._refresh_gpus)
            row.addWidget(gpu_refresh)
            layout.addLayout(row)

            gpu_desc = QLabel(
                "The launcher sets PRIME / render-offload variables so the game "
                "runs on the selected GPU.")
            gpu_desc.setObjectName("mutedText")
            gpu_desc.setWordWrap(True)
            gpu_desc.setContentsMargins(148, 0, 0, 0)
            layout.addWidget(gpu_desc)

            setup_row = QHBoxLayout()
            setup_row.setContentsMargins(148, 4, 0, 0)
            setup_btn = QPushButton("Re-run setup wizard")
            setup_btn.setObjectName("smallBtn")
            setup_btn.clicked.connect(self._open_setup_wizard)
            setup_row.addWidget(setup_btn)
            setup_row.addStretch()
            layout.addLayout(setup_row)
            layout.addSpacing(12)

            wine_title = QLabel("Wine")
            wine_title.setObjectName("sectionTitle")
            layout.addWidget(wine_title)
            layout.addSpacing(6)

            self._wines = graphics.detect_wine_binaries()
            wrow = QHBoxLayout()
            wrow.setContentsMargins(8, 0, 8, 0)
            wine_lbl = QLabel("Wine build")
            wine_lbl.setObjectName("mutedText")
            wine_lbl.setFixedWidth(140)
            wrow.addWidget(wine_lbl)
            self.wine_combo = QComboBox()
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
            self.wine_combo.currentIndexChanged.connect(self._save_wine)
            wrow.addWidget(self.wine_combo, 1)
            layout.addLayout(wrow)

            pf_lbl = QLabel(f"Wine prefix: {self.config.get_wine_prefix()}")
            pf_lbl.setObjectName("mutedText")
            pf_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            layout.addWidget(pf_lbl)
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

        from platform_utils import IS_LINUX
        if IS_LINUX:
            import graphics
            gpu_val = graphics.describe_gpu(self.config.get_gpu(), self._gpus)
            wine_val = self.config.get_wine_binary() \
                or graphics.resolve_wine() or "Not found"
            fields.append(("GPU:", gpu_val, "gameInfoLabel"))
            fields.append(("Wine:", wine_val, "gameInfoLabel"))

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

    # ------------------------------------------------------------------ interface
    def _fill_ui_combo(self):
        self.ui_combo.blockSignals(True)
        self.ui_combo.clear()
        for g in self._ui_guis:
            label = g["name"]
            if not g.get("available", True):
                label += f"  (unavailable: {g.get('reason') or 'missing modules'})"
            self.ui_combo.addItem(label, g["id"])
        idx = self.ui_combo.findData(self.config.get_ui_mode())
        if idx >= 0:
            self.ui_combo.setCurrentIndex(idx)
        self.ui_combo.blockSignals(False)

    def _save_ui_mode(self):
        mode = self.ui_combo.currentData()
        if mode:
            self.config.set_ui_mode(mode)

    def _save_display_backend(self):
        self.config.set_display_backend(self.display_combo.currentData() or "")

    def _refresh_ui_combo(self):
        self._ui_guis = ui_registry.list_guis(self.config)
        self._fill_ui_combo()

    def _edit_custom_gui(self):
        mode = self.config.get_ui_mode()
        path = None
        if mode.startswith("custom:"):
            path = ui_registry.custom_gui_path(self.config, mode.split(":", 1)[1])
        if not path:
            QMessageBox.information(
                self, "Edit Custom GUI",
                "Select one of your custom GUIs in the dropdown first,\n"
                "or create a new one.")
            return
        from platform_utils import open_local_path
        try:
            open_local_path(path)
        except Exception as e:
            QMessageBox.warning(self, "Edit Custom GUI", str(e))

    def _restart_now(self):
        reply = QMessageBox.question(
            self, "Restart Launcher",
            "Close and restart the launcher now to apply the changes?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        import app_restart
        try:
            app_restart.restart()
        except Exception as e:
            QMessageBox.warning(self, "Restart Launcher", str(e))

    def _open_guis_folder(self):
        from platform_utils import open_local_path
        try:
            open_local_path(self.config.guis_dir)
        except Exception as e:
            QMessageBox.warning(self, "Open GUI folder", str(e))

    def _create_custom_gui(self):
        templates = ui_registry.custom_gui_templates()
        labels = [f"{t['name']} — {t['description']}" for t in templates]
        choice, ok = QInputDialog.getItem(
            self, "Create Custom GUI", "Starter template:", labels, 0, False)
        if not ok:
            return
        template_id = "launcher"
        if choice in labels:
            template_id = templates[labels.index(choice)]["id"]
        name, ok = QInputDialog.getText(
            self, "Create Custom GUI", "Name for your GUI:")
        if not ok or not name.strip():
            return
        try:
            path = ui_registry.create_custom_gui(self.config, name, template_id)
        except FileExistsError:
            QMessageBox.warning(self, "Create Custom GUI",
                                "A GUI with that name already exists.")
            return
        except Exception as e:
            QMessageBox.warning(self, "Create Custom GUI", str(e))
            return
        self._refresh_ui_combo()
        idx = self.ui_combo.findData(f"custom:{path.stem}")
        if idx >= 0:
            self.ui_combo.setCurrentIndex(idx)
            self._save_ui_mode()
        QMessageBox.information(
            self, "Create Custom GUI",
            f"Created:\n{path}\n\n"
            "It is now selected. Use \"Edit Custom GUI\" to open it in your\n"
            "editor, then press \"Restart now\" to apply.")

    def _refresh_gpus(self):
        import graphics
        self._gpus = graphics.detect_gpus()
        self.gpu_combo.blockSignals(True)
        current = self.config.get_gpu()
        self.gpu_combo.clear()
        self.gpu_combo.addItem("System default", "")
        for g in self._gpus:
            tag = "discrete" if g.get("discrete") else "integrated"
            self.gpu_combo.addItem(f"{g['name']}  ({tag})", g["id"])
        idx = self.gpu_combo.findData(current)
        if idx >= 0:
            self.gpu_combo.setCurrentIndex(idx)
        self.gpu_combo.blockSignals(False)

    def _save_wine(self):
        data = self.wine_combo.currentData()
        if data:
            self._save_setting("wine_binary", data)
            return
        text = self.wine_combo.currentText().strip()
        if text == "Auto-detect":
            text = ""
        self._save_setting("wine_binary", text)

    def _open_setup_wizard(self):
        from gui_qt.setup_wizard import SetupWizard
        dlg = SetupWizard(self.config, self)
        if dlg.exec():
            self._refresh_gpus()

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
                # Refresh sidebar nav icon colors for the new theme
                from gui_qt import icons
                icons.refresh_nav_buttons(main_win)
                launcher = getattr(main_win, "_launcher", None)
                if launcher is not None:
                    launcher._refresh_toggle_icon()
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
            from gui_qt import icons
            for w in app.topLevelWidgets():
                if hasattr(w, 'nav_buttons'):
                    icons.refresh_nav_buttons(w)
                    launcher = getattr(w, "_launcher", None)
                    if launcher is not None:
                        launcher._refresh_toggle_icon()
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


def _find_bundled_doc(name):
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
        candidates = [base / "DOC" / name, base / "_internal" / "DOC" / name]
    else:
        root = Path(__file__).resolve().parents[3]
        candidates = [root / "DOC" / name]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _show_docs_dialog(parent, title, intro, buttons, preview_names=()):
    from PySide6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextBrowser,
    )

    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    dlg.setMinimumSize(560, 460)

    layout = QVBoxLayout(dlg)
    label = QLabel(intro)
    label.setWordWrap(True)
    layout.addWidget(label)

    browser = QTextBrowser()
    browser.setOpenExternalLinks(True)
    text = ""
    for name in preview_names:
        path = _find_bundled_doc(name)
        if path:
            try:
                text += path.read_text(encoding="utf-8") + "\n\n"
            except OSError:
                pass
    if text:
        browser.setMarkdown(text)
    else:
        browser.setHtml(
            "<p style='color:#888888'>Documentation could not be loaded locally. "
            "Use the buttons below to open it online.</p>"
        )
    layout.addWidget(browser, 1)

    row = QHBoxLayout()
    for label_text, url in buttons:
        btn = QPushButton(label_text)
        btn.setObjectName("toolBtn")
        btn.setFixedHeight(36)
        btn.clicked.connect(lambda checked=False, u=url: webbrowser.open(u))
        row.addWidget(btn)
    row.addStretch()
    close_btn = QPushButton("Close")
    close_btn.setObjectName("successBtn")
    close_btn.setFixedHeight(36)
    close_btn.clicked.connect(dlg.accept)
    row.addWidget(close_btn)
    layout.addLayout(row)

    dlg.exec()


def show_linux_docs(parent=None):
    _show_docs_dialog(
        parent,
        "Linux Setup",
        "This action needs Among Us running through Wine/Lutris on Linux.\n"
        "See the documentation below. The launcher never changes your Wine or "
        "Lutris configuration.",
        [("Open LINUX.md", LINUX_DOC_URL), ("Open WINE.md", WINE_DOC_URL)],
        preview_names=("LINUX.md", "WINE.md"),
    )


def show_wine_missing(parent=None):
    _show_docs_dialog(
        parent,
        "Wine Not Found",
        "To sign in with itch.io on Linux, Wine is required.\n"
        "Please install Wine, then try again. The launcher will not install or "
        "modify Wine for you.",
        [("Open LINUX.md", LINUX_DOC_URL), ("Open WINE.md", WINE_DOC_URL)],
        preview_names=("WINE.md", "LINUX.md"),
    )


def wine_login_gate(parent=None) -> bool:
    """Gate itch.io sign-in on Wine availability (Linux only).

    Returns ``True`` when sign-in may proceed: on Windows/macOS, when ``wine``
    is found on PATH, or when the user explicitly forces it because they already
    have Wine that wasn't auto-detected. Returns ``False`` to block sign-in.
    """
    from platform_utils import IS_LINUX, find_wine

    if not IS_LINUX or find_wine():
        return True

    while True:
        box = QMessageBox(parent)
        box.setWindowTitle("Wine Not Found")
        box.setIcon(QMessageBox.Icon.Warning)
        box.setText("To sign in with itch.io on Linux, Wine is required.\n"
                    "Please install Wine, then try again. The launcher will not "
                    "install or modify Wine for you.")
        box.setInformativeText("Already have Wine but it wasn't detected?\n"
                               "That can happen with Lutris bundles or custom "
                               "installs. Continue anyway as long as the game runs "
                               "in the configured prefix.")
        box.setStandardButtons(QMessageBox.StandardButton.Cancel)
        force_btn = box.addButton("I have Wine — Continue anyway",
                                  QMessageBox.ButtonRole.AcceptRole)
        doc_wine = box.addButton("Open WINE.md", QMessageBox.ButtonRole.ActionRole)
        doc_linux = box.addButton("Open LINUX.md", QMessageBox.ButtonRole.ActionRole)
        box.exec()
        clicked = box.clickedButton()
        if clicked is force_btn:
            return True
        if clicked is doc_wine:
            webbrowser.open(WINE_DOC_URL)
            continue
        if clicked is doc_linux:
            webbrowser.open(LINUX_DOC_URL)
            continue
        return False
