"""
Isam AULauncher — main entry point.
Thin launcher: window + orchestrator. All logic in separate modules.
"""
import os
import sys
import json
import logging
import threading
import subprocess
import shutil
from pathlib import Path
from typing import Optional

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from config import (
    Config, APP_NAME, BRAND_SHORT, MAKER, LAUNCHER_VERSION,
    VERSION_URL, LAUNCHER_VERSION_URL, LAUNCHER_DOWNLOAD_URL,
    GITHUB_REPO, AUNLOCKER_JSON_URL,
)
from network import NetworkManager, DiscordRPC, GameVersion
from file_manager import FileManager
from ui.theme import Pal
from ui.titlebar import TitleBar
from ui.sidebar import SideBar
from ui.game_tab import GameTab
from ui.news_tab import NewsTab
from ui.settings_dialog import SettingsDialog
from ui.dialogs import KebabMenu, InstallSpecificDialog, VerifyDialog


class LaunchWindow:
    def __init__(self):
        self.config = Config()
        self.network = NetworkManager()
        self.discord = DiscordRPC()

        # --- root (borderless) with hidden parent for taskbar icon ---
        self._root_hidden = tk.Tk()
        self._root_hidden.withdraw()

        self.root = tk.Toplevel(self._root_hidden)
        self.root.withdraw()
        self.root.overrideredirect(True)
        self.root.geometry("1150x740")
        self.root.minsize(1024, 660)
        self.root.configure(bg=Pal.ACCENT)
        self.root.attributes("-topmost", False)

        # Variables shared across UI components (require root window)
        self.current_version = tk.StringVar(value="Not Installed")
        self.latest_version = tk.StringVar(value="Checking...")
        self.status_text = tk.StringVar(value="Starting...")
        self.progress_var = tk.DoubleVar(value=0)
        self._busy = False

        # Outer frame
        bw = Pal.BORDER_W
        self.outer = tk.Frame(self.root, bg=Pal.BG_DARK, highlightthickness=bw,
                              highlightbackground=Pal.BORDER)
        self.outer.pack(fill=tk.BOTH, expand=True, padx=bw, pady=bw)

        # Build UI components
        self.titlebar = TitleBar(self.outer, self.root, self._close)

        # Content area (sidebar + main)
        body = tk.Frame(self.outer, bg=Pal.BG_DARK)
        body.pack(fill=tk.BOTH, expand=True)

        # Sidebar
        actions = {
            "install_aunlocker": self.install_aunlocker,
            "create_shortcut": self.create_shortcut,
            "open_folder": self.open_folder,
            "change_location": self.change_location,
            "show_settings": self._show_settings,
            "reinstall_game": self.reinstall_game,
            "uninstall_game": self.uninstall_game,
        }
        self.sidebar = SideBar(body, on_tab_switch=self._switch_tab, actions=actions)

        # Content area
        content_frame = tk.Frame(body, bg=Pal.BG_DARK)
        content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.game_tab = GameTab(content_frame, self)
        self.news_tab = NewsTab(content_frame, self.network)

        self._active_tab = "game"
        self.game_tab.pack(fill=tk.BOTH, expand=True)

        # Kebab menu
        self.kebab = KebabMenu(self.root, self)

        # Show window
        self.root.deiconify()
        self.root.update_idletasks()
        self.root.update()

        # Start title bar animation
        self.titlebar.start_animation()

        # Mousewheel
        self.root.bind_all("<MouseWheel>", self._on_mousewheel)

        # Deferred data load (after first frame renders)
        self.root.after(100, self._load_initial_data)

    # ------------------------------------------------------------------ window
    def _close(self):
        self.titlebar.stop_animation()
        self.discord.disconnect()
        self.root.destroy()
        self._root_hidden.destroy()

    def _on_mousewheel(self, event):
        try:
            self.sidebar.on_mousewheel(event)
            if self._active_tab == "news":
                self.news_tab.on_mousewheel(event)
        except:
            pass

    # ------------------------------------------------------------------ tabs
    def _switch_tab(self, tid):
        self._active_tab = tid
        self.game_tab.pack_forget()
        self.news_tab.pack_forget()
        if tid == "game":
            self.game_tab.pack(fill=tk.BOTH, expand=True)
        elif tid == "news":
            self.news_tab.pack(fill=tk.BOTH, expand=True)
            self.news_tab.load_patches()

    # ------------------------------------------------------------------ state
    def _load_initial_data(self):
        def go():
            v = self.config.get_version()
            if v:
                self._safe_set(self.current_version, v)
            latest = self.network.fetch_text(VERSION_URL)
            if latest:
                self._safe_set(self.latest_version, latest)
            self.root.after(0, self._update_btn)
            if self.config.settings.get("discord_rpc"):
                self.discord.connect()
        threading.Thread(target=go, daemon=True).start()

    def _safe_set(self, var, val):
        self.root.after(0, lambda: var.set(val))

    def _update_btn(self):
        cur = self.current_version.get()
        lat = self.latest_version.get()
        gp = self.config.get_game_path()
        if cur == "Not Installed" or not gp or not (gp / "Among Us.exe").exists():
            self._set_btn("INSTALL GAME", Pal.GREEN, Pal.GREEN_HOVER)
        elif cur != lat and lat != "Checking...":
            self._set_btn("UPDATE AVAILABLE", Pal.BLUE, Pal.BLUE_HOVER)
        else:
            self._set_btn("LAUNCH GAME", Pal.GREEN, Pal.GREEN_HOVER)

    def _set_btn(self, text, color, hover):
        btn = self.game_tab.main_button
        btn.config(text=text, bg=color, activebackground=hover)
        btn.bind("<Enter>", lambda e, c=color, h=hover: btn.config(bg=h))
        btn.bind("<Leave>", lambda e, c=color: btn.config(bg=c))

    def _set_status(self, text, color=None):
        self.root.after(0, lambda: (
            self.status_text.set(text),
            self.game_tab.status_icon.config(fg=color or Pal.GREEN) if color else None,
        ))

    def _busy_on(self):
        self._busy = True
        self.root.after(0, lambda: self.game_tab.main_button.config(state=tk.DISABLED))

    def _busy_off(self):
        self._busy = False
        self.root.after(0, lambda: self.game_tab.main_button.config(state=tk.NORMAL))

    # ------------------------------------------------------------------ main action
    def main_action(self):
        t = self.game_tab.main_button.cget("text")
        if "INSTALL" in t or "UPDATE" in t:
            self.download_latest()
        elif "LAUNCH" in t:
            self.launch_game()

    def show_kebab_menu(self):
        self.kebab.show()

    def _show_settings(self):
        SettingsDialog(self.root, self.config, self.discord)

    # ------------------------------------------------------------------ actions
    def download_latest(self):
        def go():
            try:
                self._busy_on()
                self._set_status("Preparing download...", Pal.BLUE)
                latest = self.latest_version.get()
                if latest == "Checking...":
                    latest = self.network.fetch_text(VERSION_URL)
                    if not latest:
                        self._set_status("Failed to fetch version info", Pal.RED)
                        return
                gp = self.config.get_game_path()
                if not gp:
                    gp = self._select_install_location()
                    if not gp:
                        self._set_status("Installation cancelled", Pal.TEXT_DIM)
                        return
                url = f"https://github.com/{GITHUB_REPO}/releases/download/{latest}/app.zip"
                zf = Path("game.zip")
                self._set_status(f"Downloading v{latest}...", Pal.BLUE)

                def prog(cur, total, spd):
                    pct = cur / total * 100 if total else 0
                    self.progress_var.set(pct)
                    self._set_status(f"Downloading: {pct:.1f}% \u2014 {FileManager.format_size(spd)}/s")

                if not self.network.download_file(url, zf, prog):
                    self._set_status("Download failed!", Pal.RED)
                    return
                self._set_status("Extracting...", Pal.BLUE)
                gp.mkdir(parents=True, exist_ok=True)

                def xp(cur, total):
                    self.progress_var.set(cur / total * 100 if total else 0)
                    self._set_status(f"Extracting: {cur / total * 100:.0f}%")

                if not FileManager.extract_zip(zf, gp, xp):
                    self._set_status("Extraction failed!", Pal.RED)
                    return
                FileManager.safe_delete(zf)
                self.config.set_version(latest)
                self.config.set_game_path(gp)
                self._safe_set(self.current_version, latest)
                self.progress_var.set(100)
                self._set_status("Installation complete!", Pal.GREEN)
                self.root.after(0, lambda: messagebox.showinfo("Success", f"Game v{latest} installed!"))
            except Exception as e:
                logging.error(f"Download error: {e}")
                self._set_status(f"Error: {e}", Pal.RED)
            finally:
                self._busy_off()
                self.root.after(0, self._update_btn)
        threading.Thread(target=go, daemon=True).start()

    def check_updates(self):
        def go():
            try:
                self._set_status("Checking for updates...", Pal.BLUE)
                lat = self.network.fetch_text(VERSION_URL)
                if lat:
                    self._safe_set(self.latest_version, lat)
                    cur = self.current_version.get()
                    msg = "Up to date!" if cur == lat else f"New version: {lat}"
                    self.root.after(0, lambda: messagebox.showinfo("Updates", msg))
                    self.root.after(0, self._update_btn)
                else:
                    self.root.after(0, lambda: messagebox.showerror("Error", "Failed to check"))
                self._set_status("Ready")
            except Exception as e:
                logging.error(f"Update check: {e}")
                self._set_status("Ready")
        threading.Thread(target=go, daemon=True).start()

    def install_specific(self):
        InstallSpecificDialog(self.root, self.network, self._install_version)

    def _install_version(self, ver: GameVersion):
        def go():
            try:
                self._busy_on()
                gp = self.config.get_game_path() or self._select_install_location()
                if not gp:
                    return
                self._set_status(f"Installing v{ver.version}...", Pal.BLUE)
                zf = Path("game.zip")

                def prog(cur, total, spd):
                    self.progress_var.set(cur / total * 100 if total else 0)
                    self._set_status(f"Downloading: {cur / total * 100:.0f}%")

                if self.network.download_file(ver.url, zf, prog):
                    gp.mkdir(parents=True, exist_ok=True)
                    FileManager.extract_zip(zf, gp)
                    FileManager.safe_delete(zf)
                    self.config.set_version(ver.version)
                    self.config.set_game_path(gp)
                    self._safe_set(self.current_version, ver.version)
                    self.root.after(0, lambda: messagebox.showinfo("Success", f"v{ver.version} installed!"))
                else:
                    self.root.after(0, lambda: messagebox.showerror("Error", "Failed"))
            except Exception as e:
                logging.error(f"Install: {e}")
                self._set_status(f"Error: {e}", Pal.RED)
            finally:
                self._busy_off()
                self.root.after(0, self._update_btn)
        threading.Thread(target=go, daemon=True).start()

    def launch_game(self):
        gp = self.config.get_game_path()
        if not gp:
            messagebox.showerror("Error", "Game not installed!")
            return
        exe = gp / "Among Us.exe"
        if not exe.exists():
            messagebox.showerror("Error", "Among Us.exe not found!")
            return
        try:
            subprocess.Popen([str(exe)], cwd=str(gp))
            self._set_status("Game launched!", Pal.GREEN)
        except PermissionError:
            messagebox.showerror("Error", "Permission denied. Try running as administrator.")
        except FileNotFoundError:
            messagebox.showerror("Error", "Game executable not found at expected path.")
        except OSError as e:
            messagebox.showerror("Error", f"Failed to launch: {e}")

    # ------------------------------------------------------------------ tools
    def install_aunlocker(self):
        ver = self.config.get_version()
        gp = self.config.get_game_path()
        if not ver or not gp:
            messagebox.showerror("Error", "Game not installed!")
            return

        def go():
            try:
                self._busy_on()
                self._set_status("Checking AUnlocker...", Pal.BLUE)
                data = self.network.fetch_text(AUNLOCKER_JSON_URL)
                if not data:
                    self.root.after(0, lambda: messagebox.showerror("Error", "Failed to fetch data"))
                    return
                versions = json.loads(data).get("versions", [])
                for entry in versions:
                    if entry["version"] == ver:
                        zp = Path("AUnlocker.zip")
                        self._set_status("Downloading AUnlocker...", Pal.BLUE)
                        if self.network.download_file(entry["link"], zp):
                            FileManager.extract_zip(zp, gp)
                            FileManager.safe_delete(zp)
                            self.root.after(0, lambda: messagebox.showinfo("Success", "AUnlocker installed!"))
                            self._set_status("Ready")
                            return
                self.root.after(0, lambda: messagebox.showwarning("Not Found", "No compatible version"))
            except Exception as e:
                logging.error(f"AUnlocker: {e}")
                self._set_status("Ready")
            finally:
                self._busy_off()
        threading.Thread(target=go, daemon=True).start()

    def create_shortcut(self):
        gp = self.config.get_game_path()
        if not gp:
            messagebox.showerror("Error", "Game not installed!")
            return
        try:
            import win32com.client
        except ImportError:
            messagebox.showerror("Error", "pywin32 not installed")
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
            messagebox.showinfo("Success", "Shortcut created!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed: {e}")

    def open_folder(self):
        gp = self.config.get_game_path()
        if gp and gp.exists():
            os.startfile(gp)
        else:
            messagebox.showerror("Error", "Game folder not found!")

    def change_location(self):
        new_path = self._select_install_location()
        if not new_path:
            return
        self._set_status("Verifying game files...", Pal.BLUE)
        self.root.update_idletasks()
        result = FileManager.verify_game_folder(new_path)
        if not result["exe_found"]:
            self._set_status("Invalid folder!", Pal.RED)
            messagebox.showerror("Invalid Folder",
                                 "Among Us.exe not found.\nSelect a valid Among Us installation.")
            return
        if result["missing"]:
            self._set_status("Some files missing", Pal.ORANGE)
            if not messagebox.askyesno("Warning",
                    f"Some game files are missing:\n{', '.join(result['missing'])}\n\n"
                    f"Found {result['file_count']} files ({FileManager.format_size(result['total_size'])}).\n"
                    "The game may not run correctly.\n\nContinue anyway?"):
                self._set_status("Ready")
                return
        self._set_status(f"Verified \u2014 {result['file_count']} files, {FileManager.format_size(result['total_size'])}", Pal.GREEN)
        old = self.config.get_game_path()
        if old and old.exists() and old != new_path:
            if messagebox.askyesno("Move Files", "Move existing game files to new location?"):
                self._set_status("Moving files...", Pal.BLUE)
                self.root.update_idletasks()
                try:
                    shutil.move(str(old), str(new_path))
                    self._set_status("Files moved!", Pal.GREEN)
                except PermissionError:
                    self._set_status("Permission denied", Pal.RED)
                    messagebox.showerror("Error", "Permission denied. Close any running game and try again.")
                    return
                except OSError as e:
                    self._set_status("Move failed", Pal.RED)
                    messagebox.showerror("Error", f"Failed to move files: {e}")
                    return
        self.config.set_game_path(new_path)
        self._set_status("Location changed!", Pal.GREEN)
        messagebox.showinfo("Success", f"Location: {new_path}")

    def verify_files(self):
        gp = self.config.get_game_path()
        if not gp:
            messagebox.showerror("Error", "Game not installed!")
            return
        self._set_status("Verifying...", Pal.BLUE)
        self.root.update_idletasks()
        result = FileManager.verify_game_folder(gp)
        VerifyDialog.show(self.root, result)
        self._set_status("Ready")

    def _select_install_location(self) -> Optional[Path]:
        folder = filedialog.askdirectory(
            title="Select Among Us Installation Folder",
            initialdir=str(Path.cwd()),
        )
        return Path(folder) if folder else None

    # ------------------------------------------------------------------ maintenance
    def reinstall_game(self):
        if not messagebox.askyesno("Confirm", "Delete and reinstall the game?"):
            return
        gp = self.config.get_game_path()
        if gp and gp.exists():
            FileManager.safe_delete(gp)
        self._safe_set(self.current_version, "Not Installed")
        self.download_latest()

    def uninstall_game(self):
        if not messagebox.askyesno("Confirm", "Remove all game files and launcher data?"):
            return
        gp = self.config.get_game_path()
        if gp and gp.exists():
            if FileManager.safe_delete(gp):
                messagebox.showinfo("Done", "Game files removed")
            else:
                messagebox.showerror("Error", "Failed to remove game files")
        if FileManager.safe_delete(self.config.appdata_dir):
            messagebox.showinfo("Done", "Launcher data removed")
        self._safe_set(self.current_version, "Not Installed")
        self.root.after(0, self._update_btn)

    def run(self):
        self._root_hidden.mainloop()
        self.titlebar.stop_animation()
        self.discord.disconnect()


# ---------------------------------------------------------------------------
# CLI launcher update check
# ---------------------------------------------------------------------------
def check_launcher_update(network: NetworkManager) -> bool:
    try:
        print(f"Checking for launcher updates...")
        latest = network.fetch_text(LAUNCHER_VERSION_URL)
        if latest and latest != LAUNCHER_VERSION:
            print(f"Update available: {latest} (current: {LAUNCHER_VERSION})")
            r = input("Download? (y/n): ").lower()
            if r in ("y", "yes"):
                new = Path(f"IsamAULauncher_{latest}.exe")
                if network.download_file(LAUNCHER_DOWNLOAD_URL, new):
                    print("Downloaded! Run the new launcher.")
                    subprocess.Popen([str(new)])
                    return False
                print("Download failed.")
        else:
            print("Up to date")
        return True
    except Exception as e:
        logging.error(f"Update check failed: {e}")
        return True


# ---------------------------------------------------------------------------
# Entry point — fast: window appears first, update check runs in background
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    while True:
        try:
            app = LaunchWindow()
            # Check for launcher updates in background (non-blocking)
            threading.Thread(target=check_launcher_update, args=(app.network,), daemon=True).start()
            app.run()
            break
        except KeyboardInterrupt:
            break
        except Exception as e:
            logging.critical(e, exc_info=True)
            print(f"Error: {e}")
            r = input("Enter to restart, 'exit' to quit: ").strip().lower()
            if r == "exit":
                break
