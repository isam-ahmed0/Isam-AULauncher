"""First-run Linux setup wizard (tkinter).

Mirrors the Qt SetupWizard: picks GPU and Wine build, saves choices.
"""
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import graphics
import gui_tk.theme as theme


class SetupWizard:
    def __init__(self, config, parent):
        self.config = config
        self.parent = parent
        self._gpus = graphics.detect_gpus()
        self._wines = graphics.detect_wine_binaries()

        self.win = tk.Toplevel(parent)
        self.win.title("CrewLauncher Setup")
        self.win.configure(bg=theme.BG_BASE)
        self.win.transient(parent)
        self.win.resizable(False, False)
        self.win.protocol("WM_DELETE_WINDOW", self._cancel)
        self.win.grab_set()

        body = ttk.Frame(self.win, style="Card.TFrame", padding=18)
        body.pack(fill="both", expand=True)

        ttk.Label(body, text="Finish setting up CrewLauncher", style="Heading.TLabel").pack(anchor="w")
        ttk.Separator(body, orient="horizontal").pack(fill="x", pady=10)

        desc = ttk.Label(
            body,
            text="This wizard picks the GPU and Wine build Among Us runs with.\n\nYou can change these later in Settings.",
            style="CardMuted.TLabel", wraplength=400, justify="left")
        desc.pack(anchor="w", pady=(0, 12))

        self.stack = ttk.Notebook(body)
        self.stack.pack(fill="both", expand=True)

        self._page_welcome = self._build_welcome()
        self._page_gpu = self._build_gpu()
        self._page_wine = self._build_wine()
        self._page_summary = self._build_summary()

        self.stack.add(self._page_welcome, text="Welcome")
        self.stack.add(self._page_gpu, text="GPU")
        self.stack.add(self._page_wine, text="Wine")
        self.stack.add(self._page_summary, text="Summary")

        self.stack.bind("<<NotebookTabChanged>>", self._on_tab_change)

        btn_row = ttk.Frame(body)
        btn_row.pack(fill="x", pady=(10, 0))
        self.back_btn = ttk.Button(btn_row, text="Back", command=self._back, style="Secondary.TButton")
        self.back_btn.pack(side="left")
        self.cancel_btn = ttk.Button(btn_row, text="Cancel", command=self._cancel, style="Secondary.TButton")
        self.cancel_btn.pack(side="right")
        self.next_btn = ttk.Button(btn_row, text="Next", command=self._next, style="Primary.TButton")
        self.next_btn.pack(side="right", padx=(0, 6))

        self._update_nav()

    def _build_welcome(self):
        page = ttk.Frame(self.stack, padding=6)
        if not self._gpus:
            warn = ttk.Label(page,
                text="No GPUs were detected (lspci unavailable). The game will use "
                     "your system default GPU.",
                style="CardMuted.TLabel", wraplength=400, justify="left")
            warn.pack(anchor="w")
        return page

    def _build_gpu(self):
        page = ttk.Frame(self.stack, padding=6)
        ttk.Label(page, text="Graphics card", style="CardMuted.TLabel").pack(anchor="w")
        self.gpu_var = tk.StringVar(value=self.config.get_gpu())
        self.gpu_combo = ttk.Combobox(page, state="readonly", width=42,
            values=[("System default", "")] + [(f"{g['name']}  ({'discrete' if g.get('discrete') else 'integrated'})", g['id']) for g in self._gpus])
        self.gpu_combo.pack(fill="x", pady=(2, 6))
        cur = self.config.get_gpu()
        idx = 0
        for i, g in enumerate(self._gpus):
            if g["id"] == cur:
                idx = i + 1
                break
        self.gpu_combo.current(idx)
        ttk.Label(page,
            text="The launcher sets the right PRIME / render-offload variables so "
                 "the game uses this GPU.",
            style="CardMuted.TLabel", wraplength=400, justify="left").pack(anchor="w")
        return page

    def _build_wine(self):
        page = ttk.Frame(self.stack, padding=6)
        ttk.Label(page, text="Wine build", style="CardMuted.TLabel").pack(anchor="w")
        row = ttk.Frame(page)
        row.pack(fill="x", pady=(2, 6))
        self.wine_var = tk.StringVar(value=self.config.get_wine_binary())
        self.wine_combo = ttk.Combobox(row, state="readonly", width=30,
            values=["Auto-detect"] + [f"{w['name']} — {w['path']}" for w in self._wines])
        self.wine_combo.pack(side="left", fill="x", expand=True)
        cur = self.config.get_wine_binary()
        idx = 0
        for i, w in enumerate(self._wines):
            if w["path"] == cur:
                idx = i + 1
                break
        self.wine_combo.current(idx)
        browse = ttk.Button(row, text="Browse…", command=self._browse_wine, style="Secondary.TButton")
        browse.pack(side="left", padx=(6, 0))
        if not self._wines:
            ttk.Label(page,
                text="Wine was not found on this system. Install Wine, or browse to "
                     "a Wine / Proton-GE build.",
                style="CardMuted.TLabel", wraplength=400, justify="left").pack(anchor="w")
        ttk.Label(page, text=f"Prefix: {self.config.get_wine_prefix()}",
            style="CardMuted.TLabel", wraplength=400).pack(anchor="w")
        return page

    def _build_summary(self):
        page = ttk.Frame(self.stack, padding=6)
        ttk.Label(page, text="Summary", style="CardMuted.TLabel").pack(anchor="w")
        self.summary_lbl = ttk.Label(page, text="", style="Card.TLabel",
            wraplength=400, justify="left")
        self.summary_lbl.pack(anchor="w", pady=(2, 8))
        test = ttk.Button(page, text="Test Wine", command=self._test_wine, style="Secondary.TButton")
        test.pack(anchor="w")
        return page

    def _on_tab_change(self, _e):
        if self.stack.index("current") == 3:
            self.summary_lbl.configure(text=self._summary_text())
        self._update_nav()

    def _update_nav(self):
        idx = self.stack.index("current")
        self.back_btn.configure(state="normal" if idx > 0 else "disabled")
        self.next_btn.configure(text="Finish" if idx == 3 else "Next")

    def _back(self):
        idx = self.stack.index("current")
        if idx > 0:
            self.stack.select(idx - 1)

    def _next(self):
        idx = self.stack.index("current")
        if idx == 3:
            self._finish()
            return
        self.stack.select(idx + 1)

    def _selected_gpu(self):
        idx = self.gpu_combo.current()
        if idx <= 0:
            return ""
        return self._gpus[idx - 1]["id"]

    def _selected_wine(self):
        idx = self.wine_combo.current()
        if idx <= 0:
            return ""
        return self._wines[idx - 1]["path"]

    def _summary_text(self):
        gpu = graphics.describe_gpu(self._selected_gpu(), self._gpus)
        wine = self._selected_wine() or graphics.resolve_wine() or "Not found"
        return f"GPU: {gpu}\nWine: {wine}\nPrefix: {self.config.get_wine_prefix()}"

    def _browse_wine(self):
        start = "/usr/bin" if __import__("pathlib").Path("/usr/bin").is_dir() else str(__import__("pathlib").Path.home())
        path = filedialog.askopenfilename(
            title="Select the Wine executable", initialdir=start,
            parent=self.win)
        if path:
            self.wine_combo.set(path)

    def _test_wine(self):
        wine = self._selected_wine() or graphics.resolve_wine()
        if not wine:
            messagebox.showwarning("Wine not found", "No Wine binary is selected.", parent=self.win)
            return
        try:
            from platform_utils import external_env
            out = subprocess.run(
                [wine, "--version"], capture_output=True, text=True,
                timeout=15, env=external_env())
            text = (out.stdout or out.stderr or "").strip() or "No output"
            messagebox.showinfo("Wine test", text, parent=self.win)
        except Exception as e:
            messagebox.showwarning("Wine test failed", str(e), parent=self.win)

    def _finish(self):
        self.config.set_gpu(self._selected_gpu())
        self.config.set_wine_binary(self._selected_wine())
        self.config.set_linux_setup_complete(True)
        self.win.destroy()

    def _cancel(self):
        self.win.destroy()