"""
Sidebar — navigation tabs, tools, settings, footer links.
"""
import os
import tkinter as tk
from tkinter import ttk, messagebox

from config import DISCORD_INVITE, YOUTUBE_CHANNEL, SOURCE_CODE_URL, APP_NAME, BRAND_SHORT, LAUNCHER_VERSION, MAKER
from .theme import Pal, make_side_button, make_divider, make_section_label


class SideBar:
    def __init__(self, parent, on_tab_switch, actions):
        """
        actions: dict of callback functions:
            install_aunlocker, create_shortcut, open_folder, change_location,
            show_settings, reinstall_game, uninstall_game
        """
        self.on_tab_switch = on_tab_switch
        self.actions = actions
        self.tab_buttons = {}
        self.current_tab = "game"
        self._active_scroll_canvas = None

        width = 260
        sc = tk.Frame(parent, bg=Pal.BG_SIDEBAR, width=width)
        sc.pack(side=tk.LEFT, fill=tk.Y)
        sc.pack_propagate(False)

        # Scrollable sidebar
        self.canvas = tk.Canvas(sc, bg=Pal.BG_SIDEBAR, highlightthickness=0, width=width)
        sb = ttk.Scrollbar(sc, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=Pal.BG_SIDEBAR)
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=sb.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self.canvas.bind("<Enter>", lambda e: setattr(self, "_active_scroll_canvas", self.canvas))
        self.canvas.bind("<Leave>", lambda e: setattr(self, "_active_scroll_canvas", None))

        self._build_brand()
        self._build_nav()
        self._build_tools()
        self._build_settings()
        self._build_footer()

    def _build_brand(self):
        bf = tk.Frame(self.inner, bg=Pal.BG_SIDEBAR)
        bf.pack(fill=tk.X, padx=18, pady=(14, 4))

        tk.Label(bf, text=BRAND_SHORT, font=(Pal.FONT, 22, "bold"),
                 bg=Pal.BG_SIDEBAR, fg=Pal.TEXT).pack(anchor=tk.W)
        tk.Label(bf, text=APP_NAME, font=(Pal.FONT, 10),
                 bg=Pal.BG_SIDEBAR, fg=Pal.TEXT_DIM).pack(anchor=tk.W, pady=(1, 0))

        ver_frame = tk.Frame(bf, bg=Pal.BG_SIDEBAR)
        ver_frame.pack(anchor=tk.W, pady=(4, 0))
        tk.Label(ver_frame, text=f"v{LAUNCHER_VERSION}", font=(Pal.FONT, 9, "bold"),
                 bg=Pal.ACCENT, fg="white", padx=8, pady=2).pack(anchor=tk.W)

        make_divider(self.inner)

    def _build_nav(self):
        nf = tk.Frame(self.inner, bg=Pal.BG_SIDEBAR)
        nf.pack(fill=tk.X, padx=14, pady=6)
        for text, tid, accent in [("Game", "game", Pal.ACCENT), ("News", "news", Pal.BLUE)]:
            btn = self._make_tab(nf, text, tid, accent)
            btn.pack(fill=tk.X, pady=3)
            self.tab_buttons[tid] = btn
        make_divider(self.inner)

    def _make_tab(self, parent, text, tid, accent):
        outer = tk.Frame(parent, bg=Pal.BG_LIGHT, height=40)
        outer.pack_propagate(False)
        bar = tk.Frame(outer, bg=Pal.BG_SIDEBAR, width=3)
        bar.pack(side=tk.LEFT, fill=tk.Y)
        btn = tk.Button(
            outer, text=text, font=(Pal.FONT, 11, "bold"),
            bg=Pal.BG_LIGHT, fg=Pal.TEXT,
            activebackground=Pal.BG_LIGHT, relief=tk.FLAT, cursor="hand2",
            command=lambda: self._switch(tid),
            anchor=tk.W, padx=14, borderwidth=0,
        )
        btn.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        outer._tab_id = tid
        outer._tab_accent = accent
        outer._tab_bar = bar
        outer._tab_button = btn

        def on_enter(e):
            if self.current_tab != tid:
                for w in (outer, btn, bar):
                    w.config(bg=Pal.BG_HOVER)

        def on_leave(e):
            if self.current_tab != tid:
                outer.config(bg=Pal.BG_LIGHT)
                btn.config(bg=Pal.BG_LIGHT)
                bar.config(bg=Pal.BG_SIDEBAR)

        for w in (outer, btn):
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)
        return outer

    def _switch(self, tid):
        self.current_tab = tid
        self.on_tab_switch(tid)
        self._update_tab_visuals()

    def _update_tab_visuals(self):
        for t, btn in self.tab_buttons.items():
            accent = getattr(btn, "_tab_accent", Pal.ACCENT)
            bar = getattr(btn, "_tab_bar", None)
            button = getattr(btn, "_tab_button", None)
            if t == self.current_tab:
                btn.config(bg=accent)
                if bar:
                    bar.config(bg=Pal.TEXT_BRIGHT)
                if button:
                    button.config(bg=accent, fg=Pal.TEXT_BRIGHT, activebackground=accent)
            else:
                btn.config(bg=Pal.BG_LIGHT)
                if bar:
                    bar.config(bg=Pal.BG_SIDEBAR)
                if button:
                    button.config(bg=Pal.BG_LIGHT, fg=Pal.TEXT, activebackground=Pal.BG_LIGHT)

    def _build_tools(self):
        tf = tk.Frame(self.inner, bg=Pal.BG_SIDEBAR)
        tf.pack(fill=tk.X, padx=14, pady=6)
        make_section_label(tf, "TOOLS")
        for text, key, accent in [
            ("Install AUnlocker", "install_aunlocker", Pal.BLUE),
            ("Create Shortcut", "create_shortcut", Pal.TEXT_DIM),
            ("Open Folder", "open_folder", Pal.TEXT_DIM),
            ("Change Location", "change_location", Pal.TEXT_DIM),
        ]:
            make_side_button(tf, text, self.actions[key], accent).pack(fill=tk.X, pady=2)
        make_divider(self.inner)

    def _build_settings(self):
        sf = tk.Frame(self.inner, bg=Pal.BG_SIDEBAR)
        sf.pack(fill=tk.X, padx=14, pady=6)
        make_section_label(sf, "SETTINGS")
        for text, key, accent in [
            ("Preferences", "show_settings", Pal.GREEN),
            ("Reinstall Game", "reinstall_game", Pal.BLUE),
            ("Uninstall", "uninstall_game", Pal.RED),
        ]:
            make_side_button(sf, text, self.actions[key], accent).pack(fill=tk.X, pady=2)

    def _build_footer(self):
        footer = tk.Frame(self.canvas, bg=Pal.BG_SIDEBAR)
        footer.pack(side=tk.BOTTOM, fill=tk.X, padx=14, pady=12)
        for text, url, accent in [
            ("Discord", DISCORD_INVITE, Pal.PURPLE),
            ("YouTube", YOUTUBE_CHANNEL, Pal.RED),
            ("Source Code", SOURCE_CODE_URL, Pal.ORANGE),
        ]:
            if url:
                make_side_button(footer, text, lambda u=url: os.system(f"start {u}"), accent).pack(fill=tk.X, pady=3)
            else:
                make_side_button(footer, text + " (Coming soon)", lambda: messagebox.showinfo("Discord", "Discord server coming soon!"), accent).pack(fill=tk.X, pady=3)
        tk.Label(footer, text=f"Made by {MAKER}", font=(Pal.FONT, 8),
                 bg=Pal.BG_SIDEBAR, fg=Pal.TEXT_MUTED).pack(pady=(8, 0))

    def on_mousewheel(self, event):
        try:
            c = self._active_scroll_canvas
            if c:
                c.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except:
            pass
