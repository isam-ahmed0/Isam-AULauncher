"""
Window — main Dear PyGui window with sidebar, game tab, news tab.
"""
import os
import json
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
from ui.theme import (
    apply_theme, init_accent_themes, bind_accent,
    ACCENT, ACCENT_2, GREEN, GREEN_HOVER, BLUE, BLUE_HOVER,
    RED, RED_HOVER, PURPLE, ORANGE, CYAN,
    TEXT, TEXT_DIM, TEXT_BRIGHT, TEXT_MUTED,
    BG_DARK, BG_MEDIUM, BG_LIGHT, BG_HOVER,
)


class LauncherApp:
    def __init__(self):
        self.config = Config()
        self.network = NetworkManager()
        self.discord = DiscordRPC()

        # State
        self.current_version = "Not Installed"
        self.latest_version = "Checking..."
        self.status_text = "Starting..."
        self.progress = 0.0
        self._busy = False
        self._active_tab = "game"
        self._news_loaded = False

        self._setup_dpg()
        self._build_ui()
        self._load_initial_data()

    def _setup_dpg(self):
        dpg.create_context()
        apply_theme()
        init_accent_themes()

        dpg.create_viewport(
            title=f"{APP_NAME} v{LAUNCHER_VERSION}",
            width=1150, height=740,
            min_width=900, min_height=560,
            resizable=True,
        )
        dpg.setup_dearpygui()

    def _build_ui(self):
        with dpg.window(tag="main_window", no_scrollbar=True):
            with dpg.group(horizontal=True):

                # === SIDEBAR ===
                self._build_sidebar()

                # Vertical separator
                dpg.add_spacer(width=8)
                dpg.add_separator()
                dpg.add_spacer(width=8)

                # === CONTENT ===
                self._build_content()

        dpg.set_primary_window("main_window", True)

    # ------------------------------------------------------------------ sidebar
    def _build_sidebar(self):
        with dpg.group(width=220):
            # Brand
            dpg.add_text(f"  {BRAND_SHORT}")
            dpg.add_text(f"  {APP_NAME}")
            dpg.add_text(f"  v{LAUNCHER_VERSION}")
            dpg.add_spacer(height=4)
            dpg.add_separator()
            dpg.add_spacer(height=6)

            # Nav
            dpg.add_text("  NAVIGATION")
            dpg.add_spacer(height=4)

            with dpg.group(horizontal=True):
                self._nav_btn("  Game", "game")
                self._nav_btn("  News", "news")

            dpg.add_spacer(height=8)
            dpg.add_separator()
            dpg.add_spacer(height=6)

            # Tools
            dpg.add_text("  TOOLS")
            dpg.add_spacer(height=4)
            dpg.add_button(label="Install AUnlocker", callback=lambda s, a, u: self._cb_install_aunlocker(s, a, u), width=-1)
            dpg.add_button(label="Create Shortcut", callback=lambda s, a, u: self._cb_create_shortcut(s, a, u), width=-1)
            dpg.add_button(label="Open Folder", callback=lambda s, a, u: self._cb_open_folder(s, a, u), width=-1)
            dpg.add_button(label="Change Location", callback=lambda s, a, u: self._cb_change_location(s, a, u), width=-1)

            dpg.add_spacer(height=8)
            dpg.add_separator()
            dpg.add_spacer(height=6)

            # Settings
            dpg.add_text("  SETTINGS")
            dpg.add_spacer(height=4)
            dpg.add_button(label="Preferences", callback=lambda s, a, u: self._cb_settings(s, a, u), width=-1)
            dpg.add_button(label="Reinstall Game", callback=lambda s, a, u: self._cb_reinstall(s, a, u), width=-1)
            dpg.add_button(label="Uninstall", callback=lambda s, a, u: self._cb_uninstall(s, a, u), width=-1)

            # Footer (push to bottom via spacer)
            dpg.add_spacer(width=1, height=9999)
            dpg.add_separator()
            dpg.add_spacer(height=4)

            if DISCORD_INVITE:
                dpg.add_button(label="Discord", callback=lambda: os.system(f"start {DISCORD_INVITE}"), width=-1)
            else:
                dpg.add_button(label="Discord (Coming soon)", callback=lambda s, a, u: self._cb_coming_soon(s, a, u), width=-1)

            dpg.add_button(label="YouTube", callback=lambda: os.system(f"start {YOUTUBE_CHANNEL}"), width=-1)
            dpg.add_button(label="Source Code", callback=lambda: os.system(f"start {SOURCE_CODE_URL}"), width=-1)
            dpg.add_spacer(height=4)
            dpg.add_text(f"  Made by {MAKER}")

    def _nav_btn(self, label, tab_id):
        tag = f"nav_{tab_id}"
        dpg.add_button(label=label, tag=tag, callback=lambda s, a, u: self._switch_tab(s, a), width=-1, height=30)
        if tab_id == self._active_tab:
            bind_accent(tag, "accent")

    def _switch_tab(self, sender, app_data):
        tab_id = sender.replace("nav_", "")
        self._active_tab = tab_id

        # Reset nav buttons
        for t in ("game", "news"):
            tag = f"nav_{t}"
            if t == tab_id:
                bind_accent(tag, "accent")
            else:
                dpg.bind_item_theme(tag, 0)  # reset to default

        # Toggle pages
        if tab_id == "game":
            dpg.show_item("page_game")
            dpg.hide_item("page_news")
        elif tab_id == "news":
            dpg.hide_item("page_game")
            dpg.show_item("page_news")
            if not self._news_loaded:
                self._news_loaded = True
                self._load_patches()

    # ------------------------------------------------------------------ content
    def _build_content(self):
        with dpg.group():
            # === GAME TAB ===
            self._build_game_tab()
            # === NEWS TAB ===
            self._build_news_tab()

    def _build_game_tab(self):
        with dpg.group(tag="page_game"):
            # Hero
            self._build_hero("Game Management",
                           "Install, update, and manage your Among Us installation")

            dpg.add_spacer(height=12)

            # Version cards
            with dpg.group(horizontal=True):
                self._ver_card("INSTALLED VERSION", "ver_installed", GREEN)
                dpg.add_spacer(width=10)
                self._ver_card("LATEST VERSION", "ver_latest", BLUE)

            dpg.add_spacer(height=16)

            # Action buttons
            with dpg.group(horizontal=True):
                dpg.add_button(label="INSTALL GAME", tag="main_action_btn",
                             callback=lambda s, a, u: self._cb_main_action(s, a, u), width=180, height=45)
                bind_accent("main_action_btn", "green")

                dpg.add_button(label="Check Updates", callback=lambda s, a, u: self._cb_check_updates(s, a, u), width=130, height=45)
                dpg.add_button(label="Install Specific", callback=lambda s, a, u: self._cb_install_specific(s, a, u), width=130, height=45)

            dpg.add_spacer(height=16)

            # Progress bar
            dpg.add_progress_bar(tag="progress_bar", default_value=0, width=-1, height=20, overlay="0%")

            dpg.add_spacer(height=8)

            # Status
            with dpg.group(horizontal=True):
                dpg.add_text("● ", color=GREEN, tag="status_icon")
                dpg.add_text("Starting...", tag="status_text")

            # Kebab menu (bottom right)
            dpg.add_spacer(height=9999)
            with dpg.group(horizontal=True):
                dpg.add_spacer(width=9999)
                dpg.add_button(label="···", callback=lambda s, a, u: self._show_kebab(s, a, u), width=40)

    def _build_hero(self, title, subtitle):
        with dpg.drawlist(width=-1, height=100, tag="hero_drawlist"):
            pass

        def draw_hero(sender, app_data):
            w = dpg.get_item_width("hero_drawlist")
            h = dpg.get_item_height("hero_drawlist")
            if w <= 0 or h <= 0:
                return
            dpg.delete_item("hero_drawlist", children_only=True)
            # Gradient background (multi-stop)
            steps = 20
            for i in range(steps):
                t = i / steps
                r = int(12 + (18 - 12) * t)
                g = int(14 + (21 - 14) * t)
                b = int(20 + (30 - 20) * t)
                x0 = int(i * w / steps)
                x1 = int((i + 1) * w / steps)
                dpg.draw_rectangle([x0, 0], [x1, h], fill=(r, g, b, 255))
            # Decorative circles
            dpg.draw_circle([w - 100, h // 2], 50, color=(*ACCENT, 40), thickness=2)
            dpg.draw_circle([w - 50, h // 2 - 15], 25, color=(*ACCENT_2, 40), thickness=2)
            dpg.draw_circle([70, h - 10], 70, color=(*ACCENT, 30), thickness=2)
            # Text
            dpg.draw_text([24, h // 2 - 20], title, color=TEXT_BRIGHT, size=22)
            dpg.draw_text([24, h // 2 + 8], subtitle, color=TEXT_DIM, size=10)
            # Version chip
            dpg.draw_rectangle([w - 100, 10], [w - 15, 36], fill=(*BG_DARK, 200), color=(*BORDER, 150))
            dpg.draw_text([w - 85, 16], f"v{LAUNCHER_VERSION}", color=ACCENT_2, size=10)

        dpg.set_item_resize_callback("hero_drawlist", draw_hero)

    def _ver_card(self, label, var_tag, accent):
        with dpg.group():
            dpg.add_text(label, color=TEXT_MUTED)
            dpg.add_text("Not Installed" if "installed" in var_tag.lower() else "Checking...",
                        tag=var_tag, color=accent)

    # ------------------------------------------------------------------ news tab
    def _build_news_tab(self):
        with dpg.group(tag="page_news", show=False):
            self._build_hero("Game Updates & News",
                           "Stay up to date with the latest patches and updates")
            dpg.add_spacer(height=8)
            with dpg.child_window(tag="patches_container", autosize_x=True, autosize_y=True):
                dpg.add_text("Loading patches...", color=TEXT_DIM)

    def _load_patches(self):
        def go():
            try:
                xml = self.network.fetch_text(PATCHES_URL)
                if not xml:
                    self._set_status("Failed to load patches", RED)
                    return
                patches = ET.fromstring(xml).findall(".//patch")
                if not patches:
                    return
                dpg.delete_item("patches_container", children_only=True)
                colors = [BLUE, PURPLE, GREEN, ORANGE]
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
                dpg.set_value("status_text", f"Patches error: {e}")
        threading.Thread(target=go, daemon=True).start()

    def _patch_card(self, title, desc, link, accent):
        with dpg.group(parent="patches_container"):
            with dpg.group(horizontal=True):
                dpg.add_spacer(width=4)
                with dpg.group():
                    dpg.add_text(f"  {title}", color=accent)
                    if link:
                        dpg.add_button(label="Read More",
                                      callback=lambda: os.system(f"start {link}"))
                    dpg.add_spacer(height=2)
                    dpg.add_text(desc, color=TEXT, wrap=650)
                    dpg.add_spacer(height=4)
                    dpg.add_separator()

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
            dpg.show_item("error_modal")

    def _cb_change_location(self, sender, app_data):
        self._change_location()

    def _cb_settings(self, sender, app_data):
        self._show_settings()

    def _cb_reinstall(self, sender, app_data):
        self._reinstall_game()

    def _cb_uninstall(self, sender, app_data):
        self._uninstall_game()

    def _cb_coming_soon(self, sender, app_data):
        with dpg.window(label="Discord", modal=True, tag="discord_modal",
                       width=350, height=150, no_resize=True):
            dpg.add_text("Discord server coming soon!")
            dpg.add_spacer(height=10)
            dpg.add_button(label="OK", callback=lambda: dpg.delete_item("discord_modal"), width=-1)
        dpg.split_frame()

    def _show_kebab(self, sender, app_data):
        with dpg.window(label="Options", modal=True, tag="kebab_modal",
                       width=280, height=200, no_resize=True):
            dpg.add_button(label="Verify Game Files", callback=lambda s, a, u: self._verify_files(s, a, u), width=-1)
            dpg.add_button(label="View Logs", callback=lambda s, a, u: self._view_logs(s, a, u), width=-1)
            dpg.add_separator()
            dpg.add_button(label="About", callback=lambda s, a, u: self._show_about(s, a, u), width=-1)
            dpg.add_button(label="Close", callback=lambda: dpg.delete_item("kebab_modal"), width=-1)

    def _show_about(self, sender, app_data):
        dpg.delete_item("kebab_modal")
        with dpg.window(label="About", modal=True, tag="about_modal",
                       width=400, height=250, no_resize=True):
            dpg.add_text(f"{APP_NAME} v{LAUNCHER_VERSION}")
            dpg.add_spacer(height=6)
            dpg.add_text(f"Made by {MAKER}")
            dpg.add_spacer(height=6)
            dpg.add_text("A sleek launcher for Among Us\nwith auto-updates and mod support.")
            dpg.add_spacer(height=10)
            dpg.add_button(label="OK", callback=lambda: dpg.delete_item("about_modal"), width=-1)

    def _view_logs(self, sender, app_data):
        dpg.delete_item("kebab_modal")
        lf = Path("launcher.log")
        if lf.exists():
            os.startfile(lf)

    def _show_settings(self, sender=None, app_data=None):
        settings = self.config.settings

        with dpg.window(label="Settings", modal=True, tag="settings_modal",
                       width=480, height=400, no_resize=True):
            dpg.add_text("Preferences")
            dpg.add_spacer(height=8)

            # Discord RPC
            dpg.add_checkbox(label="Discord Rich Presence",
                           tag="sett_discord_rpc",
                           default_value=settings.get("discord_rpc", True))
            dpg.add_text("  Show activity on Discord", color=TEXT_DIM)
            dpg.add_spacer(height=8)

            # Auto update
            dpg.add_checkbox(label="Auto-update game",
                           tag="sett_auto_update",
                           default_value=settings.get("auto_update", True))
            dpg.add_text("  Download game updates automatically", color=TEXT_DIM)
            dpg.add_spacer(height=8)

            # Verify integrity
            dpg.add_checkbox(label="Verify file integrity",
                           tag="sett_check_integrity",
                           default_value=settings.get("check_integrity", True))
            dpg.add_text("  Check checksums after download", color=TEXT_DIM)

            dpg.add_spacer(height=16)

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

            dpg.add_button(label="Save", callback=save_settings, width=-1)
            bind_accent(dpg.last_item(), "green")

    # ------------------------------------------------------------------ actions
    def _download_latest(self):
        def go():
            try:
                self._busy_on()
                self._set_status("Preparing download...", BLUE)
                latest = self.latest_version
                if latest == "Checking...":
                    latest = self.network.fetch_text(VERSION_URL)
                    if not latest:
                        self._set_status("Failed to fetch version info", RED)
                        return
                gp = self.config.get_game_path()
                if not gp:
                    gp = self._select_folder()
                    if not gp:
                        self._set_status("Installation cancelled", TEXT_DIM)
                        return
                url = f"https://github.com/{GITHUB_REPO}/releases/download/{latest}/app.zip"
                zf = Path("game.zip")
                self._set_status(f"Downloading v{latest}...", BLUE)

                def prog(cur, total, spd):
                    pct = cur / total * 100 if total else 0
                    self._update_progress(pct)
                    self._set_status(f"Downloading: {pct:.1f}% — {FileManager.format_size(spd)}/s")

                if not self.network.download_file(url, zf, prog):
                    self._set_status("Download failed!", RED)
                    return
                self._set_status("Extracting...", BLUE)
                gp.mkdir(parents=True, exist_ok=True)

                def xp(cur, total):
                    pct = cur / total * 100 if total else 0
                    self._update_progress(pct)
                    self._set_status(f"Extracting: {pct:.0f}%")

                if not FileManager.extract_zip(zf, gp, xp):
                    self._set_status("Extraction failed!", RED)
                    return
                FileManager.safe_delete(zf)
                self.config.set_version(latest)
                self.config.set_game_path(gp)
                self.current_version = latest
                self._update_version_display()
                self._update_progress(100)
                self._set_status("Installation complete!", GREEN)
            except Exception as e:
                self._set_status(f"Error: {e}", RED)
            finally:
                self._busy_off()
                self._update_main_btn()
        threading.Thread(target=go, daemon=True).start()

    def _check_updates(self):
        def go():
            try:
                self._set_status("Checking for updates...", BLUE)
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

            dpg.delete_item("specific_modal", children_only=False) if dpg.does_item_exist("specific_modal") else None
            with dpg.window(label="Install Specific Version", modal=True, tag="specific_modal",
                           width=440, height=500, no_resize=True):
                dpg.add_text("Available Versions")
                dpg.add_spacer(height=8)
                for i, v in enumerate(versions):
                    dpg.add_button(label=v.version, width=-1,
                                  callback=lambda s, a, u=v: self._do_install_version(u))
                dpg.add_spacer(height=8)
                dpg.add_button(label="Cancel",
                              callback=lambda: dpg.delete_item("specific_modal"), width=-1)
        threading.Thread(target=go, daemon=True).start()

    def _do_install_version(self, ver: GameVersion):
        def go():
            try:
                self._busy_on()
                gp = self.config.get_game_path() or self._select_folder()
                if not gp:
                    return
                self._set_status(f"Installing v{ver.version}...", BLUE)
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
                self._set_status(f"Error: {e}", RED)
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
            self._set_status("Game launched!", GREEN)
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
                self._set_status("Checking AUnlocker...", BLUE)
                data = self.network.fetch_text(AUNLOCKER_JSON_URL)
                if not data:
                    self._show_error("Failed to fetch data")
                    return
                versions = json.loads(data).get("versions", [])
                for entry in versions:
                    if entry["version"] == ver:
                        zp = Path("AUnlocker.zip")
                        self._set_status("Downloading AUnlocker...", BLUE)
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
            self._show_info("Shortcut created!")
        except Exception as e:
            self._show_error(f"Failed: {e}")

    def _change_location(self):
        new_path = self._select_folder()
        if not new_path:
            return
        self._set_status("Verifying game files...", BLUE)
        result = FileManager.verify_game_folder(new_path)
        if not result["exe_found"]:
            self._set_status("Invalid folder!", RED)
            self._show_error("Among Us.exe not found.\nSelect a valid Among Us installation.")
            return
        if result["missing"]:
            self._set_status("Some files missing", ORANGE)
            msg = (f"Some game files are missing:\n{', '.join(result['missing'])}\n\n"
                   f"Found {result['file_count']} files ({FileManager.format_size(result['total_size'])}).\n"
                   "Continue anyway?")
            if not self._ask_yes_no(msg):
                self._set_status("Ready")
                return
        self._set_status(f"Verified — {result['file_count']} files, {FileManager.format_size(result['total_size'])}", GREEN)
        old = self.config.get_game_path()
        if old and old.exists() and old != new_path:
            if self._ask_yes_no("Move existing game files to new location?"):
                self._set_status("Moving files...", BLUE)
                try:
                    shutil.move(str(old), str(new_path))
                    self._set_status("Files moved!", GREEN)
                except (PermissionError, OSError) as e:
                    self._set_status("Move failed", RED)
                    self._show_error(f"Failed to move files: {e}")
                    return
        self.config.set_game_path(new_path)
        self._set_status("Location changed!", GREEN)
        self._show_info(f"Location: {new_path}")

    def _verify_files(self):
        if dpg.does_item_exist("kebab_modal"):
            dpg.delete_item("kebab_modal")
        gp = self.config.get_game_path()
        if not gp:
            self._show_error("Game not installed!")
            return
        self._set_status("Verifying...", BLUE)
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
            self._set_status(f"Selected: {path}", GREEN)
            return path
        return None

    # ------------------------------------------------------------------ helpers
    def _set_status(self, text, color=None):
        self.status_text = text
        dpg.set_value("status_text", text)
        if color:
            dpg.configure_item("status_icon", color=color)

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
            bind_accent("main_action_btn", "green")
        elif cur != lat and lat != "Checking...":
            dpg.configure_item("main_action_btn", label="UPDATE AVAILABLE")
            bind_accent("main_action_btn", "blue")
        else:
            dpg.configure_item("main_action_btn", label="LAUNCH GAME")
            bind_accent("main_action_btn", "green")

    def _busy_on(self):
        self._busy = True
        dpg.configure_item("main_action_btn", enabled=False)

    def _busy_off(self):
        self._busy = False
        dpg.configure_item("main_action_btn", enabled=True)

    def _show_info(self, msg):
        with dpg.window(label="Info", modal=True, tag="info_modal",
                       width=400, height=180, no_resize=True):
            dpg.add_text(msg, wrap=360)
            dpg.add_spacer(height=10)
            dpg.add_button(label="OK", callback=lambda: dpg.delete_item("info_modal"), width=-1)

    def _show_error(self, msg):
        with dpg.window(label="Error", modal=True, tag="error_modal",
                       width=400, height=180, no_resize=True):
            dpg.add_text(msg, wrap=360, color=RED)
            dpg.add_spacer(height=10)
            dpg.add_button(label="OK", callback=lambda: dpg.delete_item("error_modal"), width=-1)

    def _show_warning(self, msg):
        with dpg.window(label="Warning", modal=True, tag="warning_modal",
                       width=400, height=180, no_resize=True):
            dpg.add_text(msg, wrap=360, color=ORANGE)
            dpg.add_spacer(height=10)
            dpg.add_button(label="OK", callback=lambda: dpg.delete_item("warning_modal"), width=-1)

    def _ask_yes_no(self, msg):
        result = [False]

        def on_yes(sender, app_data):
            result[0] = True
            dpg.delete_item("yesno_modal")

        def on_no(sender, app_data):
            dpg.delete_item("yesno_modal")

        with dpg.window(label="Confirm", modal=True, tag="yesno_modal",
                       width=420, height=180, no_resize=True):
            dpg.add_text(msg, wrap=380)
            dpg.add_spacer(height=10)
            with dpg.group(horizontal=True):
                dpg.add_button(label="Yes", callback=on_yes, width=100)
                bind_accent(dpg.last_item(), "green")
                dpg.add_button(label="No", callback=on_no, width=100)

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
        self.discord.disconnect()
        dpg.destroy_context()
