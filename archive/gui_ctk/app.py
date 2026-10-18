# Requires CustomTkinter:  pip install customtkinter
import os
import sys
import shutil
import logging
import webbrowser
import tkinter as tk
import customtkinter as ctk
from pathlib import Path
from tkinter import ttk, filedialog, messagebox

from gui_tk.util import UIQueue
from config import *



THEME_BG = "#2b2b2b"
THEME_FG = "#e8e8e8"
THEME_ACCENT = "#26a269"
THEME_ACCENT_FG = "#ffffff"
THEME_FIELD_BG = "#3c3c3c"
THEME_FONT_FAMILY = "Segoe UI"
THEME_FONT_SIZE = 10


def apply_theme(self, root):
    """Apply the project theme to a window. CustomTkinter styles per widget,
    so the widgets themselves carry the rest of the colours."""
    root.configure(fg_color=THEME_BG)


class LauncherCTKApp:
    def __init__(self, config, network, discord, root=None):
        self.config = config
        self.network = network
        self.discord = discord
        from game_core import GameCore
        self.game = GameCore(config, network)

        self.root = root if root is not None else ctk.CTk()
        self.root.title(APP_NAME)
        self.root.geometry("564x392")
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

    def _wire_game_callbacks(self):
        self.game.on_status = lambda text, level="info": self.ui.call(
            lambda: self._set_status(text, level))
        self.game.on_progress = lambda pct: self.ui.call(
            lambda: self._set_progress(pct))
        self.game.on_started = lambda: self.ui.call(self._on_game_started)
        self.game.on_stopped = lambda: self.ui.call(self._on_game_stopped)


def _build_ui(self):   
    self.GName = ctk.CTkLabel(root, text="Among Us", font=ctk.CTkFont(family="Helvetica", size=17), text_color=THEME_FG, width=140, height=30)
    self.GName.place(x=65, y=46)

    self.LAUNCHBTN = ctk.CTkButton(root, text="Launch", command=self.launch_game, fg_color=THEME_ACCENT, text_color=THEME_ACCENT_FG, font=ctk.CTkFont(family=THEME_FONT_FAMILY, size=THEME_FONT_SIZE), width=200, height=40)
    self.LAUNCHBTN.place(x=30, y=160)

    self.INSTALLBTN = ctk.CTkButton(root, text="Install", command=self.install_game, fg_color=THEME_ACCENT, text_color=THEME_ACCENT_FG, font=ctk.CTkFont(family=THEME_FONT_FAMILY, size=THEME_FONT_SIZE), width=200, height=40)
    self.INSTALLBTN.place(x=30, y=100)

    self.user = ctk.CTkLabel(root, text="username", text_color=THEME_FG, font=ctk.CTkFont(family=THEME_FONT_FAMILY, size=THEME_FONT_SIZE), width=90, height=26)
    self.user.place(x=480, y=2)

    self.APP_NAME = ctk.CTkLabel(root, text=APP_NAME, text_color=THEME_FG, font=ctk.CTkFont(family=THEME_FONT_FAMILY, size=THEME_FONT_SIZE), width=100, height=30)
    self.APP_NAME.place(x=0, y=0)

    self.frame1 = ctk.CTkFrame(root, border_width=2, fg_color=THEME_BG, width=260, height=150)
    self.frame1.place(x=10, y=220)

    self.Mods = ctk.CTkLabel(self.frame1, text="Mods", font=ctk.CTkFont(family="Helvetica", size=18), text_color=THEME_FG, width=100, height=30)
    self.Mods.place(x=70, y=10)

    self.frame2 = ctk.CTkFrame(root, border_width=2, fg_color=THEME_BG, width=250, height=150)
    self.frame2.place(x=300, y=220)

    self.frame3 = ctk.CTkFrame(root, border_width=2, fg_color=THEME_BG, width=250, height=150)
    self.frame3.place(x=300, y=46)

    self.Mods_count = ctk.CTkLabel(self.frame1, text="Mods: mods_count", text_color=THEME_FG, font=ctk.CTkFont(family=THEME_FONT_FAMILY, size=THEME_FONT_SIZE), width=130, height=30)
    self.Mods_count.place(x=5, y=45)

    self.profiles = ctk.CTkLabel(self.frame1, text="Profile: profile_count", text_color=THEME_FG, font=ctk.CTkFont(family=THEME_FONT_FAMILY, size=THEME_FONT_SIZE), width=130, height=30)
    self.profiles.place(x=10, y=75)

    self.open_folder = ctk.CTkButton(self.frame2, text="Open Folder", command=self.open_folder, fg_color=THEME_ACCENT, text_color=THEME_ACCENT_FG, font=ctk.CTkFont(family=THEME_FONT_FAMILY, size=THEME_FONT_SIZE), width=200, height=30)
    self.open_folder.place(x=25, y=50)

    self.quick = ctk.CTkLabel(self.frame2, text="Quick Tool", font=ctk.CTkFont(family="Helvetica", size=18), text_color=THEME_FG, width=140, height=30)
    self.quick.place(x=55, y=10)

    self.shortcut = ctk.CTkButton(self.frame2, text="Add Shortcut", command=self.add_shortcut, fg_color=THEME_ACCENT, text_color=THEME_ACCENT_FG, font=ctk.CTkFont(family=THEME_FONT_FAMILY, size=THEME_FONT_SIZE), width=200, height=30)
    self.shortcut.place(x=25, y=90)

    def launch_game(self):
        pass

    def insatll_game(self):
        pass

    def open_folder(self):
        pass

    def add_shortcut(self):
        pass


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    root = ctk.CTk()
    app = Application(root)
    root.mainloop()
