"""
News Tab — patches feed with styled cards.
"""
import os
import tkinter as tk
from tkinter import ttk
import logging
import xml.etree.ElementTree as ET

from config import PATCHES_URL, APP_NAME, LAUNCHER_VERSION
from .theme import Pal, cached_multistop_gradient


class NewsTab:
    def __init__(self, parent, network):
        self.network = network
        self.frame = tk.Frame(parent, bg=Pal.BG_DARK)
        self._patches_frame = None
        self._patches_canvas = None
        self._active_scroll_canvas = None
        self._built = False
        self._build()

    def _build(self):
        self._build_hero()
        self._build_patches_container()

    def _build_hero(self):
        c = tk.Canvas(self.frame, height=130, bg=Pal.BG_DARK, highlightthickness=0)
        c.pack(fill=tk.X)

        def draw(evt=None):
            c.delete("all")
            w = max(c.winfo_width(), 60)
            h = c.winfo_height()
            photo = cached_multistop_gradient(w, h, [
                (0.0, "#0f1a30"),
                (0.4, "#1a1040"),
                (1.0, "#0c0e14"),
            ])
            c.create_image(0, 0, image=photo, anchor="nw")
            # Decorative shapes
            for cx, cy, rad, col in [
                (w - 100, h // 2 + 10, 50, "#3b82f610"),
                (60, h - 10, 70, "#a855f708"),
            ]:
                c.create_ellipse(cx - rad, cy - rad, cx + rad, cy + rad,
                                 fill="", outline=col, width=2)
            c.create_text(30, h // 2 - 14, text="Game Updates & News",
                          font=(Pal.FONT, 22, "bold"), fill=Pal.TEXT_BRIGHT, anchor="w")
            c.create_text(30, h // 2 + 14,
                          text="Stay up to date with the latest patches and updates",
                          font=(Pal.FONT, 10), fill=Pal.TEXT_DIM, anchor="w")
            chip = f"v{LAUNCHER_VERSION}"
            c.create_rectangle(w - 110, 14, w - 20, 40, fill=Pal.SHADOW, outline=Pal.BORDER)
            c.create_text(w - 65, 27, text=chip,
                          font=(Pal.FONT, 10, "bold"), fill=Pal.ACCENT_2, anchor="center")

        c.bind("<Configure>", draw)
        draw()

    def _build_patches_container(self):
        pc = tk.Frame(self.frame, bg=Pal.BG_DARK)
        pc.pack(fill=tk.BOTH, expand=True, padx=20, pady=6)

        c = tk.Canvas(pc, bg=Pal.BG_DARK, highlightthickness=0)
        sb = ttk.Scrollbar(pc, orient="vertical", command=c.yview)
        self._patches_frame = tk.Frame(c, bg=Pal.BG_DARK)
        self._patches_frame.bind("<Configure>", lambda e: c.configure(scrollregion=c.bbox("all")))
        c.create_window((0, 0), window=self._patches_frame, anchor="nw", width=1)
        c.configure(yscrollcommand=sb.set)
        c.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        c.bind("<Enter>", lambda e: setattr(self, "_active_scroll_canvas", c))
        c.bind("<Leave>", lambda e: setattr(self, "_active_scroll_canvas", None))
        c.bind("<Configure>", lambda e: c.itemconfigure(1, width=e.width - 10))
        self._patches_canvas = c

    def load_patches(self):
        if self._built:
            return
        self._built = True

        def go():
            try:
                for w in self._patches_frame.winfo_children():
                    w.destroy()
                xml = self.network.fetch_text(PATCHES_URL)
                if not xml:
                    self._patch_err("Failed to load patches")
                    return
                patches = ET.fromstring(xml).findall(".//patch")
                if not patches:
                    self._patch_err("No patches found")
                    return
                colors = [Pal.BLUE, Pal.PURPLE, Pal.GREEN, Pal.ORANGE]
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
                logging.error(f"Patches: {e}")
                self._patch_err(str(e))

        import threading
        threading.Thread(target=go, daemon=True).start()

    def _patch_card(self, title, desc, link, accent):
        card = tk.Frame(self._patches_frame, bg=Pal.BG_CARD,
                        highlightbackground=Pal.BORDER, highlightthickness=1)
        card.pack(fill=tk.X, padx=8, pady=8)

        # Left accent bar
        tk.Frame(card, bg=accent, width=4).pack(side=tk.LEFT, fill=tk.Y)

        ct = tk.Frame(card, bg=Pal.BG_CARD)
        ct.pack(fill=tk.BOTH, padx=18, pady=14)

        tr = tk.Frame(ct, bg=Pal.BG_CARD)
        tr.pack(fill=tk.X, pady=(0, 8))
        tk.Label(tr, text=title, font=(Pal.FONT, 11, "bold"),
                 bg=accent, fg="white", padx=12, pady=4).pack(side=tk.LEFT, padx=(0, 10))
        tk.Label(tr, text=f"{APP_NAME} Update", font=(Pal.FONT, 9),
                 bg=Pal.BG_CARD, fg=Pal.TEXT_MUTED).pack(side=tk.LEFT)

        tk.Label(ct, text=desc, font=(Pal.FONT, 10), bg=Pal.BG_CARD,
                 fg=Pal.TEXT, wraplength=660, justify=tk.LEFT).pack(anchor=tk.W, pady=(0, 10))

        if link and link.strip():
            b = tk.Button(
                ct, text="Read More", font=(Pal.FONT, 9, "bold"),
                bg=Pal.BG_LIGHT, fg=accent,
                activebackground=accent, activeforeground="white",
                relief=tk.FLAT, cursor="hand2",
                command=lambda: os.system(f"start {link}"),
                padx=16, pady=6, bd=0,
            )
            b.pack(anchor=tk.W)
            b.bind("<Enter>", lambda e, b=b, c=accent: b.config(bg=c, fg="white"))
            b.bind("<Leave>", lambda e, b=b, c=accent: b.config(bg=Pal.BG_LIGHT, fg=c))

    def _patch_err(self, msg):
        f = tk.Frame(self._patches_frame, bg=Pal.BG_DARK)
        f.pack(fill=tk.BOTH, expand=True, padx=20, pady=40)
        tk.Label(f, text="No connection", font=(Pal.FONT, 18, "bold"),
                 bg=Pal.BG_DARK, fg=Pal.RED).pack(pady=16)
        tk.Label(f, text=msg, font=(Pal.FONT, 11),
                 bg=Pal.BG_DARK, fg=Pal.TEXT_DIM).pack()

    def pack(self, **kw):
        self.frame.pack(**kw)

    def pack_forget(self):
        self.frame.pack_forget()

    def on_mousewheel(self, event):
        try:
            c = self._active_scroll_canvas
            if c:
                c.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except:
            pass
