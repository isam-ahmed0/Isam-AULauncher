"""Minimal dark theme + ttk styling for the Tk (lite) launcher.

Only stock tkinter/ttk widgets are used so the GUI stays lightweight and works
on older Tk versions.
"""
import tkinter as tk
from tkinter import ttk

# Palette
BG_BASE = "#12141a"
BG_SURFACE = "#1a1d26"
BG_ELEVATED = "#232733"
BG_HOVER = "#2b3040"
BG_ACTIVE = "#343a4d"
BORDER = "#2c313f"

ACCENT = "#5b8def"
ACCENT_HOVER = "#6f9bf2"
SUCCESS = "#4ade80"
SUCCESS_HOVER = "#3fc772"
DANGER = "#f87171"
DANGER_HOVER = "#ef5f5f"
WARNING = "#fbbf24"

TEXT_PRIMARY = "#e8e9ed"
TEXT_SECONDARY = "#a1a5b0"
TEXT_MUTED = "#6b7280"
TEXT_ON_ACCENT = "#0b0d12"

FONT = ("Segoe UI", 10)
FONT_SMALL = ("Segoe UI", 9)
FONT_TITLE = ("Segoe UI", 18, "bold")
FONT_HEADING = ("Segoe UI", 12, "bold")
FONT_BIG = ("Segoe UI", 13, "bold")


def apply_theme(root: tk.Misc):
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    root.configure(bg=BG_BASE)

    style.configure(".", background=BG_BASE, foreground=TEXT_PRIMARY, font=FONT)
    style.configure("TFrame", background=BG_BASE)
    style.configure("Card.TFrame", background=BG_SURFACE)
    style.configure("Bar.TFrame", background=BG_SURFACE)

    style.configure("TLabel", background=BG_BASE, foreground=TEXT_PRIMARY, font=FONT)
    style.configure("Card.TLabel", background=BG_SURFACE, foreground=TEXT_PRIMARY)
    style.configure("Title.TLabel", background=BG_BASE, foreground=TEXT_PRIMARY, font=FONT_TITLE)
    style.configure("Heading.TLabel", background=BG_SURFACE, foreground=TEXT_PRIMARY, font=FONT_HEADING)
    style.configure("Muted.TLabel", background=BG_BASE, foreground=TEXT_MUTED, font=FONT_SMALL)
    style.configure("CardMuted.TLabel", background=BG_SURFACE, foreground=TEXT_MUTED, font=FONT_SMALL)
    style.configure("Secondary.TLabel", background=BG_BASE, foreground=TEXT_SECONDARY, font=FONT)
    style.configure("Status.TLabel", background=BG_SURFACE, foreground=TEXT_SECONDARY, font=FONT)

    # Buttons
    style.configure(
        "TButton",
        background=BG_ELEVATED, foreground=TEXT_PRIMARY,
        bordercolor=BORDER, focuscolor=ACCENT,
        padding=(12, 7), font=FONT, relief="flat",
    )
    style.map(
        "TButton",
        background=[("pressed", BG_ACTIVE), ("active", BG_HOVER), ("disabled", BG_SURFACE)],
        foreground=[("disabled", TEXT_MUTED)],
    )

    def variant(name, bg, hover, fg=TEXT_ON_ACCENT):
        style.configure(
            name, background=bg, foreground=fg,
            bordercolor=bg, focuscolor=bg,
            padding=(14, 8), font=FONT, relief="flat",
        )
        style.map(
            name,
            background=[("pressed", hover), ("active", hover), ("disabled", BG_SURFACE)],
            foreground=[("disabled", TEXT_MUTED)],
        )

    variant("Primary.TButton", ACCENT, ACCENT_HOVER)
    variant("Success.TButton", SUCCESS, SUCCESS_HOVER)
    variant("Danger.TButton", DANGER, DANGER_HOVER, fg="#2a0d0d")

    style.configure(
        "Big.TButton",
        background=ACCENT, foreground=TEXT_ON_ACCENT,
        bordercolor=ACCENT, focuscolor=ACCENT,
        padding=(16, 14), font=FONT_BIG, relief="flat",
    )
    style.map(
        "Big.TButton",
        background=[("pressed", ACCENT_HOVER), ("active", ACCENT_HOVER), ("disabled", BG_ELEVATED)],
        foreground=[("disabled", TEXT_MUTED)],
    )
    style.configure(
        "BigSuccess.TButton",
        background=SUCCESS, foreground=TEXT_ON_ACCENT,
        bordercolor=SUCCESS, focuscolor=SUCCESS,
        padding=(16, 14), font=FONT_BIG, relief="flat",
    )
    style.map(
        "BigSuccess.TButton",
        background=[("pressed", SUCCESS_HOVER), ("active", SUCCESS_HOVER), ("disabled", BG_ELEVATED)],
        foreground=[("disabled", TEXT_MUTED)],
    )
    style.configure(
        "BigDanger.TButton",
        background=DANGER, foreground="#2a0d0d",
        bordercolor=DANGER, focuscolor=DANGER,
        padding=(16, 14), font=FONT_BIG, relief="flat",
    )
    style.map(
        "BigDanger.TButton",
        background=[("pressed", DANGER_HOVER), ("active", DANGER_HOVER), ("disabled", BG_ELEVATED)],
        foreground=[("disabled", TEXT_MUTED)],
    )

    # Progress bar
    style.configure(
        "TProgressbar",
        troughcolor=BG_ELEVATED, background=ACCENT,
        bordercolor=BG_ELEVATED, lightcolor=ACCENT, darkcolor=ACCENT,
        thickness=10,
    )

    # Checkbutton / Combobox / Entry
    style.configure(
        "TCheckbutton", background=BG_BASE, foreground=TEXT_PRIMARY,
        focuscolor=BG_BASE, font=FONT,
    )
    style.map("TCheckbutton", background=[("active", BG_BASE)])
    style.configure(
        "TCombobox", fieldbackground=BG_ELEVATED, background=BG_ELEVATED,
        foreground=TEXT_PRIMARY, arrowcolor=TEXT_SECONDARY, bordercolor=BORDER,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", BG_ELEVATED)],
        foreground=[("readonly", TEXT_PRIMARY)],
    )
    root.option_add("*TCombobox*Listbox.background", BG_ELEVATED)
    root.option_add("*TCombobox*Listbox.foreground", TEXT_PRIMARY)
    root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
    root.option_add("*TCombobox*Listbox.selectForeground", TEXT_ON_ACCENT)

    style.configure(
        "TEntry", fieldbackground=BG_ELEVATED, foreground=TEXT_PRIMARY,
        bordercolor=BORDER,
    )
    style.configure("TSeparator", background=BORDER)
    return style
