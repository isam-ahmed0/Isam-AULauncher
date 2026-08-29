"""
Theme — Premium Steam-like dark theme for Isam AULauncher.
GPU-accelerated, fully customizable via DPG theme API.
Uses DPG built-in font — no custom fonts needed.
"""
import dearpygui.dearpygui as dpg

# ---------------------------------------------------------------------------
# Palette — Steam-like minimal dark
# ---------------------------------------------------------------------------
BG_BASE = (18, 20, 26)
BG_SURFACE = (24, 27, 34)
BG_ELEVATED = (32, 36, 46)
BG_HOVER = (40, 44, 56)
BG_ACTIVE = (48, 52, 66)

BORDER_SUBTLE = (40, 44, 56)
BORDER_FOCUS = (99, 102, 241)

ACCENT = (99, 102, 241)
ACCENT_HOVER = (129, 132, 247)
ACCENT_2 = (6, 182, 212)

SUCCESS = (52, 211, 153)
SUCCESS_HOVER = (16, 185, 129)
INFO = (96, 165, 250)
INFO_HOVER = (59, 130, 246)
WARNING = (251, 191, 36)
WARNING_HOVER = (245, 158, 11)
DANGER = (248, 113, 113)
DANGER_HOVER = (239, 68, 68)

GREEN = SUCCESS
GREEN_HOVER = SUCCESS_HOVER
BLUE = INFO
BLUE_HOVER = INFO_HOVER
RED = DANGER
RED_HOVER = DANGER_HOVER
PURPLE = (168, 85, 247)
PURPLE_HOVER = (147, 51, 234)
ORANGE = WARNING
CYAN = ACCENT_2

TEXT_PRIMARY = (229, 231, 235)
TEXT_SECONDARY = (156, 163, 175)
TEXT_MUTED = (107, 114, 128)
TEXT_BRIGHT = (255, 255, 255)

TEXT = TEXT_PRIMARY
TEXT_DIM = TEXT_SECONDARY

# ---------------------------------------------------------------------------
# Global theme
# ---------------------------------------------------------------------------
def apply_theme():
    with dpg.theme() as theme:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (*BG_BASE, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (*BG_SURFACE, 255))
            dpg.add_theme_color(dpg.mvThemeCol_PopupBg, (*BG_SURFACE, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Text, (*TEXT_PRIMARY, 255))
            dpg.add_theme_color(dpg.mvThemeCol_TextDisabled, (*TEXT_MUTED, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Button, (*BG_ELEVATED, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (*BG_HOVER, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (*BG_ACTIVE, 255))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (*BG_ELEVATED, 255))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, (*BG_HOVER, 255))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, (*BG_ACTIVE, 255))
            dpg.add_theme_color(dpg.mvThemeCol_TitleBg, (*BG_BASE, 255))
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, (*BG_SURFACE, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Header, (*BG_ELEVATED, 255))
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, (*BG_HOVER, 255))
            dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, (*ACCENT, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Border, (*BORDER_SUBTLE, 200))
            dpg.add_theme_color(dpg.mvThemeCol_Tab, (*BG_ELEVATED, 255))
            dpg.add_theme_color(dpg.mvThemeCol_TabHovered, (*BG_HOVER, 255))
            dpg.add_theme_color(dpg.mvThemeCol_TabActive, (*ACCENT, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarBg, (*BG_BASE, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrab, (*BG_HOVER, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabHovered, (*BG_ACTIVE, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabActive, (*ACCENT, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Separator, (*BORDER_SUBTLE, 255))
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrab, (*ACCENT, 255))
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrabActive, (*ACCENT_2, 255))
            dpg.add_theme_color(dpg.mvThemeCol_PlotHistogram, (*ACCENT, 255))
            dpg.add_theme_color(dpg.mvThemeCol_CheckMark, (*ACCENT, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ResizeGrip, (*ACCENT, 40))
            dpg.add_theme_color(dpg.mvThemeCol_ResizeGripHovered, (*ACCENT, 100))
            dpg.add_theme_color(dpg.mvThemeCol_ResizeGripActive, (*ACCENT, 200))
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 8)
            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 10)
            dpg.add_theme_style(dpg.mvStyleVar_GrabRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_TabRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 14, 8)
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 20, 16)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 10, 8)
            dpg.add_theme_style(dpg.mvStyleVar_ScrollbarSize, 8)
            dpg.add_theme_style(dpg.mvStyleVar_ScrollbarRounding, 4)
    dpg.bind_theme(theme)


# ---------------------------------------------------------------------------
# Accent buttons
# ---------------------------------------------------------------------------
ACCENT_THEMES = {}


def _make_accent_theme(name, color, hover_color):
    with dpg.theme() as theme:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (*color, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (*hover_color, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (*hover_color, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255, 255))
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 8)
    ACCENT_THEMES[name] = theme


def _make_ghost_theme(name, color):
    with dpg.theme() as theme:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (0, 0, 0, 0))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (*BG_HOVER, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (*BG_ACTIVE, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Text, (*color, 255))
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 8)
    ACCENT_THEMES[name] = theme


def _make_large_accent_theme(name, color, hover_color):
    with dpg.theme() as theme:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (*color, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (*hover_color, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (*hover_color, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255, 255))
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 10)
    ACCENT_THEMES[name] = theme


def _make_modal_button_theme(name, color, hover_color):
    with dpg.theme() as theme:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (*color, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (*hover_color, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (*hover_color, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255, 255))
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 8)
    ACCENT_THEMES[name] = theme


def _make_secondary_button_theme(name):
    with dpg.theme() as theme:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (*BG_ELEVATED, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (*BG_HOVER, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (*BG_ACTIVE, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Text, (*TEXT_PRIMARY, 255))
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 8)
    ACCENT_THEMES[name] = theme


def init_accent_themes():
    _make_accent_theme("green", SUCCESS, SUCCESS_HOVER)
    _make_accent_theme("blue", INFO, INFO_HOVER)
    _make_accent_theme("red", DANGER, DANGER_HOVER)
    _make_accent_theme("purple", PURPLE, PURPLE_HOVER)
    _make_accent_theme("accent", ACCENT, ACCENT_HOVER)
    _make_accent_theme("orange", WARNING, WARNING_HOVER)
    _make_accent_theme("cyan", ACCENT_2, (5, 150, 180))
    _make_large_accent_theme("btn_primary", ACCENT, ACCENT_HOVER)
    _make_large_accent_theme("btn_success", SUCCESS, SUCCESS_HOVER)
    _make_large_accent_theme("btn_info", INFO, INFO_HOVER)
    _make_large_accent_theme("btn_danger", DANGER, DANGER_HOVER)
    _make_large_accent_theme("btn_warning", WARNING, WARNING_HOVER)
    _make_secondary_button_theme("btn_secondary")
    _make_ghost_theme("ghost_accent", ACCENT)
    _make_ghost_theme("ghost_text", TEXT_SECONDARY)
    _make_modal_button_theme("modal_primary", ACCENT, ACCENT_HOVER)
    _make_modal_button_theme("modal_success", SUCCESS, SUCCESS_HOVER)
    _make_modal_button_theme("modal_danger", DANGER, DANGER_HOVER)
    _make_modal_button_theme("modal_secondary", BG_ELEVATED, BG_HOVER)


def bind_accent(tag, name):
    if name in ACCENT_THEMES:
        dpg.bind_item_theme(tag, ACCENT_THEMES[name])


# ---------------------------------------------------------------------------
# Modal theme
# ---------------------------------------------------------------------------
MODAL_THEME = None


def init_modal_theme():
    global MODAL_THEME
    with dpg.theme() as theme:
        with dpg.theme_component(dpg.mvWindowAppItem):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (*BG_SURFACE, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Border, (*BORDER_SUBTLE, 200))
            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 12)
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 24, 20)
            dpg.add_theme_style(dpg.mvStyleVar_WindowBorderSize, 1)
    MODAL_THEME = theme


def bind_modal(tag):
    if MODAL_THEME:
        dpg.bind_item_theme(tag, MODAL_THEME)


# ---------------------------------------------------------------------------
# Sidebar theme
# ---------------------------------------------------------------------------
BG_SIDEBAR = (14, 16, 22)
SIDEBAR_THEME = None


def init_sidebar_theme():
    global SIDEBAR_THEME
    with dpg.theme() as theme:
        with dpg.theme_component(dpg.mvChildWindow):
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (*BG_SIDEBAR, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Border, (*BORDER_SUBTLE, 200))
            dpg.add_theme_style(dpg.mvStyleVar_ChildBorderSize, 1)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 0)
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 12, 8)
    SIDEBAR_THEME = theme


def bind_sidebar(tag):
    if SIDEBAR_THEME:
        dpg.bind_item_theme(tag, SIDEBAR_THEME)
