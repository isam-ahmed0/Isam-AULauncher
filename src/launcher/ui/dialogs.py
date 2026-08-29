"""
Dialogs — about, kebab menu, install specific version, verify results.
"""
import os
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

from config import APP_NAME, LAUNCHER_VERSION, MAKER
from file_manager import FileManager
from .theme import Pal, make_action_button


class KebabMenu:
    """Right-click / overflow menu."""

    def __init__(self, root, app):
        self.root = root
        self.app = app

    def show(self):
        m = tk.Menu(self.root, tearoff=0, bg=Pal.BG_LIGHT, fg=Pal.TEXT_BRIGHT,
                     activebackground=Pal.ACCENT, activeforeground="white",
                     relief=tk.FLAT, font=(Pal.FONT, 10))
        m.add_command(label="Verify Game Files", command=self.app.verify_files)
        m.add_command(label="View Logs", command=self._view_logs)
        m.add_separator()
        m.add_command(label="About", command=self._show_about)
        try:
            m.tk_popup(self.root.winfo_pointerx(), self.root.winfo_pointery())
        finally:
            m.grab_release()

    def _view_logs(self):
        lf = Path("launcher.log")
        if lf.exists():
            os.startfile(lf)
        else:
            messagebox.showinfo("Info", "No log file found")

    def _show_about(self):
        messagebox.showinfo(
            "About",
            f"{APP_NAME} v{LAUNCHER_VERSION}\n\n"
            f"Made by {MAKER}\n\n"
            "A sleek launcher for Among Us\nwith auto-updates and mod support.\n\n"
            f"\u00a9 2026 {MAKER}",
        )


class InstallSpecificDialog:
    """Dialog to pick and install a specific version."""

    def __init__(self, parent, network, on_install):
        self.on_install = on_install

        w = tk.Toplevel(parent)
        w.title("Install Specific Version")
        w.geometry("440x520")
        w.configure(bg=Pal.BG_DARK)
        w.transient(parent)
        w.resizable(False, False)
        w.update_idletasks()
        x = (w.winfo_screenwidth() - 440) // 2
        y = (w.winfo_screenheight() - 520) // 2
        w.geometry(f"440x520+{x}+{y}")

        tk.Label(w, text="Available Versions", font=(Pal.FONT, 14, "bold"),
                 bg=Pal.BG_DARK, fg=Pal.TEXT_BRIGHT).pack(pady=14)

        lf = tk.Frame(w, bg=Pal.BG_DARK)
        lf.pack(fill=tk.BOTH, expand=True, padx=20, pady=8)

        sb = ttk.Scrollbar(lf)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        lb = tk.Listbox(
            lf, bg=Pal.BG_MEDIUM, fg=Pal.TEXT_BRIGHT,
            selectbackground=Pal.ACCENT, selectforeground="white",
            font=(Pal.FONT, 10), yscrollcommand=sb.set,
            relief=tk.FLAT, highlightthickness=0, bd=0,
        )
        lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.config(command=lb.yview)

        versions = network.get_releases()
        for v in versions:
            lb.insert(tk.END, v.version)

        def pick():
            sel = lb.curselection()
            if sel:
                w.destroy()
                self.on_install(versions[sel[0]])

        make_action_button(w, "Install Selected", pick,
                           Pal.BLUE, Pal.BLUE_HOVER, font_size=11).pack(pady=14)


class VerifyDialog:
    """Show verification results."""

    @staticmethod
    def show(parent, result):
        if result["valid"]:
            messagebox.showinfo(
                "Verification",
                f"All game files verified.\n"
                f"{result['file_count']} files, "
                f"{FileManager.format_size(result['total_size'])}",
            )
        elif result["exe_found"]:
            messagebox.showwarning(
                "Verification",
                f"Among Us.exe found but some files are missing:\n"
                f"{', '.join(result['missing'])}\n\n"
                f"Found {result['file_count']} files "
                f"({FileManager.format_size(result['total_size'])})",
            )
        else:
            messagebox.showerror(
                "Verification",
                "Among Us.exe not found in installation folder.",
            )
