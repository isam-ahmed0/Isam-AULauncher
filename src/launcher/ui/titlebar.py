"""
Titlebar — borderless window title bar with animated accent strip.
"""
import tkinter as tk
from .theme import Pal, HueAnimator, make_title_button


class TitleBar:
    def __init__(self, parent, root, on_close):
        self.root = root
        self._drag_x = 0
        self._drag_y = 0

        self.frame = tk.Frame(parent, bg=Pal.BG_DARK, height=Pal.TITLEBAR_H)
        self.frame.pack(fill=tk.X, side=tk.TOP)
        self.frame.pack_propagate(False)

        # Animated accent strip at the very top
        self._strip = tk.Canvas(self.frame, height=3, bg=Pal.BG_DARK, highlightthickness=0)
        self._strip.pack(fill=tk.X, side=tk.TOP)
        self._animator = HueAnimator(self._strip, height=3, speed=0.4)

        # Content row
        row = tk.Frame(self.frame, bg=Pal.BG_DARK)
        row.pack(fill=tk.BOTH, expand=True, padx=10, pady=0)

        # Brand mark
        tk.Label(
            row, text="ISAM AU", font=(Pal.FONT, 11, "bold"),
            bg=Pal.BG_DARK, fg=Pal.ACCENT,
        ).pack(side=tk.LEFT, padx=(2, 8))

        tk.Label(
            row, text="v0.1", font=(Pal.FONT, 8),
            bg=Pal.BG_DARK, fg=Pal.TEXT_MUTED,
        ).pack(side=tk.LEFT)

        # Window controls — close only
        make_title_button(row, "\u00d7", on_close, Pal.RED, font_size=14)

        # Drag bindings
        for w in (self.frame, row):
            w.bind("<ButtonPress-1>", self._start_move)
            w.bind("<B1-Motion>", self._do_move)

    def start_animation(self):
        self._animator.start()

    def stop_animation(self):
        self._animator.stop()

    def _start_move(self, e):
        self._drag_x = e.x_root - self.root.winfo_x()
        self._drag_y = e.y_root - self.root.winfo_y()

    def _do_move(self, e):
        x = e.x_root - self._drag_x
        y = e.y_root - self._drag_y
        self.root.geometry(f"+{x}+{y}")
