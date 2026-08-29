"""
Window — Premium Steam/Epic-style Dear PyGui launcher.
Animated hero, card-based layout, refined modals.
"""
import math
import os
import json
import time
import random
import threading
import subprocess
import shutil
import xml.etree.ElementTree as ET
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
    load_fonts, bind_default_font,
    apply_theme, init_accent_themes, bind_accent,
    init_card_theme, init_modal_theme, bind_card, bind_modal,
    ACCENT, ACCENT_2,
    SUCCESS, SUCCESS_HOVER, INFO, INFO_HOVER, DANGER, DANGER_HOVER,
    WARNING, PURPLE,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_BRIGHT,
    BG_BASE, BG_SURFACE, BG_ELEVATED, BG_HOVER, BG_ACTIVE,
    BORDER_SUBTLE,
    FONT_TITLE, FONT_HEADING, FONT_SUBHEADING, FONT_BODY, FONT_SMALL, FONT_LABEL,
)


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
        self._active_tab = "game"
        self._news_loaded = False

        # Animation state
        self._particles = []
        self._glow_orbs = []
        self._hero_time = 0.0
        self._hero_timer = None
        self._hero_active = False

        self._setup_dpg()
        self._build_ui()
        self._load_initial_data()

    # ------------------------------------------------------------------ setup
    def _setup_dpg(self):
        dpg.create_context()
        load_fonts()
        apply_theme()
        init_accent_themes()
        init_card_theme()
        init_modal_theme()

        dpg.create_viewport(
            title=f"{APP_NAME} v{LAUNCHER_VERSION}",
            width=1280, height=720,
            min_width=960, min_height=580,
            resizable=True,
        )
        dpg.setup_dearpygui()
        bind_default_font()

    def _build_ui(self):
        with dpg.window(tag="main_window", no_scrollbar=True, no_collapse=True,
                        no_title_bar=True):
            self._build_top_bar()
            self._build_content()
            self._build_status_bar()

        dpg.set_primary_window("main_window", True)

        # Folder dialog for game path selection
        with dpg.file_dialog(directory_selector=True, show=False,
                             callback=self._folder_selected,
                             tag="folder_dialog", width=600, height=400,
                             modal=True):
            dpg.add_file_extension(".exe", color=(150, 255, 150, 255))
            dpg.add_file_extension(".*")

    # ------------------------------------------------------------------ top bar
    def _build_top_bar(self):
        with dpg.group(horizontal=True, tag="top_bar"):
            dpg.add_spacer(width=20)
            dpg.add_text(BRAND_SHORT, color=ACCENT)
            dpg.add_spacer(width=6)
            dpg.add_text("|", color=BORDER_SUBTLE)
            dpg.add_spacer(width=6)
            dpg.add_text(APP_NAME, color=TEXT_SECONDARY)
            dpg.add_spacer(width=40)

            self._nav_btn("Game", "game")
            dpg.add_spacer(width=8)
            self._nav_btn("News", "news")

            dpg.add_spacer(width=9999)

            dpg.add_button(label="Settings", callback=self._cb_settings, width=82, height=32)
            dpg.add_spacer(width=6)
            dpg.add_button(label="...", callback=self._show_kebab, width=36, height=32)
            dpg.add_spacer(width=20)

        dpg.add_spacer(height=4)
        dpg.add_separator()
        dpg.add_spacer(height=8)

    def _nav_btn(self, label, tab_id):
        tag = f"nav_{tab_id}"
        dpg.add_button(label=label, tag=tag, callback=self._switch_tab,
                       width=72, height=32)
        if tab_id == self._active_tab:
            bind_accent(tag, "accent")

    def _switch_tab(self, sender, app_data):
        tab_id = sender.replace("nav_", "")
        self._active_tab = tab_id

        for t in ("game", "news"):
            tag = f"nav_{t}"
            if t == tab_id:
                bind_accent(tag, "accent")
            else:
                dpg.bind_item_theme(tag, 0)

        if tab_id == "game":
            dpg.show_item("page_game")
            dpg.hide_item("page_news")
            self._start_hero_animation()
        elif tab_id == "news":
            dpg.hide_item("page_game")
            dpg.show_item("page_news")
            self._start_hero_animation()
            if not self._news_loaded:
                self._news_loaded = True
                self._load_patches()

    # ------------------------------------------------------------------ content
    def _build_content(self):
        dpg.add_spacer(height=8)
        self._build_game_tab()
        self._build_news_tab()

    # ------------------------------------------------------------------ game tab
    def _build_game_tab(self):
        with dpg.group(tag="page_game"):

            self._build_hero("Game Management",
                             "Install, update, and manage your Among Us installation",
                             "game")

            dpg.add_spacer(height=20)

            # Primary action button — full width
            with dpg.group():
                dpg.add_button(label="INSTALL GAME", tag="main_action_btn",
                               callback=self._cb_main_action, width=-1, height=56)
                bind_accent("main_action_btn", "btn_success")

            dpg.add_spacer(height=20)

            # Info cards row
            with dpg.group(horizontal=True):
                dpg.add_spacer(width=4)

                # Version card
                with dpg.child_window(tag="version_card", width=280, height=160,
                                      autosize_x=False, autosize_y=False,
                                      no_scrollbar=True):
                    bind_card("version_card")
                    dpg.add_text("VERSION", color=TEXT_MUTED)
                    dpg.add_spacer(height=12)
                    dpg.add_text("Installed", color=TEXT_SECONDARY)
                    dpg.add_spacer(height=2)
                    dpg.add_text("Not Installed", tag="ver_installed",
                                 color=SUCCESS)
                    dpg.add_spacer(height=16)
                    dpg.add_text("Latest", color=TEXT_SECONDARY)
                    dpg.add_spacer(height=2)
                    dpg.add_text("Checking...", tag="ver_latest",
                                 color=INFO)

                dpg.add_spacer(width=12)

                # Status card
                with dpg.child_window(tag="status_card", width=-1, height=160,
                                      autosize_x=False, autosize_y=False,
                                      no_scrollbar=True):
                    bind_card("status_card")
                    dpg.add_text("STATUS", color=TEXT_MUTED)
                    dpg.add_spacer(height=12)
                    with dpg.group(horizontal=True):
                        dpg.add_text("●", color=SUCCESS, tag="game_status_icon")
                        dpg.add_text("Starting...", tag="game_status_text",
                                     color=TEXT_SECONDARY)
                    dpg.add_spacer(height=12)
                    dpg.add_progress_bar(tag="progress_bar", default_value=0,
                                         width=-1, height=20, overlay="0%")
                    dpg.add_spacer(height=8)
                    dpg.add_text("Ready", tag="game_ready_text", color=TEXT_MUTED)

                dpg.add_spacer(width=4)

            dpg.add_spacer(height=20)

            # Quick actions row
            dpg.add_text("QUICK ACTIONS", color=TEXT_MUTED)
            dpg.add_spacer(height=8)
            with dpg.group(horizontal=True, tag="quick_actions_row"):
                dpg.add_spacer(width=4)
                dpg.add_button(label="Open Folder", callback=self._cb_open_folder,
                               width=160, height=38)
                dpg.add_spacer(width=8)
                dpg.add_button(label="Change Location", callback=self._cb_change_location,
                               width=160, height=38)
                dpg.add_spacer(width=8)
                dpg.add_button(label="Verify Files", callback=self._cb_verify,
                               width=160, height=38)
                dpg.add_spacer(width=8)
                dpg.add_button(label="Create Shortcut", callback=self._cb_create_shortcut,
                               width=160, height=38)
                dpg.add_spacer(width=4)

            dpg.add_spacer(height=20)

            # AUnlocker section
            with dpg.child_window(tag="aunlocker_card", width=-1, height=80,
                                  autosize_x=True, autosize_y=False,
                                  no_scrollbar=True):
                bind_card("aunlocker_card")
                with dpg.group(horizontal=True):
                    with dpg.group():
                        dpg.add_text("AUnlocker", color=TEXT_PRIMARY)
                        dpg.add_spacer(height=2)
                        dpg.add_text("Install the Among Us unlocker for this version",
                                     color=TEXT_MUTED)
                    dpg.add_spacer(width=9999)
                    dpg.add_button(label="Install AUnlocker", callback=self._cb_install_aunlocker,
                                   width=180, height=36)
                    bind_accent(dpg.last_item(), "accent")
                    dpg.add_spacer(width=4)

            dpg.add_spacer(height=28)

    # ------------------------------------------------------------------ hero banner
    def _build_hero(self, title, subtitle, tag):
        drawlist_tag = f"hero_{tag}"
        with dpg.drawlist(width=-1, height=300, tag=drawlist_tag):
            pass

        # Store hero info for animation
        self._hero_title = title
        self._hero_subtitle = subtitle
        self._hero_tag = tag

        # Initialize particles and glow orbs
        self._init_particles()

        def draw_hero_static(sender, app_data):
            self._draw_hero_frame(drawlist_tag, title, subtitle)

        # Draw initial frame
        self._draw_hero_frame(drawlist_tag, title, subtitle)

        # Start animation
        self._start_hero_animation()

    def _init_particles(self):
        random.seed(42)
        self._particles = []
        for _ in range(18):
            self._particles.append({
                "x": random.uniform(0.05, 0.95),
                "y": random.uniform(0.0, 1.0),
                "speed": random.uniform(0.0003, 0.001),
                "size": random.uniform(1.5, 3.5),
                "alpha": random.uniform(15, 40),
                "drift": random.uniform(-0.0002, 0.0002),
            })

        self._glow_orbs = [
            {"cx": 0.75, "cy": 0.35, "r": 70, "base_alpha": 25, "phase": 0.0},
            {"cx": 0.85, "cy": 0.6, "r": 50, "base_alpha": 18, "phase": 1.5},
            {"cx": 0.15, "cy": 0.7, "r": 55, "base_alpha": 15, "phase": 3.0},
        ]

    def _start_hero_animation(self):
        if self._hero_active:
            return
        self._hero_active = True
        self._hero_time = time.time()
        self._animate_hero()

    def _stop_hero_animation(self):
        self._hero_active = False
        if self._hero_timer:
            self._hero_timer = None

    def _animate_hero(self):
        if not self._hero_active:
            return

        drawlist_tag = f"hero_{self._hero_tag}"
        if dpg.does_item_exist(drawlist_tag):
            self._draw_hero_frame(drawlist_tag, self._hero_title, self._hero_subtitle)

        # Schedule next frame (~30fps)
        def schedule():
            time.sleep(0.033)
            if self._hero_active:
                self._animate_hero()
        t = threading.Thread(target=schedule, daemon=True)
        t.start()

    def _draw_hero_frame(self, drawlist_tag, title, subtitle):
        if not dpg.does_item_exist(drawlist_tag):
            return

        w = dpg.get_item_width(drawlist_tag)
        h = dpg.get_item_height(drawlist_tag)
        if w <= 0 or h <= 0:
            return

        dpg.delete_item(drawlist_tag, children_only=True)
        elapsed = time.time() - self._hero_time

        # Background gradient (vertical, subtle)
        steps = 20
        for i in range(steps):
            t = i / steps
            r = int(BG_BASE[0] + (BG_SURFACE[0] - BG_BASE[0]) * t)
            g = int(BG_BASE[1] + (BG_SURFACE[1] - BG_BASE[1]) * t)
            b = int(BG_BASE[2] + (BG_SURFACE[2] - BG_BASE[2]) * t)
            y0 = int(i * h / steps)
            y1 = int((i + 1) * h / steps)
            dpg.draw_rectangle([0, y0], [w, y1], fill=(r, g, b, 255))

        # Animated glow orbs
        for orb in self._glow_orbs:
            alpha = orb["base_alpha"] + 12 * math.sin(elapsed * 1.2 + orb["phase"])
            cx = int(orb["cx"] * w)
            cy = int(orb["cy"] * h)
            dpg.draw_circle([cx, cy], orb["r"],
                            fill=(*ACCENT, int(max(0, alpha))))

        # Animated floating particles
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
                            fill=(*ACCENT, int(p["alpha"])))

        # Bottom accent line (2px gradient)
        line_y = h - 2
        line_steps = 60
        for i in range(line_steps):
            t = i / line_steps
            r = int(ACCENT[0] + (ACCENT_2[0] - ACCENT[0]) * t)
            g = int(ACCENT[1] + (ACCENT_2[1] - ACCENT[1]) * t)
            b = int(ACCENT[2] + (ACCENT_2[2] - ACCENT[2]) * t)
            x0 = int(i * w / line_steps)
            x1 = int((i + 1) * w / line_steps)
            dpg.draw_rectangle([x0, line_y], [x1, line_y + 2], fill=(r, g, b, 180))

        # Title
        dpg.draw_text([28, h // 2 - 36], title, color=TEXT_BRIGHT)
        # Subtitle
        dpg.draw_text([28, h // 2 + 4], subtitle, color=TEXT_SECONDARY)

        # Version badge (rounded pill)
        chip_text = f"v{LAUNCHER_VERSION}"
        chip_w = 70
        chip_h = 26
        chip_x = 28
        chip_y = h - 40
        dpg.draw_rectangle([chip_x, chip_y], [chip_x + chip_w, chip_y + chip_h],
                           fill=(*BG_ELEVATED, 220), rounding=13)
        dpg.draw_rectangle([chip_x, chip_y], [chip_x + chip_w, chip_y + chip_h],
                           color=(*ACCENT, 100), rounding=13, thickness=1)
        dpg.draw_text([chip_x + 16, chip_y + 5], chip_text,
                      color=ACCENT_2)

    # ------------------------------------------------------------------ news tab
    def _build_news_tab(self):
        with dpg.group(tag="page_news", show=False):
            self._build_hero("Game Updates & News",
                             "Stay up to date with the latest patches and updates",
                             "news")
            dpg.add_spacer(height=16)
            with dpg.child_window(tag="patches_container", autosize_x=True,
                                  autosize_y=True):
                dpg.add_text("Loading patches...", color=TEXT_SECONDARY)

    def _load_patches(self):
        def go():
            try:
                xml = self.network.fetch_text(PATCHES_URL)
                if not xml:
                    self._set_status("Failed to load patches", DANGER)
                    return
                patches = ET.fromstring(xml).findall(".//patch")
                if not patches:
                    return
                dpg.delete_item("patches_container", children_only=True)
                colors = [INFO, ACCENT, SUCCESS, WARNING]
                for i, p in enumerate(patches):
                    t = p.find("Title")
                    tx = p.find("Text")
                    lk = p.find("Link")
                    if t is not None and tx is not None:
                        self._patch_card(
                            t.text or "?", tx.text or "",
                            lk.text if lk is not None and lk.text else None,
                            colors[i % len(colors)],
                        )
            except Exception as e:
                self._set_status(f"Patches error: {e}", DANGER)
        threading.Thread(target=go, daemon=True).start()

    def _patch_card(self, title, desc, link, accent):
        with dpg.group(parent="patches_container"):
            with dpg.child_window(autosize_x=True, height=120, no_scrollbar=True):
                # Left accent bar
                with dpg.group(horizontal=True):
                    dpg.add_spacer(width=4)
                    with dpg.group():
                        with dpg.group(horizontal=True):
                            dpg.add_text(f"  {title}", color=accent)
                            if link:
                                dpg.add_spacer(width=8)
                                dpg.add_button(label="Read More",
                                               callback=lambda: os.system(f"start {link}"),
                                               width=90, height=26)
                                bind_accent(dpg.last_item(), "ghost_accent")
                        dpg.add_spacer(height=4)
                        dpg.add_text(desc, color=TEXT_SECONDARY, wrap=650)

    # ------------------------------------------------------------------ callbacks
    def _cb_main_action(self, sender, app_data):
        btn_text = dpg.get_item_label("main_action_btn")
        if "INSTALL" in btn_text or "UPDATE" in btn_text:
            self._download_latest()
        elif "LAUNCH" in btn_text:
            self._launch_game()

    def _cb_check_updates(self, sender, app_data):
        self._check_updates()

    def _cb_install_specific(self, sender, app_data):
        self._install_specific()

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
        self._change_location()

    def _cb_verify(self, sender, app_data):
        self._verify_files()

    def _cb_settings(self, sender, app_data):
        self._show_settings()

    def _cb_reinstall(self, sender, app_data):
        self._reinstall_game()

    def _cb_uninstall(self, sender, app_data):
        self._uninstall_game()

    def _cb_coming_soon(self, sender, app_data):
        self._safe_delete("discord_modal")
        with dpg.window(label="Discord", modal=True, tag="discord_modal",
                        width=350, height=150, no_resize=True):
            bind_modal("discord_modal")
            dpg.add_text("Discord server coming soon!")
            dpg.add_spacer(height=10)
            with dpg.group(horizontal=True):
                dpg.add_spacer(width=9999)
                dpg.add_button(label="OK", callback=lambda: dpg.delete_item(
                    "discord_modal"), width=80, height=36)
                bind_accent(dpg.last_item(), "modal_primary")
                dpg.add_spacer(width=9999)
        dpg.split_frame()

    def _show_kebab(self, sender, app_data):
        self._safe_delete("kebab_modal")
        with dpg.window(label="Tools", modal=True, tag="kebab_modal",
                        width=340, height=420, no_resize=True):
            bind_modal("kebab_modal")
            # Header
            dpg.add_text("Tools")
            dpg.add_spacer(height=4)
            dpg.add_separator()
            dpg.add_spacer(height=8)

            # Game tools section
            dpg.add_text("GAME", color=TEXT_MUTED)
            dpg.add_spacer(height=6)
            dpg.add_button(label="Verify Game Files", callback=self._cb_verify,
                           width=-1, height=36)
            dpg.add_spacer(height=4)
            dpg.add_button(label="Reinstall Game", callback=self._cb_reinstall,
                           width=-1, height=36)
            dpg.add_spacer(height=4)
            dpg.add_button(label="Uninstall", callback=self._cb_uninstall, width=-1, height=36)
            bind_accent(dpg.last_item(), "btn_danger")
            dpg.add_spacer(height=12)

            # Shortcuts section
            dpg.add_text("SHORTCUTS", color=TEXT_MUTED)
            dpg.add_spacer(height=6)
            dpg.add_button(label="Create Desktop Shortcut", callback=self._cb_create_shortcut,
                           width=-1, height=36)
            dpg.add_spacer(height=4)
            dpg.add_button(label="Open Game Folder", callback=self._cb_open_folder,
                           width=-1, height=36)
            dpg.add_spacer(height=4)
            dpg.add_button(label="Change Install Location", callback=self._cb_change_location,
                           width=-1, height=36)
            dpg.add_spacer(height=12)

            # Misc section
            dpg.add_text("OTHER", color=TEXT_MUTED)
            dpg.add_spacer(height=6)
            dpg.add_button(label="View Logs", callback=self._view_logs, width=-1, height=36)
            dpg.add_spacer(height=4)
            dpg.add_button(label="About", callback=self._show_about, width=-1, height=36)
            dpg.add_spacer(height=16)

            dpg.add_separator()
            dpg.add_spacer(height=8)
            dpg.add_button(label="Close", callback=lambda: dpg.delete_item(
                "kebab_modal"), width=-1, height=36)
            bind_accent(dpg.last_item(), "btn_secondary")

    def _show_about(self, sender, app_data):
        if dpg.does_item_exist("kebab_modal"):
            self._safe_delete("kebab_modal")
        with dpg.window(label="About", modal=True, tag="about_modal",
                        width=460, height=360, no_resize=True):
            bind_modal("about_modal")
            # Header
            dpg.add_text("About")
            dpg.add_spacer(height=4)
            dpg.add_separator()
            dpg.add_spacer(height=12)

            dpg.add_text(f"{APP_NAME}", color=TEXT_BRIGHT)
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

            # Links
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

    def _view_logs(self, sender, app_data):
        if dpg.does_item_exist("kebab_modal"):
            self._safe_delete("kebab_modal")
        lf = Path("launcher.log")
        if lf.exists():
            os.startfile(lf)

    def _show_settings(self, sender=None, app_data=None):
        settings = self.config.settings
        self._safe_delete("settings_modal")

        with dpg.window(label="Settings", modal=True, tag="settings_modal",
                        width=520, height=420, no_resize=True):
            bind_modal("settings_modal")

            # Header
            dpg.add_text("Settings")
            dpg.add_spacer(height=4)
            dpg.add_separator()
            dpg.add_spacer(height=12)

            # Discord RPC
            with dpg.group():
                dpg.add_checkbox(label="Discord Rich Presence",
                                 tag="sett_discord_rpc",
                                 default_value=settings.get("discord_rpc", True))
                dpg.add_text("  Show your activity on Discord", color=TEXT_MUTED,
                             )
                dpg.add_spacer(height=12)

            # Auto update
            with dpg.group():
                dpg.add_checkbox(label="Auto-update game",
                                 tag="sett_auto_update",
                                 default_value=settings.get("auto_update", True))
                dpg.add_text("  Download game updates automatically", color=TEXT_MUTED,
                             )
                dpg.add_spacer(height=12)

            # File integrity
            with dpg.group():
                dpg.add_checkbox(label="Verify file integrity",
                                 tag="sett_check_integrity",
                                 default_value=settings.get("check_integrity", True))
                dpg.add_text("  Check checksums after download", color=TEXT_MUTED,
                             )

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
                    gp = self._select_folder()
                    if not gp:
                        self._set_status("Installation cancelled", TEXT_MUTED)
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

    def _check_updates(self):
        def go():
            try:
                self._set_status("Checking for updates...", INFO)
                lat = self.network.fetch_text(VERSION_URL)
                if lat:
                    self.latest_version = lat
                    self._update_version_display()
                    if self.current_version == lat:
                        self._show_info("Up to date!")
                    else:
                        self._show_info(f"New version available: {lat}")
                    self._update_main_btn()
                else:
                    self._show_error("Failed to check for updates")
                self._set_status("Ready")
            except Exception as e:
                self._set_status("Ready")
        threading.Thread(target=go, daemon=True).start()

    def _install_specific(self):
        def go():
            versions = self.network.get_releases()
            if not versions:
                self._show_error("No versions available")
                return

            self._safe_delete("specific_modal")
            with dpg.window(label="Install Specific Version", modal=True,
                            tag="specific_modal", width=440, height=500, no_resize=True):
                bind_modal("specific_modal")
                # Header
                dpg.add_text("Available Versions")
                dpg.add_spacer(height=4)
                dpg.add_separator()
                dpg.add_spacer(height=8)
                for i, v in enumerate(versions):
                    dpg.add_button(label=v.version, width=-1, height=32,
                                   callback=lambda s, a, u=v: self._do_install_version(u))
                dpg.add_spacer(height=8)
                dpg.add_separator()
                dpg.add_spacer(height=8)
                dpg.add_button(label="Cancel",
                               callback=lambda: dpg.delete_item("specific_modal"),
                               width=-1, height=36)
                bind_accent(dpg.last_item(), "btn_secondary")
        threading.Thread(target=go, daemon=True).start()

    def _do_install_version(self, ver: GameVersion):
        def go():
            try:
                self._busy_on()
                gp = self.config.get_game_path() or self._select_folder()
                if not gp:
                    return
                self._set_status(f"Installing v{ver.version}...", INFO)
                zf = Path("game.zip")
                if self.network.download_file(ver.url, zf):
                    gp.mkdir(parents=True, exist_ok=True)
                    FileManager.extract_zip(zf, gp)
                    FileManager.safe_delete(zf)
                    self.config.set_version(ver.version)
                    self.config.set_game_path(gp)
                    self.current_version = ver.version
                    self._update_version_display()
                    self._show_info(f"v{ver.version} installed!")
                else:
                    self._show_error("Download failed")
            except Exception as e:
                self._set_status(f"Error: {e}", DANGER)
            finally:
                self._busy_off()
                self._update_main_btn()
        if dpg.does_item_exist("specific_modal"):
            dpg.delete_item("specific_modal")
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

    def _change_location(self):
        new_path = self._select_folder()
        if not new_path:
            return
        self._set_status("Verifying game files...", INFO)
        result = FileManager.verify_game_folder(new_path)
        if not result["exe_found"]:
            self._set_status("Invalid folder!", DANGER)
            self._show_error("Among Us.exe not found.\nSelect a valid Among Us installation.")
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
        if dpg.does_item_exist("kebab_modal"):
            self._safe_delete("kebab_modal")
        if self._ask_yes_no("Delete and reinstall the game?"):
            gp = self.config.get_game_path()
            if gp and gp.exists():
                FileManager.safe_delete(gp)
            self.current_version = "Not Installed"
            self._update_version_display()
            self._download_latest()

    def _uninstall_game(self):
        if dpg.does_item_exist("kebab_modal"):
            self._safe_delete("kebab_modal")
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
            self._set_status(f"Selected: {path}", SUCCESS)
            return path
        return None

    def _safe_delete(self, tag):
        if dpg.does_item_exist(tag):
            dpg.delete_item(tag)

    # ------------------------------------------------------------------ helpers
    def _set_status(self, text, color=None):
        self.status_text = text
        # Update game tab status (unique tags)
        dpg.set_value("game_status_text", text)
        if color:
            dpg.configure_item("game_status_icon", color=color)
        # Also update status bar
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
        elif cur != lat and lat != "Checking...":
            dpg.configure_item("main_action_btn", label="UPDATE AVAILABLE")
            bind_accent("main_action_btn", "btn_info")
        else:
            dpg.configure_item("main_action_btn", label="LAUNCH GAME")
            bind_accent("main_action_btn", "btn_success")

    def _busy_on(self):
        self._busy = True
        dpg.configure_item("main_action_btn", enabled=False)

    def _busy_off(self):
        self._busy = False
        dpg.configure_item("main_action_btn", enabled=True)

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
            dpg.add_text(msg, wrap=370, color=TEXT_PRIMARY)
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

    # ------------------------------------------------------------------ status bar
    def _build_status_bar(self):
        dpg.add_spacer(height=4)
        dpg.add_separator()
        dpg.add_spacer(height=6)
        with dpg.group(horizontal=True, tag="status_bar"):
            dpg.add_spacer(width=16)
            dpg.add_text("●", color=SUCCESS, tag="sb_status_icon")
            dpg.add_text("Starting...", tag="sb_status_text", color=TEXT_SECONDARY)
            dpg.add_spacer(width=9999)
            dpg.add_text(f"{APP_NAME} v{LAUNCHER_VERSION} — Made by {MAKER}",
                         color=TEXT_MUTED)
            dpg.add_spacer(width=16)

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
