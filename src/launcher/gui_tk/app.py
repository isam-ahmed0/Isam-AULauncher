"""CrewLauncher Lite — main tkinter window.

Install / Play / Uninstall, Discord Rich Presence and Settings only. All real
work is delegated to the shared backend (``GameCore``, ``NetworkManager``,
``DiscordRPC``, ``FileManager``, ``platform_utils``).
"""
import os
import sys
import shutil
import logging
import webbrowser
import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, messagebox

from config import (
    APP_NAME, BRAND_SHORT, MAKER, LAUNCHER_VERSION,
    DEFAULT_GAME_DIR, VERSION_URL, LAUNCHER_UPDATE_URL, SOURCE_CODE_URL,
)
from file_manager import FileManager
from platform_utils import IS_LINUX, IS_WINDOWS, open_local_path
from itch_oauth import fetch_itch_profile, fetch_itch_username, read_itch_token
import gui_tk.theme as theme
from gui_tk.theme import apply_theme
from gui_tk.util import UIQueue, run_thread

_STATUS_COLORS = {
    "info": theme.TEXT_SECONDARY,
    "success": theme.SUCCESS,
    "warning": theme.WARNING,
    "danger": theme.DANGER,
}


class LauncherLiteApp:
    def __init__(self, config, network, discord, root=None):
        self.config = config
        self.network = network
        self.discord = discord
        from game_core import GameCore
        self.game = GameCore(config, network)

        self.root = root or tk.Tk()
        self.root.title(APP_NAME)
        self._set_icon()

        self.ui = UIQueue(self.root)
        self._busy = False
        self._running = False
        self._closing = False
        self._gated = False
        self._login_win = None
        self._profile_hook = None
        self._profile = {"token": False, "username": None, "among_us_name": None, "platforms": []}
        self.current_version = config.get_version() or "Not Installed"
        self.latest_version = None

        apply_theme(self.root)
        self._wire_game_callbacks()
        self._build_ui()
        self._refresh_state()

        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)
        self.root.minsize(560, 460)
        self._center(640, 520)

        self.root.after(80, self._check_login_gate)
        self.root.after(120, self._initial_load)
        self.root.after(2000, self._poll_game)

    # ------------------------------------------------------------------ setup
    def _set_icon(self):
        try:
            icon = Path(__file__).resolve().parent.parent / "resources" / "icon.ico"
            if icon.exists():
                if IS_WINDOWS:
                    self.root.iconbitmap(str(icon))
                else:
                    self._icon_img = tk.PhotoImage(file=str(icon))
                    self.root.iconphoto(True, self._icon_img)
        except Exception:
            pass

    def _center(self, w, h):
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = max((sw - w) // 2, 0)
        y = max((sh - h) // 3, 0)
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _wire_game_callbacks(self):
        self.game.on_status = lambda text, level="info": self.ui.call(
            lambda: self._set_status(text, level))
        self.game.on_progress = lambda pct: self.ui.call(
            lambda: self._set_progress(pct))
        self.game.on_started = lambda: self.ui.call(self._on_game_started)
        self.game.on_stopped = lambda: self.ui.call(self._on_game_stopped)

    # ------------------------------------------------------------------ layout
    def _build_ui(self):
        root = self.root
        root.columnconfigure(0, weight=1)
        root.rowconfigure(2, weight=1)

        # Header
        header = ttk.Frame(root, padding=(20, 16, 20, 10))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text=BRAND_SHORT, style="Title.TLabel").grid(row=0, column=0, sticky="w")
        self.account_lbl = ttk.Label(header, text="Not signed in", style="Muted.TLabel")
        self.account_lbl.grid(row=0, column=1, sticky="e", padx=(0, 10))
        self.ver_lbl = ttk.Label(header, text=f"v{LAUNCHER_VERSION}", style="Muted.TLabel")
        self.ver_lbl.grid(row=0, column=2, sticky="e")

        # Status bar
        self.status_bar = ttk.Frame(root, style="Bar.TFrame", padding=(16, 10))
        self.status_bar.grid(row=1, column=0, sticky="ew", padx=16)
        self.status_lbl = ttk.Label(
            self.status_bar, text="Ready", style="Status.TLabel", wraplength=560)
        self.status_lbl.pack(anchor="w")

        # Body card
        card = ttk.Frame(root, style="Card.TFrame", padding=20)
        card.grid(row=2, column=0, sticky="nsew", padx=16, pady=16)
        card.columnconfigure(0, weight=1)

        self.installed_lbl = ttk.Label(
            card, text="Version: Not Installed", style="Card.TLabel")
        self.installed_lbl.grid(row=0, column=0, sticky="w")

        self.action_btn = ttk.Button(
            card, text="INSTALL GAME", style="Big.TButton", command=self._on_primary)
        self.action_btn.grid(row=1, column=0, sticky="ew", pady=(16, 10), ipady=4)

        self.progress = ttk.Progressbar(card, mode="determinate", maximum=100)
        self.progress.grid(row=2, column=0, sticky="ew")

        tools = ttk.Frame(card, style="Card.TFrame")
        tools.grid(row=3, column=0, sticky="ew", pady=(16, 0))
        for i in range(3):
            tools.columnconfigure(i, weight=1)
        self.open_btn = ttk.Button(tools, text="Open Folder", command=self._open_folder)
        self.open_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.uninstall_btn = ttk.Button(
            tools, text="Uninstall", style="Danger.TButton", command=self._uninstall)
        self.uninstall_btn.grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(tools, text="Settings", command=self._open_settings).grid(
            row=0, column=2, sticky="ew", padx=(4, 0))

        # Footer
        footer = ttk.Frame(root, padding=(20, 0, 20, 14))
        footer.grid(row=3, column=0, sticky="ew")
        ttk.Label(
            footer, text=f"{APP_NAME} v{LAUNCHER_VERSION} — Made by {MAKER}",
            style="Muted.TLabel").pack(side="left")

    # ------------------------------------------------------------------ status
    def _set_status(self, text, level="info"):
        self.status_lbl.configure(text=text, foreground=_STATUS_COLORS.get(level, theme.TEXT_SECONDARY))

    def _set_progress(self, pct):
        try:
            self.progress.configure(value=max(0, min(100, pct)))
        except Exception:
            pass

    def _busy_on(self):
        self._busy = True
        self._refresh_state()

    def _busy_off(self):
        self._busy = False
        self._refresh_state()

    # ------------------------------------------------------------------ state
    def _game_path(self):
        gp = self.config.get_game_path()
        if gp and (gp / "Among Us.exe").exists():
            return gp
        return None

    def _refresh_state(self):
        gp = self._game_path()
        installed = gp is not None

        if self._gated:
            self.action_btn.configure(
                text="SIGN IN REQUIRED", style="Big.TButton", state="disabled")
        elif self._busy:
            self.action_btn.configure(text="WORKING...", style="Big.TButton", state="disabled")
        elif self._running:
            self.action_btn.configure(
                text="PLAYING  (click to stop)", style="BigDanger.TButton", state="normal")
        elif not installed:
            self.action_btn.configure(text="INSTALL GAME", style="Big.TButton", state="normal")
        elif self.latest_version and self.current_version and self.latest_version != self.current_version:
            self.action_btn.configure(text="UPDATE", style="Big.TButton", state="normal")
        else:
            self.action_btn.configure(text="PLAY", style="BigSuccess.TButton", state="normal")

        ver = self.current_version if installed else "Not Installed"
        self.installed_lbl.configure(text=f"Version: {ver}")
        self.open_btn.configure(state="normal" if installed else "disabled")
        self.uninstall_btn.configure(state="normal" if installed else "disabled")

    # ------------------------------------------------------------------ account
    def _check_login_gate(self):
        """Require an itch.io sign-in before the launcher can be used."""
        if self._closing:
            return
        if read_itch_token(self.config.get_wine_prefix()):
            self._gated = False
            self._refresh_account_ui(
                {"token": True, "username": None, "among_us_name": None, "platforms": []})
            self._load_profile()
            self._refresh_state()
            self._set_status("Ready", "info")
            return

        self._gated = True
        self._refresh_state()
        self._set_status("Sign in with itch.io to use the launcher.", "warning")
        self._require_sign_in()

    def _require_sign_in(self):
        from gui_tk.login import LoginDialog
        self._login_win = LoginDialog(
            self.root,
            ui=self.ui,
            prefix=self.config.get_wine_prefix(),
            on_status=lambda text: self._set_status(text, "warning"),
            on_success=self._on_sign_in_success,
        )
        self._login_win.win.grab_set()
        self._login_win.win.focus_set()
        self.root.wait_window(self._login_win.win)
        if self._gated and not self._closing:
            self.shutdown()

    def _on_sign_in_success(self):
        self._gated = False
        self._set_status("Login successful!", "success")
        self._refresh_account_ui(
            {"token": True, "username": None, "among_us_name": None, "platforms": []})
        self._load_profile()
        self._refresh_state()

    def _load_profile(self):
        def work():
            prefix = self.config.get_wine_prefix()
            username = None
            try:
                username = fetch_itch_username(prefix, timeout=6)
            except Exception:
                logging.exception("Username fetch failed")
            if username:
                self.ui.call(lambda u=username: self._set_account_username(u))
            try:
                profile = fetch_itch_profile(prefix, username=username)
            except Exception:
                logging.exception("Profile fetch failed")
                profile = {"token": True, "username": username,
                           "among_us_name": None, "platforms": []}
            self.ui.call(lambda p=profile: self._refresh_account_ui(p))
        run_thread(work, "profile")

    def _set_account_username(self, username):
        self._refresh_account_ui(
            {"token": True, "username": username, "among_us_name": None, "platforms": []})

    def _refresh_account_ui(self, profile):
        self._profile = profile
        if profile.get("token"):
            username = profile.get("username")
            text = f"Logged in as {username}" if username else "Signed in"
            self.account_lbl.configure(text=text, foreground=theme.SUCCESS)
        else:
            self.account_lbl.configure(text="Not signed in", foreground=theme.TEXT_MUTED)
        hook = self._profile_hook
        if hook:
            try:
                hook(profile)
            except Exception:
                logging.debug("Profile hook failed", exc_info=True)

    # ------------------------------------------------------------------ primary
    def _on_primary(self):
        if self._gated:
            self._check_login_gate()
            return
        if self._running:
            self.game.stop()
            return
        txt = self.action_btn.cget("text")
        if "INSTALL" in txt or "UPDATE" in txt:
            self._install()
        elif "PLAY" in txt:
            self._launch()

    def _initial_load(self):
        def work():
            try:
                v = self.config.get_version()
                if v:
                    self.current_version = v
                latest = self.network.fetch_text(VERSION_URL)
                if latest:
                    self.latest_version = latest
                self.ui.call(self._refresh_state)

                if self.config.settings.get("discord_rpc"):
                    self.discord.connect()
                    self.ui.call(self.apply_discord_rpc)

                self._check_launcher_update()
            except Exception:
                logging.exception("Initial load failed")
        run_thread(work, "initial-load")

    def _check_launcher_update(self):
        try:
            remote = (self.network.fetch_text(LAUNCHER_UPDATE_URL) or "").strip()
            if not remote or remote == LAUNCHER_VERSION:
                return
            try:
                from packaging.version import Version
                if Version(remote) <= Version(LAUNCHER_VERSION):
                    return
            except Exception:
                return

            def prompt():
                if messagebox.askyesno(
                    "Update Available",
                    f"A new version (v{remote}) is available.\n"
                    f"Current: v{LAUNCHER_VERSION}\n\nOpen the downloads page?"):
                    webbrowser.open(f"{SOURCE_CODE_URL}/releases/latest")
            self.ui.call(prompt)
        except Exception:
            logging.debug("Launcher update check failed", exc_info=True)

    def _install(self):
        gp = self._game_path()
        if gp is None:
            default = Path(DEFAULT_GAME_DIR)
            try:
                default.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
            folder = filedialog.askdirectory(
                title="Select Install Folder", initialdir=str(default), mustexist=False)
            if not folder:
                return
            gp = Path(folder)
            self.config.set_game_path(gp)

        version = self.latest_version
        if not version:
            self._set_status("Fetching version info...", "info")
            version = self.network.fetch_text(VERSION_URL)
        if not version:
            self._set_status("Failed to fetch version info", "danger")
            return

        self._busy_on()
        self._set_status("Preparing download...", "info")
        self._set_progress(0)
        if self.discord.connected:
            self.discord.update_status("Updating Game", "Downloading...")

        def work():
            try:
                ok = self.game.download_update(version, gp)
                if ok:
                    self.current_version = version
            except Exception as e:
                logging.exception("Install failed")
                self.ui.call(lambda: self._set_status(f"Error: {e}", "danger"))
            finally:
                self.ui.call(self._busy_off)
                self.ui.call(self._refresh_state)
                if self.discord.connected:
                    self.discord.update_status("In Launcher", "Browsing Menu")
        run_thread(work, "install")

    def _launch(self):
        if IS_LINUX:
            self._launch_linux()
        else:
            self.game.launch()
        self.root.after(300, self._refresh_state)

    def _launch_linux(self):
        from platform_utils import find_lutris
        gp = self._game_path()
        if gp is None:
            self._set_status("Game not installed!", "danger")
            return
        method = self.config.settings.get("launch_method", "ask")
        try:
            lutris_cmd = find_lutris()
            entry = None
            if lutris_cmd:
                entry = self._resolve_lutris_entry(gp, lutris_cmd)
                self._cache_lutris_entry(gp, entry)

            if method == "wine":
                self._launch_wine_warning(gp)
            elif method == "lutris":
                if lutris_cmd and entry and entry.get("id") is not None:
                    self.game.launch_lutris(entry["id"])
                else:
                    self._launch_wine_warning(gp)
            else:
                self._prompt_launch_choice(gp, entry, lutris_cmd)
        except Exception as e:
            logging.exception("Linux launch failed")
            messagebox.showerror("Launch failed", str(e), parent=self.root)

    def _resolve_lutris_entry(self, gp, lutris_cmd):
        from platform_utils import (
            lutris_find_entry, lutris_find_existing_install, lutris_entry_by_configpath,
        )
        cached_id = self.config.get_lutris_id(gp)
        if cached_id is not None:
            entry = lutris_find_entry(gp, cached_id, lutris_cmd)
            if entry:
                return entry
        configpath = lutris_find_existing_install(
            gp, gp / "Among Us.exe", prefix="among-us-isam")
        if configpath:
            entry = lutris_entry_by_configpath(configpath)
            if entry and entry.get("id") is not None:
                return entry
        return None

    def _cache_lutris_entry(self, gp, entry):
        if entry:
            self.config.set_lutris_entry(gp, entry)
            if entry.get("id") is not None:
                self.config.set_lutris_id(gp, entry.get("id"))
        else:
            self.config.clear_lutris_entry(gp)

    def _launch_wine_warning(self, gp):
        from platform_utils import find_wine
        if not find_wine():
            messagebox.showwarning(
                "Wine not found",
                "Wine is not installed. Install Wine or use Lutris.", parent=self.root)
            return
        if self.config.settings.get("warn_plain_wine", True):
            if not messagebox.askyesno(
                "Launch with Wine",
                "Running Among Us directly with Wine is not recommended.\n"
                "Lutris lets you choose your GPU. Launch anyway?",
                parent=self.root, default="no"):
                return
        self.game.launch_wine(gp, gp / "Among Us.exe")

    def _prompt_launch_choice(self, gp, entry, lutris_cmd):
        options = []
        if lutris_cmd:
            if entry and entry.get("id") is not None:
                options.append(("lutris", "Launch with Lutris", "Success.TButton"))
            options.append(("wine", "Launch with Wine", "TButton"))
        else:
            options.append(("wine", "Launch with Wine", "Success.TButton"))
        choice = self._choose(
            "Launch Among Us",
            "How do you want to launch Among Us?",
            options)
        if choice == "lutris" and entry and entry.get("id") is not None:
            self.game.launch_lutris(entry["id"])
        elif choice == "wine":
            self._launch_wine_warning(gp)

    def _choose(self, title, message, options):
        """Small modal chooser returning the picked key or None."""
        result = {"value": None}
        win = tk.Toplevel(self.root)
        win.title(title)
        win.configure(bg=theme.BG_BASE)
        win.transient(self.root)
        win.resizable(False, False)
        frame = ttk.Frame(win, style="Card.TFrame", padding=18)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=title, style="Heading.TLabel").pack(anchor="w")
        ttk.Label(frame, text=message, style="CardMuted.TLabel",
                  wraplength=320, justify="left").pack(anchor="w", pady=(4, 12))
        for key, label, style in options:
            def cmd(k=key):
                result["value"] = k
                win.destroy()
            ttk.Button(frame, text=label, style=style, command=cmd).pack(
                fill="x", pady=3)

        def cancel():
            result["value"] = None
            win.destroy()
        ttk.Button(frame, text="Cancel", command=cancel).pack(fill="x", pady=(8, 0))
        win.protocol("WM_DELETE_WINDOW", cancel)
        win.update_idletasks()
        win.geometry(f"+{self.root.winfo_rootx() + 120}+{self.root.winfo_rooty() + 120}")
        win.grab_set()
        self.root.wait_window(win)
        return result["value"]

    # ------------------------------------------------------------------ actions
    def _open_folder(self):
        gp = self._game_path()
        if gp:
            try:
                open_local_path(gp)
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=self.root)
        else:
            messagebox.showwarning("Error", "Game not installed!", parent=self.root)

    def _uninstall(self):
        gp = self._game_path()
        if gp is None:
            messagebox.showwarning("Error", "Game not installed!", parent=self.root)
            return
        if not messagebox.askyesno(
                "Confirm", "Remove all game files and launcher data?",
                parent=self.root, default="no"):
            return
        if FileManager.safe_delete(gp):
            self._set_status("Game files removed", "success")
        else:
            messagebox.showerror("Error", "Failed to remove game files", parent=self.root)
            return

        if messagebox.askyesno(
                "Confirm",
                "Also remove launcher settings and data?\nThe launcher will restart.",
                parent=self.root, default="no"):
            try:
                shutil.rmtree(str(self.config.appdata_dir), ignore_errors=True)
            except Exception:
                pass
            os._exit(0)

        self.current_version = "Not Installed"
        self.latest_version = None
        self._set_progress(0)
        self._refresh_state()

    def _open_settings(self):
        from gui_tk.settings import SettingsDialog
        SettingsDialog(self.root, self)

    # ------------------------------------------------------------------ discord
    def apply_discord_rpc(self):
        enabled = bool(self.config.settings.get("discord_rpc", True))
        if enabled and not self.discord.connected:
            self.discord.connect()
        elif not enabled and self.discord.connected:
            self.discord.disconnect()

    def _on_game_started(self):
        self._running = True
        self._refresh_state()
        self._set_status("Game launched!", "success")
        if self.discord.connected:
            self.discord.update_status("Playing Among Us", "In Game")

    def _on_game_stopped(self):
        self._running = False
        self._refresh_state()
        self._set_status("Game stopped.", "info")
        if self.discord.connected:
            self.discord.update_status("In Launcher", "Browsing Menu")

    # ------------------------------------------------------------------ loop
    def _poll_game(self):
        if self._closing:
            return
        try:
            self.game.poll()
            running = self.game.is_running
            if running != self._running:
                self._running = running
                self._refresh_state()
        except Exception:
            logging.debug("Game poll failed", exc_info=True)
        self.root.after(2000, self._poll_game)

    def run(self):
        self.root.mainloop()

    def shutdown(self):
        if self._closing:
            return
        self._closing = True
        self.ui.stop()
        try:
            self.discord.disconnect()
        except Exception:
            pass
        try:
            self.network.session.close()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass
