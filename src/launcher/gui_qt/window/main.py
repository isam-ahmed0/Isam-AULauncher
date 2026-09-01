"""
Window — Steam-style sidebar launcher for Isam AULauncher (PySide6).
Professional dark UI with sidebar navigation and stacked pages.
"""
import os
import sys
import logging
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QStackedWidget, QLabel, QFrame, QProgressBar,
    QStatusBar, QComboBox, QScrollArea, QSystemTrayIcon, QMenu,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QAction

from gui_qt.worker import _UISignaler, Worker
from .widgets import HeroBanner, _ICON_PATH, SIDEBAR_W
from .dialogs import SettingsDialog, AboutDialog

from config import (
    Config, APP_NAME, BRAND_SHORT, MAKER, LAUNCHER_VERSION,
)
from network import NetworkManager, DiscordRPC
from gui_qt.theme import (
    apply_theme, SUCCESS,
    INFO, DANGER, WARNING, TEXT_PRIMARY,
    TEXT_SECONDARY, TEXT_MUTED,
)
from gui_qt.game import GameManager
from gui_qt.regions import RegionManager
from gui_qt.profiles import ProfileManager

from .game_actions import GameActionsMixin
from .region_editor import RegionEditorMixin
from .mod_manager import ModManagerMixin
from .itch_profile import ItchProfileMixin
from .updater import UpdaterMixin


class LauncherApp(GameActionsMixin, RegionEditorMixin, ModManagerMixin, ItchProfileMixin, UpdaterMixin):
    def __init__(self, existing_app=None):
        self.config = Config()
        self.network = NetworkManager()
        self.discord = DiscordRPC()
        self.game = GameManager(self.config, self.network)
        self.region_mgr = RegionManager()
        self.profile_mgr = ProfileManager(self.config.profiles_dir)

        self.game.game_started.connect(self._on_game_started)
        self.game.game_stopped.connect(self._on_game_stopped)

        self.current_version = "Not Installed"
        self.latest_version = "Checking..."
        self.status_text = "Starting..."
        self.progress = 0.0
        self._busy = False
        self._active_page = "game"
        self._workers = []

        self._locate_pending = False
        self._change_location_pending = False
        self._install_folder_pending = False
        self._pending_install_path = None

        self._itch_auth_shown = False

        self._existing_app = existing_app
        self._ui_signaler = _UISignaler()
        self._ui_signaler.invoke.connect(lambda fn: fn())
        self._shutting_down = False
        self._setup_app()
        self._build_ui()
        self._setup_tray()
        self._setup_game_timer()
        self.window.closeEvent = self._close_event

    # ------------------------------------------------------------------ setup
    def _setup_app(self):
        if hasattr(self, '_existing_app') and self._existing_app:
            self.app = self._existing_app
        else:
            self.app = QApplication(sys.argv)
            apply_theme(self.app)
        if _ICON_PATH.exists():
            self.app.setWindowIcon(QIcon(str(_ICON_PATH)))

    def _setup_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self._tray = None
            return
        self._tray = QSystemTrayIcon(self.app)
        if _ICON_PATH.exists():
            self._tray.setIcon(QIcon(str(_ICON_PATH)))
        self._tray.setToolTip(APP_NAME)

        menu = QMenu()
        show_action = QAction("Show Launcher", menu)
        show_action.triggered.connect(self._show_from_tray)
        menu.addAction(show_action)

        menu.addSeparator()

        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(self._quit_from_tray)
        menu.addAction(quit_action)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def _show_from_tray(self):
        self.window.showNormal()
        self.window.activateWindow()
        self.window.raise_()

    def _quit_from_tray(self):
        self._force_quit = True
        self.window.close()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.window.isVisible():
                self.window.hide()
            else:
                self._show_from_tray()

    def _run(self, fn):
        """Run fn in a background thread."""
        w = Worker(fn)
        w.finished.connect(lambda: self._cleanup_worker(w))
        self._workers.append(w)
        w.start()

    def _cleanup_worker(self, w):
        if w in self._workers:
            self._workers.remove(w)

    def _invoke_main(self, fn):
        """Schedule fn to run on the main thread."""
        if self._shutting_down:
            return
        self._ui_signaler.invoke.emit(fn)

    def _setup_game_timer(self):
        """Poll game process state every 2 seconds."""
        self._game_timer = QTimer()
        self._game_timer.timeout.connect(self._poll_game_state)
        self._game_timer.start(2000)

    def _poll_game_state(self):
        """Check if game is still running, update button accordingly."""
        self.game.poll()
        if self.game.is_running:
            if self.main_action_btn.text() != "PLAYING":
                self._on_game_started()

    def _on_game_started(self):
        """Update UI and RPC when game launches."""
        self._update_main_btn()
        if self.discord.connected:
            self.discord.update_status("Playing Among Us", "In Game")

    def _on_game_stopped(self):
        """Update UI and RPC when game closes."""
        self._update_main_btn()
        if self.discord.connected:
            self.discord.update_status("In Launcher", "Browsing Menu")

    # ------------------------------------------------------------------ build UI
    def _build_ui(self):
        self.window = QMainWindow()
        self.window.setWindowTitle(f"{APP_NAME} v{LAUNCHER_VERSION}")
        self.window.setMinimumSize(960, 580)
        self.window.resize(1100, 680)
        if _ICON_PATH.exists():
            self.window.setWindowIcon(QIcon(str(_ICON_PATH)))

        central = QWidget()
        self.window.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(SIDEBAR_W)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 20, 12, 20)
        sidebar_layout.setSpacing(4)

        brand = QLabel(BRAND_SHORT)
        brand.setObjectName("brandLabel")
        sidebar_layout.addWidget(brand)
        app_name = QLabel(APP_NAME)
        app_name.setObjectName("brandSubLabel")
        sidebar_layout.addWidget(app_name)
        sidebar_layout.addSpacing(16)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sidebar_layout.addWidget(sep)
        sidebar_layout.addSpacing(8)

        self.pages = QStackedWidget()
        self.page_game = self._build_game_page()
        self.page_tools = self._build_tools_page()
        self.page_profile = self._build_profile_page()
        self.pages.addWidget(self.page_game)
        self.pages.addWidget(self.page_tools)
        self.pages.addWidget(self.page_profile)
        self.page_mods = self._build_mods_page()
        self.pages.addWidget(self.page_mods)

        self.nav_buttons = {}
        for label, idx in [("Game", 0), ("Tools", 1), ("Profile", 2), ("Mods", 3)]:
            btn = QPushButton(f"  {label}")
            btn.setCheckable(True)
            btn.setFixedHeight(40)
            btn.clicked.connect(lambda checked, i=idx, l=label: self._switch_page(i, l))
            sidebar_layout.addWidget(btn)
            self.nav_buttons[label] = btn

        sidebar_layout.addSpacing(8)
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sidebar_layout.addWidget(sep2)
        sidebar_layout.addSpacing(8)

        btn_settings = QPushButton("  Settings")
        btn_settings.setFixedHeight(40)
        btn_settings.clicked.connect(self._show_settings)
        sidebar_layout.addWidget(btn_settings)

        btn_about = QPushButton("  About")
        btn_about.setFixedHeight(40)
        btn_about.clicked.connect(self._show_about)
        sidebar_layout.addWidget(btn_about)

        sidebar_layout.addStretch()

        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.pages)

        self.status_bar = QStatusBar()
        self.window.setStatusBar(self.status_bar)
        self.status_icon_label = QLabel("●")
        self.status_icon_label.setObjectName("statusDot")
        self.status_text_label = QLabel("Starting...")
        self.status_text_label.setObjectName("statusText")
        self.status_bar.addWidget(self.status_icon_label)
        self.status_bar.addWidget(self.status_text_label)
        self.status_bar.addPermanentWidget(
            QLabel(f"{APP_NAME} v{LAUNCHER_VERSION} — Made by {MAKER}")
        )

        self.nav_buttons["Game"].setChecked(True)

    # ------------------------------------------------------------------ pages
    def _build_game_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        hero = HeroBanner(
            "Game Management",
            "Install, update, and manage your Among Us installation",
        )
        layout.addWidget(hero)

        profile_widget = QWidget()
        profile_layout = QHBoxLayout(profile_widget)
        profile_layout.setContentsMargins(28, 12, 28, 0)
        profile_icon = QLabel("●")
        profile_icon.setObjectName("statusDot")
        profile_icon.setStyleSheet(f"color: {TEXT_MUTED};")
        profile_layout.addWidget(profile_icon)
        self.profile_game_text = QLabel("Loading...")
        self.profile_game_text.setObjectName("profileDetail")
        profile_layout.addWidget(self.profile_game_text)
        self.profile_game_detail = QLabel("")
        self.profile_game_detail.setObjectName("profileDetail")
        profile_layout.addWidget(self.profile_game_detail)
        profile_layout.addStretch()
        layout.addWidget(profile_widget)

        btn_row = QWidget()
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(28, 16, 28, 0)
        self.main_action_btn = QPushButton("INSTALL GAME")
        self.main_action_btn.setObjectName("successBtn")
        self.main_action_btn.setFixedHeight(44)
        self.main_action_btn.clicked.connect(self._cb_main_action)
        btn_layout.addWidget(self.main_action_btn)
        layout.addWidget(btn_row)

        loc_row = QWidget()
        loc_layout = QHBoxLayout(loc_row)
        loc_layout.setContentsMargins(28, 8, 28, 0)
        self.locate_btn = QPushButton("LOCATE GAME")
        self.locate_btn.setObjectName("toolBtn")
        self.locate_btn.setFixedHeight(36)
        self.locate_btn.clicked.connect(self._cb_locate_game)
        self.locate_btn.hide()
        loc_layout.addWidget(self.locate_btn)
        layout.addWidget(loc_row)

        info_widget = QWidget()
        info_layout = QHBoxLayout(info_widget)
        info_layout.setContentsMargins(28, 16, 28, 0)

        left = QVBoxLayout()
        left.addWidget(self._muted_label("INSTALLED"))
        self.ver_installed = QLabel("Not Installed")
        self.ver_installed.setObjectName("mutedText")
        left.addWidget(self.ver_installed)
        left.addSpacing(12)
        left.addWidget(self._muted_label("LATEST"))
        self.ver_latest = QLabel("Checking...")
        self.ver_latest.setObjectName("infoText")
        left.addWidget(self.ver_latest)
        info_layout.addLayout(left)

        info_layout.addSpacing(32)

        right = QVBoxLayout()
        right.addWidget(self._muted_label("STATUS"))
        status_row = QHBoxLayout()
        self.game_status_icon = QLabel("●")
        self.game_status_icon.setObjectName("statusDot")
        self.game_status_text = QLabel("Starting...")
        self.game_status_text.setObjectName("statusText")
        status_row.addWidget(self.game_status_icon)
        status_row.addWidget(self.game_status_text)
        status_row.addStretch()
        right.addLayout(status_row)
        right.addSpacing(10)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("0%")
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFixedHeight(18)
        right.addWidget(self.progress_bar)

        self.game_ready_text = QLabel("Ready")
        self.game_ready_text.setObjectName("mutedText")
        right.addWidget(self.game_ready_text)

        info_layout.addLayout(right)
        layout.addWidget(info_widget)

        layout.addStretch()
        return page

    def _build_tools_page(self):
        page = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setObjectName("toolsScroll")

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(28, 20, 28, 20)
        layout.setSpacing(16)

        title = QLabel("TOOLS")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        row1 = QHBoxLayout()
        row1.setSpacing(8)
        for label, cb in [
            ("Open Folder", self._cb_open_folder),
            ("Change Location", self._cb_change_location),
            ("Verify Files", self._cb_verify),
        ]:
            btn = QPushButton(label)
            btn.setObjectName("toolBtn")
            btn.setFixedHeight(36)
            btn.clicked.connect(cb)
            row1.addWidget(btn)
        layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(8)
        for label, cb, obj_name in [
            ("Create Shortcut", self._cb_create_shortcut, "toolBtn"),
            ("Reinstall Game", self._cb_reinstall, "toolBtn"),
            ("Uninstall", self._cb_uninstall, "dangerBtn"),
        ]:
            btn = QPushButton(label)
            btn.setObjectName(obj_name)
            btn.setFixedHeight(36)
            btn.clicked.connect(cb)
            row2.addWidget(btn)
        layout.addLayout(row2)

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep1)

        region_title = QLabel("REGION EDITOR")
        region_title.setObjectName("sectionTitle")
        layout.addWidget(region_title)

        self._region_list = QListWidget()
        self._region_list.setObjectName("regionList")
        self._region_list.setFixedHeight(160)
        layout.addWidget(self._region_list)

        region_btn_row = QHBoxLayout()
        region_btn_row.setSpacing(8)

        add_region_btn = QPushButton("Add Region")
        add_region_btn.setObjectName("toolBtn")
        add_region_btn.setFixedHeight(36)
        add_region_btn.clicked.connect(self._cb_add_region)
        region_btn_row.addWidget(add_region_btn)

        remove_region_btn = QPushButton("Remove")
        remove_region_btn.setObjectName("dangerBtn")
        remove_region_btn.setFixedHeight(36)
        remove_region_btn.clicked.connect(self._cb_remove_region)
        region_btn_row.addWidget(remove_region_btn)

        reset_region_btn = QPushButton("Reset to Official")
        reset_region_btn.setObjectName("toolBtn")
        reset_region_btn.setFixedHeight(36)
        reset_region_btn.clicked.connect(self._cb_reset_regions)
        region_btn_row.addWidget(reset_region_btn)

        apply_region_btn = QPushButton("Apply")
        apply_region_btn.setObjectName("successBtn")
        apply_region_btn.setFixedHeight(36)
        apply_region_btn.clicked.connect(self._cb_apply_region)
        region_btn_row.addWidget(apply_region_btn)
        region_btn_row.addStretch()

        layout.addLayout(region_btn_row)

        self._region_status = QLabel("")
        self._region_status.setObjectName("statusText")
        layout.addWidget(self._region_status)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep2)

        zip_title = QLabel("ZIP EXTRACTOR")
        zip_title.setObjectName("sectionTitle")
        layout.addWidget(zip_title)

        zip_desc = QLabel("Extract mod files (BepInEx, etc.) into your game folder.")
        zip_desc.setObjectName("statusText")
        layout.addWidget(zip_desc)

        self._zip_path_label = QLabel("No zip selected")
        self._zip_path_label.setObjectName("mutedText")
        layout.addWidget(self._zip_path_label)

        zip_btn_row = QHBoxLayout()
        zip_btn_row.setSpacing(8)

        select_zip_btn = QPushButton("Select Zip")
        select_zip_btn.setObjectName("toolBtn")
        select_zip_btn.setFixedHeight(36)
        select_zip_btn.clicked.connect(self._cb_select_zip)
        zip_btn_row.addWidget(select_zip_btn)

        extract_zip_btn = QPushButton("Extract to Game Folder")
        extract_zip_btn.setObjectName("successBtn")
        extract_zip_btn.setFixedHeight(36)
        extract_zip_btn.clicked.connect(self._cb_extract_zip)
        zip_btn_row.addWidget(extract_zip_btn)
        zip_btn_row.addStretch()

        layout.addLayout(zip_btn_row)

        self._zip_contents_label = QLabel("")
        self._zip_contents_label.setObjectName("mutedText")
        self._zip_contents_label.setWordWrap(True)
        layout.addWidget(self._zip_contents_label)

        self._zip_progress = QProgressBar()
        self._zip_progress.setRange(0, 100)
        self._zip_progress.setValue(0)
        self._zip_progress.setFixedHeight(18)
        self._zip_progress.hide()
        layout.addWidget(self._zip_progress)

        layout.addStretch()

        scroll.setWidget(content)
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        self._load_region_list()

        return page

    def _build_mods_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 20, 28, 20)
        layout.setSpacing(16)

        title = QLabel("MODS")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        desc = QLabel("Manage BepInEx mod profiles for Among Us.\nEach profile is an isolated set of mods — zero file duplication.")
        desc.setObjectName("statusText")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        layout.addSpacing(8)

        bep_title = QLabel("BepInEx Setup")
        bep_title.setObjectName("sectionTitle")
        layout.addWidget(bep_title)

        self._bep_status = QLabel("")
        self._bep_status.setObjectName("statusText")
        layout.addWidget(self._bep_status)

        bep_btn_row = QHBoxLayout()
        bep_btn_row.setSpacing(8)

        self._bep_setup_btn = QPushButton("Setup BepInEx")
        self._bep_setup_btn.setObjectName("successBtn")
        self._bep_setup_btn.setFixedHeight(36)
        self._bep_setup_btn.clicked.connect(self._cb_setup_bepinex)
        bep_btn_row.addWidget(self._bep_setup_btn)

        bep_btn_row.addStretch()
        layout.addLayout(bep_btn_row)

        layout.addSpacing(4)
        layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine))
        layout.addSpacing(4)

        prof_title = QLabel("MOD PROFILES")
        prof_title.setObjectName("sectionTitle")
        layout.addWidget(prof_title)

        prof_sel_row = QHBoxLayout()
        prof_sel_row.setSpacing(8)

        self._profile_combo = QComboBox()
        self._profile_combo.setFixedHeight(36)
        self._profile_combo.setMinimumWidth(200)
        self._profile_combo.currentTextChanged.connect(self._on_profile_selected)
        prof_sel_row.addWidget(self._profile_combo)

        create_btn = QPushButton("Create")
        create_btn.setObjectName("toolBtn")
        create_btn.setFixedHeight(36)
        create_btn.clicked.connect(self._cb_create_profile)
        prof_sel_row.addWidget(create_btn)

        rename_btn = QPushButton("Rename")
        rename_btn.setObjectName("toolBtn")
        rename_btn.setFixedHeight(36)
        rename_btn.clicked.connect(self._cb_rename_profile)
        prof_sel_row.addWidget(rename_btn)

        delete_btn = QPushButton("Delete")
        delete_btn.setObjectName("dangerBtn")
        delete_btn.setFixedHeight(36)
        delete_btn.clicked.connect(self._cb_delete_profile)
        prof_sel_row.addWidget(delete_btn)

        prof_sel_row.addStretch()
        layout.addLayout(prof_sel_row)

        self._profile_active_label = QLabel("")
        self._profile_active_label.setObjectName("statusText")
        layout.addWidget(self._profile_active_label)

        switch_row = QHBoxLayout()
        switch_row.setSpacing(8)

        self._profile_switch_btn = QPushButton("Switch to This Profile")
        self._profile_switch_btn.setObjectName("primaryBtn")
        self._profile_switch_btn.setFixedHeight(36)
        self._profile_switch_btn.clicked.connect(self._cb_switch_profile)
        switch_row.addWidget(self._profile_switch_btn)

        switch_row.addStretch()
        layout.addLayout(switch_row)

        layout.addSpacing(4)
        layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine))
        layout.addSpacing(4)

        mods_title = QLabel("MODS IN PROFILE")
        mods_title.setObjectName("sectionTitle")
        layout.addWidget(mods_title)

        self._mods_list = QListWidget()
        self._mods_list.setObjectName("modsList")
        self._mods_list.setMinimumHeight(120)
        layout.addWidget(self._mods_list)

        mods_btn_row = QHBoxLayout()
        mods_btn_row.setSpacing(8)

        refresh_mods_btn = QPushButton("Refresh")
        refresh_mods_btn.setObjectName("toolBtn")
        refresh_mods_btn.setFixedHeight(36)
        refresh_mods_btn.clicked.connect(self._cb_refresh_mods)
        mods_btn_row.addWidget(refresh_mods_btn)

        add_mods_btn = QPushButton("Add Mod Files")
        add_mods_btn.setObjectName("successBtn")
        add_mods_btn.setFixedHeight(36)
        add_mods_btn.clicked.connect(self._cb_add_mods)
        mods_btn_row.addWidget(add_mods_btn)

        move_mods_btn = QPushButton("Move to...")
        move_mods_btn.setObjectName("toolBtn")
        move_mods_btn.setFixedHeight(36)
        move_mods_btn.clicked.connect(self._cb_move_mods)
        mods_btn_row.addWidget(move_mods_btn)

        remove_mods_btn = QPushButton("Remove Selected")
        remove_mods_btn.setObjectName("dangerBtn")
        remove_mods_btn.setFixedHeight(36)
        remove_mods_btn.clicked.connect(self._cb_remove_mods)
        mods_btn_row.addWidget(remove_mods_btn)

        info_mods_btn = QPushButton("Info")
        info_mods_btn.setObjectName("toolBtn")
        info_mods_btn.setFixedHeight(36)
        info_mods_btn.clicked.connect(self._cb_mod_info)
        mods_btn_row.addWidget(info_mods_btn)

        mods_btn_row.addStretch()
        layout.addLayout(mods_btn_row)

        self._mods_status = QLabel("")
        self._mods_status.setObjectName("statusText")
        layout.addWidget(self._mods_status)

        layout.addStretch()

        self._update_bep_status()
        self._run_first_time_migration()
        self._refresh_profile_list()

        return page

    def _build_profile_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        hero = HeroBanner(
            "ITCH.IO PROFILE",
            "Your itch.io account and Among Us identity",
        )
        layout.addWidget(hero)

        card = QFrame()
        card.setObjectName("profileCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 24, 28, 24)
        card_layout.setSpacing(12)

        self.profile_page_name = QLabel("Loading...")
        self.profile_page_name.setObjectName("profileName")
        card_layout.addWidget(self.profile_page_name)

        self.profile_page_status = QLabel("Checking login...")
        self.profile_page_status.setObjectName("profileStatus")
        card_layout.addWidget(self.profile_page_status)

        card_layout.addSpacing(4)
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        card_layout.addWidget(sep)
        card_layout.addSpacing(4)

        self.profile_page_au = QLabel("")
        self.profile_page_au.setObjectName("profileDetail")
        card_layout.addWidget(self.profile_page_au)

        self.profile_page_platforms = QLabel("")
        self.profile_page_platforms.setObjectName("profileDetail")
        card_layout.addWidget(self.profile_page_platforms)

        card_layout.addStretch()

        card_wrapper = QWidget()
        card_wrapper_layout = QVBoxLayout(card_wrapper)
        card_wrapper_layout.setContentsMargins(28, 20, 28, 0)
        card_wrapper_layout.addWidget(card)
        layout.addWidget(card_wrapper)

        layout.addStretch()
        return page

    # ------------------------------------------------------------------ helpers
    def _muted_label(self, text):
        lbl = QLabel(text)
        lbl.setObjectName("sectionTitle")
        return lbl

    def _switch_page(self, index, label):
        self.pages.setCurrentIndex(index)
        self._active_page = label.lower()
        for name, btn in self.nav_buttons.items():
            btn.setChecked(name == label)

    # ------------------------------------------------------------------ status
    def _set_status(self, text, color_name=None):
        self.status_text = text
        self.game_status_text.setText(text)
        self.status_text_label.setText(text)
        if color_name:
            color_map = {
                "success": SUCCESS, "info": INFO,
                "danger": DANGER, "warning": WARNING,
            }
            c = color_map.get(color_name, TEXT_SECONDARY)
            self.game_status_icon.setStyleSheet(f"color: {c};")
            self.status_icon_label.setStyleSheet(f"color: {c};")

    def _set_status_color(self, color_hex):
        self.game_status_icon.setStyleSheet(f"color: {color_hex};")
        self.status_icon_label.setStyleSheet(f"color: {color_hex};")

    def _update_progress(self, pct):
        self.progress = pct
        self.progress_bar.setValue(int(pct))
        self.progress_bar.setFormat(f"{pct:.0f}%")

    def _update_version_display(self):
        self.ver_installed.setText(self.current_version)
        if self.current_version and self.current_version not in ("Not Installed", "Unknown"):
            self.ver_installed.setObjectName("successText")
        else:
            self.ver_installed.setObjectName("mutedText")
        self.ver_installed.style().polish(self.ver_installed)
        self.ver_latest.setText(self.latest_version)

    def _update_main_btn(self):
        if self.game.is_running:
            self.main_action_btn.setText("PLAYING")
            self.main_action_btn.setObjectName("dangerBtn")
            self.main_action_btn.style().polish(self.main_action_btn)
            self.locate_btn.hide()
            return

        cur = self.current_version
        lat = self.latest_version
        gp = self.config.get_game_path()
        if cur == "Not Installed" or not gp or not (gp / "Among Us.exe").exists():
            self.main_action_btn.setText("INSTALL GAME")
            self.main_action_btn.setObjectName("successBtn")
            self.main_action_btn.style().polish(self.main_action_btn)
            self.locate_btn.show()
        elif cur != lat and lat != "Checking...":
            self.main_action_btn.setText("UPDATE AVAILABLE")
            self.main_action_btn.setObjectName("primaryBtn")
            self.main_action_btn.style().polish(self.main_action_btn)
            self.locate_btn.hide()
        else:
            self.main_action_btn.setText("LAUNCH GAME")
            self.main_action_btn.setObjectName("successBtn")
            self.main_action_btn.style().polish(self.main_action_btn)
            self.locate_btn.hide()

    def _busy_on(self):
        self._busy = True
        self.main_action_btn.setEnabled(False)

    def _busy_off(self):
        self._busy = False
        self.main_action_btn.setEnabled(True)

    # ------------------------------------------------------------------ modals
    def _show_settings(self):
        dlg = SettingsDialog(self.config, self.discord, self.profile_mgr, self.window)
        dlg.exec()

    def _show_about(self):
        dlg = AboutDialog(self.window)
        dlg.exec()

    # ------------------------------------------------------------------ run
    def run(self):
        self.window.show()
        self._load_itch_profile()

    # ------------------------------------------------------------------ shutdown
    def _close_event(self, event):
        """Minimize to tray instead of closing. Force-quit from tray menu."""
        if getattr(self, '_force_quit', False):
            self.shutdown()
            if self._tray:
                self._tray.hide()
            event.accept()
            os._exit(0)
        if self._tray and self._tray.isVisible():
            event.ignore()
            self.window.hide()
            self._tray.showMessage(
                APP_NAME,
                "Launcher minimized to tray. Right-click to restore or quit.",
                QSystemTrayIcon.MessageIcon.Information,
                2000,
            )
        else:
            self.shutdown()
            event.accept()

    def shutdown(self):
        """Stop all background tasks, disconnect services."""
        if self._shutting_down:
            return
        self._shutting_down = True
        try:
            if hasattr(self, '_game_timer') and self._game_timer:
                self._game_timer.stop()
        except Exception:
            pass
        try:
            if self.game and self.game.is_running:
                self.game.stop()
        except Exception:
            pass
        try:
            self.discord.disconnect()
        except Exception:
            pass
        try:
            self.network.session.close()
        except Exception:
            pass
        for w in list(self._workers):
            try:
                w.wait(2000)
            except Exception:
                pass
