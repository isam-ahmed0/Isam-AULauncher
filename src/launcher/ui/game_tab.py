"""
Game Tab — hero banner, version cards, action buttons, progress bar, status.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

from config import LAUNCHER_VERSION, VERSION_URL, GITHUB_REPO
from network import GameVersion
from file_manager import FileManager
from .theme import Pal, cached_gradient, cached_multistop_gradient, make_action_button, setup_ttk_styles


class GameTab:
    def __init__(self, parent, app):
        """
        app: reference to the LaunchWindow (for callbacks).
        """
        self.app = app
        self.frame = tk.Frame(parent, bg=Pal.BG_DARK)
        self._hero_canvas = None
        self._build()

    def _build(self):
        self._build_hero()
        self._build_version_cards()
        self._build_actions()
        self._build_progress()
        self._build_status()
        self._build_kebab()

    # ------------------------------------------------------------------ hero
    def _build_hero(self):
        c = tk.Canvas(self.frame, height=150, bg=Pal.BG_DARK, highlightthickness=0)
        c.pack(fill=tk.X, pady=(0, 0))
        self._hero_canvas = c

        def draw(evt=None):
            c.delete("all")
            w = max(c.winfo_width(), 60)
            h = c.winfo_height()
            photo = cached_multistop_gradient(w, h, [
                (0.0, "#1a1040"),
                (0.3, "#0f1a30"),
                (0.7, "#0c1220"),
                (1.0, "#0c0e14"),
            ])
            c.create_image(0, 0, image=photo, anchor="nw")
            # Decorative circles
            for cx, cy, rad, col in [
                (w - 120, h // 2, 60, "#8b5cf610"),
                (w - 60, h // 2 - 20, 30, "#06b6d410"),
                (80, h + 20, 90, "#8b5cf608"),
            ]:
                c.create_ellipse(cx - rad, cy - rad, cx + rad, cy + rad,
                                 fill="", outline=col, width=2)
            # Title
            c.create_text(30, h // 2 - 18, text="Game Management",
                          font=(Pal.FONT, 24, "bold"), fill=Pal.TEXT_BRIGHT, anchor="w")
            c.create_text(30, h // 2 + 14,
                          text="Install, update, and manage your Among Us installation",
                          font=(Pal.FONT, 10), fill=Pal.TEXT_DIM, anchor="w")
            # Version chip
            chip_text = f"v{LAUNCHER_VERSION}"
            c.create_rectangle(w - 110, 14, w - 20, 40, fill=Pal.SHADOW, outline=Pal.BORDER)
            c.create_text(w - 65, 27, text=chip_text,
                          font=(Pal.FONT, 10, "bold"), fill=Pal.ACCENT_2, anchor="center")

        c.bind("<Configure>", draw)
        draw()

    # ------------------------------------------------------------------ version cards
    def _build_version_cards(self):
        ir = tk.Frame(self.frame, bg=Pal.BG_DARK)
        ir.pack(fill=tk.X, padx=28, pady=6)
        ir.grid_columnconfigure(0, weight=1)
        ir.grid_columnconfigure(1, weight=1)

        self.current_version = self.app.current_version
        self.latest_version = self.app.latest_version

        self._ver_card(ir, 0, "INSTALLED", self.current_version, Pal.GREEN)
        self._ver_card(ir, 1, "LATEST", self.latest_version, Pal.BLUE)

    def _ver_card(self, parent, col, label, var, accent):
        card = tk.Frame(parent, bg=Pal.BG_CARD, highlightbackground=Pal.BORDER, highlightthickness=1)
        card.grid(row=0, column=col, padx=10, pady=8, sticky="nsew")
        # Gradient top accent
        tk.Frame(card, bg=accent, height=3).pack(fill=tk.X)
        inner = tk.Frame(card, bg=Pal.BG_CARD)
        inner.pack(fill=tk.BOTH, padx=24, pady=16)
        tk.Label(inner, text=label, font=(Pal.FONT, 9, "bold"),
                 bg=Pal.BG_CARD, fg=Pal.TEXT_MUTED).pack(anchor=tk.W)
        tk.Label(inner, textvariable=var, font=(Pal.FONT, 22, "bold"),
                 bg=Pal.BG_CARD, fg=accent).pack(anchor=tk.W, pady=(4, 0))

    # ------------------------------------------------------------------ actions
    def _build_actions(self):
        af = tk.Frame(self.frame, bg=Pal.BG_DARK)
        af.pack(pady=16)

        self.main_button = make_action_button(
            af, "INSTALL GAME", self.app.main_action,
            Pal.GREEN, Pal.GREEN_HOVER, font_size=12, wide=True,
        )
        self.main_button.grid(row=0, column=0, padx=8)

        make_action_button(
            af, "Check Updates", self.app.check_updates,
            Pal.BG_LIGHT, Pal.BLUE, font_size=10,
        ).grid(row=0, column=1, padx=8)

        make_action_button(
            af, "Install Specific", self.app.install_specific,
            Pal.BG_LIGHT, Pal.PURPLE, font_size=10,
        ).grid(row=0, column=2, padx=8)

    # ------------------------------------------------------------------ progress
    def _build_progress(self):
        pc = tk.Frame(self.frame, bg=Pal.BG_DARK)
        pc.pack(fill=tk.X, padx=60, pady=4)

        pb = tk.Frame(pc, bg=Pal.BG_MEDIUM, height=8)
        pb.pack(fill=tk.X)
        setup_ttk_styles()
        self.progress_bar = ttk.Progressbar(
            pb, variable=self.app.progress_var,
            maximum=100, mode="determinate",
            style="Custom.Horizontal.TProgressbar",
        )
        self.progress_bar.pack(fill=tk.BOTH, expand=True)

    # ------------------------------------------------------------------ status
    def _build_status(self):
        sf = tk.Frame(self.frame, bg=Pal.BG_DARK)
        sf.pack(pady=(8, 0))
        self.status_icon = tk.Label(sf, text="\u25cf", font=(Pal.FONT, 12),
                                    bg=Pal.BG_DARK, fg=Pal.GREEN)
        self.status_icon.pack(side=tk.LEFT, padx=(0, 8))
        tk.Label(sf, textvariable=self.app.status_text, font=(Pal.FONT, 10),
                 bg=Pal.BG_DARK, fg=Pal.TEXT_DIM).pack(side=tk.LEFT)

    # ------------------------------------------------------------------ kebab
    def _build_kebab(self):
        bb = tk.Frame(self.frame, bg=Pal.BG_DARK)
        bb.pack(side=tk.BOTTOM, anchor=tk.SE, padx=25, pady=14)
        make_action_button(bb, "\u2026", self.app.show_kebab_menu,
                           Pal.BG_LIGHT, Pal.BG_HOVER, font_size=12).pack()

    def pack(self, **kw):
        self.frame.pack(**kw)

    def pack_forget(self):
        self.frame.pack_forget()
