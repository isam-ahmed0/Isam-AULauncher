"""
Theme — Dear PyGui gaming dark theme.
GPU-accelerated, fully customizable via DPG theme API.
"""
import dearpygui.dearpygui as dpg

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
BG_DARK = (12, 14, 20)
BG_MEDIUM = (18, 21, 30)
BG_LIGHT = (26, 31, 46)
BG_HOVER = (34, 40, 64)
SHADOW = (6, 8, 14)
BORDER = (30, 42, 66)

ACCENT = (139, 92, 246)
ACCENT_2 = (6, 182, 212)
GREEN = (16, 185, 129)
GREEN_HOVER = (5, 150, 105)
BLUE = (59, 130, 246)
BLUE_HOVER = (37, 99, 235)
RED = (239, 68, 68)
RED_HOVER = (220, 38, 38)
PURPLE = (168, 85, 247)
PURPLE_HOVER = (147, 51, 234)
ORANGE = (245, 158, 11)
CYAN = (34, 211, 238)

TEXT = (241, 245, 249)
TEXT_DIM = (100, 116, 139)
TEXT_BRIGHT = (255, 255, 255)
TEXT_MUTED = (71, 85, 105)


def apply_theme():
    """Apply the gaming dark theme to DPG."""
    with dpg.theme() as theme:
        with dpg.theme_component(dpg.mvAll):
            # Backgrounds
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (*BG_DARK, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (*BG_MEDIUM, 255))
            dpg.add_theme_color(dpg.mvThemeCol_PopupBg, (*BG_LIGHT, 255))

            # Text
            dpg.add_theme_color(dpg.mvThemeCol_Text, (*TEXT, 255))
            dpg.add_theme_color(dpg.mvThemeCol_TextDisabled, (*TEXT_MUTED, 255))

            # Buttons
            dpg.add_theme_color(dpg.mvThemeCol_Button, (*BG_LIGHT, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (*BG_HOVER, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (*ACCENT, 255))

            # Frames / inputs
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (*BG_MEDIUM, 255))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, (*BG_HOVER, 255))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, (*ACCENT, 255))

            # Title bar
            dpg.add_theme_color(dpg.mvThemeCol_TitleBg, (*BG_DARK, 255))
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, (*BG_LIGHT, 255))

            # Headers
            dpg.add_theme_color(dpg.mvThemeCol_Header, (*BG_LIGHT, 255))
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, (*BG_HOVER, 255))
            dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, (*ACCENT, 255))

            # Borders
            dpg.add_theme_color(dpg.mvThemeCol_Border, (*BORDER, 150))

            # Tabs
            dpg.add_theme_color(dpg.mvThemeCol_Tab, (*BG_LIGHT, 255))
            dpg.add_theme_color(dpg.mvThemeCol_TabHovered, (*BG_HOVER, 255))
            dpg.add_theme_color(dpg.mvThemeCol_TabActive, (*ACCENT, 255))

            # Scrollbar
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarBg, (*BG_DARK, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrab, (*BG_LIGHT, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabHovered, (*BG_HOVER, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabActive, (*ACCENT, 255))

            # Separator
            dpg.add_theme_color(dpg.mvThemeCol_Separator, (*BORDER, 255))

            # Slider / grab
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrab, (*ACCENT, 255))
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrabActive, (*ACCENT_2, 255))

            # Progress bar
            dpg.add_theme_color(dpg.mvThemeCol_PlotHistogram, (*ACCENT, 255))
            dpg.add_theme_color(dpg.mvThemeCol_PlotHistogramBorder, (*ACCENT_2, 255))

            # Check mark
            dpg.add_theme_color(dpg.mvThemeCol_CheckMark, (*ACCENT, 255))

            # Resize grip
            dpg.add_theme_color(dpg.mvThemeCol_ResizeGrip, (*ACCENT, 40))
            dpg.add_theme_color(dpg.mvThemeCol_ResizeGripHovered, (*ACCENT, 100))
            dpg.add_theme_color(dpg.mvThemeCol_ResizeGripActive, (*ACCENT, 200))

            # Styles
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 4)
            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_GrabRounding, 4)
            dpg.add_theme_style(dpg.mvStyleVar_TabRounding, 4)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 8, 4)

    dpg.bind_theme(theme)


# ---------------------------------------------------------------------------
# Accent buttons (colored variants)
# ---------------------------------------------------------------------------
ACCENT_THEMES = {}


def _make_accent_theme(name, color, hover_color):
    with dpg.theme() as theme:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (*color, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (*hover_color, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (*hover_color, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255, 255))
    ACCENT_THEMES[name] = theme
    return theme


def init_accent_themes():
    _make_accent_theme("green", GREEN, GREEN_HOVER)
    _make_accent_theme("blue", BLUE, BLUE_HOVER)
    _make_accent_theme("red", RED, RED_HOVER)
    _make_accent_theme("purple", PURPLE, PURPLE_HOVER)
    _make_accent_theme("accent", ACCENT, (100, 70, 200))
    _make_accent_theme("orange", ORANGE, (200, 130, 10))
    _make_accent_theme("cyan", ACCENT_2, (5, 150, 180))


def bind_accent(tag, name):
    if name in ACCENT_THEMES:
        dpg.bind_item_theme(tag, ACCENT_THEMES[name])
