"""Lite itch.io sign-in dialog (tkinter).

Reuses the shared, toolkit-free OAuth flow from ``itch_oauth`` — the exact same
client, callback server and token file as the Qt GUI.
"""
import logging
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox

from itch_oauth import ItchOAuthFlow, save_itch_token
from platform_utils import IS_LINUX, find_wine, itch_token_dir
import gui_tk.theme as theme


class LoginDialog:
    """Small top-level window that runs the itch.io OAuth flow."""

    def __init__(self, parent, ui=None, prefix=None, on_status=None, on_success=None):
        self.parent = parent
        self._ui = ui
        self.prefix = prefix
        self.on_status = on_status
        self.on_success = on_success
        self._flow = None

        self.win = tk.Toplevel(parent)
        self.win.title("Sign in with itch.io")
        self.win.configure(bg=theme.BG_BASE)
        self.win.resizable(False, False)
        self.win.transient(parent)

        pad = {"padx": 18, "pady": 6}
        ttk.Label(self.win, text="itch.io Account", style="Title.TLabel").pack(
            anchor="w", padx=18, pady=(18, 2))
        ttk.Label(
            self.win,
            text=("You need a free itch.io account to play Among Us online.\n"
                  "Signing in writes the token Among Us reads."),
            justify="left", style="Secondary.TLabel", wraplength=380,
        ).pack(anchor="w", padx=18)

        self.status = tk.StringVar(value="")
        ttk.Label(self.win, textvariable=self.status, style="Muted.TLabel",
                  wraplength=380).pack(anchor="w", padx=18, pady=(10, 4))

        row = ttk.Frame(self.win, style="TFrame")
        row.pack(fill="x", padx=18, pady=(6, 18))
        self.signin_btn = ttk.Button(row, text="Sign in with itch.io",
                                     style="Success.TButton", command=self._start)
        self.signin_btn.pack(side="left")
        ttk.Button(row, text="Close", command=self._close).pack(side="right")

        self.win.protocol("WM_DELETE_WINDOW", self._close)
        self._center()

    def _center(self):
        self.win.update_idletasks()
        try:
            px = self.parent.winfo_rootx()
            py = self.parent.winfo_rooty()
            pw = self.parent.winfo_width()
            w = self.win.winfo_width()
            self.win.geometry(f"+{px + max((pw - w) // 2, 0)}+{py + 80}")
        except Exception:
            pass

    def _set_status(self, text: str, notify=True):
        self.status.set(text)
        if notify and self.on_status:
            try:
                self.on_status(text)
            except Exception:
                pass

    def _marshal(self, fn):
        """Run ``fn`` on the Tk main thread (safe from any background thread)."""
        if self._ui is not None:
            self._ui.call(fn)
            return
        try:
            self.win.after(0, fn)
        except Exception:
            pass

    def _start(self):
        if IS_LINUX and not find_wine():
            if not messagebox.askyesno(
                "Wine Not Found",
                "To sign in with itch.io on Linux, Wine is required: the token "
                "is written into the Wine prefix that Among Us reads.\n\n"
                "Already have Wine that wasn't auto-detected (e.g. a Lutris "
                "bundle or custom install)? Click Yes to continue anyway, as "
                "long as the game runs in the configured prefix.",
                parent=self.win, default="no",
            ):
                return

        if self._flow is not None:
            self._flow.stop()
        self.signin_btn.configure(state="disabled")

        self._flow = ItchOAuthFlow()
        self._flow.on_token = self._on_token
        self._flow.on_timed_out = self._on_timed_out
        try:
            self._flow.start()
        except OSError:
            self.signin_btn.configure(state="normal")
            messagebox.showwarning(
                "Login unavailable",
                "The itch.io callback port (7890) is already in use.\n"
                "Close any app using it and try again.",
                parent=self.win,
            )
            return

        webbrowser.open(self._flow.auth_url())
        self._set_status("Check your browser to authorize your itch.io account.")

    def _on_token(self, token: str):
        # Called from the OAuth server thread; marshals GUI updates to main.
        try:
            save_itch_token(token, self.prefix)
        except OSError as e:
            self._marshal(lambda: self._failed(f"Could not save token: {e}"))
            return

        def done():
            self._set_status("Login successful!", notify=False)
            if self.on_success:
                try:
                    self.on_success()
                except Exception:
                    pass
            self._close()

        self._marshal(done)

    def _on_timed_out(self):
        self._marshal(lambda: self._failed("Login timed out. Try again."))

    def _failed(self, message: str):
        self._set_status(message)
        try:
            self.signin_btn.configure(state="normal")
        except Exception:
            pass

    def _close(self):
        if self._flow is not None:
            self._flow.stop()
            self._flow = None
        try:
            self.win.destroy()
        except Exception:
            pass
