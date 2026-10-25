"""
Window — Steam-style sidebar launcher for CrewLauncher (PySide6).
Professional dark UI with sidebar navigation and stacked pages.
"""
import os
import sys
import logging
from pathlib import Path

from .game_actions import GameActionsMixin
from .region_editor import RegionEditorMixin
from .mod_manager import ModManagerMixin
from .itch_profile import ItchProfileMixin
from .updater import UpdaterMixin
from ..assets_manager import AssetsManagerMixin


class LauncherApp(GameActionsMixin, RegionEditorMixin, ModManagerMixin, ItchProfileMixin, UpdaterMixin, AssetsManagerMixin):
    def __init__(self, existing_app=None):
        # Import heavy modules lazily
        from PySide6.QtWidgets import QApplication
        from config import Config
        from network import NetworkManager, DiscordRPC
        from gui_qt.game import GameManager
        from gui_qt.regions import RegionManager
        from gui_qt.profiles import ProfileManager
        import gui_qt.theme as theme
        from gui_qt.theme import apply_theme
        from gui_qt.worker import _UISignaler
        
        self.config = Config()
        try:
            from platform_utils import set_lutris_override
            set_lutris_override(self.config.get_lutris_cmd_override(), persist=False)
        except Exception:
            logging.exception("Failed to load Lutris override")
        self.network = NetworkManager()
        self.discord = DiscordRPC()
        self.game = GameManager(self.config, self.network)
        self.region_mgr = RegionManager()
        self.profile_mgr = ProfileManager(self.config.profiles_dir)

        self.game.game_started.connect(self._on_game_started)
        self.game.game_stopped.connect(self._on_game_stopped)

        self.current_version = "Not Installed"
        self.latest_version = "Checking..."
        self.available_versions = []
        self._releases_error = None
        self.status_text = "Starting..."
        self.progress = 0.0
        self._busy = False
        self._active_page = "game"
        self._workers = []

        self._locate_pending = False
        self._change_location_pending = False
        self._install_folder_pending = False
        self._pending_install_path = None

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

        # ---- sidebar: fixed icon-only rail ----
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(SIDEBAR_W)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 14, 0, 14)
        sidebar_layout.setSpacing(6)
        sidebar_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._sidebar = sidebar

        self.nav_buttons = {}
        self.nav_icon_names = {}
        for label, idx, icon_name in [
            ("Home", 0, "game-controller"),
            ("Assets", 6, "package"),
            ("Tools", 1, "wrench"),
            ("Profile", 2, "user-circle"),
            ("Settings", 4, "gear"),
            ("About", 5, "info"),
        ]:
            btn = QPushButton()
            btn.setCheckable(True)
            btn.setFixedSize(52, 52)
            btn.setIcon(icons.nav_icon(icon_name))
            btn.setIconSize(QSize(24, 24))
            btn.setToolTip(label)
            btn._nav_icon_name = icon_name
            btn.clicked.connect(lambda checked, i=idx, l=label: self._switch_page(i, l))
            sidebar_layout.addWidget(btn, 0, Qt.AlignmentFlag.AlignHCenter)
            self.nav_buttons[label] = btn
            self.nav_icon_names[label] = icon_name
            enable_hover_glow(btn)

        sidebar_layout.addStretch()

        # ---- right column: global header + stacked pages ----
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        right_layout.addWidget(self._build_header())

        self.pages = QStackedWidget()
        self.page_game = self._build_game_page()
        self.page_tools = self._build_tools_page()
        self.page_profile = self._build_profile_page()
        self.page_mods = self._build_mods_page()
        self.page_settings = SettingsPage(self.config, self.discord, self.profile_mgr)
        self.page_about = AboutPage()
        self.page_assets = self._build_assets_page()
        self.pages.addWidget(self.page_game)
        self.pages.addWidget(self.page_tools)
        self.pages.addWidget(self.page_profile)
        self.pages.addWidget(self.page_mods)
        self.pages.addWidget(self.page_settings)
        self.pages.addWidget(self.page_about)
        self.pages.addWidget(self.page_assets)

        right_layout.addWidget(self.pages, 1)

        main_layout.addWidget(sidebar)
        main_layout.addWidget(right, 1)

        self.window.nav_buttons = self.nav_buttons
        self.window._launcher = self

        self.status_bar = QStatusBar()
        self.status_bar.setFixedHeight(40)
        self.status_bar.setSizeGripEnabled(False)
        self.window.setStatusBar(self.status_bar)
        self.status_icon_label = QLabel("●")
        self.status_icon_label.setObjectName("statusDot")
        self.status_text_label = QLabel("Starting...")
        self.status_text_label.setObjectName("statusText")
        self.status_bar.addWidget(self.status_icon_label)
        self.status_bar.addWidget(self.status_text_label)

        # These used to live inside the Game card. They now sit in the status bar
        # so the Home card stays minimal while every existing binding keeps working.
        self.game_status_icon = self.status_icon_label
        self.game_status_text = self.status_text_label

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("0%")
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFixedWidth(160)
        self.progress_bar.setFixedHeight(14)
        self.progress_bar.hide()
        self.status_bar.addWidget(self.progress_bar)

        self.ver_latest = QLabel("Latest: Checking...")
        self.ver_latest.setObjectName("infoText")
        self.status_bar.addPermanentWidget(self.ver_latest)

        self.gfx_text = QLabel("")
        self.gfx_text.setObjectName("mutedText")
        self.status_bar.addPermanentWidget(self.gfx_text)

        self.choose_version_btn = QPushButton("Versions")
        self.choose_version_btn.setObjectName("statusBtn")
        self.choose_version_btn.clicked.connect(self._open_version_picker)
        self.status_bar.addPermanentWidget(self.choose_version_btn)

        self.locate_btn = QPushButton("LOCATE GAME")
        self.locate_btn.setObjectName("statusBtn")
        self.locate_btn.clicked.connect(self._cb_locate_game)
        self.locate_btn.hide()
        self.status_bar.addPermanentWidget(self.locate_btn)

        permanent_label = QLabel(f"{APP_NAME} v{LAUNCHER_VERSION} — Made by {MAKER}")
        permanent_label.setObjectName("footerText")
        self.status_bar.addPermanentWidget(permanent_label)

        self.nav_buttons["Home"].setChecked(True)

    def _build_header(self):
        """Global top bar: brand on the left, itch user + launcher version right."""
        header = QWidget()
        header.setObjectName("topHeader")
        header.setFixedHeight(56)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(12)

        brand = QLabel("CREW LAUNCHER")
        brand.setObjectName("headerBrand")
        layout.addWidget(brand)
        layout.addStretch()

        user_box = QVBoxLayout()
        user_box.setSpacing(0)
        self.profile_game_text = QLabel("Loading...")
        self.profile_game_text.setObjectName("headerUser")
        self.profile_game_text.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.profile_game_detail = QLabel("")
        self.profile_game_detail.setObjectName("headerUserDetail")
        self.profile_game_detail.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        user_box.addWidget(self.profile_game_text)
        user_box.addWidget(self.profile_game_detail)
        layout.addLayout(user_box)

        self.launcher_version_label = QLabel(f"v{LAUNCHER_VERSION}")
        self.launcher_version_label.setObjectName("launcherVersion")
        layout.addWidget(self.launcher_version_label)
        return header

    def _refresh_nav_icons(self):
        icons.refresh_nav_buttons(self.window)

    def _refresh_toggle_icon(self):
        # Sidebar is now a fixed icon rail; keep this hook for theme switching.
        self._refresh_nav_icons()

    # ------------------------------------------------------------------ home page
    def _build_game_page(self):
        page = QWidget()
        page.setObjectName("homePage")
        outer = QVBoxLayout(page)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(16)

        grid = QGridLayout()
        grid.setSpacing(16)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setRowStretch(0, 1)
        grid.setRowStretch(1, 1)

        grid.addWidget(self._build_game_card(), 0, 0)
        grid.addWidget(self._build_custom_card(), 0, 1)
        grid.addWidget(self._build_mods_card(), 1, 0)
        grid.addWidget(self._build_tools_card(), 1, 1)

        outer.addLayout(grid)
        self._update_game_size()
        return page

    def _build_game_card(self):
        card = QFrame()
        card.setObjectName("homeGamePanel")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(10)

        title = QLabel("Among Us")
        title.setObjectName("homeGameTitle")
        layout.addWidget(title)

        layout.addSpacing(6)

        self.ver_installed = QLabel("Version: Not Installed")
        self.ver_installed.setObjectName("homeCardValue")
        layout.addWidget(self.ver_installed)

        self.game_size_text = QLabel("Size: —")
        self.game_size_text.setObjectName("homeCardValue")
        layout.addWidget(self.game_size_text)

        layout.addStretch()

        self.main_action_btn = QPushButton("INSTALL GAME")
        self.main_action_btn.setObjectName("homeSuccessBtn")
        self.main_action_btn.setMinimumHeight(54)
        self.main_action_btn.clicked.connect(self._cb_main_action)
        layout.addWidget(self.main_action_btn)

        return card

    def _build_custom_card(self):
        card = QFrame()
        card.setObjectName("homeCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(16)

        header = QHBoxLayout()
        header.setSpacing(10)
        title = QLabel("CUSTOM")
        title.setObjectName("homeCardSubtitle")
        header.addWidget(title)
        header.addStretch()

        img_btn = QPushButton("Image")
        img_btn.setObjectName("homeToolBtn")
        img_btn.clicked.connect(self._cb_set_home_image)
        header.addWidget(img_btn)

        note_btn = QPushButton("Note")
        note_btn.setObjectName("homeToolBtn")
        note_btn.clicked.connect(self._cb_set_home_note)
        header.addWidget(note_btn)
        layout.addLayout(header)

        self.custom_media = CoverLabel()
        self.custom_media.setObjectName("homeCustomMedia")
        self.custom_media.setMinimumHeight(150)
        layout.addWidget(self.custom_media, 1)

        self._render_custom_card()
        return card

    def _build_mods_card(self):
        card = QFrame()
        card.setObjectName("homeCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(10)

        title = QLabel("Mods")
        title.setObjectName("homeCardTitle")
        layout.addWidget(title)

        layout.addSpacing(4)

        self.home_profile_label = QLabel("Profile: —")
        self.home_profile_label.setObjectName("homeCardValue")
        layout.addWidget(self.home_profile_label)

        self.home_mods_count_label = QLabel("Mods: —")
        self.home_mods_count_label.setObjectName("homeCardValue")
        layout.addWidget(self.home_mods_count_label)

        layout.addStretch()

        manage_btn = QPushButton("Manage Mods")
        manage_btn.setObjectName("homeToolBtn")
        manage_btn.setMinimumHeight(48)
        manage_btn.clicked.connect(lambda: self._switch_page(3, "Mods"))
        layout.addWidget(manage_btn)

        self._refresh_home_mods_card()
        return card

    def _build_tools_card(self):
        card = QFrame()
        card.setObjectName("homeCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(10)

        title = QLabel("Tools")
        title.setObjectName("homeCardTitle")
        layout.addWidget(title)
        subtitle = QLabel("Quick Tools")
        subtitle.setObjectName("homeCardSubtitle")
        layout.addWidget(subtitle)

        layout.addStretch()

        btn_grid = QGridLayout()
        btn_grid.setSpacing(12)
        for label, cb, obj_name, r, c in [
            ("Change Location", self._cb_change_location, "homeToolBtn", 0, 0),
            ("Create Shortcut", self._cb_create_shortcut, "homeToolBtn", 0, 1),
            ("Open Folder", self._cb_open_folder, "homeToolBtn", 1, 0),
            ("Uninstall", self._cb_uninstall, "homeDangerBtn", 1, 1),
        ]:
            btn = QPushButton(label)
            btn.setObjectName(obj_name)
            btn.setMinimumHeight(48)
            btn.clicked.connect(cb)
            btn_grid.addWidget(btn, r, c)
        layout.addLayout(btn_grid)

        return card

    # ------------------------------------------------------------------ home cards data
    def _refresh_home_mods_card(self):
        if not hasattr(self, "home_profile_label"):
            return
        active = self.config.get_active_profile()
        self.home_profile_label.setText(f"Profile: {active}")
        count = 0
        try:
            profile_dir = self.profile_mgr.profile_path(active)
            if profile_dir.exists():
                count = len(list(profile_dir.glob("*.dll")))
        except Exception:
            count = 0
        self.home_mods_count_label.setText(f"Mods: {count}")

    def _update_game_size(self):
        if not hasattr(self, "game_size_text"):
            return
        gp = self.config.get_game_path()
        if not gp or not (gp / "Among Us.exe").exists():
            self.game_size_text.setText("Size: —")
            return

        def compute():
            from file_manager import FileManager
            total = 0
            try:
                for f in gp.rglob("*"):
                    if f.is_file():
                        total += f.stat().st_size
            except OSError:
                pass
            text = FileManager.format_size(total)
            self._invoke_main(lambda: self.game_size_text.setText(f"Size: {text}"))

        self._run(compute)

    # ------------------------------------------------------------------ custom card
    def _cb_set_home_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self.window, "Choose Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;All Files (*)",
        )
        if not path:
            return
        self.config.settings["home_image_path"] = path
        self.config.save_settings()
        self._render_custom_card()

    def _cb_set_home_note(self):
        note, ok = QInputDialog.getMultiLineText(
            self.window, "Custom Note", "Text to show on your Home card:",
            self.config.settings.get("home_note", ""),
        )
        if not ok:
            return
        self.config.settings["home_note"] = note
        self.config.save_settings()
        self._render_custom_card()

    def _render_custom_card(self):
        if not hasattr(self, "custom_media"):
            return
        img = (self.config.settings.get("home_image_path") or "").strip()
        note = (self.config.settings.get("home_note") or "").strip()
        if img and Path(img).exists():
            pm = QPixmap(img)
            if not pm.isNull():
                self.custom_media.set_image(pm)
                return
        if note:
            self.custom_media.set_text(note)
            return
        self.custom_media.set_text(
            "No custom image or note yet.\nUse Image / Note to add one."
        )

    def _build_tools_page(self):
        page = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setObjectName("toolsScroll")

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(32, 20, 32, 20)
        layout.setSpacing(16)

        title = QLabel("TOOLS")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        row1 = QHBoxLayout()
        row1.setSpacing(10)
        for label, cb in [
            ("Open Folder", self._cb_open_folder),
            ("Change Location", self._cb_change_location),
            ("Verify Files", self._cb_verify),
        ]:
            btn = QPushButton(label)
            btn.setObjectName("toolBtn")
            btn.setFixedHeight(38)
            btn.clicked.connect(cb)
            row1.addWidget(btn)
        layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(10)
        for label, cb, obj_name in [
            ("Create Shortcut", self._cb_create_shortcut, "toolBtn"),
            ("Reinstall Game", self._cb_reinstall, "toolBtn"),
            ("Uninstall", self._cb_uninstall, "dangerBtn"),
        ]:
            btn = QPushButton(label)
            btn.setObjectName(obj_name)
            btn.setFixedHeight(38)
            btn.clicked.connect(cb)
            row2.addWidget(btn)
        layout.addLayout(row2)

        from platform_utils import IS_LINUX
        if IS_LINUX:
            row_linux = QHBoxLayout()
            row_linux.setSpacing(10)
            btn = QPushButton("Run Setup")
            btn.setObjectName("toolBtn")
            btn.setFixedHeight(38)
            btn.clicked.connect(self._run_setup_wizard)
            row_linux.addWidget(btn)
            layout.addLayout(row_linux)

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep1)

        region_title = QLabel("REGION EDITOR")
        region_title.setObjectName("sectionTitle")
        layout.addWidget(region_title)

        self._region_list = QListWidget()
        self._region_list.setObjectName("regionList")
        self._region_list.setMinimumHeight(100)
        self._region_list.setMaximumHeight(250)
        layout.addWidget(self._region_list)

        region_btn_row = QHBoxLayout()
        region_btn_row.setSpacing(10)

        add_region_btn = QPushButton("Add Region")
        add_region_btn.setObjectName("toolBtn")
        add_region_btn.setFixedHeight(38)
        add_region_btn.clicked.connect(self._cb_add_region)
        region_btn_row.addWidget(add_region_btn)

        remove_region_btn = QPushButton("Remove")
        remove_region_btn.setObjectName("dangerBtn")
        remove_region_btn.setFixedHeight(38)
        remove_region_btn.clicked.connect(self._cb_remove_region)
        region_btn_row.addWidget(remove_region_btn)

        reset_region_btn = QPushButton("Reset to Official")
        reset_region_btn.setObjectName("toolBtn")
        reset_region_btn.setFixedHeight(38)
        reset_region_btn.clicked.connect(self._cb_reset_regions)
        region_btn_row.addWidget(reset_region_btn)

        apply_region_btn = QPushButton("Apply")
        apply_region_btn.setObjectName("successBtn")
        apply_region_btn.setFixedHeight(38)
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
        zip_btn_row.setSpacing(10)

        select_zip_btn = QPushButton("Select Zip")
        select_zip_btn.setObjectName("toolBtn")
        select_zip_btn.setFixedHeight(38)
        select_zip_btn.clicked.connect(self._cb_select_zip)
        zip_btn_row.addWidget(select_zip_btn)

        extract_zip_btn = QPushButton("Extract to Game Folder")
        extract_zip_btn.setObjectName("successBtn")
        extract_zip_btn.setFixedHeight(38)
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
        self._zip_progress.setFixedHeight(16)
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
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(32, 20, 32, 20)
        layout.setSpacing(16)

        title = QLabel("MODS")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        desc = QLabel("Manage BepInEx mod profiles for Among Us.\nEach profile is an isolated set of mods — zero file duplication.")
        desc.setObjectName("bodyText")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        layout.addSpacing(8)

        layout.addSpacing(8)
        layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine))
        layout.addSpacing(8)

        prof_title = QLabel("MOD PROFILES")
        prof_title.setObjectName("sectionTitle")
        layout.addWidget(prof_title)

        prof_sel_row = QHBoxLayout()
        prof_sel_row.setSpacing(10)

        self._profile_combo = QComboBox()
        self._profile_combo.setFixedHeight(38)
        self._profile_combo.setMinimumWidth(200)
        self._profile_combo.currentTextChanged.connect(self._on_profile_selected)
        prof_sel_row.addWidget(self._profile_combo)

        create_btn = QPushButton("Create")
        create_btn.setObjectName("toolBtn")
        create_btn.setFixedHeight(38)
        create_btn.clicked.connect(self._cb_create_profile)
        prof_sel_row.addWidget(create_btn)

        rename_btn = QPushButton("Rename")
        rename_btn.setObjectName("toolBtn")
        rename_btn.setFixedHeight(38)
        rename_btn.clicked.connect(self._cb_rename_profile)
        prof_sel_row.addWidget(rename_btn)

        delete_btn = QPushButton("Delete")
        delete_btn.setObjectName("dangerBtn")
        delete_btn.setFixedHeight(38)
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
        self._profile_switch_btn.setFixedHeight(38)
        self._profile_switch_btn.clicked.connect(self._cb_switch_profile)
        switch_row.addWidget(self._profile_switch_btn)

        switch_row.addStretch()
        layout.addLayout(switch_row)

        layout.addSpacing(8)
        layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine))
        layout.addSpacing(8)

        mods_title = QLabel("MODS IN PROFILE")
        mods_title.setObjectName("sectionTitle")
        layout.addWidget(mods_title)

        self._mods_list = QListWidget()
        self._mods_list.setObjectName("modsList")
        self._mods_list.setMinimumHeight(120)
        layout.addWidget(self._mods_list)

        mods_btn_row = QHBoxLayout()
        mods_btn_row.setSpacing(10)

        refresh_mods_btn = QPushButton("Refresh")
        refresh_mods_btn.setObjectName("toolBtn")
        refresh_mods_btn.setFixedHeight(38)
        refresh_mods_btn.clicked.connect(self._cb_refresh_mods)
        mods_btn_row.addWidget(refresh_mods_btn)

        add_mods_btn = QPushButton("Add Mod Files")
        add_mods_btn.setObjectName("successBtn")
        add_mods_btn.setFixedHeight(38)
        add_mods_btn.clicked.connect(self._cb_add_mods)
        mods_btn_row.addWidget(add_mods_btn)

        move_mods_btn = QPushButton("Move to...")
        move_mods_btn.setObjectName("toolBtn")
        move_mods_btn.setFixedHeight(38)
        move_mods_btn.clicked.connect(self._cb_move_mods)
        mods_btn_row.addWidget(move_mods_btn)

        remove_mods_btn = QPushButton("Remove Selected")
        remove_mods_btn.setObjectName("dangerBtn")
        remove_mods_btn.setFixedHeight(38)
        remove_mods_btn.clicked.connect(self._cb_remove_mods)
        mods_btn_row.addWidget(remove_mods_btn)

        info_mods_btn = QPushButton("Info")
        info_mods_btn.setObjectName("toolBtn")
        info_mods_btn.setFixedHeight(38)
        info_mods_btn.clicked.connect(self._cb_mod_info)
        mods_btn_row.addWidget(info_mods_btn)

        mods_btn_row.addStretch()
        layout.addLayout(mods_btn_row)

        self._mods_status = QLabel("")
        self._mods_status.setObjectName("statusText")
        layout.addWidget(self._mods_status)

        layout.addStretch()

        self._run_first_time_migration()
        self._refresh_profile_list()

        scroll.setWidget(content)
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        return page

    def _build_profile_page(self):
        page = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._hero_profile = HeroBanner(
            "ITCH.IO PROFILE",
            "Your itch.io account and Among Us identity",
        )
        layout.addWidget(self._hero_profile)

        card = QFrame()
        card.setObjectName("profileCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(32, 24, 32, 24)
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
        card_wrapper_layout.setContentsMargins(32, 20, 32, 0)
        card_wrapper_layout.addWidget(card)
        layout.addWidget(card_wrapper)

        btn_row = QWidget()
        btn_row_layout = QHBoxLayout(btn_row)
        btn_row_layout.setContentsMargins(32, 12, 32, 0)
        self._itch_login_btn = QPushButton("Login with itch.io")
        self._itch_login_btn.setObjectName("successBtn")
        self._itch_login_btn.setFixedHeight(38)
        self._itch_login_btn.setMinimumWidth(200)
        self._itch_login_btn.clicked.connect(self.open_itch_fixer)
        btn_row_layout.addWidget(self._itch_login_btn)
        btn_row_layout.addStretch()
        layout.addWidget(btn_row)

        layout.addStretch()

        scroll.setWidget(content)
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        return page

    # ------------------------------------------------------------------ helpers
    def _muted_label(self, text):
        lbl = QLabel(text)
        lbl.setObjectName("sectionTitle")
        return lbl

    def _switch_page(self, index, label):
        if self.pages.currentIndex() == index:
            return

        effect = QGraphicsOpacityEffect(self.pages)
        self.pages.setGraphicsEffect(effect)

        fade_out = QPropertyAnimation(effect, b"opacity", self.pages)
        fade_out.setDuration(90)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.Type.InCubic)

        def _swap():
            self.pages.setCurrentIndex(index)
            self._active_page = label.lower()
            if label == "Assets" and hasattr(self, "assets_page"):
                try:
                    self.assets_page.refresh()
                except Exception:
                    logging.exception("Failed to refresh assets page")
            effective = label if label in self.nav_buttons else "Home"
            for name, btn in self.nav_buttons.items():
                btn.setChecked(name == effective)
            fade_in = QPropertyAnimation(effect, b"opacity", self.pages)
            fade_in.setDuration(120)
            fade_in.setStartValue(0.0)
            fade_in.setEndValue(1.0)
            fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)
            fade_in.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
            self._page_anim_ref = fade_in

        fade_out.finished.connect(_swap)
        fade_out.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        self._page_anim_ref = fade_out

    # ------------------------------------------------------------------ status
    def _set_status(self, text, color_name=None):
        self.status_text = text
        self.game_status_text.setText(text)
        self.status_text_label.setText(text)
        if color_name:
            color_map = {
                "success": theme.SUCCESS, "info": theme.INFO,
                "danger": theme.DANGER, "warning": theme.WARNING,
            }
            c = color_map.get(color_name, theme.TEXT_SECONDARY)
            self.game_status_icon.setStyleSheet(f"color: {c};")
            self.status_icon_label.setStyleSheet(f"color: {c};")

    def _set_status_color(self, color_hex):
        self.game_status_icon.setStyleSheet(f"color: {color_hex};")
        self.status_icon_label.setStyleSheet(f"color: {color_hex};")

    def _update_progress(self, pct):
        self.progress = pct
        self.progress_bar.setValue(int(pct))
        self.progress_bar.setFormat(f"{pct:.0f}%")
        self.progress_bar.setVisible(pct > 0)

    def _update_version_display(self):
        self.ver_installed.setText(f"Version: {self.current_version}")
        installed = bool(self.current_version) and self.current_version not in ("Not Installed", "Unknown")
        self.ver_installed.setProperty("state", "installed" if installed else "muted")
        self.ver_installed.style().unpolish(self.ver_installed)
        self.ver_installed.style().polish(self.ver_installed)
        self.ver_latest.setText(f"Latest: {self.latest_version}")
        self._update_game_size()

    def _update_gfx_info(self):
        """Show GPU / Wine status in the status bar (Linux only)."""
        if not hasattr(self, "gfx_text"):
            return
        from platform_utils import IS_LINUX
        if not IS_LINUX:
            self.gfx_text.hide()
            return
        self.gfx_text.show()
        import graphics
        gpu = graphics.describe_gpu(self.config.get_gpu())
        wine = self.config.get_wine_binary() or graphics.resolve_wine() or "Not found"
        self.gfx_text.setText(f"GPU: {gpu}  |  Wine: {wine}")

    def _update_main_btn(self):
        self._update_gfx_info()
        if self.game.is_running:
            self.main_action_btn.setText("PLAYING")
            self.main_action_btn.setObjectName("homeDangerBtn")
            self.main_action_btn.style().polish(self.main_action_btn)
            self.locate_btn.hide()
            start_playing_pulse(self.main_action_btn, color=theme.DANGER)
            return

        stop_playing_pulse(self.main_action_btn)

        cur = self.current_version
        lat = self.latest_version
        gp = self.config.get_game_path()
        if cur == "Not Installed" or not gp or not (gp / "Among Us.exe").exists():
            self.main_action_btn.setText("INSTALL GAME")
            self.main_action_btn.setObjectName("homeSuccessBtn")
            self.main_action_btn.style().polish(self.main_action_btn)
            self.locate_btn.show()
        elif cur != lat and lat != "Checking...":
            self.main_action_btn.setText("UPDATE AVAILABLE")
            self.main_action_btn.setObjectName("homePrimaryBtn")
            self.main_action_btn.style().polish(self.main_action_btn)
            self.locate_btn.hide()
        else:
            self.main_action_btn.setText("LAUNCH GAME")
            self.main_action_btn.setObjectName("homeSuccessBtn")
            self.main_action_btn.style().polish(self.main_action_btn)
            self.locate_btn.hide()

    def _busy_on(self):
        self._busy = True
        self.main_action_btn.setEnabled(False)

    def _busy_off(self):
        self._busy = False
        self.main_action_btn.setEnabled(True)

    # ------------------------------------------------------------------ run
    def run(self):
        self.window.show()
        self._load_itch_profile()
        self._maybe_show_setup_wizard()

    def _maybe_show_setup_wizard(self):
        """Show the setup wizard on first Linux run."""
        from platform_utils import IS_LINUX
        if not IS_LINUX:
            return
        if self.config.is_linux_setup_complete():
            return
        from gui_qt.setup_wizard import SetupWizard
        dlg = SetupWizard(self.config, self.window)
        dlg.exec()

    def _run_setup_wizard(self):
        """Tools button: re-run the setup wizard."""
        from gui_qt.setup_wizard import SetupWizard
        dlg = SetupWizard(self.config, self.window)
        if dlg.exec():
            self._update_gfx_info()

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
