import os
import sys
import time
import json
import hashlib
import logging
import threading
import subprocess
import shutil
import stat
import zipfile
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass

try:
    import requests
    from colorama import init, Fore, Style
    import ctypes
    from win32com.client import Dispatch
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    from PIL import Image, ImageTk, ImageDraw
except ImportError as e:
    print(f"Missing required package: {e}")
    print("Install with: pip install requests colorama pywin32 pillow")
    sys.exit(1)

try:
    from pypresence import Presence
    DISCORD_RPC_AVAILABLE = True
except ImportError:
    DISCORD_RPC_AVAILABLE = False

init(autoreset=True)
logging.basicConfig(
    filename='launcher.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ---------------------------------------------------------------------------
# Branding
# ---------------------------------------------------------------------------
APP_NAME = "Isam AULauncher"
BRAND_SHORT = "ISAM AU"
MAKER = "Isam"
LAUNCHER_VERSION = "0.1"

LAUNCHER_VERSION_URL = "https://raw.githubusercontent.com/jogamerforgames2021/AmongUsLauncherNew/refs/heads/main/LauncherVersion.txt"
LAUNCHER_DOWNLOAD_URL = "https://raw.githubusercontent.com/jogamerforgames2021/AmongUsLauncherNew/refs/heads/main/AmongUsLauncher.exe"
VERSION_URL = "https://raw.githubusercontent.com/jogamerforgames2021/BootstrapperTEST/main/Version.txt"
MESSAGE_URL = "https://raw.githubusercontent.com/jogamerforgames2021/AmongUsLauncherNew/refs/heads/main/message.txt"
PATCHES_URL = "https://raw.githubusercontent.com/jogamerforgames2021/AmongUsLauncherNew/refs/heads/main/Patches.xml"
SOURCE_CODE_URL = "https://github.com/jogamerforgames2021/BootstrapperTEST/blob/main/my_script.py"
GITHUB_REPO = "jogamerforgames2021/AmongUsLauncherNew"
AUNLOCKER_JSON_URL = "https://raw.githubusercontent.com/jogamerforgames2021/AmongUsLauncherNew/refs/heads/main/AUnlockerStuff/Versions.json"
DISCORD_CLIENT_ID = "1378503147768647821"
DISCORD_INVITE = "https://discord.gg/7Vvj2vpT6S"
YOUTUBE_CHANNEL = "https://www.youtube.com/@ShadowSlimeDEV"
REQUEST_TIMEOUT = 10
CHUNK_SIZE = 8192


class Colors:
    """Centralized color definitions"""
    SUCCESS = Fore.GREEN
    ERROR = Fore.RED
    WARNING = Fore.YELLOW
    INFO = Fore.CYAN
    HIGHLIGHT = Fore.MAGENTA
    GOLD = Fore.YELLOW + Style.BRIGHT
    RESET = Style.RESET_ALL


@dataclass
class GameVersion:
    """Game version information"""
    version: str
    url: str
    checksum: Optional[str] = None


class Config:
    """Configuration manager"""
    def __init__(self):
        self.appdata_dir = Path(os.environ["APPDATA"]) / "IsamAULauncher"
        self.appdata_dir.mkdir(parents=True, exist_ok=True)
        self.version_file = self.appdata_dir / "current_version.txt"
        self.game_path_file = self.appdata_dir / "game_path.txt"
        self.config_file = self.appdata_dir / "config.json"
        self.settings = self._load_settings()

    def _load_settings(self) -> Dict:
        """Load launcher settings"""
        default_settings = {
            "auto_update": True,
            "create_shortcuts": True,
            "discord_rpc": True,
            "minimize_on_game_start": False,
            "check_integrity": True,
            "ui_mode": "gui"
        }
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    return {**default_settings, **json.load(f)}
        except Exception as e:
            logging.error(f"Failed to load settings: {e}")
        return default_settings

    def save_settings(self):
        """Save launcher settings"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            logging.error(f"Failed to save settings: {e}")

    def get_version(self) -> Optional[str]:
        """Get installed game version"""
        try:
            if self.version_file.exists():
                return self.version_file.read_text().strip()
        except Exception as e:
            logging.error(f"Failed to read version: {e}")
        return None

    def set_version(self, version: str):
        """Set installed game version"""
        try:
            self.version_file.write_text(version)
        except Exception as e:
            logging.error(f"Failed to write version: {e}")

    def get_game_path(self) -> Optional[Path]:
        """Get game installation path"""
        try:
            if self.game_path_file.exists():
                path = Path(self.game_path_file.read_text().strip())
                if path.exists():
                    return path
        except Exception as e:
            logging.error(f"Failed to read game path: {e}")
        return None

    def set_game_path(self, path: Path):
        """Set game installation path"""
        try:
            self.game_path_file.write_text(str(path))
        except Exception as e:
            logging.error(f"Failed to write game path: {e}")


class NetworkManager:
    """Handle all network operations"""
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': f'IsamAULauncher/{LAUNCHER_VERSION}'
        })

    def is_connected(self) -> bool:
        """Check internet connectivity"""
        try:
            self.session.get("https://www.google.com", timeout=3)
            return True
        except:
            return False

    def fetch_text(self, url: str) -> Optional[str]:
        """Fetch text content from URL"""
        try:
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.text.strip()
        except requests.RequestException as e:
            logging.error(f"Failed to fetch {url}: {e}")
            return None

    def download_file(self, url: str, output_path: Path, progress_callback=None) -> bool:
        """Download file with progress tracking"""
        try:
            start_time = time.time()
            with self.session.get(url, stream=True, timeout=REQUEST_TIMEOUT) as response:
                response.raise_for_status()
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0

                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if progress_callback and total_size:
                                elapsed = time.time() - start_time
                                speed = downloaded / elapsed if elapsed > 0 else 0
                                progress_callback(downloaded, total_size, speed)
            return True
        except requests.RequestException as e:
            logging.error(f"Download failed: {e}")
            return False

    def get_releases(self) -> List[GameVersion]:
        """Fetch available game versions from GitHub"""
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases"
        try:
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            releases = response.json()
            versions = []
            for release in releases:
                for asset in release.get("assets", []):
                    if asset["name"] == "app.zip":
                        versions.append(GameVersion(
                            version=release.get("tag_name"),
                            url=asset["browser_download_url"]
                        ))
            return versions
        except Exception as e:
            logging.error(f"Failed to fetch releases: {e}")
            return []


class FileManager:
    """Handle file operations"""
    @staticmethod
    def calculate_checksum(file_path: Path) -> str:
        """Calculate SHA256 checksum of file"""
        sha256 = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(CHUNK_SIZE), b''):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception as e:
            logging.error(f"Failed to calculate checksum: {e}")
            return ""

    @staticmethod
    def extract_zip(zip_path: Path, extract_to: Path, progress_callback=None) -> bool:
        """Extract zip file with progress"""
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                members = zip_ref.infolist()
                total = len(members)
                for i, member in enumerate(members):
                    zip_ref.extract(member, extract_to)
                    if progress_callback:
                        progress_callback(i + 1, total)
            return True
        except zipfile.BadZipFile as e:
            logging.error(f"Corrupt zip file: {e}")
            return False
        except Exception as e:
            logging.error(f"Extraction failed: {e}")
            return False

    @staticmethod
    def remove_readonly(func, path, exc_info):
        """Remove read-only flag and retry"""
        os.chmod(path, stat.S_IWRITE)
        func(path)

    @staticmethod
    def safe_delete(path: Path) -> bool:
        """Safely delete file or directory"""
        try:
            if not path.exists():
                return True
            if path.is_dir():
                shutil.rmtree(path, onerror=FileManager.remove_readonly)
            else:
                path.unlink()
            return True
        except Exception as e:
            logging.error(f"Failed to delete {path}: {e}")
            return False

    @staticmethod
    def format_size(bytes: int) -> str:
        """Convert bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes < 1024:
                return f"{bytes:.2f} {unit}"
            bytes /= 1024
        return f"{bytes:.2f} TB"


class DiscordRPC:
    """Discord Rich Presence manager"""
    def __init__(self):
        self.rpc: Optional[Presence] = None
        self.connected = False

    def connect(self) -> bool:
        """Connect to Discord RPC"""
        if not DISCORD_RPC_AVAILABLE:
            return False
        try:
            if self.connected and self.rpc:
                try:
                    self.rpc.close()
                except:
                    pass

            self.rpc = Presence(DISCORD_CLIENT_ID)
            self.rpc.connect()
            self.connected = True
            self.update_status("In Launcher", "Browsing Menu")
            return True
        except Exception as e:
            logging.error(f"Discord RPC failed: {e}")
            self.connected = False
            return False

    def update_status(self, state: str, details: str, large_text: str = APP_NAME):
        """Update Discord status"""
        if self.connected and self.rpc:
            try:
                self.rpc.update(
                    state=state,
                    details=details,
                    large_image="amongus",
                    large_text=large_text
                )
            except Exception as e:
                logging.error(f"Failed to update RPC: {e}")
                self.connected = False

    def disconnect(self):
        """Disconnect from Discord RPC"""
        if self.connected and self.rpc:
            try:
                self.rpc.close()
                self.connected = False
            except:
                pass


class ModernUI:
    """A clean, sleek launcher GUI for Isam AULauncher"""

    FONT = "Segoe UI"

    # Palette
    BG_DARK = "#0e1116"
    BG_MEDIUM = "#151a23"
    BG_LIGHT = "#1d2430"
    BG_HOVER = "#272f3f"
    SHADOW = "#080a0f"

    ACCENT = "#7c5cff"
    ACCENT_2 = "#00d4ff"
    GREEN = "#2dd98a"
    GREEN_HOVER = "#1fb371"
    BLUE = "#4f8dff"
    BLUE_HOVER = "#3670d9"
    RED = "#ff5470"
    RED_HOVER = "#d93c55"
    PURPLE = "#a45cff"
    PURPLE_HOVER = "#8a44d9"
    ORANGE = "#ffaf3d"
    ORANGE_HOVER = "#d98f2b"
    TEXT = "#eef1f8"
    DIM = "#8b93a7"

    def __init__(self, config: Config, network: NetworkManager):
        self.config = config
        self.network = network
        self.discord = DiscordRPC()

        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} v{LAUNCHER_VERSION}")
        self.root.geometry("1150x740")
        self.root.minsize(1024, 660)
        self.root.configure(bg=self.BG_DARK)

        self.menu_expanded = tk.BooleanVar(value=True)
        self.current_version = tk.StringVar(value="Not Installed")
        self.latest_version = tk.StringVar(value="Checking...")
        self.status_text = tk.StringVar(value="Ready")
        self.progress_var = tk.DoubleVar(value=0)
        self.current_tab = tk.StringVar(value="game")

        self._images = []  # keep PhotoImage references alive
        self._active_scroll_canvas = None

        self.setup_ui()
        self.load_initial_data()

    # ---------------- helpers ----------------

    @staticmethod
    def _hex_to_rgb(value: str) -> Tuple[int, int, int]:
        value = value.lstrip("#")
        return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))

    def _make_gradient(self, width: int, height: int, color_start: str, color_end: str):
        """Create a smooth horizontal gradient PhotoImage"""
        width = max(width, 2)
        height = max(height, 2)
        r1, g1, b1 = self._hex_to_rgb(color_start)
        r2, g2, b2 = self._hex_to_rgb(color_end)
        palette = Image.new("RGB", (256, 1))
        for i in range(256):
            t = i / 255
            palette.putpixel((i, 0), (
                int(r1 + (r2 - r1) * t),
                int(g1 + (g2 - g1) * t),
                int(b1 + (b2 - b1) * t)
            ))
        img = palette.resize((width, height))
        photo = ImageTk.PhotoImage(img)
        self._images.append(photo)
        return photo

    def _flat_button(self, parent, text, command, bg, hover, fg=None,
                    font=None, padx=15, pady=10, anchor=None):
        """Button with clean hover state"""
        btn = tk.Button(
            parent,
            text=text,
            font=font or (self.FONT, 10, "bold"),
            bg=bg,
            fg=fg or self.TEXT,
            activebackground=hover,
            activeforeground="white",
            relief=tk.FLAT,
            cursor="hand2",
            command=command,
            padx=padx,
            pady=pady,
            borderwidth=0
        )
        if anchor:
            btn.config(anchor=anchor)
        btn.bind("<Enter>", lambda e, b=btn, h=hover, c=bg: b.config(bg=h))
        btn.bind("<Leave>", lambda e, b=btn, h=hover, c=bg: b.config(bg=c))
        return btn

    def _hero(self, parent, height, start, end, title, subtitle, chip=None):
        """Gradient hero banner with title/subtitle"""
        canvas = tk.Canvas(parent, height=height, bg=self.BG_DARK, highlightthickness=0)
        canvas.pack(fill=tk.X, pady=20)
        canvas.bind("<Configure>", lambda e, c=canvas: self._redraw_hero(c, start, end, title, subtitle, chip))

        self._redraw_hero(canvas, start, end, title, subtitle, chip)
        return canvas

    def _redraw_hero(self, canvas, start, end, title, subtitle, chip):
        canvas.delete("all")
        w = max(canvas.winfo_width(), 60)
        h = canvas.winfo_height()
        photo = self._make_gradient(w, h, start, end)
        canvas.create_image(0, 0, image=photo, anchor="nw")
        canvas.create_text(
            30, h // 2 - 18, text=title,
            font=(self.FONT, 22, "bold"), fill=self.TEXT, anchor="w"
        )
        canvas.create_text(
            30, h // 2 + 16, text=subtitle,
            font=(self.FONT, 10), fill=self.DIM, anchor="w"
        )
        if chip:
            try:
                canvas.create_rectangle(w - 108, 14, w - 22, 40, fill=self.SHADOW, outline="")
            except Exception:
                pass
            canvas.create_text(
                w - 65, 27, text=chip,
                font=(self.FONT, 10, "bold"), fill=self.ACCENT_2, anchor="center"
            )

    def _section_header(self, parent, text):
        tk.Label(
            parent,
            text=text,
            font=(self.FONT, 10, "bold"),
            bg=self.BG_MEDIUM,
            fg=self.DIM,
            anchor=tk.W
        ).pack(anchor=tk.W, pady=(0, 8))

    # ---------------- main UI ----------------

    def setup_ui(self):
        self._build_sidebar()
        self._build_content()

    def _build_sidebar(self):
        width = 250
        self.sidebar_container = tk.Frame(self.root, bg=self.BG_MEDIUM, width=width)
        self.sidebar_container.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar_container.pack_propagate(False)

        self.sidebar_canvas = tk.Canvas(
            self.sidebar_container, bg=self.BG_MEDIUM, highlightthickness=0, width=width
        )
        sidebar_scrollbar = ttk.Scrollbar(
            self.sidebar_container, orient="vertical", command=self.sidebar_canvas.yview
        )
        self.sidebar_frame = tk.Frame(self.sidebar_canvas, bg=self.BG_MEDIUM)
        self.sidebar_frame.bind(
            "<Configure>",
            lambda e: self.sidebar_canvas.configure(scrollregion=self.sidebar_canvas.bbox("all"))
        )
        self.sidebar_canvas.create_window((0, 0), window=self.sidebar_frame, anchor="nw")
        self.sidebar_canvas.configure(yscrollcommand=sidebar_scrollbar.set)

        self.sidebar_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sidebar_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.sidebar_canvas.bind("<Enter>", lambda e: setattr(self, "_active_scroll_canvas", self.sidebar_canvas))
        self.sidebar_canvas.bind("<Leave>", lambda e: setattr(self, "_active_scroll_canvas", None))
        self.root.bind_all("<MouseWheel>", self._on_mousewheel)

        # Brand header
        brand_strip = tk.Canvas(self.sidebar_frame, height=6, bg=self.BG_MEDIUM, highlightthickness=0)
        brand_strip.pack(fill=tk.X)
        brand_strip.bind("<Configure>", lambda e, c=brand_strip: self._draw_brand_strip(c))
        self._draw_brand_strip(brand_strip)

        brand_frame = tk.Frame(self.sidebar_frame, bg=self.BG_MEDIUM)
        brand_frame.pack(fill=tk.X, padx=16, pady=(14, 6))

        tk.Label(
            brand_frame, text=BRAND_SHORT,
            font=(self.FONT, 20, "bold"), bg=self.BG_MEDIUM, fg=self.TEXT
        ).pack(anchor=tk.W)

        tk.Label(
            brand_frame, text=APP_NAME,
            font=(self.FONT, 10), bg=self.BG_MEDIUM, fg=self.DIM
        ).pack(anchor=tk.W, pady=(1, 0))

        tk.Label(
            brand_frame, text=f"v{LAUNCHER_VERSION}",
            font=(self.FONT, 9, "bold"), bg=self.BG_MEDIUM, fg=self.PURPLE
        ).pack(anchor=tk.W, pady=(4, 0))

        self._divider(self.sidebar_frame)

        # Navigation
        nav_frame = tk.Frame(self.sidebar_frame, bg=self.BG_MEDIUM)
        nav_frame.pack(fill=tk.X, padx=14, pady=8)

        self.tab_buttons = {}
        tabs = [
            ("Game", "game", self.ACCENT),
            ("News", "news", self.BLUE),
        ]
        for text, tab_id, accent in tabs:
            btn = self.create_tab_button(nav_frame, text, tab_id, accent)
            btn.pack(fill=tk.X, pady=3)
            self.tab_buttons[tab_id] = btn

        self._divider(self.sidebar_frame)

        tools_frame = tk.Frame(self.sidebar_frame, bg=self.BG_MEDIUM)
        tools_frame.pack(fill=tk.X, padx=14, pady=8)
        self._section_header(tools_frame, "TOOLS")
        for text, cmd, accent in [
            ("Install AUnlocker", self.install_aunlocker, self.BLUE),
            ("Create Shortcut", self.create_shortcut, self.DIM),
            ("Open Folder", self.open_folder, self.DIM),
            ("Change Location", self.change_location, self.DIM),
        ]:
            self._sidebar_button(tools_frame, text, cmd, accent).pack(fill=tk.X, pady=2)

        self._divider(self.sidebar_frame)

        settings_frame = tk.Frame(self.sidebar_frame, bg=self.BG_MEDIUM)
        settings_frame.pack(fill=tk.X, padx=14, pady=8)
        self._section_header(settings_frame, "SETTINGS")
        for text, cmd, accent in [
            ("Preferences", self.show_settings, self.GREEN),
            ("Reinstall Game", self.reinstall_game, self.BLUE),
            ("Uninstall", self.uninstall_game, self.RED),
        ]:
            self._sidebar_button(settings_frame, text, cmd, accent).pack(fill=tk.X, pady=2)

        # Footer (always visible)
        footer = tk.Frame(self.sidebar_container, bg=self.BG_MEDIUM)
        footer.pack(side=tk.BOTTOM, fill=tk.X, padx=14, pady=12)

        for text, cmd, accent in [
            ("Discord", lambda: os.system(f"start {DISCORD_INVITE}"), self.PURPLE),
            ("YouTube", lambda: os.system(f"start {YOUTUBE_CHANNEL}"), self.RED),
            ("Source Code", lambda: os.system(f"start {SOURCE_CODE_URL}"), self.ORANGE),
        ]:
            self._flat_button(
                footer, text, cmd, self.BG_LIGHT, accent, padx=14, pady=8
            ).pack(fill=tk.X, pady=3)

        tk.Label(
            footer,
            text=f"{APP_NAME} v{LAUNCHER_VERSION}  ·  Made by {MAKER}",
            font=(self.FONT, 8),
            bg=self.BG_MEDIUM,
            fg=self.DIM
        ).pack(pady=(10, 0))

    def _draw_brand_strip(self, canvas):
        canvas.delete("all")
        w = max(canvas.winfo_width(), 2)
        photo = self._make_gradient(w, 6, self.ACCENT_2, self.PURPLE)
        canvas.create_image(0, 0, image=photo, anchor="nw")

    def _divider(self, parent):
        tk.Frame(parent, bg=self.BG_LIGHT, height=1).pack(fill=tk.X, padx=14, pady=8)

    def _sidebar_button(self, parent, text, command, accent):
        return self._flat_button(
            parent, text, command, self.BG_LIGHT, accent, padx=14, pady=9, anchor=tk.W
        )

    def create_tab_button(self, parent, text, tab_id, accent_color):
        """Create a tab navigation button with accent bar"""
        outer = tk.Frame(parent, bg=self.BG_LIGHT, height=40)
        outer.pack_propagate(False)

        bar = tk.Frame(outer, bg=self.BG_MEDIUM, width=4)
        bar.pack(side=tk.LEFT, fill=tk.Y)
        bar_id = bar

        btn = tk.Button(
            outer,
            text=text,
            font=(self.FONT, 11, "bold"),
            bg=self.BG_LIGHT,
            fg=self.TEXT,
            activebackground=self.BG_LIGHT,
            activeforeground=self.TEXT,
            relief=tk.FLAT,
            cursor="hand2",
            command=lambda: self.switch_tab(tab_id),
            anchor=tk.W,
            padx=14,
            borderwidth=0
        )
        btn.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        outer._tab_id = tab_id
        outer._tab_accent = accent_color
        outer._tab_bar = bar_id
        outer._tab_button = btn

        def on_enter(e):
            if self.current_tab.get() != tab_id:
                btn.config(bg=self.BG_HOVER)
                outer.config(bg=self.BG_HOVER)
                bar.config(bg=self.BG_HOVER)

        def on_leave(e):
            if self.current_tab.get() != tab_id:
                btn.config(bg=self.BG_LIGHT)
                outer.config(bg=self.BG_LIGHT)
                bar.config(bg=self.BG_MEDIUM)

        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        outer.bind("<Enter>", on_enter)
        outer.bind("<Leave>", on_leave)

        return outer

    def switch_tab(self, tab_id):
        """Switch between tabs"""
        self.current_tab.set(tab_id)

        self.game_tab.pack_forget()
        self.news_tab.pack_forget()

        for tid, btn in self.tab_buttons.items():
            accent = getattr(btn, "_tab_accent", self.ACCENT)
            bar = getattr(btn, "_tab_bar", None)
            button = getattr(btn, "_tab_button", None)

            if tid == tab_id:
                btn.config(bg=accent)
                if bar:
                    bar.config(bg="#ffffff")
                if button:
                    button.config(bg=accent, fg="white", activebackground=accent)
            else:
                btn.config(bg=self.BG_LIGHT)
                if bar:
                    bar.config(bg=self.BG_MEDIUM)
                if button:
                    button.config(bg=self.BG_LIGHT, fg=self.TEXT, activebackground=self.BG_LIGHT)

        if tab_id == "game":
            self.game_tab.pack(fill=tk.BOTH, expand=True)
        elif tab_id == "news":
            self.news_tab.pack(fill=tk.BOTH, expand=True)

    def _build_content(self):
        self.content_frame = tk.Frame(self.root, bg=self.BG_DARK)
        self.content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.game_tab = tk.Frame(self.content_frame, bg=self.BG_DARK)
        self.news_tab = tk.Frame(self.content_frame, bg=self.BG_DARK)

        self.setup_game_tab()
        self.setup_news_tab()

        self.switch_tab("game")
        self.setup_styles()

    # ---------------- game tab ----------------

    def setup_game_tab(self):
        self._hero(self.game_tab, 150, self.ACCENT_2, "#151a23",
                   "Game Management",
                   "Install, update, and manage your Among Us installation",
                   chip=f"v{LAUNCHER_VERSION}")

        info_row = tk.Frame(self.game_tab, bg=self.BG_DARK)
        info_row.pack(fill=tk.X, padx=25, pady=4)
        info_row.grid_columnconfigure(0, weight=1)
        info_row.grid_columnconfigure(1, weight=1)

        self._version_card(info_row, 0, "INSTALLED VERSION", self.current_version, self.GREEN)
        self._version_card(info_row, 1, "LATEST VERSION", self.latest_version, self.BLUE)

        action_frame = tk.Frame(self.game_tab, bg=self.BG_DARK)
        action_frame.pack(pady=24)

        self.main_button = self._flat_button(
            action_frame, "INSTALL GAME", self.main_action,
            self.GREEN, self.GREEN_HOVER, font=(self.FONT, 14, "bold"), padx=45, pady=16
        )
        self.main_button.grid(row=0, column=0, padx=8)

        self._flat_button(
            action_frame, "Check Updates", self.check_updates,
            self.BG_LIGHT, self.BLUE, padx=20, pady=14
        ).grid(row=0, column=1, padx=8)

        self._flat_button(
            action_frame, "Install Specific", self.install_specific,
            self.BG_LIGHT, self.PURPLE, padx=20, pady=14
        ).grid(row=0, column=2, padx=8)

        progress_container = tk.Frame(self.game_tab, bg=self.BG_DARK)
        progress_container.pack(fill=tk.X, padx=60, pady=14)

        progress_bg = tk.Frame(progress_container, bg=self.BG_MEDIUM, height=10)
        progress_bg.pack(fill=tk.X)

        self.progress_bar = ttk.Progressbar(
            progress_bg,
            variable=self.progress_var,
            maximum=100,
            mode='determinate',
            style="Custom.Horizontal.TProgressbar"
        )
        self.progress_bar.pack(fill=tk.BOTH, expand=True)

        status_frame = tk.Frame(progress_container, bg=self.BG_DARK)
        status_frame.pack(pady=(12, 0))

        self.status_icon = tk.Label(
            status_frame, text="●", font=(self.FONT, 12), bg=self.BG_DARK, fg=self.GREEN
        )
        self.status_icon.pack(side=tk.LEFT, padx=(0, 8))

        tk.Label(
            status_frame, textvariable=self.status_text,
            font=(self.FONT, 10), bg=self.BG_DARK, fg=self.DIM
        ).pack(side=tk.LEFT)

        bottom_bar = tk.Frame(self.game_tab, bg=self.BG_DARK)
        bottom_bar.pack(side=tk.BOTTOM, anchor=tk.SE, padx=25, pady=18)

        self._flat_button(
            bottom_bar, "…", self.show_kebab_menu,
            self.BG_LIGHT, self.BG_HOVER, font=(self.FONT, 14, "bold"),
            padx=14, pady=6
        ).pack()

    def _version_card(self, parent, column, label, var, accent):
        card = tk.Frame(parent, bg=self.BG_MEDIUM, highlightbackground=accent, highlightthickness=1)
        card.grid(row=0, column=column, padx=10, pady=8, sticky="nsew")

        strip = tk.Frame(card, bg=accent, height=4)
        strip.pack(fill=tk.X)

        inner = tk.Frame(card, bg=self.BG_MEDIUM)
        inner.pack(fill=tk.BOTH, padx=24, pady=16)

        tk.Label(
            inner, text=label, font=(self.FONT, 10, "bold"),
            bg=self.BG_MEDIUM, fg=self.DIM
        ).pack(anchor=tk.W)

        tk.Label(
            inner, textvariable=var, font=(self.FONT, 20, "bold"),
            bg=self.BG_MEDIUM, fg=accent
        ).pack(anchor=tk.W, pady=(6, 0))

    # ---------------- news tab ----------------

    def setup_news_tab(self):
        self._hero(self.news_tab, 130, self.BLUE, "#151a23",
                   "Game Updates & News",
                   "Stay up to date with the latest patches and updates",
                   chip=f"v{LAUNCHER_VERSION}")

        patches_container = tk.Frame(self.news_tab, bg=self.BG_DARK)
        patches_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=6)

        patches_canvas = tk.Canvas(patches_container, bg=self.BG_DARK, highlightthickness=0)
        patches_scrollbar = ttk.Scrollbar(
            patches_container, orient="vertical", command=patches_canvas.yview
        )
        self.patches_frame = tk.Frame(patches_canvas, bg=self.BG_DARK)
        self.patches_frame.bind(
            "<Configure>",
            lambda e: patches_canvas.configure(scrollregion=patches_canvas.bbox("all"))
        )
        patches_canvas.create_window((0, 0), window=self.patches_frame, anchor="nw", width=1)
        patches_canvas.configure(yscrollcommand=patches_scrollbar.set)

        patches_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        patches_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        patches_canvas.bind("<Enter>", lambda e: setattr(self, "_active_scroll_canvas", patches_canvas))
        patches_canvas.bind("<Leave>", lambda e: setattr(self, "_active_scroll_canvas", None))
        patches_canvas.bind("<Configure>", lambda e: patches_canvas.itemconfigure(1, width=e.width - 10))

        self.load_patches()

    def load_patches(self):
        """Load and display patches from XML"""
        def fetch_and_display():
            try:
                for widget in self.patches_frame.winfo_children():
                    widget.destroy()

                xml_data = self.network.fetch_text(PATCHES_URL)
                if not xml_data:
                    self.show_patch_error("Failed to load patches")
                    return

                import xml.etree.ElementTree as ET
                root = ET.fromstring(xml_data)
                patches = root.findall('.//patch')

                if not patches:
                    self.show_patch_error("No patches found")
                    return

                for i, patch in enumerate(patches):
                    title = patch.find('Title')
                    text = patch.find('Text')
                    link = patch.find('Link')
                    if title is not None and text is not None:
                        self.create_patch_card(
                            title.text or "Unknown Version",
                            text.text or "No description",
                            link.text if link is not None and link.text else None,
                            i
                        )
            except Exception as e:
                logging.error(f"Failed to load patches: {e}")
                self.show_patch_error(f"Error loading patches: {str(e)}")

        threading.Thread(target=fetch_and_display, daemon=True).start()

    def create_patch_card(self, title, description, link, index):
        """Create a patch card"""
        colors = [self.BLUE, self.PURPLE, self.GREEN, self.ORANGE]
        accent = colors[index % len(colors)]

        card = tk.Frame(
            self.patches_frame, bg=self.BG_MEDIUM,
            highlightbackground=self.BG_LIGHT, highlightthickness=1
        )
        card.pack(fill=tk.X, padx=8, pady=8)

        bar = tk.Frame(card, bg=accent, width=5)
        bar.pack(side=tk.LEFT, fill=tk.Y)

        content = tk.Frame(card, bg=self.BG_MEDIUM)
        content.pack(fill=tk.BOTH, padx=18, pady=14)

        title_row = tk.Frame(content, bg=self.BG_MEDIUM)
        title_row.pack(fill=tk.X, pady=(0, 8))

        badge = tk.Label(
            title_row, text=title, font=(self.FONT, 10, "bold"),
            bg=accent, fg="white", padx=10, pady=4
        )
        badge.pack(side=tk.LEFT, padx=(0, 10))

        tk.Label(
            title_row, text=f"{APP_NAME} Update",
            font=(self.FONT, 9), bg=self.BG_MEDIUM, fg=self.DIM
        ).pack(side=tk.LEFT)

        tk.Label(
            content, text=description, font=(self.FONT, 10),
            bg=self.BG_MEDIUM, fg=self.TEXT, wraplength=680, justify=tk.LEFT
        ).pack(anchor=tk.W, pady=(0, 10))

        if link and link.strip():
            self._flat_button(
                content, "Read More",
                lambda: os.system(f"start {link}"),
                self.BG_LIGHT, accent
            ).pack(anchor=tk.W)

    def show_patch_error(self, message):
        """Show error message in patches tab"""
        error_frame = tk.Frame(self.patches_frame, bg=self.BG_DARK)
        error_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=40)

        tk.Label(
            error_frame, text="No connection",
            font=(self.FONT, 20, "bold"), bg=self.BG_DARK, fg=self.RED
        ).pack(pady=20)

        tk.Label(
            error_frame, text=message,
            font=(self.FONT, 12), bg=self.BG_DARK, fg=self.DIM
        ).pack()

    # ---------------- styles ----------------

    def setup_styles(self):
        """Setup ttk styles"""
        style = ttk.Style()
        style.theme_use('clam')

        style.configure(
            "Custom.Horizontal.TProgressbar",
            troughcolor=self.BG_MEDIUM,
            background=self.ACCENT,
            borderwidth=0,
            thickness=10
        )

        style.configure(
            "TScrollbar",
            background=self.BG_MEDIUM,
            troughcolor=self.BG_DARK,
            borderwidth=0,
            arrowcolor=self.TEXT
        )

    def _on_mousewheel(self, event):
        """Unified mousewheel handler for scrollable canvases"""
        try:
            canvas = self._active_scroll_canvas
            if not canvas:
                return
            delta = int(-1 * (event.delta / 120))
            canvas.yview_scroll(delta, "units")
        except Exception:
            pass

    # ---------------- state & actions ----------------

    def load_initial_data(self):
        """Load initial data in background"""
        def load():
            version = self.config.get_version()
            if version:
                self.current_version.set(version)
                self.update_main_button()

            latest = self.network.fetch_text(VERSION_URL)
            if latest:
                self.latest_version.set(latest)
                self.update_main_button()

            if self.config.settings.get("discord_rpc"):
                self.discord.connect()

        threading.Thread(target=load, daemon=True).start()

    def update_main_button(self):
        """Update the main button based on game state"""
        current = self.current_version.get()
        latest = self.latest_version.get()
        game_path = self.config.get_game_path()

        if current == "Not Installed" or not game_path or not (game_path / "Among Us.exe").exists():
            self._style_main_button("INSTALL GAME", self.GREEN, self.GREEN_HOVER)
        elif current != latest and latest != "Checking...":
            self._style_main_button("UPDATE AVAILABLE", self.BLUE, self.BLUE_HOVER)
        else:
            self._style_main_button("LAUNCH GAME", self.GREEN, self.GREEN_HOVER)

    def _style_main_button(self, text, color, hover):
        """Style the main action button for its current state"""
        self.main_button.config(text=text, bg=color, activebackground=hover)
        self.main_button.bind("<Enter>", lambda e, c=color, h=hover: self.main_button.config(bg=h))
        self.main_button.bind("<Leave>", lambda e, c=color, h=hover: self.main_button.config(bg=c))

    def main_action(self):
        """Main button action"""
        button_text = self.main_button.cget("text")

        if "INSTALL" in button_text:
            self.download_latest()
        elif "UPDATE" in button_text:
            self.download_latest()
        elif "LAUNCH" in button_text:
            self.launch_game()

    def show_kebab_menu(self):
        """Show kebab menu with additional options"""
        menu = tk.Menu(self.root, tearoff=0, bg=self.BG_LIGHT, fg=self.TEXT)
        menu.add_command(label="Verify Game Files", command=self.verify_files)
        menu.add_command(label="View Logs", command=self.view_logs)
        menu.add_separator()
        menu.add_command(label="About", command=self.show_about)

        try:
            menu.tk_popup(self.root.winfo_pointerx(), self.root.winfo_pointery())
        finally:
            menu.grab_release()

    def download_latest(self):
        """Download latest game version"""
        def download():
            self.status_text.set("Preparing download...")
            self.main_button.config(state=tk.DISABLED)

            latest = self.latest_version.get()
            if latest == "Checking...":
                latest = self.network.fetch_text(VERSION_URL)
                if not latest:
                    self.status_text.set("Failed to fetch version info")
                    self.main_button.config(state=tk.NORMAL)
                    return

            game_path = self.config.get_game_path()
            if not game_path:
                game_path = self.select_install_location()
                if not game_path:
                    self.status_text.set("Installation cancelled")
                    self.main_button.config(state=tk.NORMAL)
                    return

            url = f"https://github.com/{GITHUB_REPO}/releases/download/{latest}/app.zip"
            zip_file = Path("game.zip")

            self.status_text.set(f"Downloading version {latest}...")

            def progress(current, total, speed):
                percent = (current / total * 100) if total else 0
                self.progress_var.set(percent)
                speed_str = FileManager.format_size(speed) + "/s"
                self.status_text.set(f"Downloading: {percent:.1f}% - {speed_str}")

            if not self.network.download_file(url, zip_file, progress):
                self.status_text.set("Download failed!")
                self.main_button.config(state=tk.NORMAL)
                return

            self.status_text.set("Extracting files...")
            game_path.mkdir(parents=True, exist_ok=True)

            def extract_progress(current, total):
                percent = (current / total * 100) if total else 0
                self.progress_var.set(percent)
                self.status_text.set(f"Extracting: {percent:.1f}%")

            if not FileManager.extract_zip(zip_file, game_path, extract_progress):
                self.status_text.set("Extraction failed!")
                self.main_button.config(state=tk.NORMAL)
                return

            FileManager.safe_delete(zip_file)
            self.config.set_version(latest)
            self.config.set_game_path(game_path)
            self.current_version.set(latest)

            self.progress_var.set(100)
            self.status_text.set("Installation complete!")
            self.main_button.config(state=tk.NORMAL)
            self.update_main_button()

            messagebox.showinfo("Success", f"Game version {latest} installed successfully!")

        threading.Thread(target=download, daemon=True).start()

    def check_updates(self):
        """Check for game updates"""
        def check():
            self.status_text.set("Checking for updates...")
            latest = self.network.fetch_text(VERSION_URL)
            if latest:
                self.latest_version.set(latest)
                current = self.current_version.get()
                if current == latest:
                    messagebox.showinfo("Up to Date", "You have the latest version!")
                else:
                    messagebox.showinfo("Update Available", f"New version available: {latest}")
                self.update_main_button()
            else:
                messagebox.showerror("Error", "Failed to check for updates")
            self.status_text.set("Ready")

        threading.Thread(target=check, daemon=True).start()

    def install_specific(self):
        """Install specific game version"""
        versions_window = tk.Toplevel(self.root)
        versions_window.title("Install Specific Version")
        versions_window.geometry("420x520")
        versions_window.configure(bg=self.BG_DARK)
        versions_window.transient(self.root)

        tk.Label(
            versions_window, text="Available Versions",
            font=(self.FONT, 15, "bold"), bg=self.BG_DARK, fg=self.TEXT
        ).pack(pady=12)

        listbox_frame = tk.Frame(versions_window, bg=self.BG_DARK)
        listbox_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        scrollbar = ttk.Scrollbar(listbox_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        listbox = tk.Listbox(
            listbox_frame,
            bg=self.BG_MEDIUM,
            fg=self.TEXT,
            selectbackground=self.BLUE,
            selectforeground="white",
            font=(self.FONT, 10),
            yscrollcommand=scrollbar.set,
            relief=tk.FLAT,
            highlightthickness=0
        )
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=listbox.yview)

        versions = self.network.get_releases()
        for v in versions:
            listbox.insert(tk.END, v.version)

        def install_selected():
            selection = listbox.curselection()
            if selection:
                selected = versions[selection[0]]
                versions_window.destroy()
                self.install_version(selected)

        self._flat_button(
            versions_window, "Install Selected", install_selected,
            self.BLUE, self.BLUE_HOVER, padx=30, pady=12
        ).pack(pady=12)

    def install_version(self, version: GameVersion):
        """Install a specific version"""
        def install():
            game_path = self.config.get_game_path() or self.select_install_location()
            if not game_path:
                return

            self.status_text.set(f"Installing version {version.version}...")
            self.main_button.config(state=tk.DISABLED)

            zip_file = Path("game.zip")

            def progress(current, total, speed):
                percent = (current / total * 100) if total else 0
                self.progress_var.set(percent)
                self.status_text.set(f"Downloading: {percent:.1f}%")

            if self.network.download_file(version.url, zip_file, progress):
                game_path.mkdir(parents=True, exist_ok=True)
                FileManager.extract_zip(zip_file, game_path)
                FileManager.safe_delete(zip_file)
                self.config.set_version(version.version)
                self.config.set_game_path(game_path)
                self.current_version.set(version.version)
                messagebox.showinfo("Success", f"Version {version.version} installed!")
            else:
                messagebox.showerror("Error", "Installation failed!")

            self.main_button.config(state=tk.NORMAL)
            self.status_text.set("Ready")
            self.update_main_button()

        threading.Thread(target=install, daemon=True).start()

    def launch_game(self):
        """Launch the game"""
        game_path = self.config.get_game_path()
        if not game_path:
            messagebox.showerror("Error", "Game not installed!")
            return

        exe_path = game_path / "Among Us.exe"
        if not exe_path.exists():
            messagebox.showerror("Error", "Game executable not found!")
            return

        try:
            subprocess.Popen([str(exe_path)], cwd=str(game_path))
            self.status_text.set("Game launched!")
            if self.config.settings.get("minimize_on_game_start"):
                self.root.iconify()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch game: {e}")

    # ---------------- tools ----------------

    def install_aunlocker(self):
        """Install AUnlocker"""
        version = self.config.get_version()
        game_path = self.config.get_game_path()

        if not version or not game_path:
            messagebox.showerror("Error", "Game not installed!")
            return

        def install():
            self.status_text.set("Checking AUnlocker compatibility...")
            data = self.network.fetch_text(AUNLOCKER_JSON_URL)

            if not data:
                messagebox.showerror("Error", "Failed to fetch AUnlocker data")
                return

            try:
                versions = json.loads(data).get("versions", [])
                for entry in versions:
                    if entry["version"] == version:
                        zip_path = Path("AUnlocker.zip")
                        self.status_text.set("Downloading AUnlocker...")
                        if self.network.download_file(entry["link"], zip_path):
                            FileManager.extract_zip(zip_path, game_path)
                            FileManager.safe_delete(zip_path)
                            messagebox.showinfo("Success", "AUnlocker installed!")
                            self.status_text.set("Ready")
                            return
                messagebox.showwarning("Not Found", "No compatible AUnlocker for this version")
            except json.JSONDecodeError:
                messagebox.showerror("Error", "Invalid AUnlocker data")

            self.status_text.set("Ready")

        threading.Thread(target=install, daemon=True).start()

    def create_shortcut(self):
        """Create desktop shortcut"""
        game_path = self.config.get_game_path()
        if not game_path:
            messagebox.showerror("Error", "Game not installed!")
            return

        exe = game_path / "Among Us.exe"
        version = self.config.get_version()

        try:
            desktop = Path.home() / "Desktop"
            shortcut_path = desktop / f"Among Us {version}.lnk"
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(str(shortcut_path))
            shortcut.Targetpath = str(exe)
            shortcut.WorkingDirectory = str(game_path)
            shortcut.IconLocation = str(exe)
            shortcut.save()
            messagebox.showinfo("Success", "Shortcut created on desktop!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create shortcut: {e}")

    def open_folder(self):
        """Open game folder"""
        game_path = self.config.get_game_path()
        if game_path and game_path.exists():
            os.startfile(game_path)
        else:
            messagebox.showerror("Error", "Game folder not found!")

    def change_location(self):
        """Change game installation location"""
        new_path = self.select_install_location()
        if not new_path:
            return

        old_path = self.config.get_game_path()
        if old_path and old_path.exists():
            if messagebox.askyesno("Move Files", "Move existing game files to new location?"):
                try:
                    shutil.move(str(old_path), str(new_path))
                    messagebox.showinfo("Success", "Game files moved successfully!")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to move files: {e}")

        self.config.set_game_path(new_path)
        messagebox.showinfo("Success", f"Location changed to: {new_path}")

    def show_settings(self):
        """Show settings window"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("500x470")
        settings_window.configure(bg=self.BG_DARK)
        settings_window.transient(self.root)
        settings_window.resizable(False, False)

        settings_window.update_idletasks()
        x = (settings_window.winfo_screenwidth() // 2) - (500 // 2)
        y = (settings_window.winfo_screenheight() // 2) - (470 // 2)
        settings_window.geometry(f"500x470+{x}+{y}")

        header_frame = tk.Frame(settings_window, bg=self.BG_MEDIUM, height=70)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)

        tk.Label(
            header_frame, text="Launcher Settings", font=(self.FONT, 15, "bold"),
            bg=self.BG_MEDIUM, fg=self.TEXT
        ).pack(anchor=tk.W, padx=24, pady=18)

        container = tk.Frame(settings_window, bg=self.BG_DARK)
        container.pack(fill=tk.BOTH, expand=True, padx=24, pady=10)

        settings_canvas = tk.Canvas(container, bg=self.BG_DARK, highlightthickness=0)
        settings_scrollbar = ttk.Scrollbar(container, orient="vertical", command=settings_canvas.yview)
        settings_canvas.configure(yscrollcommand=settings_scrollbar.set)

        settings_inner = tk.Frame(settings_canvas, bg=self.BG_DARK)
        settings_inner.bind(
            "<Configure>",
            lambda e: settings_canvas.configure(scrollregion=settings_canvas.bbox("all"))
        )
        window_id = settings_canvas.create_window((0, 0), window=settings_inner, anchor="nw")

        settings_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        settings_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        settings_canvas.bind("<Configure>", lambda e: settings_canvas.itemconfig(window_id, width=e.width))

        settings_canvas.bind("<Enter>", lambda e: setattr(self, "_active_scroll_canvas", settings_canvas))
        settings_canvas.bind("<Leave>", lambda e: setattr(self, "_active_scroll_canvas", None))

        settings = self.config.settings
        options = [
            ("Auto-update game", "auto_update", "Automatically download game updates"),
            ("Discord Rich Presence", "discord_rpc", "Show what you're doing on Discord"),
            ("Verify file integrity", "check_integrity", "Check file checksums after download"),
            ("Minimize on game start", "minimize_on_game_start", "Hide launcher when game starts"),
        ]

        vars = {}
        for label, key, desc in options:
            option_frame = tk.Frame(settings_inner, bg=self.BG_MEDIUM)
            option_frame.pack(fill=tk.X, pady=7)

            var = tk.BooleanVar(value=settings.get(key, False))
            vars[key] = var

            cb_frame = tk.Frame(option_frame, bg=self.BG_MEDIUM)
            cb_frame.pack(fill=tk.X, padx=18, pady=13)

            cb = tk.Checkbutton(
                cb_frame,
                text=label,
                variable=var,
                bg=self.BG_MEDIUM,
                fg=self.TEXT,
                selectcolor=self.BG_LIGHT,
                activebackground=self.BG_MEDIUM,
                activeforeground=self.TEXT,
                font=(self.FONT, 10, "bold"),
                cursor="hand2",
                relief=tk.FLAT,
                borderwidth=0,
                highlightthickness=0
            )
            cb.pack(anchor=tk.W)

            tk.Label(
                cb_frame, text=desc, font=(self.FONT, 8),
                bg=self.BG_MEDIUM, fg=self.DIM
            ).pack(anchor=tk.W, padx=(24, 0), pady=(2, 0))

            def on_enter(e, frame=option_frame):
                frame.config(bg=self.BG_LIGHT)
                for widget in frame.winfo_children():
                    widget.config(bg=self.BG_LIGHT)
                    for child in widget.winfo_children():
                        if isinstance(child, (tk.Label, tk.Checkbutton)):
                            child.config(bg=self.BG_LIGHT)

            def on_leave(e, frame=option_frame):
                frame.config(bg=self.BG_MEDIUM)
                for widget in frame.winfo_children():
                    widget.config(bg=self.BG_MEDIUM)
                    for child in widget.winfo_children():
                        if isinstance(child, (tk.Label, tk.Checkbutton)):
                            child.config(bg=self.BG_MEDIUM)

            option_frame.bind("<Enter>", on_enter)
            option_frame.bind("<Leave>", on_leave)

        button_frame = tk.Frame(settings_window, bg=self.BG_DARK)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=24, pady=16)

        def save_settings():
            for key, var in vars.items():
                settings[key] = var.get()
            self.config.save_settings()

            if settings.get("discord_rpc") and not self.discord.connected:
                self.discord.connect()
            elif not settings.get("discord_rpc") and self.discord.connected:
                self.discord.disconnect()

            messagebox.showinfo("Success", "Settings saved successfully!")
            settings_window.destroy()

        self._flat_button(
            button_frame, "Save Settings", save_settings,
            self.GREEN, self.GREEN_HOVER, font=(self.FONT, 12, "bold"), padx=30, pady=12
        ).pack()

    # ---------------- maintenance ----------------

    def reinstall_game(self):
        """Reinstall the game"""
        if not messagebox.askyesno("Confirm", "This will delete and reinstall the game. Continue?"):
            return

        game_path = self.config.get_game_path()
        if game_path and game_path.exists():
            FileManager.safe_delete(game_path)

        self.current_version.set("Not Installed")
        self.download_latest()

    def uninstall_game(self):
        """Uninstall the game"""
        if not messagebox.askyesno("Confirm", "This will remove all game files and launcher data. Continue?"):
            return

        game_path = self.config.get_game_path()
        if game_path and game_path.exists():
            if FileManager.safe_delete(game_path):
                messagebox.showinfo("Success", "Game files removed")
            else:
                messagebox.showerror("Error", "Failed to remove game files")

        if FileManager.safe_delete(self.config.appdata_dir):
            messagebox.showinfo("Success", "Launcher data removed")
        else:
            messagebox.showerror("Error", "Failed to remove launcher data")

        self.current_version.set("Not Installed")
        self.update_main_button()

    def verify_files(self):
        """Verify game files integrity"""
        messagebox.showinfo("Info", "File verification coming soon!")

    def view_logs(self):
        """Open log file"""
        log_file = Path("launcher.log")
        if log_file.exists():
            os.startfile(log_file)
        else:
            messagebox.showinfo("Info", "No log file found")

    def show_about(self):
        """Show about dialog"""
        about_text = f"""{APP_NAME} v{LAUNCHER_VERSION}

Made by {MAKER}

A modern, clean launcher for Among Us
with auto-updates and mod support.

© 2026 {MAKER}"""
        messagebox.showinfo("About", about_text)

    def select_install_location(self) -> Optional[Path]:
        """Show folder selection dialog"""
        folder = filedialog.askdirectory(
            title="Select Among Us Installation Folder",
            initialdir=str(Path.cwd())
        )
        return Path(folder) if folder else None

    def run(self):
        """Start the GUI"""
        self.root.mainloop()
        if self.discord.connected:
            self.discord.disconnect()


def check_launcher_update(network: NetworkManager) -> bool:
    """Check for launcher updates before starting"""
    try:
        print(f"{Colors.INFO}Checking for launcher updates...{Colors.RESET}")
        latest = network.fetch_text(LAUNCHER_VERSION_URL)

        if latest and latest != LAUNCHER_VERSION:
            print(f"{Colors.WARNING}Launcher update available: {latest} (current: {LAUNCHER_VERSION}){Colors.RESET}")
            response = input(f"{Colors.HIGHLIGHT}Download and install update? (yes/no): {Colors.RESET}").lower()

            if response in ['yes', 'y']:
                new_exe = Path(f"IsamAULauncher_{latest}.exe")
                print(f"{Colors.INFO}Downloading update...{Colors.RESET}")

                if network.download_file(LAUNCHER_DOWNLOAD_URL, new_exe):
                    print(f"{Colors.SUCCESS}Update downloaded! Please run the new launcher.{Colors.RESET}")
                    subprocess.Popen([str(new_exe)])
                    return False
                else:
                    print(f"{Colors.ERROR}Update download failed. Continuing with current version.{Colors.RESET}")
        else:
            print(f"{Colors.SUCCESS}Launcher is up to date{Colors.RESET}")

        return True
    except Exception as e:
        logging.error(f"Launcher update check failed: {e}")
        print(f"{Colors.WARNING}Could not check for updates. Continuing...{Colors.RESET}")
        return True


def is_admin():
    """Check if running with admin privileges"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def request_admin():
    """Request admin privileges if not already admin"""
    if not is_admin():
        try:
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable,
                f'"{os.path.abspath(__file__)}"',
                None, 1
            )
            sys.exit()
        except Exception as e:
            logging.error(f"Failed to request admin: {e}")
            print(f"{Colors.ERROR}Failed to request administrator privileges.{Colors.RESET}")
            return False
    return True


if __name__ == "__main__":
    print(f"{Colors.INFO}Starting {APP_NAME}...{Colors.RESET}\n")

    while True:
        try:
            config = Config()
            network = NetworkManager()

            if not network.is_connected():
                print(f"{Colors.ERROR}No internet connection detected!{Colors.RESET}")
                print(f"{Colors.WARNING}Please connect to the internet and restart the launcher.{Colors.RESET}")
                input("\nPress Enter to exit...")
                break

            if not check_launcher_update(network):
                break

            print(f"\n{Colors.SUCCESS}Launching GUI...{Colors.RESET}\n")
            time.sleep(0.5)
            app = ModernUI(config, network)
            app.run()

            logging.info("Launcher closed normally")
            break

        except KeyboardInterrupt:
            print(f"\n{Colors.WARNING}[!] Launcher interrupted by user{Colors.RESET}")
            logging.info("Launcher interrupted by user")
            break

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logging.critical(error_msg, exc_info=True)
            print(f"\n{Colors.ERROR}╔════════════════════════════════════════════════╗{Colors.RESET}")
            print(f"{Colors.ERROR}║          CRITICAL ERROR OCCURRED               ║{Colors.RESET}")
            print(f"{Colors.ERROR}╚════════════════════════════════════════════════╝{Colors.RESET}")
            print(f"{Colors.ERROR}Error: {str(e)}{Colors.RESET}")
            print(f"{Colors.INFO}Full error details saved to launcher.log{Colors.RESET}\n")

            retry = input(f"{Colors.WARNING}Press Enter to restart launcher, or type 'exit' to quit: {Colors.RESET}").strip().lower()
            if retry == 'exit':
                logging.info("User chose to exit after error")
                break

            print(f"\n{Colors.INFO}Restarting launcher...{Colors.RESET}\n")

    print(f"\n{Colors.INFO}═══════════════════════════════════════════════════{Colors.RESET}")
    print(f"{Colors.GOLD}Thanks for using {APP_NAME}!{Colors.RESET}")
    print(f"{Colors.INFO}═══════════════════════════════════════════════════{Colors.RESET}\n")
    input("Press Enter to close...")