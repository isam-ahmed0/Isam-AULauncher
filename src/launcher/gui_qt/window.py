"""
Window — Steam-style sidebar launcher for Isam AULauncher (PySide6).
Professional dark UI with sidebar navigation and stacked pages.
"""
import os
import sys
import json
import logging
import shutil
import subprocess
import webbrowser
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QStackedWidget, QLabel, QFrame, QProgressBar,
    QCheckBox, QDialog, QFileDialog, QStatusBar, QMessageBox,
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QLinearGradient, QFont

from config import (
    Config, APP_NAME, BRAND_SHORT, MAKER, LAUNCHER_VERSION,
    VERSION_URL, GITHUB_REPO, AUNLOCKER_JSON_URL, PATCHES_URL,
    DISCORD_INVITE, YOUTUBE_CHANNEL, SOURCE_CODE_URL,
)
from network import NetworkManager, DiscordRPC
from file_manager import FileManager
from gui_qt.theme import (
    apply_theme, ACCENT, ACCENT_2, SUCCESS, SUCCESS_HOVER,
    INFO, DANGER, WARNING, TEXT_BRIGHT, TEXT_PRIMARY,
    TEXT_SECONDARY, TEXT_MUTED, BG_BASE, BG_SIDEBAR, BG_ELEVATED,
)
from gui_qt.game import GameManager

_RESOURCES_DIR = Path(__file__).parent.parent / "resources"
_HERO_IMAGE_PATH = _RESOURCES_DIR / "hero.png"
_ICON_PATH = _RESOURCES_DIR / "icon.ico"

ITCH_FIXER_NAME = "Itch_Login_Fixer.exe"

_ITCH_TOKEN_DIR = Path(os.environ.get("USERPROFILE", "")) / "AppData" / "LocalLow" / "Innersloth" / "Among Us"
_ITCH_TOKEN_FILE = _ITCH_TOKEN_DIR / "itch"

ITCHIO_API = "https://itch.io/api/1/key/me"
EOS_AUTH_URL = "https://accounts.innersloth.com/eos-auth"
BACKEND_API = "https://backend.innersloth.com/api"
BACKEND_HEADERS = {
    "Accept": "application/vnd.api+json",
    "Origin": "https://accounts.innersloth.com",
    "Referer": "https://accounts.innersloth.com/",
}
PLATFORM_LABELS = {
    'itchio': 'itch.io', 'itch': 'itch.io',
    'steam': 'Steam', 'epic': 'Epic Games', 'epicgames': 'Epic Games',
    'microsoft': 'Microsoft Store', 'winstore': 'Microsoft Store',
    'xbox': 'Xbox', 'xboxlive': 'Xbox',
}

SIDEBAR_W = 200


# ---------------------------------------------------------------------------
# Hero banner with gradient background
# ---------------------------------------------------------------------------
class HeroBanner(QLabel):
    """Custom hero banner that draws a gradient background with overlay text."""

    def __init__(self, title, subtitle, parent=None):
        super().__init__(parent)
        self._title = title
        self._subtitle = subtitle
        self._hero_image = None
        self.setMinimumHeight(220)
        self.setMaximumHeight(220)

        if _HERO_IMAGE_PATH.exists():
            self._hero_image = QPixmap(str(_HERO_IMAGE_PATH))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Background
        if self._hero_image and not self._hero_image.isNull():
            scaled = self._hero_image.scaled(
                w, h,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            painter.drawPixmap(0, 0, scaled)
            # Dark overlay
            painter.fillRect(0, 0, w, h, QColor(12, 14, 20, 160))
        else:
            # Gradient background
            gradient = QLinearGradient(0, 0, w, h)
            gradient.setColorAt(0, QColor(18, 20, 26))
            gradient.setColorAt(0.5, QColor(24, 27, 34))
            gradient.setColorAt(1, QColor(18, 20, 26))
            painter.fillRect(0, 0, w, h, gradient)

        # Subtle glow orb
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(99, 102, 241, 25))
        painter.drawEllipse(int(w * 0.75) - 80, int(h * 0.35) - 80, 160, 160)
        painter.setBrush(QColor(6, 182, 212, 20))
        painter.drawEllipse(int(w * 0.15) - 65, int(h * 0.7) - 65, 130, 130)

        # Bottom accent gradient line
        gradient = QLinearGradient(0, 0, w, 0)
        gradient.setColorAt(0, QColor(99, 102, 241, 200))
        gradient.setColorAt(1, QColor(6, 182, 212, 200))
        painter.setBrush(gradient)
        painter.drawRect(0, h - 3, w, 3)

        # Title text
        painter.setPen(QColor(255, 255, 255))
        title_font = QFont("Segoe UI", 24)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.drawText(28, int(h * 0.45), self._title)

        # Subtitle text
        painter.setPen(QColor(156, 163, 175))
        sub_font = QFont("Segoe UI", 13)
        painter.setFont(sub_font)
        painter.drawText(28, int(h * 0.45) + 32, self._subtitle)

        # Version badge
        badge_text = f"v{LAUNCHER_VERSION}"
        badge_font = QFont("Segoe UI", 10)
        painter.setFont(badge_font)
        fm = painter.fontMetrics()
        tw = fm.horizontalAdvance(badge_text) + 20
        bx, by = 28, h - 38
        painter.setBrush(QColor(32, 36, 46, 220))
        painter.setPen(QColor(99, 102, 241, 100))
        painter.drawRoundedRect(bx, by, tw, 24, 12, 12)
        painter.setPen(QColor(6, 182, 212))
        painter.drawText(bx, by, tw, 24, Qt.AlignmentFlag.AlignCenter, badge_text)

        painter.end()


# ---------------------------------------------------------------------------
# Background worker thread
# ---------------------------------------------------------------------------
class Worker(QThread):
    """Run a function in a background thread, emit finished signal."""
    finished = Signal()

    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self._fn = fn

    def run(self):
        try:
            self._fn()
        finally:
            self.finished.emit()


# ---------------------------------------------------------------------------
# Main Window
# ---------------------------------------------------------------------------
class LauncherApp:
    def __init__(self):
        self.config = Config()
        self.network = NetworkManager()
        self.discord = DiscordRPC()
        self.game = GameManager(self.config, self.network)

        # Connect game manager signals
        self.game.game_started.connect(self._on_game_started)
        self.game.game_stopped.connect(self._on_game_stopped)
        self.game.status_message.connect(lambda text, level: self._set_status(text, level))

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

        self._setup_app()
        self._build_ui()
        self._setup_game_timer()
        self._load_initial_data()

    # ------------------------------------------------------------------ setup
    def _setup_app(self):
        self.app = QApplication(sys.argv)
        apply_theme(self.app)
        if _ICON_PATH.exists():
            self.app.setWindowIcon(QIcon(str(_ICON_PATH)))

    def _run(self, fn):
        """Run fn in a background thread."""
        w = Worker(fn)
        w.finished.connect(lambda: self._cleanup_worker(w))
        self._workers.append(w)
        w.start()

    def _cleanup_worker(self, w):
        if w in self._workers:
            self._workers.remove(w)

    def _setup_game_timer(self):
        """Poll game process state every 2 seconds."""
        self._game_timer = QTimer()
        self._game_timer.timeout.connect(self._poll_game_state)
        self._game_timer.start(2000)

    def _poll_game_state(self):
        """Check if game is still running, update button accordingly."""
        was_running = self.game.is_running
        self.game.poll()
        if was_running and not self.game.is_running:
            self._on_game_stopped()
        elif self.game.is_running:
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

        # Central widget
        central = QWidget()
        self.window.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(SIDEBAR_W)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 20, 12, 20)
        sidebar_layout.setSpacing(4)

        # Brand
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

        # Stacked pages
        self.pages = QStackedWidget()
        self.page_game = self._build_game_page()
        self.page_tools = self._build_tools_page()
        self.page_aunlocker = self._build_aunlocker_page()
        self.page_profile = self._build_profile_page()
        self.pages.addWidget(self.page_game)
        self.pages.addWidget(self.page_tools)
        self.pages.addWidget(self.page_aunlocker)
        self.pages.addWidget(self.page_profile)

        # Nav buttons
        self.nav_buttons = {}
        for label, idx in [("Game", 0), ("Tools", 1), ("AUnlocker", 2), ("Profile", 3)]:
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

        # Settings & About (open modals, not pages)
        btn_settings = QPushButton("  Settings")
        btn_settings.setFixedHeight(40)
        btn_settings.clicked.connect(self._show_settings)
        sidebar_layout.addWidget(btn_settings)

        btn_about = QPushButton("  About")
        btn_about.setFixedHeight(40)
        btn_about.clicked.connect(self._show_about)
        sidebar_layout.addWidget(btn_about)

        sidebar_layout.addStretch()

        # Add sidebar and pages to main layout
        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.pages)

        # Status bar
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

        # Activate first page
        self.nav_buttons["Game"].setChecked(True)

    # ------------------------------------------------------------------ pages
    def _build_game_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Hero banner
        hero = HeroBanner(
            "Game Management",
            "Install, update, and manage your Among Us installation",
        )
        layout.addWidget(hero)

        # Profile section (itch.io account info)
        profile_widget = QWidget()
        profile_layout = QHBoxLayout(profile_widget)
        profile_layout.setContentsMargins(28, 12, 28, 0)
        profile_icon = QLabel("●")
        profile_icon.setObjectName("statusDot")
        profile_icon.setStyleSheet(f"color: {TEXT_MUTED};")
        profile_layout.addWidget(profile_icon)
        self.profile_game_text = QLabel("Loading profile...")
        self.profile_game_text.setObjectName("profileDetail")
        profile_layout.addWidget(self.profile_game_text)
        self.profile_game_detail = QLabel("")
        self.profile_game_detail.setObjectName("profileDetail")
        profile_layout.addWidget(self.profile_game_detail)
        profile_layout.addStretch()
        layout.addWidget(profile_widget)

        # Action buttons
        btn_row = QWidget()
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(28, 16, 28, 0)
        self.main_action_btn = QPushButton("INSTALL GAME")
        self.main_action_btn.setObjectName("successBtn")
        self.main_action_btn.setFixedHeight(52)
        self.main_action_btn.clicked.connect(self._cb_main_action)
        btn_layout.addWidget(self.main_action_btn)
        layout.addWidget(btn_row)

        # Locate button (hidden by default)
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

        # Info row
        info_widget = QWidget()
        info_layout = QHBoxLayout(info_widget)
        info_layout.setContentsMargins(28, 16, 28, 0)

        # Left column — versions
        left = QVBoxLayout()
        left.addWidget(self._muted_label("INSTALLED"))
        self.ver_installed = QLabel("Not Installed")
        self.ver_installed.setObjectName("successText")
        left.addWidget(self.ver_installed)
        left.addSpacing(12)
        left.addWidget(self._muted_label("LATEST"))
        self.ver_latest = QLabel("Checking...")
        self.ver_latest.setObjectName("infoText")
        left.addWidget(self.ver_latest)
        info_layout.addLayout(left)

        info_layout.addSpacing(32)

        # Right column — status + progress
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
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 20, 28, 0)

        title = QLabel("TOOLS")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        layout.addSpacing(12)

        row1 = QHBoxLayout()
        row1.setSpacing(8)
        for label, cb in [
            ("Open Folder", self._cb_open_folder),
            ("Change Location", self._cb_change_location),
            ("Verify Files", self._cb_verify),
        ]:
            btn = QPushButton(label)
            btn.setObjectName("toolBtn")
            btn.setFixedHeight(44)
            btn.clicked.connect(cb)
            row1.addWidget(btn)
        layout.addLayout(row1)

        layout.addSpacing(8)

        row2 = QHBoxLayout()
        row2.setSpacing(8)
        for label, cb, obj_name in [
            ("Create Shortcut", self._cb_create_shortcut, "toolBtn"),
            ("Reinstall Game", self._cb_reinstall, "toolBtn"),
            ("Uninstall", self._cb_uninstall, "dangerBtn"),
        ]:
            btn = QPushButton(label)
            btn.setObjectName(obj_name)
            btn.setFixedHeight(44)
            btn.clicked.connect(cb)
            row2.addWidget(btn)
        layout.addLayout(row2)

        layout.addStretch()
        return page

    def _build_aunlocker_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 20, 28, 0)

        title = QLabel("AUNLOCKER")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        layout.addSpacing(12)

        desc = QLabel("Install the Among Us unlocker for your game version.")
        desc.setObjectName("statusText")
        layout.addWidget(desc)
        layout.addSpacing(16)

        self.aunlocker_btn = QPushButton("Install AUnlocker")
        self.aunlocker_btn.setObjectName("primaryBtn")
        self.aunlocker_btn.setFixedHeight(52)
        self.aunlocker_btn.setFixedWidth(240)
        self.aunlocker_btn.clicked.connect(self._cb_install_aunlocker)
        layout.addWidget(self.aunlocker_btn)

        layout.addStretch()
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
        # Load itch profile on first visit to Profile page
        if label == "Profile" and not hasattr(self, '_itch_profile_loaded'):
            self._itch_profile_loaded = True
            self._load_itch_profile()

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
        self.aunlocker_btn.setEnabled(False)

    def _busy_off(self):
        self._busy = False
        self.main_action_btn.setEnabled(True)
        self.aunlocker_btn.setEnabled(True)

    # ------------------------------------------------------------------ callbacks
    def _cb_main_action(self):
        txt = self.main_action_btn.text()
        if "INSTALL" in txt or "UPDATE" in txt:
            self._download_latest()
        elif "LAUNCH" in txt:
            self._launch_game()
        elif "PLAYING" in txt:
            self.game.stop()
            self._update_main_btn()

    def _cb_install_aunlocker(self):
        self._install_aunlocker()

    def _cb_create_shortcut(self):
        self._create_shortcut()

    def _cb_open_folder(self):
        gp = self.config.get_game_path()
        if gp and gp.exists():
            os.startfile(str(gp))
        else:
            QMessageBox.warning(self.window, "Error", "Game not installed!")

    def _cb_change_location(self):
        self._change_location_pending = True
        folder = QFileDialog.getExistingDirectory(self.window, "Select Game Folder")
        if folder:
            self._folder_selected(folder)
        else:
            self._change_location_pending = False

    def _cb_locate_game(self):
        self._locate_pending = True
        folder = QFileDialog.getExistingDirectory(self.window, "Select Among Us Folder")
        if folder:
            self._folder_selected(folder)
        else:
            self._locate_pending = False

    def _cb_verify(self):
        self._verify_files()

    def _cb_reinstall(self):
        self._reinstall_game()

    def _cb_uninstall(self):
        self._uninstall_game()

    # ------------------------------------------------------------------ folder selected
    def _folder_selected(self, folder):
        path = Path(folder)
        if self._install_folder_pending:
            self._install_folder_pending = False
            self._pending_install_path = path
            self._download_latest()
            return
        if self._change_location_pending:
            self._change_location_pending = False
            self._change_location(path)
            return
        if self._locate_pending:
            self._locate_pending = False
            result = FileManager.verify_game_folder(path)
            if not result["exe_found"]:
                self._set_status("Among Us.exe not found in this folder", "danger")
                QMessageBox.warning(self.window, "Error",
                                    "Among Us.exe not found.\nSelect a valid Among Us installation.")
                return
            self.config.set_game_path(path)
            ver = self.latest_version if self.latest_version != "Checking..." else "Unknown"
            self.config.set_version(ver)
            self.current_version = ver
            self._update_version_display()
            self._update_main_btn()
            self._set_status(f"Game located at {path}", "success")
            return

    # ------------------------------------------------------------------ actions
    def _download_latest(self):
        def go():
            try:
                self._busy_on()
                self._set_status("Preparing download...", "info")
                if self.discord.connected:
                    self.discord.update_status("Updating Game", "Downloading...")
                latest = self.latest_version
                if latest == "Checking...":
                    latest = self.network.fetch_text(VERSION_URL)
                    if not latest:
                        self._set_status("Failed to fetch version info", "danger")
                        return
                gp = self.config.get_game_path()
                if not gp:
                    gp = self._pending_install_path
                    if not gp:
                        self._busy_off()
                        self._install_folder_pending = True
                        self._set_status("Select a folder to install into", "info")
                        folder = QFileDialog.getExistingDirectory(
                            self.window, "Select Install Folder"
                        )
                        if folder:
                            self._folder_selected(folder)
                        return

                # Wire up progress signals from GameManager
                def on_progress(pct):
                    self._update_progress(pct)

                def on_status(text, level):
                    self._set_status(text, level)

                self.game.update_progress.connect(on_progress)
                self.game.status_message.connect(on_status)
                try:
                    ok = self.game.download_update(latest, gp)
                    if ok:
                        self._pending_install_path = None
                        self.current_version = latest
                        self._update_version_display()
                        self._update_progress(100)
                finally:
                    self.game.update_progress.disconnect(on_progress)
                    self.game.status_message.disconnect(on_status)
            except Exception as e:
                self._set_status(f"Error: {e}", "danger")
            finally:
                self._busy_off()
                self._update_main_btn()
                if self.discord.connected:
                    self.discord.update_status("In Launcher", "Browsing Menu")
        self._run(go)

    def _install_aunlocker(self):
        ver = self.config.get_version()
        gp = self.config.get_game_path()
        if not ver or not gp:
            QMessageBox.warning(self.window, "Error", "Game not installed!")
            return

        def go():
            try:
                self._busy_on()
                self._set_status("Checking AUnlocker...", "info")
                data = self.network.fetch_text(AUNLOCKER_JSON_URL)
                if not data:
                    QMessageBox.warning(self.window, "Error", "Failed to fetch data")
                    return
                versions = json.loads(data).get("versions", [])
                for entry in versions:
                    if entry["version"] == ver:
                        zp = Path("AUnlocker.zip")
                        self._set_status("Downloading AUnlocker...", "info")
                        if self.network.download_file(entry["link"], zp):
                            FileManager.extract_zip(zp, gp)
                            FileManager.safe_delete(zp)
                            QMessageBox.information(self.window, "Info",
                                                    "AUnlocker installed!")
                            self._set_status("Ready")
                            return
                QMessageBox.warning(self.window, "Warning",
                                    "No compatible AUnlocker version found")
            except Exception:
                self._set_status("Ready")
            finally:
                self._busy_off()
        self._run(go)

    def _launch_game(self):
        ok = self.game.launch()
        if ok:
            self._update_main_btn()

    def _create_shortcut(self):
        gp = self.config.get_game_path()
        if not gp:
            QMessageBox.warning(self.window, "Error", "Game not installed!")
            return
        try:
            import win32com.client
        except ImportError:
            QMessageBox.warning(self.window, "Error", "pywin32 not installed")
            return
        exe = gp / "Among Us.exe"
        ver = self.config.get_version()
        try:
            sc = Path.home() / "Desktop" / f"Among Us {ver}.lnk"
            sh = win32com.client.Dispatch("WScript.Shell")
            lnk = sh.CreateShortCut(str(sc))
            lnk.Targetpath = str(exe)
            lnk.WorkingDirectory = str(gp)
            lnk.IconLocation = str(exe)
            lnk.save()
            QMessageBox.information(self.window, "Info", "Shortcut created on Desktop!")
        except Exception as e:
            QMessageBox.warning(self.window, "Error", f"Failed: {e}")

    def _change_location(self, new_path):
        self._set_status("Verifying game files...", "info")
        result = FileManager.verify_game_folder(new_path)
        if not result["exe_found"]:
            self.config.set_game_path(new_path)
            self.config.set_version("Not Installed")
            self.current_version = "Not Installed"
            self._update_version_display()
            self._update_main_btn()
            self._set_status(f"Location set to {new_path}", "success")
            QMessageBox.information(self.window, "Info",
                                    f"Location: {new_path}\nClick INSTALL GAME to download.")
            return
        if result["missing"]:
            self._set_status("Some files missing", "warning")
            msg = (f"Some game files are missing:\n{', '.join(result['missing'])}\n\n"
                   f"Found {result['file_count']} files "
                   f"({FileManager.format_size(result['total_size'])}).\nContinue anyway?")
            if QMessageBox.question(
                self.window, "Confirm", msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            ) != QMessageBox.StandardButton.Yes:
                self._set_status("Ready")
                return
        self._set_status(
            f"Verified — {result['file_count']} files, "
            f"{FileManager.format_size(result['total_size'])}",
            "success",
        )
        old = self.config.get_game_path()
        if old and old.exists() and old != new_path:
            if QMessageBox.question(
                self.window, "Confirm", "Move existing game files to new location?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            ) == QMessageBox.StandardButton.Yes:
                self._set_status("Moving files...", "info")
                try:
                    shutil.move(str(old), str(new_path))
                    self._set_status("Files moved!", "success")
                except (PermissionError, OSError) as e:
                    self._set_status("Move failed", "danger")
                    QMessageBox.warning(self.window, "Error",
                                        f"Failed to move files: {e}")
                    return
        self.config.set_game_path(new_path)
        self._set_status("Location changed!", "success")
        QMessageBox.information(self.window, "Info", f"Location: {new_path}")

    def _verify_files(self):
        gp = self.config.get_game_path()
        if not gp:
            QMessageBox.warning(self.window, "Error", "Game not installed!")
            return
        self._set_status("Verifying...", "info")
        result = FileManager.verify_game_folder(gp)
        if result["valid"]:
            QMessageBox.information(
                self.window, "Info",
                f"All files verified.\n{result['file_count']} files, "
                f"{FileManager.format_size(result['total_size'])}",
            )
        elif result["exe_found"]:
            QMessageBox.warning(
                self.window, "Warning",
                f"Some files missing:\n{', '.join(result['missing'])}",
            )
        else:
            QMessageBox.warning(self.window, "Error", "Among Us.exe not found!")
        self._set_status("Ready")

    def _reinstall_game(self):
        reply = QMessageBox.question(
            self.window, "Confirm", "Delete and reinstall the game?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            gp = self.config.get_game_path()
            if gp:
                self._pending_install_path = gp
            if gp and gp.exists():
                FileManager.safe_delete(gp)
            self.current_version = "Not Installed"
            self._update_version_display()
            self._download_latest()

    def _uninstall_game(self):
        reply = QMessageBox.question(
            self.window, "Confirm",
            "Remove all game files and launcher data?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            gp = self.config.get_game_path()
            if gp and gp.exists():
                if FileManager.safe_delete(gp):
                    QMessageBox.information(self.window, "Info", "Game files removed")
                else:
                    QMessageBox.warning(self.window, "Error",
                                        "Failed to remove game files")
            if FileManager.safe_delete(self.config.appdata_dir):
                QMessageBox.information(self.window, "Info",
                                        "Launcher data removed")
            self.current_version = "Not Installed"
            self._update_version_display()
            self._update_main_btn()

    # ------------------------------------------------------------------ modals
    def _show_settings(self):
        settings = self.config.settings
        dialog = QDialog(self.window)
        dialog.setWindowTitle("Settings")
        dialog.setFixedSize(480, 360)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 20, 24, 20)

        title = QLabel("Settings")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        layout.addSpacing(4)
        layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine))
        layout.addSpacing(12)

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

        cb_verify = QCheckBox("Verify file integrity")
        cb_verify.setChecked(settings.get("check_integrity", True))
        layout.addWidget(cb_verify)
        desc3 = QLabel("  Check checksums after download")
        desc3.setObjectName("mutedText")
        layout.addWidget(desc3)

        layout.addSpacing(20)
        layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine))
        layout.addSpacing(12)

        def save():
            settings["discord_rpc"] = cb_rpc.isChecked()
            settings["auto_update"] = cb_auto.isChecked()
            settings["check_integrity"] = cb_verify.isChecked()
            self.config.save_settings()
            if settings["discord_rpc"] and not self.discord.connected:
                self.discord.connect()
            elif not settings["discord_rpc"] and self.discord.connected:
                self.discord.disconnect()
            dialog.accept()

        save_btn = QPushButton("Save")
        save_btn.setObjectName("successBtn")
        save_btn.setFixedHeight(40)
        save_btn.clicked.connect(save)
        layout.addWidget(save_btn)

        dialog.exec()

    def _show_about(self):
        dialog = QDialog(self.window)
        dialog.setWindowTitle("About")
        dialog.setFixedSize(460, 340)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 20, 24, 20)

        title = QLabel("About")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        layout.addSpacing(4)
        layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine))
        layout.addSpacing(12)

        name = QLabel(APP_NAME)
        name.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {TEXT_BRIGHT};")
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
            discord_btn.clicked.connect(lambda: os.system(f"start {DISCORD_INVITE}"))
            links_row.addWidget(discord_btn)
        else:
            discord_btn = QPushButton("Discord (Coming soon)")
            discord_btn.setObjectName("toolBtn")
            discord_btn.clicked.connect(self._cb_coming_soon)
            links_row.addWidget(discord_btn)

        yt_btn = QPushButton("YouTube")
        yt_btn.setObjectName("toolBtn")
        yt_btn.clicked.connect(lambda: os.system(f"start {YOUTUBE_CHANNEL}"))
        links_row.addWidget(yt_btn)

        src_btn = QPushButton("Source Code")
        src_btn.setObjectName("toolBtn")
        src_btn.clicked.connect(lambda: os.system(f"start {SOURCE_CODE_URL}"))
        links_row.addWidget(src_btn)
        layout.addLayout(links_row)

        layout.addSpacing(20)
        layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine))
        layout.addSpacing(8)

        ok_btn = QPushButton("OK")
        ok_btn.setObjectName("modalPrimary")
        ok_btn.setFixedHeight(36)
        ok_btn.clicked.connect(dialog.accept)
        layout.addWidget(ok_btn)

        dialog.exec()

    def _cb_coming_soon(self):
        QMessageBox.information(self.window, "Discord", "Discord server coming soon!")

    # ------------------------------------------------------------------ initial data
    def _load_initial_data(self):
        def go():
            v = self.config.get_version()
            if v:
                self.current_version = v
            latest = self.network.fetch_text(VERSION_URL)
            if latest:
                self.latest_version = latest
            self._update_version_display()
            self._update_main_btn()
            if self.config.settings.get("discord_rpc"):
                self.discord.connect()
        self._run(go)

    # ------------------------------------------------------------------ itchfixer
    def _find_itch_fixer(self):
        """Find Itch_Login_Fixer.exe relative to the launcher."""
        if getattr(sys, 'frozen', False):
            return Path(sys.executable).parent / ITCH_FIXER_NAME
        return Path(__file__).parent.parent.parent / "release" / "Fixer" / ITCH_FIXER_NAME

    def _launch_itch_fixer(self):
        """Launch ItchFixer as a separate process."""
        exe = self._find_itch_fixer()
        if exe.exists():
            subprocess.Popen([str(exe)], cwd=str(exe.parent))
        else:
            logging.warning(f"ItchFixer not found: {exe}")

    def _show_itch_auth_dialog(self):
        """Show 2-step itch.io authentication popup."""
        dialog = QDialog(self.window)
        dialog.setWindowTitle("itch.io Authentication")
        dialog.setFixedSize(480, 320)
        dialog.setModal(True)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("itch.io Login Required")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        layout.addSpacing(4)
        layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine))
        layout.addSpacing(8)

        # Step 1
        step1_label = QLabel("Step 1")
        step1_label.setObjectName("profileName")
        layout.addWidget(step1_label)

        step1_desc = QLabel("Open itch.io and sign in or create an account.")
        step1_desc.setObjectName("profileDetail")
        step1_desc.setWordWrap(True)
        layout.addWidget(step1_desc)

        open_btn = QPushButton("Open itch.io")
        open_btn.setObjectName("primaryBtn")
        open_btn.setFixedHeight(36)
        open_btn.clicked.connect(lambda: webbrowser.open("https://itch.io/login"))
        layout.addWidget(open_btn)

        layout.addSpacing(12)

        # Step 2
        step2_label = QLabel("Step 2")
        step2_label.setObjectName("profileName")
        layout.addWidget(step2_label)

        step2_desc = QLabel("After logging in, click Authenticate to open ItchFixer and complete the login.")
        step2_desc.setObjectName("profileDetail")
        step2_desc.setWordWrap(True)
        layout.addWidget(step2_desc)

        auth_btn = QPushButton("Authenticate")
        auth_btn.setObjectName("successBtn")
        auth_btn.setFixedHeight(40)
        layout.addWidget(auth_btn)

        def do_authenticate():
            dialog.accept()
            self._launch_itch_fixer()
            self.app.quit()

        auth_btn.clicked.connect(do_authenticate)

        dialog.exec()

    # ------------------------------------------------------------------ itch profile (read-only)
    def _read_itch_token(self):
        """Read the itch.io token from ItchFixer's saved file. Read-only."""
        try:
            if _ITCH_TOKEN_FILE.exists():
                token = _ITCH_TOKEN_FILE.read_text().strip()
                if token:
                    return token
        except Exception:
            pass
        return None

    def _fetch_itch_profile(self):
        """Fetch itch.io account data using the saved token. All GET requests, no writes."""
        import requests as _req

        token = self._read_itch_token()
        if not token:
            return None

        profile = {"token": True, "username": None, "among_us_name": None, "platforms": []}

        # 1. Fetch itch.io username
        try:
            r = _req.get(ITCHIO_API, headers={"Authorization": token}, timeout=15)
            if r.status_code == 200:
                u = r.json().get("user", {})
                profile["username"] = u.get("username")
        except Exception:
            pass

        # 2. Fetch Among Us account data via EOS
        try:
            r = _req.get(EOS_AUTH_URL, params={"store": "itchio", "token": token},
                         headers={"Accept": "application/json"}, timeout=20)
            if r.status_code == 200:
                eos = r.json()
                if eos.get("token") and eos.get("id_token"):
                    # Query primary account
                    r2 = _req.get(f"{BACKEND_API}/user/query-primary-before-merge",
                                  params={"access_token": eos["token"]},
                                  headers={"Authorization": "Bearer " + eos["id_token"],
                                           **BACKEND_HEADERS}, timeout=20)
                    if r2.status_code == 200:
                        data = r2.json().get("data", {})
                        platforms = data.get("platforms") or []
                        profile["platforms"] = [
                            PLATFORM_LABELS.get(p.lower(), p) for p in platforms
                        ]
                    # Query Among Us username
                    r3 = _req.get(f"{BACKEND_API}/user/username",
                                  headers={"Authorization": "Bearer " + eos["id_token"],
                                           **BACKEND_HEADERS}, timeout=15)
                    if r3.status_code == 200:
                        attrs = r3.json().get("data", {}).get("attributes", {})
                        name = attrs.get("username")
                        disc = attrs.get("discriminator")
                        if name:
                            profile["among_us_name"] = f"{name}#{disc}" if disc else name
        except Exception:
            pass

        return profile

    def _load_itch_profile(self):
        """Fetch itch profile in background, update UI on main thread via signal."""
        def go():
            self._itch_profile = self._fetch_itch_profile()
        w = Worker(go)
        w.finished.connect(lambda: self._update_profile_ui(self._itch_profile))
        self._workers.append(w)
        w.start()

    def _update_profile_ui(self, profile):
        """Update all profile-related UI elements."""
        if not profile:
            # Not logged in
            self.profile_game_text.setText("Not logged in")
            self.profile_game_text.setStyleSheet(f"color: {TEXT_MUTED};")
            self.profile_game_detail.setText("Click Profile to authenticate")
            self.profile_game_detail.setStyleSheet(f"color: {TEXT_MUTED};")
            self.profile_page_status.setText("Not logged in")
            self.profile_page_status.setStyleSheet(f"color: {TEXT_MUTED};")
            self.profile_page_name.setText("")
            self.profile_page_au.setText("")
            self.profile_page_platforms.setText("")
            if not self._itch_auth_shown:
                self._itch_auth_shown = True
                self._show_itch_auth_dialog()
            return

        username = profile.get("username") or "Unknown"
        au_name = profile.get("among_us_name")
        platforms = profile.get("platforms") or []

        # Game page profile section
        self.profile_game_text.setText(f"Logged in as {username}")
        self.profile_game_text.setStyleSheet(f"color: {SUCCESS}; font-weight: 600;")
        detail_parts = []
        if au_name:
            detail_parts.append(f"Among Us: {au_name}")
        if platforms:
            detail_parts.append(f"Linked: {', '.join(platforms)}")
        self.profile_game_detail.setText(" — ".join(detail_parts) if detail_parts else "")
        self.profile_game_detail.setStyleSheet(f"color: {TEXT_SECONDARY};")

        # Profile page
        self.profile_page_status.setText("Logged in")
        self.profile_page_status.setStyleSheet(f"color: {SUCCESS}; font-weight: 600;")
        self.profile_page_name.setText(username)
        if au_name:
            self.profile_page_au.setText(f"Among Us: {au_name}")
            self.profile_page_au.setStyleSheet(f"color: {INFO};")
        else:
            self.profile_page_au.setText("No Among Us data yet")
            self.profile_page_au.setStyleSheet(f"color: {TEXT_MUTED};")
        if platforms:
            self.profile_page_platforms.setText(f"Linked: {', '.join(platforms)}")
            self.profile_page_platforms.setStyleSheet(f"color: {TEXT_SECONDARY};")
        else:
            self.profile_page_platforms.setText("No platforms linked")
            self.profile_page_platforms.setStyleSheet(f"color: {TEXT_MUTED};")

    # ------------------------------------------------------------------ run
    def run(self):
        self.window.show()
        self._load_initial_data()
        exit_code = self.app.exec()
        self.discord.disconnect()
        sys.exit(exit_code)
