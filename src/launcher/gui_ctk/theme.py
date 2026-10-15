# jeijdiusujndjnwisjdje themeeeee
import customtkinter as ctk

BG_BASE = "#0a0e0c"
BG_SURFACE = "#0f1512"
BG_ELEVATED = "#151d18"
BG_HOVER = "#1c261f"
BG_ACTIVE = "#243027"
BG_SIDEBAR = "#070a08"


BORDER_SUBTLE = "#1a221d"
BORDER_DEFAULT = "#243027"
BORDER_FOCUS = "#4ade80"


ACCENT = "#4ade80"
ACCENT_HOVER = "#6ee89a"
ACCENT_MUTED = "#22c55e"
ACCENT_2 = "#a3e635"
SUCCESS = "#4ade80"
SUCCESS_HOVER = "#22c55e"
INFO = "#38bdf8"
WARNING = "#facc15"
DANGER = "#fb7185"
DANGER_HOVER = "#f43f5e"


TEXT_PRIMARY = "#e4ece7"
TEXT_SECONDARY = "#8fa398"
TEXT_MUTED = "#576359"
TEXT_BRIGHT = "#ffffff"


BTN_DISABLED_BG = "#1a221d"
BTN_DISABLED_TEXT = "#576359"
SCROLLBAR_HANDLE = "#243027"
SCROLLBAR_HOVER = "#304033"
CHECKBOX_BORDER = "#304033"


FONT = ("Segoe UI", 13)
FONT_SMALL = ("Segoe UI", 12)
FONT_TITLE = ("Segoe UI", 24, "bold")
FONT_HEADING = ("Segoe UI", 16, "bold")
FONT_BIG = ("Segoe UI", 16, "bold")


def apply_theme():
    ctk.set_appearance_mode("dark")
    