"""
Window — Steam-style sidebar launcher for Isam AULauncher.
"""
import math
import os
import json
import time
import random
import threading
import subprocess
import shutil
from pathlib import Path

import dearpygui.dearpygui as dpg

from config import (
    Config, APP_NAME, BRAND_SHORT, MAKER, LAUNCHER_VERSION,
    VERSION_URL, GITHUB_REPO, AUNLOCKER_JSON_URL, PATCHES_URL,
    DISCORD_INVITE, YOUTUBE_CHANNEL, SOURCE_CODE_URL,
)
from network import NetworkManager, DiscordRPC, GameVersion
from file_manager import FileManager
from theme import (
    apply_theme, init_accent_themes, bind_accent,
    init_modal_theme, bind_modal, init_sidebar_theme, bind_sidebar,
    ACCENT, ACCENT_2,
    SUCCESS, SUCCESS_HOVER, INFO, INFO_HOVER, DANGER, DANGER_HOVER,
    WARNING, PURPLE,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_BRIGHT,
    BG_BASE, BG_SURFACE, BG_ELEVATED, BG_HOVER, BG_ACTIVE,
    BORDER_SUBTLE,
)

_RESOURCES_DIR = Path(__file__).parent / "resources"
_HERO_IMAGE_PATH = _RESOURCES_DIR / "hero.png"
_ICON_PATH = _RESOURCES_DIR / "icon.ico"

SIDEBAR_W = 200


class LauncherApp:
    def __init__(self):
        self.config = Config()
        self.network = NetworkManager()
        self.discord = DiscordRPC()

        self.current_version = "Not Installed"
        self.latest_version = "Checking..."
        self.status_text = "Starting..."
        self.progress = 0.0
        self._busy = False
        self._active_page = "game"

        # Animation state
        self._particles = []
        self._glow_orbs = []
        self._hero_time = 0.0
        self._hero_active = False
        self._hero_texture = None
        self._hero_has_image = _HERO_IMAGE_PATH.exists()
        self._locate_pending = False
        self._change_location_pending = False
        self._install_folder_pending = False
        self._pending_install_path = None

        self._setup_dpg()
        self._build_ui()
        self._load_initial_data()

    # ------------------------------------------------------------------ setup
    def _setup_dpg(self):
        dpg.create_context()
        apply_theme()
        init_accent_themes()
        init_modal_theme()
        init_sidebar_theme()

        dpg.create_viewport(
            title=f"{APP_NAME} v{LAUNCHER_VERSION}",
            width=1100, height=680,
            min_width=960, min_height=580,
            resizable=True,
        )

        if _ICON_PATH.exists():
            try:
                dpg.set_viewport_large_icon(str(_ICON_PATH))
                dpg.set_viewport_small_icon(str(_ICON_PATH))
            except Exception:
                pass

        if self._hero_has_image:
            try:
                dpg.add_texture_registry(tag="hero_tex_registry")
                w, h, c, data = dpg.load_image(str(_HERO_IMAGE_PATH))
                dpg.add_dynamic_texture(w, h, data, tag="hero_texture",
                                        parent="hero_tex_registry")
                self._hero_texture = "hero_texture"
            except Exception:
                self._hero_has_image = False

        dpg.setup_dearpygui()

    def _build_ui(self):
        with dpg.window(tag="main_window", no_scrollbar=True, no_collapse=True,
                        width=-1, height=-1):
            with dpg.group(horizontal=True):
                self._build_sidebar()
                self._build_content_area()
            self._build_status_bar()

        dpg.set_primary_window("main_window", True)

        with dpg.file_dialog(directory_selector=True, show=False,
                             callback=self._folder_selected,
                             tag="folder_dialog", width=600, height=400,
                             modal=True):
            dpg.add_file_extension(".exe", color=(150, 255, 150, 255))
            dpg.add_file_extension(".*")

    # ------------------------------------------------------------------ sidebar
    def _build_sidebar(self):
        with dpg.child_window(width=SIDEBAR_W, tag="sidebar",
                              no_scrollbar=True):
            bind_sidebar("sidebar")
            dpg.add_spacer(height=16)
            dpg.add_text(BRAND_SHORT, color=ACCENT)
            dpg.add_spacer(height=2)
            dpg.add_text(APP_NAME, color=TEXT_MUTED)
            dpg.add_spacer(height=16)
            dpg.add_separator()
            dpg.add_spacer(height=8)

            # Nav items
            self._sidebar_btn("Game", "game", True)
            self._sidebar_btn("Tools", "tools", False)
            self._sidebar_btn("AUnlocker", "aunlocker", False)

            dpg.add_spacer(height=8)
            dpg.add_separator()
            dpg.add_spacer(height=8)

            self._sidebar_btn("Settings", "settings", False)
            self._sidebar_btn("About", "about", False)

    def _sidebar_btn(self, label, page_id, active=False):
        tag = f"nav_{page_id}"
        if page_id in ("settings", "about"):
            # These open modals, not pages
            if page_id == "settings":
                dpg.add_button(label=f"  {label}", tag=tag,
                               callback=self._cb_settings,
                               width=SIDEBAR_W - 20, height=36)
            elif page_id == "about":
                dpg.add_button(label=f"  {label}", tag=tag,
                               callback=self._cb_show_about,
                               width=SIDEBAR_W - 20, height=36)
        else:
            dpg.add_button(label=f"  {label}", tag=tag,
                           callback=self._switch_page,
                           width=SIDEBAR_W - 20, height=36)
        if active:
            bind_accent(tag, "accent")
            dpg.set_item_user_data(tag, True)
        else:
            dpg.set_item_user_data(tag, False)

    def _switch_page(self, sender, app_data):
        page_id = sender.replace("nav_", "")
        self._active_page = page_id

        for p in ("game", "tools", "aunlocker"):
            tag = f"nav_{p}"
            if p == page_id:
                bind_accent(tag, "accent")
                dpg.set_item_user_data(tag, True)
            else:
                dpg.bind_item_theme(tag, 0)
                dpg.set_item_user_data(tag, False)

        dpg.show_item("page_game") if page_id == "game" else dpg.hide_item("page_game")
        dpg.show_item("page_tools") if page_id == "tools" else dpg.hide_item("page_tools")
        dpg.show_item("page_aunlocker") if page_id == "aunlocker" else dpg.hide_item("page_aunlocker")

        if page_id == "game":
            self._start_hero_animation()
        else:
            self._stop_hero_animation()

    # ------------------------------------------------------------------ content area
    def _build_content_area(self):
        with dpg.group(tag="content_area"):
            self._build_game_page()
            self._build_tools_page()
            self._build_aunlocker_page()

    # ------------------------------------------------------------------ game page
    def _build_game_page(self):
        with dpg.group(tag="page_game"):
            self._build_hero("Game Management",
                             "Install, update, and manage your Among Us installation")

            dpg.add_spacer(height=16)

            # Action buttons
            with dpg.group(horizontal=True):
                dpg.add_spacer(width=8)
                dpg.add_button(label="INSTALL GAME", tag="main_action_btn",
                               callback=self._cb_main_action, width=-1, height=52)
                bind_accent("main_action_btn", "btn_success")
                dpg.add_spacer(width=8)
            with dpg.group(horizontal=True):
                dpg.add_spacer(width=8)
                dpg.add_button(label="LOCATE GAME", tag="locate_game_btn",
                               callback=self._cb_locate_game, width=-1, height=36, show=False)
                dpg.add_spacer(width=8)

            dpg.add_spacer(height=16)

            # Info row
            with dpg.group(horizontal=True):
                dpg.add_spacer(width=8)
                with dpg.group():
                    dpg.add_text("INSTALLED", color=TEXT_MUTED)
                    dpg.add_spacer(height=2)
                    dpg.add_text("Not Installed", tag="ver_installed", color=SUCCESS)
                    dpg.add_spacer(height=12)
                    dpg.add_text("LATEST", color=TEXT_MUTED)
                    dpg.add_spacer(height=2)
                    dpg.add_text("Checking...", tag="ver_latest", color=INFO)
                dpg.add_spacer(width=32)
                with dpg.group():
                    dpg.add_text("STATUS", color=TEXT_MUTED)
                    dpg.add_spacer(height=2)
                    with dpg.group(horizontal=True):
                        dpg.add_text("●", color=SUCCESS, tag="game_status_icon")
                        dpg.add_text("Starting...", tag="game_status_text",
                                     color=TEXT_SECONDARY)
                    dpg.add_spacer(height=10)
                    dpg.add_progress_bar(tag="progress_bar", default_value=0,
                                         width=360, height=20, overlay="0%")
                    dpg.add_spacer(height=4)
                    dpg.add_text("Ready", tag="game_ready_text", color=TEXT_MUTED)
                dpg.add_spacer(width=8)

    # ------------------------------------------------------------------ tools page
    def _build_tools_page(self):
        with dpg.group(tag="page_tools", show=False):
            dpg.add_spacer(height=20)
            dpg.add_text("TOOLS", color=TEXT_MUTED)
            dpg.add_spacer(height=12)
            with dpg.group(horizontal=True):
                dpg.add_spacer(width=8)
                dpg.add_button(label="Open Folder", callback=self._cb_open_folder,
                               width=180, height=44)
                dpg.add_spacer(width=8)
                dpg.add_button(label="Change Location", callback=self._cb_change_location,
                               width=180, height=44)
                dpg.add_spacer(width=8)
                dpg.add_button(label="Verify Files", callback=self._cb_verify,
                               width=180, height=44)
                dpg.add_spacer(width=8)
            dpg.add_spacer(height=8)
            with dpg.group(horizontal=True):
                dpg.add_spacer(width=8)
                dpg.add_button(label="Create Shortcut", callback=self._cb_create_shortcut,
                               width=180, height=44)
                dpg.add_spacer(width=8)
                dpg.add_button(label="Reinstall Game", callback=self._cb_reinstall,
                               width=180, height=44)
                dpg.add_spacer(width=8)
                dpg.add_button(label="Uninstall", callback=self._cb_uninstall,
                               width=180, height=44)
                bind_accent(dpg.last_item(), "btn_danger")
                dpg.add_spacer(width=8)

    # ------------------------------------------------------------------ aunlocker page
    def _build_aunlocker_page(self):
        with dpg.group(tag="page_aunlocker", show=False):
            dpg.add_spacer(height=20)
            dpg.add_text("AUNLOCKER", color=TEXT_MUTED)
            dpg.add_spacer(height=12)
            dpg.add_text("Install the Among Us unlocker for your game version.",
                         color=TEXT_SECONDARY)
            dpg.add_spacer(height=16)
            with dpg.group(horizontal=True):
                dpg.add_spacer(width=8)
                dpg.add_button(label="Install AUnlocker", tag="aunlocker_btn",
                               callback=self._cb_install_aunlocker, width=240, height=52)
                bind_accent("aunlocker_btn", "btn_primary")
                dpg.add_spacer(width=8)

    # ------------------------------------------------------------------ hero banner
    def _build_hero(self, title, subtitle):
        hero_h = 220
        with dpg.drawlist(width=-1, height=hero_h, tag="hero_drawlist"):
            pass
        self._hero_title = title
        self._hero_subtitle = subtitle
        self._init_particles()
        self._draw_hero_frame("hero_drawlist", title, subtitle)
        self._start_hero_animation()

    def _init_particles(self):
        random.seed(42)
        self._particles = []
        for _ in range(18):
            self._particles.append({
                "x": random.uniform(0.05, 0.95),
                "y": random.uniform(0.0, 1.0),
                "speed": random.uniform(0.0003, 0.001),
                "size": random.uniform(2.0, 4.0),
                "alpha": random.uniform(30, 60),
                "drift": random.uniform(-0.0002, 0.0002),
            })
        self._glow_orbs = [
            {"cx": 0.75, "cy": 0.35, "r": 80, "base_alpha": 40, "phase": 0.0},
            {"cx": 0.85, "cy": 0.6, "r": 60, "base_alpha": 30, "phase": 1.5},
            {"cx": 0.15, "cy": 0.7, "r": 65, "base_alpha": 25, "phase": 3.0},
        ]

    def _start_hero_animation(self):
        if self._hero_active:
            return
        self._hero_active = True
        self._hero_time = time.time()
        self._animate_hero()

    def _stop_hero_animation(self):
        self._hero_active = False

    def _animate_hero(self):
        if not self._hero_active:
            return
        if dpg.does_item_exist("hero_drawlist"):
            self._draw_hero_frame("hero_drawlist", self._hero_title, self._hero_subtitle)
        def schedule():
            time.sleep(0.033)
            if self._hero_active:
                self._animate_hero()
        threading.Thread(target=schedule, daemon=True).start()

    def _draw_hero_frame(self, drawlist_tag, title, subtitle):
        if not dpg.does_item_exist(drawlist_tag):
            return
        w = dpg.get_item_width(drawlist_tag)
        h = dpg.get_item_height(drawlist_tag)
        if w <= 0 or h <= 0:
            return
        dpg.delete_item(drawlist_tag, children_only=True)
        elapsed = time.time() - self._hero_time

        # Background
        if self._hero_has_image and self._hero_texture:
            dpg.draw_image(self._hero_texture, [0, 0], [w, h])
            dpg.draw_rectangle([0, 0], [w, h], fill=(12, 14, 20, 140))
        else:
            dpg.draw_rectangle([0, 0], [w, h], fill=(*BG_BASE, 255))

        # Glow orbs
        for orb in self._glow_orbs:
            alpha = orb["base_alpha"] + 20 * math.sin(elapsed * 1.2 + orb["phase"])
            cx = int(orb["cx"] * w)
            cy = int(orb["cy"] * h)
            dpg.draw_circle([cx, cy], orb["r"],
                            fill=(*ACCENT, int(max(0, alpha))))

        # Particles
        for p in self._particles:
            p["y"] -= p["speed"]
            p["x"] += p["drift"]
            if p["y"] < -0.05:
                p["y"] = 1.05
                p["x"] = random.uniform(0.05, 0.95)
            if p["x"] < 0.0 or p["x"] > 1.0:
                p["drift"] = -p["drift"]
            px = int(p["x"] * w)
            py = int(p["y"] * h)
            dpg.draw_circle([px, py], p["size"],
                            fill=(*ACCENT, int(min(p["alpha"] + 30, 80))))

        # Bottom accent line
        line_steps = 60
        for i in range(line_steps):
            t = i / line_steps
            r = int(ACCENT[0] + (ACCENT_2[0] - ACCENT[0]) * t)
            g = int(ACCENT[1] + (ACCENT_2[1] - ACCENT[1]) * t)
            b = int(ACCENT[2] + (ACCENT_2[2] - ACCENT[2]) * t)
            x0 = int(i * w / line_steps)
            x1 = int((i + 1) * w / line_steps)
            dpg.draw_rectangle([x0, h - 2], [x1, h], fill=(r, g, b, 180))

        # Text
        dpg.draw_text([28, h // 2 - 36], title, color=TEXT_BRIGHT, size=28)
        dpg.draw_text([28, h // 2 + 4], subtitle, color=TEXT_SECONDARY, size=14)

        # Version badge
        chip_w, chip_h = 70, 26
        chip_x, chip_y = 28, h - 40
        dpg.draw_rectangle([chip_x, chip_y], [chip_x + chip_w, chip_y + chip_h],
                           fill=(*BG_ELEVATED, 220), rounding=13)
        dpg.draw_rectangle([chip_x, chip_y], [chip_x + chip_w, chip_y + chip_h],
                           color=(*ACCENT, 100), rounding=13, thickness=1)
        dpg.draw_text([chip_x + 16, chip_y + 5], f"v{LAUNCHER_VERSION}",
                      color=ACCENT_2, size=12)

    # ------------------------------------------------------------------ status bar
    def _build_status_bar(self):
        dpg.add_spacer(height=2)
        dpg.add_separator()
        dpg.add_spacer(height=4)
        with dpg.group(horizontal=True):
            dpg.add_spacer(width=16)
            dpg.add_text("●", color=SUCCESS, tag="sb_status_icon")
            dpg.add_text("Starting...", tag="sb_status_text", color=TEXT_SECONDARY)
            dpg.add_spacer(width=9999)
            dpg.add_text(f"{APP_NAME} v{LAUNCHER_VERSION} — Made by {MAKER}",
                         color=TEXT_MUTED)
            dpg.add_spacer(width=16)

    # ------------------------------------------------------------------ callbacks
    def _cb_main_action(self, sender, app_data):
        btn_text = dpg.get_item_label("main_action_btn")
        if "INSTALL" in btn_text or "UPDATE" in btn_text:
            self._download_latest()
        elif "LAUNCH" in btn_text:
            self._launch_game()

    def _cb_install_aunlocker(self, sender, app_data):
        self._install_aunlocker()

    def _cb_create_shortcut(self, sender, app_data):
        self._create_shortcut()

    def _cb_open_folder(self, sender, app_data):
        gp = self.config.get_game_path()
        if gp and gp.exists():
            os.startfile(gp)
        else:
            self._show_error("Game not installed!")

    def _cb_change_location(self, sender, app_data):
        self._change_location_pending = True
        dpg.show_item("folder_dialog")

    def _cb_locate_game(self, sender, app_data):
        self._locate_pending = True
        dpg.show_item("folder_dialog")

    def _cb_verify(self, sender, app_data):
        self._verify_files()

    def _cb_settings(self, sender=None, app_data=None):
        self._show_settings()

    def _cb_reinstall(self, sender, app_data):
        self._reinstall_game()

    def _cb_uninstall(self, sender, app_data):
        self._uninstall_game()

    def _cb_show_about(self, sender=None, app_data=None):
        self._show_about()

    def _cb_coming_soon(self, sender, app_data):
        self._safe_delete("discord_modal")
        with dpg.window(label="Discord", modal=True, tag="discord_modal",
                        width=350, height=150, no_resize=True):
            bind_modal("discord_modal")
            dpg.add_text("Discord server coming soon!")
            dpg.add_spacer(height=10)
            dpg.add_button(label="OK", callback=lambda: dpg.delete_item(
                "discord_modal"), width=-1)
            bind_accent(dpg.last_item(), "modal_primary")
        dpg.split_frame()

    def _show_about(self):
        self._safe_delete("about_modal")
        with dpg.window(label="About", modal=True, tag="about_modal",
                        width=460, height=360, no_resize=True):
            bind_modal("about_modal")
            dpg.add_text("About")
            dpg.add_spacer(height=4)
            dpg.add_separator()
            dpg.add_spacer(height=12)
            dpg.add_text(APP_NAME, color=TEXT_BRIGHT)
            dpg.add_spacer(height=2)
            dpg.add_text(f"Version {LAUNCHER_VERSION}", color=TEXT_SECONDARY)
            dpg.add_spacer(height=4)
            dpg.add_text(f"Made by {MAKER}", color=TEXT_MUTED)
            dpg.add_spacer(height=8)
            dpg.add_text("A premium launcher for Among Us\nwith auto-updates and mod support.",
                         color=TEXT_SECONDARY)
            dpg.add_spacer(height=16)
            dpg.add_separator()
            dpg.add_spacer(height=12)
            with dpg.group(horizontal=True):
                if DISCORD_INVITE:
                    dpg.add_button(label="Discord",
                                   callback=lambda: os.system(f"start {DISCORD_INVITE}"),
                                   width=-1, height=36)
                else:
                    dpg.add_button(label="Discord (Coming soon)",
                                   callback=self._cb_coming_soon, width=-1, height=36)
                dpg.add_spacer(width=8)
                dpg.add_button(label="YouTube",
                               callback=lambda: os.system(f"start {YOUTUBE_CHANNEL}"),
                               width=-1, height=36)
                dpg.add_spacer(width=8)
                dpg.add_button(label="Source Code",
                               callback=lambda: os.system(f"start {SOURCE_CODE_URL}"),
                               width=-1, height=36)
            dpg.add_spacer(height=20)
            dpg.add_separator()
            dpg.add_spacer(height=8)
            dpg.add_button(label="OK", callback=lambda: dpg.delete_item(
                "about_modal"), width=-1, height=36)
            bind_accent(dpg.last_item(), "modal_primary")

    def _show_settings(self, sender=None, app_data=None):
        settings = self.config.settings
        self._safe_delete("settings_modal")
        with dpg.window(label="Settings", modal=True, tag="settings_modal",
                        width=520, height=420, no_resize=True):
            bind_modal("settings_modal")
            dpg.add_text("Settings")
            dpg.add_spacer(height=4)
            dpg.add_separator()
            dpg.add_spacer(height=12)
            dpg.add_checkbox(label="Discord Rich Presence",
                             tag="sett_discord_rpc",
                             default_value=settings.get("discord_rpc", True))
            dpg.add_text("  Show your activity on Discord", color=TEXT_MUTED)
            dpg.add_spacer(height=12)
            dpg.add_checkbox(label="Auto-update game",
                             tag="sett_auto_update",
                             default_value=settings.get("auto_update", True))
            dpg.add_text("  Download game updates automatically", color=TEXT_MUTED)
            dpg.add_spacer(height=12)
            dpg.add_checkbox(label="Verify file integrity",
                             tag="sett_check_integrity",
                             default_value=settings.get("check_integrity", True))
            dpg.add_text("  Check checksums after download", color=TEXT_MUTED)
            dpg.add_spacer(height=20)
            dpg.add_separator()
            dpg.add_spacer(height=12)
            def save_settings(sender, app_data):
                settings["discord_rpc"] = dpg.get_value("sett_discord_rpc")
                settings["auto_update"] = dpg.get_value("sett_auto_update")
                settings["check_integrity"] = dpg.get_value("sett_check_integrity")
                self.config.save_settings()
                if settings.get("discord_rpc") and not self.discord.connected:
                    self.discord.connect()
                elif not settings.get("discord_rpc") and self.discord.connected:
                    self.discord.disconnect()
                dpg.delete_item("settings_modal")
            dpg.add_button(label="Save", callback=save_settings, width=-1, height=40)
            bind_accent(dpg.last_item(), "btn_success")

    # ------------------------------------------------------------------ actions
    def _download_latest(self):
        def go():
            try:
                self._busy_on()
                self._set_status("Preparing download...", INFO)
                latest = self.latest_version
                if latest == "Checking...":
                    latest = self.network.fetch_text(VERSION_URL)
                    if not latest:
                        self._set_status("Failed to fetch version info", DANGER)
                        return
                gp = self.config.get_game_path()
                if not gp:
                    gp = self._pending_install_path
                    if not gp:
                        self._busy_off()
                        self._install_folder_pending = True
                        self._set_status("Select a folder to install into", INFO)
                        dpg.show_item("folder_dialog")
                        return
                url = f"https://github.com/{GITHUB_REPO}/releases/download/{latest}/app.zip"
                zf = Path("game.zip")
                self._set_status(f"Downloading v{latest}...", INFO)
                def prog(cur, total, spd):
                    pct = cur / total * 100 if total else 0
                    self._update_progress(pct)
                    self._set_status(f"Downloading: {pct:.1f}% — {FileManager.format_size(spd)}/s")
                if not self.network.download_file(url, zf, prog):
                    self._set_status("Download failed!", DANGER)
                    return
                self._set_status("Extracting...", INFO)
                gp.mkdir(parents=True, exist_ok=True)
                def xp(cur, total):
                    pct = cur / total * 100 if total else 0
                    self._update_progress(pct)
                    self._set_status(f"Extracting: {pct:.0f}%")
                if not FileManager.extract_zip(zf, gp, xp):
                    self._set_status("Extraction failed!", DANGER)
                    return
                FileManager.safe_delete(zf)
                self.config.set_version(latest)
                self.config.set_game_path(gp)
                self._pending_install_path = None
                self.current_version = latest
                self._update_version_display()
                self._update_progress(100)
                self._set_status("Installation complete!", SUCCESS)
            except Exception as e:
                self._set_status(f"Error: {e}", DANGER)
            finally:
                self._busy_off()
                self._update_main_btn()
        threading.Thread(target=go, daemon=True).start()

    def _install_aunlocker(self):
        ver = self.config.get_version()
        gp = self.config.get_game_path()
        if not ver or not gp:
            self._show_error("Game not installed!")
            return
        def go():
            try:
                self._busy_on()
                self._set_status("Checking AUnlocker...", INFO)
                data = self.network.fetch_text(AUNLOCKER_JSON_URL)
                if not data:
                    self._show_error("Failed to fetch data")
                    return
                versions = json.loads(data).get("versions", [])
                for entry in versions:
                    if entry["version"] == ver:
                        zp = Path("AUnlocker.zip")
                        self._set_status("Downloading AUnlocker...", INFO)
                        if self.network.download_file(entry["link"], zp):
                            FileManager.extract_zip(zp, gp)
                            FileManager.safe_delete(zp)
                            self._show_info("AUnlocker installed!")
                            self._set_status("Ready")
                            return
                self._show_warning("No compatible AUnlocker version found")
            except Exception as e:
                self._set_status("Ready")
            finally:
                self._busy_off()
        threading.Thread(target=go, daemon=True).start()

    def _launch_game(self):
        gp = self.config.get_game_path()
        if not gp:
            self._show_error("Game not installed!")
            return
        exe = gp / "Among Us.exe"
        if not exe.exists():
            self._show_error("Among Us.exe not found!")
            return
        try:
            subprocess.Popen([str(exe)], cwd=str(gp))
            self._set_status("Game launched!", SUCCESS)
        except PermissionError:
            self._show_error("Permission denied. Try running as administrator.")
        except OSError as e:
            self._show_error(f"Failed to launch: {e}")

    def _create_shortcut(self):
        gp = self.config.get_game_path()
        if not gp:
            self._show_error("Game not installed!")
            return
        try:
            import win32com.client
        except ImportError:
            self._show_error("pywin32 not installed")
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
            self._show_info("Shortcut created on Desktop!")
        except Exception as e:
            self._show_error(f"Failed: {e}")

    def _change_location(self, new_path):
        self._set_status("Verifying game files...", INFO)
        result = FileManager.verify_game_folder(new_path)
        if not result["exe_found"]:
            self.config.set_game_path(new_path)
            self.config.set_version("Not Installed")
            self.current_version = "Not Installed"
            self._update_version_display()
            self._update_main_btn()
            self._set_status(f"Location set to {new_path}", SUCCESS)
            self._show_info(f"Location: {new_path}\nClick INSTALL GAME to download.")
            return
        if result["missing"]:
            self._set_status("Some files missing", WARNING)
            msg = (f"Some game files are missing:\n{', '.join(result['missing'])}\n\n"
                   f"Found {result['file_count']} files ({FileManager.format_size(result['total_size'])}).\n"
                   "Continue anyway?")
            if not self._ask_yes_no(msg):
                self._set_status("Ready")
                return
        self._set_status(f"Verified — {result['file_count']} files, {FileManager.format_size(result['total_size'])}", SUCCESS)
        old = self.config.get_game_path()
        if old and old.exists() and old != new_path:
            if self._ask_yes_no("Move existing game files to new location?"):
                self._set_status("Moving files...", INFO)
                try:
                    shutil.move(str(old), str(new_path))
                    self._set_status("Files moved!", SUCCESS)
                except (PermissionError, OSError) as e:
                    self._set_status("Move failed", DANGER)
                    self._show_error(f"Failed to move files: {e}")
                    return
        self.config.set_game_path(new_path)
        self._set_status("Location changed!", SUCCESS)
        self._show_info(f"Location: {new_path}")

    def _verify_files(self):
        if dpg.does_item_exist("kebab_modal"):
            self._safe_delete("kebab_modal")
        gp = self.config.get_game_path()
        if not gp:
            self._show_error("Game not installed!")
            return
        self._set_status("Verifying...", INFO)
        result = FileManager.verify_game_folder(gp)
        if result["valid"]:
            self._show_info(f"All files verified.\n{result['file_count']} files, {FileManager.format_size(result['total_size'])}")
        elif result["exe_found"]:
            self._show_warning(f"Some files missing:\n{', '.join(result['missing'])}")
        else:
            self._show_error("Among Us.exe not found!")
        self._set_status("Ready")

    def _reinstall_game(self):
        if self._ask_yes_no("Delete and reinstall the game?"):
            gp = self.config.get_game_path()
            if gp:
                self._pending_install_path = gp
            if gp and gp.exists():
                FileManager.safe_delete(gp)
            self.current_version = "Not Installed"
            self._update_version_display()
            self._download_latest()

    def _uninstall_game(self):
        if self._ask_yes_no("Remove all game files and launcher data?"):
            gp = self.config.get_game_path()
            if gp and gp.exists():
                if FileManager.safe_delete(gp):
                    self._show_info("Game files removed")
                else:
                    self._show_error("Failed to remove game files")
            if FileManager.safe_delete(self.config.appdata_dir):
                self._show_info("Launcher data removed")
            self.current_version = "Not Installed"
            self._update_version_display()
            self._update_main_btn()

    def _select_folder(self):
        dpg.show_item("folder_dialog")

    def _folder_selected(self, sender, app_data):
        if app_data and app_data.get("file_path_name"):
            path = Path(app_data["file_path_name"])
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
                    self._set_status("Among Us.exe not found in this folder", DANGER)
                    self._show_error("Among Us.exe not found.\nSelect a valid Among Us installation.")
                    return
                self.config.set_game_path(path)
                ver = self.latest_version if self.latest_version != "Checking..." else "Unknown"
                self.config.set_version(ver)
                self.current_version = ver
                self._update_version_display()
                self._update_main_btn()
                self._set_status(f"Game located at {path}", SUCCESS)
                return
            self._set_status(f"Selected: {path}", SUCCESS)
            return path
        if self._install_folder_pending:
            self._install_folder_pending = False
            self._set_status("Installation cancelled", TEXT_MUTED)
        elif self._change_location_pending:
            self._change_location_pending = False
        elif self._locate_pending:
            self._locate_pending = False
            self._set_status("Location cancelled", TEXT_MUTED)
        return None

    def _safe_delete(self, tag):
        if dpg.does_item_exist(tag):
            dpg.delete_item(tag)

    # ------------------------------------------------------------------ helpers
    def _set_status(self, text, color=None):
        self.status_text = text
        dpg.set_value("game_status_text", text)
        if color:
            dpg.configure_item("game_status_icon", color=color)
        dpg.set_value("sb_status_text", text)
        if color:
            dpg.configure_item("sb_status_icon", color=color)

    def _update_progress(self, pct):
        self.progress = pct
        dpg.set_value("progress_bar", pct / 100.0)
        dpg.configure_item("progress_bar", overlay=f"{pct:.0f}%")

    def _update_version_display(self):
        dpg.set_value("ver_installed", self.current_version)
        dpg.set_value("ver_latest", self.latest_version)

    def _update_main_btn(self):
        cur = self.current_version
        lat = self.latest_version
        gp = self.config.get_game_path()
        if cur == "Not Installed" or not gp or not (gp / "Among Us.exe").exists():
            dpg.configure_item("main_action_btn", label="INSTALL GAME")
            bind_accent("main_action_btn", "btn_success")
            dpg.show_item("locate_game_btn")
        elif cur != lat and lat != "Checking...":
            dpg.configure_item("main_action_btn", label="UPDATE AVAILABLE")
            bind_accent("main_action_btn", "btn_info")
            dpg.hide_item("locate_game_btn")
        else:
            dpg.configure_item("main_action_btn", label="LAUNCH GAME")
            bind_accent("main_action_btn", "btn_success")
            dpg.hide_item("locate_game_btn")

    def _busy_on(self):
        self._busy = True
        dpg.configure_item("main_action_btn", enabled=False)
        if dpg.does_item_exist("aunlocker_btn"):
            dpg.configure_item("aunlocker_btn", enabled=False)

    def _busy_off(self):
        self._busy = False
        dpg.configure_item("main_action_btn", enabled=True)
        if dpg.does_item_exist("aunlocker_btn"):
            dpg.configure_item("aunlocker_btn", enabled=True)

    # ------------------------------------------------------------------ modals
    def _show_modal_header(self, title, accent_color=None):
        color = accent_color or TEXT_PRIMARY
        dpg.add_text(title, color=color)
        dpg.add_spacer(height=4)
        dpg.add_separator()
        dpg.add_spacer(height=12)

    def _show_info(self, msg):
        self._safe_delete("info_modal")
        with dpg.window(label="Info", modal=True, tag="info_modal",
                        width=420, height=220, no_resize=True):
            bind_modal("info_modal")
            self._show_modal_header("Info", INFO)
            dpg.add_text(msg, wrap=370)
            dpg.add_spacer(height=16)
            dpg.add_separator()
            dpg.add_spacer(height=8)
            dpg.add_button(label="OK", callback=lambda: dpg.delete_item(
                "info_modal"), width=-1, height=38)
            bind_accent(dpg.last_item(), "modal_primary")

    def _show_error(self, msg):
        self._safe_delete("error_modal")
        with dpg.window(label="Error", modal=True, tag="error_modal",
                        width=420, height=220, no_resize=True):
            bind_modal("error_modal")
            self._show_modal_header("Error", DANGER)
            dpg.add_text(msg, wrap=370, color=DANGER)
            dpg.add_spacer(height=16)
            dpg.add_separator()
            dpg.add_spacer(height=8)
            dpg.add_button(label="OK", callback=lambda: dpg.delete_item(
                "error_modal"), width=-1, height=38)
            bind_accent(dpg.last_item(), "modal_primary")

    def _show_warning(self, msg):
        self._safe_delete("warning_modal")
        with dpg.window(label="Warning", modal=True, tag="warning_modal",
                        width=420, height=220, no_resize=True):
            bind_modal("warning_modal")
            self._show_modal_header("Warning", WARNING)
            dpg.add_text(msg, wrap=370, color=WARNING)
            dpg.add_spacer(height=16)
            dpg.add_separator()
            dpg.add_spacer(height=8)
            dpg.add_button(label="OK", callback=lambda: dpg.delete_item(
                "warning_modal"), width=-1, height=38)
            bind_accent(dpg.last_item(), "modal_primary")

    def _ask_yes_no(self, msg):
        result = [False]
        def on_yes(sender, app_data):
            result[0] = True
            dpg.delete_item("yesno_modal")
        def on_no(sender, app_data):
            dpg.delete_item("yesno_modal")
        self._safe_delete("yesno_modal")
        with dpg.window(label="Confirm", modal=True, tag="yesno_modal",
                        width=440, height=220, no_resize=True):
            bind_modal("yesno_modal")
            self._show_modal_header("Confirm", WARNING)
            dpg.add_text(msg, wrap=390)
            dpg.add_spacer(height=16)
            dpg.add_separator()
            dpg.add_spacer(height=8)
            with dpg.group(horizontal=True):
                dpg.add_spacer(width=9999)
                dpg.add_button(label="No", callback=on_no, width=100, height=38)
                bind_accent(dpg.last_item(), "modal_secondary")
                dpg.add_spacer(width=8)
                dpg.add_button(label="Yes", callback=on_yes, width=100, height=38)
                bind_accent(dpg.last_item(), "modal_danger")
                dpg.add_spacer(width=9999)
        dpg.split_frame()
        return result[0]

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
        threading.Thread(target=go, daemon=True).start()

    def run(self):
        dpg.show_viewport()
        dpg.start_dearpygui()
        self._stop_hero_animation()
        self.discord.disconnect()
        dpg.destroy_context()
