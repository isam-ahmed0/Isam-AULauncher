import customtkinter as ctk

from config import APP_NAME, APP_VERSION, APP_AUTHOR, APP_DESCRIPTION
import gui_ctk.theme as theme

class LauncherCTkapp:
    def __init__(self, config, network, discord, root=none):
    self.config = config
        self.network = network
        self.discord = discord

        theme.apply_theme()
        self.root = root or ctk.CTk()
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.configure(fg_color=theme.BG_BASE)

        self._build_ui()
        self._center(570, 400)

        def _build_ui(self):
            header = ctk.CTkLabel(self.root, fg_color=transparent)
            header.pack(fill="x", padx=20, pady=(16, 10))
            