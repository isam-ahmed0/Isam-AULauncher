"""Lite settings dialog (tkinter).

Saves directly through the shared ``Config`` (same config.json as the Qt GUI),
so both front-ends see identical settings.
"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from file_manager import FileManager
from platform_utils import IS_LINUX, open_local_path
import graphics
import ui_registry
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

        # --- Interface ---
        ttk.Separator(body, orient="horizontal").pack(fill="x", pady=10)
        ttk.Label(body, text="Interface", style="Heading.TLabel").pack(anchor="w")

        self._guis = ui_registry.list_guis(self.config)
        irow = ttk.Frame(body, style="Card.TFrame")
        irow.pack(fill="x", pady=(6, 0))
        ttk.Label(irow, text="User interface", style="CardMuted.TLabel").pack(side="left")
        self.ui_combo = ttk.Combobox(
            irow, state="readonly", width=30, values=self._gui_labels())
        self.ui_combo.pack(side="right")
        self.ui_combo.current(self._gui_index(self.config.get_ui_mode()))
        self.ui_combo.bind("<<ComboboxSelected>>", lambda _e: self._save_ui_mode())

        if IS_LINUX:
            drow = ttk.Frame(body, style="Card.TFrame")
            drow.pack(fill="x", pady=(6, 0))
            ttk.Label(drow, text="Display backend", style="CardMuted.TLabel").pack(side="left")
            self.disp_combo = ttk.Combobox(
                drow, state="readonly", width=30,
                values=["Auto (recommended)", "X11 (xcb)", "Wayland"])
            self.disp_combo.pack(side="right")
            self.disp_combo.current(self._display_index(self.config.get_display_backend()))
            self.disp_combo.bind("<<ComboboxSelected>>", lambda _e: self._save_display_backend())

        ttk.Label(body, text="Changing the interface or display backend needs a restart.",
                  style="CardMuted.TLabel").pack(anchor="w", pady=(2, 6))

        uirow = ttk.Frame(body, style="Card.TFrame")
        uirow.pack(fill="x")
        ttk.Button(uirow, text="Open GUI folder", style="Secondary.TButton",
                   command=self._open_guis_folder).pack(side="left")
        ttk.Button(uirow, text="Create Custom GUI...", style="Secondary.TButton",
                   command=self._create_custom_gui).pack(side="left", padx=(6, 0))
        ttk.Button(uirow, text="Edit Custom GUI", style="Secondary.TButton",
                   command=self._edit_custom_gui).pack(side="left", padx=(6, 0))
        ttk.Button(uirow, text="Restart now", style="Secondary.TButton",
                   command=self._restart_now).pack(side="right")

        # --- Linux ---
        if IS_LINUX:
            self._gpus = graphics.detect_gpus()
            self._wines = graphics.detect_wine_binaries()

            ttk.Separator(body, orient="horizontal").pack(fill="x", pady=10)
            ttk.Label(body, text="Graphics", style="Heading.TLabel").pack(anchor="w")

            row = ttk.Frame(body, style="Card.TFrame")
            row.pack(fill="x", pady=(6, 0))
            ttk.Label(row, text="GPU", style="CardMuted.TLabel").pack(side="left")
            self.gpu_var = tk.StringVar(value=self.config.get_gpu())
            self.gpu_combo = ttk.Combobox(
                row, state="readonly", width=30,
                values=[("System default", "")] + [(f"{g['name']}  ({'discrete' if g.get('discrete') else 'integrated'})", g['id']) for g in self._gpus])
            self.gpu_combo.pack(side="right")
            idx = 0
            for i, g in enumerate(self._gpus):
                if g["id"] == self.config.get_gpu():
                    idx = i + 1
                    break
            self.gpu_combo.current(idx)
            self.gpu_combo.bind("<<ComboboxSelected>>", lambda _e: self._save("gpu_id", self.gpu_var.get()))

            ttk.Label(body,
                text="The launcher sets PRIME / render-offload variables so the game "
                     "runs on the selected GPU.",
                style="CardMuted.TLabel", wraplength=380, justify="left").pack(anchor="w", pady=(2, 8))

            setup_row = ttk.Frame(body, style="Card.TFrame")
            setup_row.pack(fill="x")
            ttk.Button(setup_row, text="Re-run setup wizard", command=self._open_setup_wizard,
                style="Secondary.TButton").pack(side="left")

            ttk.Separator(body, orient="horizontal").pack(fill="x", pady=10)
            ttk.Label(body, text="Wine", style="Heading.TLabel").pack(anchor="w")

            wrow = ttk.Frame(body, style="Card.TFrame")
            wrow.pack(fill="x", pady=(6, 0))
            ttk.Label(wrow, text="Wine build", style="CardMuted.TLabel").pack(side="left")
            self.wine_combo = ttk.Combobox(
                wrow, state="readonly", width=30,
                values=["Auto-detect"] + [f"{w['name']} — {w['path']}" for w in self._wines])
            self.wine_combo.pack(side="left", fill="x", expand=True)
            cur = self.config.get_wine_binary()
            idx = 0
            for i, w in enumerate(self._wines):
                if w["path"] == cur:
                    idx = i + 1
                    break
            self.wine_combo.current(idx)
            self.wine_combo.bind("<<ComboboxSelected>>", lambda _e: self._save_wine())

            ttk.Label(body, text=f"Wine prefix: {self.config.get_wine_prefix()}",
                style="CardMuted.TLabel", wraplength=380).pack(anchor="w", pady=(8, 0))

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
            gpu = graphics.describe_gpu(self.config.get_gpu())
            wine = self.config.get_wine_binary() or graphics.resolve_wine() or "Not found"
            rows.append(("GPU:", gpu))
            rows.append(("Wine:", wine))
        return rows

    def _save(self, key, value):
        self.settings[key] = value
        self.config.save_settings()
        if key == "discord_rpc":
            self.app.apply_discord_rpc()

    # ------------------------------------------------------------------ interface
    def _gui_labels(self):
        labels = []
        for g in self._guis:
            label = g["name"]
            if not g.get("available", True):
                label += f"  (unavailable: {g.get('reason') or 'missing modules'})"
            labels.append(label)
        return labels

    def _gui_index(self, mode):
        for i, g in enumerate(self._guis):
            if g["id"] == mode:
                return i
        return 0

    def _save_ui_mode(self):
        idx = self.ui_combo.current()
        if 0 <= idx < len(self._guis):
            self.config.set_ui_mode(self._guis[idx]["id"])

    def _display_index(self, value):
        return {"": 0, "x11": 1, "wayland": 2}.get(value, 0)

    def _save_display_backend(self):
        values = ["", "x11", "wayland"]
        idx = self.disp_combo.current()
        self.config.set_display_backend(values[idx] if 0 <= idx < len(values) else "")

    def _refresh_guis(self):
        self._guis = ui_registry.list_guis(self.config)
        self.ui_combo.configure(values=self._gui_labels())
        self.ui_combo.current(self._gui_index(self.config.get_ui_mode()))

    def _open_guis_folder(self):
        try:
            open_local_path(self.config.guis_dir)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self.win)

    def _create_custom_gui(self):
        templates = ui_registry.custom_gui_templates()
        options = [(t["id"], f"{t['name']} — {t['description']}", "Secondary.TButton")
                   for t in templates]
        chooser = getattr(self.app, "_choose", None)
        template_id = "launcher"
        if chooser:
            picked = chooser("Create Custom GUI", "Pick a starter template:", options)
            if not picked:
                return
            template_id = picked
        name = simpledialog.askstring(
            "Create Custom GUI", "Name for your GUI:", parent=self.win)
        if not name:
            return
        try:
            path = ui_registry.create_custom_gui(self.config, name, template_id)
        except FileExistsError:
            messagebox.showwarning(
                "Create Custom GUI", "A GUI with that name already exists.",
                parent=self.win)
            return
        except Exception as e:
            messagebox.showerror("Create Custom GUI", str(e), parent=self.win)
            return
        self._refresh_guis()
        idx = self._gui_index(f"custom:{path.stem}")
        if 0 <= idx < len(self._guis):
            self.ui_combo.current(idx)
            self._save_ui_mode()
        messagebox.showinfo(
            "Create Custom GUI",
            f"Created:\n{path}\n\n"
            "It is now selected. Use \"Edit Custom GUI\" to open it in your\n"
            "editor, then press \"Restart now\" to apply.",
            parent=self.win)

    def _edit_custom_gui(self):
        mode = self.config.get_ui_mode()
        path = None
        if mode.startswith("custom:"):
            path = ui_registry.custom_gui_path(self.config, mode.split(":", 1)[1])
        if not path:
            messagebox.showinfo(
                "Edit Custom GUI",
                "Select one of your custom GUIs in the dropdown first,\n"
                "or create a new one.",
                parent=self.win)
            return
        try:
            open_local_path(path)
        except Exception as e:
            messagebox.showerror("Edit Custom GUI", str(e), parent=self.win)

    def _restart_now(self):
        if not messagebox.askyesno(
                "Restart Launcher",
                "Close and restart the launcher now to apply the changes?",
                parent=self.win, default="yes"):
            return
        import app_restart
        try:
            app_restart.restart()
        except Exception as e:
            messagebox.showerror("Restart Launcher", str(e), parent=self.win)

    def _save_wine(self):
        idx = self.wine_combo.current()
        if idx <= 0:
            self._save("wine_binary", "")
        else:
            self._save("wine_binary", self._wines[idx - 1]["path"])

    def _open_setup_wizard(self):
        from gui_tk.setup_wizard import SetupWizard
        dlg = SetupWizard(self.config, self.win)
        self._gpus = graphics.detect_gpus()
        self._wines = graphics.detect_wine_binaries()

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
