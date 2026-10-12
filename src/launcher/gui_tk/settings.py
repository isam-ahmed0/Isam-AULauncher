"""Lite settings dialog (tkinter).

Saves directly through the shared ``Config`` (same config.json as the Qt GUI),
so both front-ends see identical settings.
"""
import tkinter as tk
from tkinter import ttk

from file_manager import FileManager
from platform_utils import IS_LINUX, find_lutris
import gui_tk.theme as theme


class SettingsDialog:
    def __init__(self, parent, app):
        self.app = app
        self.config = app.config
        self.settings = self.config.settings
        self._app_profile_hook = getattr(app, "_profile_hook", None)
        app._profile_hook = self._on_profile

        self.win = tk.Toplevel(parent)
        self.win.title("Settings")
        self.win.configure(bg=theme.BG_BASE)
        self.win.transient(parent)
        self.win.resizable(False, False)
        self.win.protocol("WM_DELETE_WINDOW", self._close)

        body = ttk.Frame(self.win, style="Card.TFrame", padding=18)
        body.pack(fill="both", expand=True, padx=0, pady=0)

        ttk.Label(body, text="Settings", style="Heading.TLabel").pack(anchor="w")
        ttk.Separator(body, orient="horizontal").pack(fill="x", pady=10)

        # --- General ---
        self.var_rpc = tk.BooleanVar(value=bool(self.settings.get("discord_rpc", True)))
        ttk.Checkbutton(
            body, text="Discord Rich Presence", variable=self.var_rpc,
            command=lambda: self._save("discord_rpc", self.var_rpc.get()),
        ).pack(anchor="w")
        ttk.Label(body, text="Show your activity on Discord",
                  style="CardMuted.TLabel").pack(anchor="w", padx=(22, 0))

        self.var_auto = tk.BooleanVar(value=bool(self.settings.get("auto_update", True)))
        ttk.Checkbutton(
            body, text="Auto-update game", variable=self.var_auto,
            command=lambda: self._save("auto_update", self.var_auto.get()),
        ).pack(anchor="w", pady=(8, 0))
        ttk.Label(body, text="Download game updates automatically",
                  style="CardMuted.TLabel").pack(anchor="w", padx=(22, 0))

        # --- Linux ---
        if IS_LINUX:
            ttk.Separator(body, orient="horizontal").pack(fill="x", pady=10)
            ttk.Label(body, text="Linux", style="Heading.TLabel").pack(anchor="w")

            row = ttk.Frame(body, style="Card.TFrame")
            row.pack(fill="x", pady=(6, 0))
            ttk.Label(row, text="Launch method", style="CardMuted.TLabel").pack(side="left")
            self.var_method = tk.StringVar(value=self.settings.get("launch_method", "ask"))
            combo = ttk.Combobox(
                row, state="readonly", width=18, values=[
                    "Ask every time", "Always use Lutris", "Always use Wine",
                ],
            )
            labels = {"ask": "Ask every time", "lutris": "Always use Lutris",
                      "wine": "Always use Wine"}
            combo.set(labels.get(self.var_method.get(), "Ask every time"))
            combo.pack(side="right")
            combo.bind("<<ComboboxSelected>>", lambda _e: self._save_method(combo.get()))

            self.var_warn = tk.BooleanVar(value=bool(self.settings.get("warn_plain_wine", True)))
            ttk.Checkbutton(
                body, text="Warn before launching with plain Wine",
                variable=self.var_warn,
                command=lambda: self._save("warn_plain_wine", self.var_warn.get()),
            ).pack(anchor="w", pady=(8, 0))

            pf = self.config.get_wine_prefix()
            ttk.Label(body, text=f"Wine prefix: {pf}",
                      style="CardMuted.TLabel", wraplength=380).pack(anchor="w", pady=(8, 0))

            detected = self.config.get_lutris_cmd_override() or find_lutris()
            lutris_txt = " ".join(detected) if detected else "Not found (auto)"
            ttk.Label(body, text=f"Lutris: {lutris_txt}",
                      style="CardMuted.TLabel", wraplength=380).pack(anchor="w")

        # --- Account ---
        ttk.Separator(body, orient="horizontal").pack(fill="x", pady=10)
        ttk.Label(body, text="Account", style="Heading.TLabel").pack(anchor="w")
        self.acc_lbl = ttk.Label(body, text=self._account_text(),
                                 style="CardMuted.TLabel", wraplength=380, justify="left")
        self.acc_lbl.pack(anchor="w")
        ttk.Button(body, text="Sign in with itch.io", style="Primary.TButton",
                   command=self._sign_in).pack(anchor="w", pady=(6, 0))

        # --- Game info ---
        ttk.Separator(body, orient="horizontal").pack(fill="x", pady=10)
        ttk.Label(body, text="Game Info", style="Heading.TLabel").pack(anchor="w")
        for label, value in self._game_info():
            row = ttk.Frame(body, style="Card.TFrame")
            row.pack(fill="x", pady=1)
            ttk.Label(row, text=label, style="CardMuted.TLabel", width=13).pack(side="left")
            val = ttk.Label(row, text=value, style="Card.TLabel", wraplength=300, justify="left")
            val.pack(side="left", fill="x", expand=True)

        ttk.Button(body, text="Close", command=self._close).pack(
            anchor="e", pady=(16, 0))
        self.win.bind("<Escape>", lambda _e: self._close())

    # ------------------------------------------------------------------ helpers
    def _game_info(self):
        gp = self.config.get_game_path()
        version = self.config.get_version() or "Not installed"
        install_path = str(gp) if gp else "Not set"
        bep = "Not installed"
        size = "N/A"
        if gp and gp.exists():
            if (gp / "BepInEx" / "core" / "BepInEx.dll").exists():
                bep = "Installed"
            try:
                total = sum(f.stat().st_size for f in gp.rglob("*") if f.is_file())
                size = FileManager.format_size(total)
            except Exception:
                size = "Unknown"
        rows = [
            ("Version:", version),
            ("Install Path:", install_path),
            ("BepInEx:", bep),
            ("Disk Usage:", size),
        ]
        if IS_LINUX:
            from platform_utils import format_lutris_entry
            entry = self.config.get_lutris_entry(gp) if gp else None
            rows.append(("Lutris:", format_lutris_entry(entry) if gp else "Not added"))
        return rows

    def _save(self, key, value):
        self.settings[key] = value
        self.config.save_settings()
        if key == "discord_rpc":
            self.app.apply_discord_rpc()

    def _save_method(self, label):
        mapping = {
            "Ask every time": "ask",
            "Always use Lutris": "lutris",
            "Always use Wine": "wine",
        }
        self._save("launch_method", mapping.get(label, "ask"))

    def _sign_in(self):
        from gui_tk.login import LoginDialog
        LoginDialog(
            self.win,
            ui=self.app.ui,
            prefix=self.config.get_wine_prefix(),
            on_success=self._on_sign_in_success,
        )

    def _account_text(self):
        profile = getattr(self.app, "_profile", {}) or {}
        if profile.get("token") and profile.get("username"):
            return f"Signed in as {profile['username']}."
        if profile.get("token"):
            return "Signed in."
        return "Sign in so Among Us can play online."

    def _on_profile(self, profile):
        try:
            self.acc_lbl.configure(text=self._account_text())
        except Exception:
            pass

    def _on_sign_in_success(self):
        app_profile = {"token": True, "username": None, "among_us_name": None, "platforms": []}
        try:
            self.app._profile = app_profile
            self.acc_lbl.configure(text="Signed in.")
        except Exception:
            pass
        self.app._on_sign_in_success()

    def _close(self):
        self.app._profile_hook = self._app_profile_hook
        try:
            self.win.destroy()
        except Exception:
            pass
