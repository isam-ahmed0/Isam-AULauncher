"""News dialog — shows the remote announcement in the Tk Lite UI."""
import re
import webbrowser
import tkinter as tk
from tkinter import ttk

import gui_tk.theme as theme
from news import news_to_plain

_URL_RE = re.compile(r"https?://[^\s<>()\[\]]+")


class NewsDialog:
    """Read-only text window rendering the message with clickable links."""

    def __init__(self, parent, item=None):
        self.win = tk.Toplevel(parent)
        self.win.title("News")
        self.win.configure(bg=theme.BG_BASE)
        self.win.transient(parent)
        self.win.minsize(540, 420)
        self._center(parent)

        frame = ttk.Frame(self.win, style="Card.TFrame", padding=16)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="NEWS", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(
            frame, text="Updates and messages from the developers.",
            style="CardMuted.TLabel",
        ).pack(anchor="w", pady=(2, 10))

        body = tk.Text(
            frame, wrap="word", relief="flat", padx=10, pady=10,
            bg=theme.BG_ELEVATED, fg=theme.TEXT_PRIMARY,
            insertbackground=theme.TEXT_PRIMARY,
            font=theme.FONT, spacing1=2, spacing3=2,
        )
        scroll = ttk.Scrollbar(frame, command=body.yview)
        body.configure(yscrollcommand=scroll.set)
        body.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.text = body

        if item and item.text:
            content = news_to_plain(item.text)
        else:
            content = "No news right now.\nCheck back later."
        body.insert("1.0", content)
        body.configure(state="disabled")

        body.tag_config(
            "link", foreground=theme.ACCENT, underline=True,
            font=(theme.FONT[0], theme.FONT[1], "underline"))
        for m in _URL_RE.finditer(content):
            start = f"1.0 + {m.start()} chars"
            end = f"1.0 + {m.end()} chars"
            body.tag_add("link", start, end)
        body.tag_bind("link", "<Button-1>", self._open_link)
        body.tag_bind("link", "<Enter>", lambda e: body.config(cursor="hand2"))
        body.tag_bind("link", "<Leave>", lambda e: body.config(cursor=""))

        close_row = ttk.Frame(self.win, style="Card.TFrame", padding=(16, 0, 16, 14))
        close_row.pack(fill="x")
        ttk.Button(close_row, text="Close", command=self._close).pack(
            side="right", padx=(8, 0))
        self.win.protocol("WM_DELETE_WINDOW", self._close)
        self.win.bind("<Escape>", lambda e: self._close())
        self.win.focus_set()

    def _center(self, parent):
        self.win.update_idletasks()
        w, h = self.win.winfo_reqwidth(), max(self.win.winfo_reqheight(), 420)
        x = parent.winfo_rootx() + max((parent.winfo_width() - w) // 2, 20)
        y = parent.winfo_rooty() + max((parent.winfo_height() - h) // 2, 20)
        self.win.geometry(f"+{x}+{y}")

    def _open_link(self, event):
        idx = self.text.index(f"@{event.x},{event.y}")
        try:
            line, char = (int(p) for p in str(idx).split("."))
        except ValueError:
            return
        ranges = self.text.tag_ranges("link")
        for i in range(0, len(ranges), 2):
            s_line, s_char = (int(p) for p in str(ranges[i]).split("."))
            e_line, e_char = (int(p) for p in str(ranges[i + 1]).split("."))
            if ((line, char) >= (s_line, s_char)
                    and (line, char) < (e_line, e_char)):
                url = self.text.get(str(ranges[i]), str(ranges[i + 1]))
                webbrowser.open(url)
                return

    def _close(self):
        try:
            self.win.destroy()
        except tk.TclError:
            pass
