"""
Settings Dialog — preferences popup with toggle switches.
"""
import tkinter as tk
from tkinter import messagebox

from .theme import Pal


class SettingsDialog:
    def __init__(self, parent, config, discord):
        self.config = config
        self.discord = discord
        self.vars = {}

        w = tk.Toplevel(parent)
        w.title("Settings")
        w.geometry("500x460")
        w.configure(bg=Pal.BG_DARK)
        w.transient(parent)
        w.resizable(False, False)
        w.update_idletasks()
        x = (w.winfo_screenwidth() - 500) // 2
        y = (w.winfo_screenheight() - 460) // 2
        w.geometry(f"500x460+{x}+{y}")

        # Header
        hd = tk.Frame(w, bg=Pal.BG_MEDIUM, height=64)
        hd.pack(fill=tk.X)
        hd.pack_propagate(False)
        tk.Label(hd, text="Settings", font=(Pal.FONT, 15, "bold"),
                 bg=Pal.BG_MEDIUM, fg=Pal.TEXT_BRIGHT).pack(anchor=tk.W, padx=24, pady=18)

        # Content
        ct = tk.Frame(w, bg=Pal.BG_DARK)
        ct.pack(fill=tk.BOTH, expand=True, padx=24, pady=12)

        settings = self.config.settings
        opts = [
            ("Auto-update game", "auto_update", "Download game updates automatically"),
            ("Discord Rich Presence", "discord_rpc", "Show activity on Discord"),
            ("Verify file integrity", "check_integrity", "Check checksums after download"),
        ]
        for label, key, desc in opts:
            self._option_row(ct, label, key, desc, settings.get(key, False))

        # Save button
        bf = tk.Frame(w, bg=Pal.BG_DARK)
        bf.pack(side=tk.BOTTOM, fill=tk.X, padx=24, pady=16)

        def save():
            for k, v in self.vars.items():
                settings[k] = v.get()
            self.config.save_settings()
            if settings.get("discord_rpc") and not self.discord.connected:
                self.discord.connect()
            elif not settings.get("discord_rpc") and self.discord.connected:
                self.discord.disconnect()
            messagebox.showinfo("Success", "Settings saved!")
            w.destroy()

        btn = tk.Button(
            bf, text="Save", font=(Pal.FONT, 11, "bold"),
            bg=Pal.GREEN, fg="white", activebackground=Pal.GREEN_HOVER,
            relief=tk.FLAT, cursor="hand2", command=save, padx=32, pady=12, bd=0,
        )
        btn.pack()
        btn.bind("<Enter>", lambda e: btn.config(bg=Pal.GREEN_HOVER))
        btn.bind("<Leave>", lambda e: btn.config(bg=Pal.GREEN))

    def _option_row(self, parent, label, key, desc, initial):
        of = tk.Frame(parent, bg=Pal.BG_MEDIUM)
        of.pack(fill=tk.X, pady=6)

        var = tk.BooleanVar(value=initial)
        self.vars[key] = var

        cf = tk.Frame(of, bg=Pal.BG_MEDIUM)
        cf.pack(fill=tk.X, padx=16, pady=14)

        tk.Checkbutton(
            cf, text=label, variable=var,
            bg=Pal.BG_MEDIUM, fg=Pal.TEXT_BRIGHT,
            selectcolor=Pal.BG_LIGHT,
            activebackground=Pal.BG_MEDIUM,
            font=(Pal.FONT, 10, "bold"), cursor="hand2",
            relief=tk.FLAT, bd=0, highlightthickness=0,
        ).pack(anchor=tk.W)

        tk.Label(cf, text=desc, font=(Pal.FONT, 8),
                 bg=Pal.BG_MEDIUM, fg=Pal.TEXT_DIM).pack(anchor=tk.W, padx=(22, 0), pady=(2, 0))

        def on_ent(e):
            of.config(bg=Pal.BG_LIGHT)
            for c in of.winfo_children():
                c.config(bg=Pal.BG_LIGHT)
                for ch in c.winfo_children():
                    try:
                        ch.config(bg=Pal.BG_LIGHT)
                    except:
                        pass

        def on_lve(e):
            of.config(bg=Pal.BG_MEDIUM)
            for c in of.winfo_children():
                c.config(bg=Pal.BG_MEDIUM)
                for ch in c.winfo_children():
                    try:
                        ch.config(bg=Pal.BG_MEDIUM)
                    except:
                        pass

        of.bind("<Enter>", on_ent)
        of.bind("<Leave>", on_lve)
