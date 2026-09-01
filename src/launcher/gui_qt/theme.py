"""
Theme dispatcher — loads palette files, builds QSS, applies to QApplication.
All palette constants are module-level and update when set_theme() is called.
"""

# ---------------------------------------------------------------------------
# Current palette (updated by set_theme)
# ---------------------------------------------------------------------------
BG_BASE = "#12141a"
BG_SURFACE = "#181b22"
BG_ELEVATED = "#20242e"
BG_HOVER = "#282c38"
BG_ACTIVE = "#303442"

BORDER_SUBTLE = "#282c38"
BORDER_FOCUS = "#6366f1"

ACCENT = "#6366f1"
ACCENT_HOVER = "#818cf8"
ACCENT_2 = "#34d399"

SUCCESS = "#34d399"
SUCCESS_HOVER = "#10b981"
INFO = "#818cf8"
WARNING = "#6366f1"
DANGER = "#f87171"
DANGER_HOVER = "#ef4444"

TEXT_PRIMARY = "#e5e7eb"
TEXT_SECONDARY = "#9ca3af"
TEXT_MUTED = "#6b7280"
TEXT_BRIGHT = "#ffffff"

BG_SIDEBAR = "#0e1016"

CURRENT_THEME = "Indigo"


# ---------------------------------------------------------------------------
# QSS builder
# ---------------------------------------------------------------------------
def build_qss(p: dict) -> str:
    return f"""
/* ===== GLOBAL ===== */
QWidget {{
    background-color: {p["bg_base"]};
    color: {p["text_primary"]};
    font-family: "Segoe UI", "Inter", "Helvetica Neue", Arial;
    font-size: 13px;
}}

/* ===== SIDEBAR ===== */
#sidebar {{
    background-color: {p["bg_sidebar"]};
    border-right: 1px solid {p["border_subtle"]};
}}

/* ===== NAV BUTTONS ===== */
#sidebar QPushButton {{
    background-color: transparent;
    color: {p["text_secondary"]};
    border: none;
    border-radius: 8px;
    padding: 10px 16px;
    text-align: left;
    font-size: 13px;
    font-weight: 500;
}}

#sidebar QPushButton:hover {{
    background-color: {p["bg_hover"]};
    color: {p["text_primary"]};
}}

#sidebar QPushButton:checked {{
    background-color: {p["accent"]};
    color: {p["text_bright"]};
}}

/* ===== PRIMARY ACTION BUTTON ===== */
QPushButton#primaryBtn {{
    background-color: {p["accent"]};
    color: {p["text_bright"]};
    border: none;
    border-radius: 10px;
    padding: 14px 24px;
    font-size: 15px;
    font-weight: 700;
    min-height: 20px;
}}

QPushButton#primaryBtn:hover {{
    background-color: {p["accent_hover"]};
}}

QPushButton#primaryBtn:disabled {{
    background-color: {p["btn_disabled_bg"]};
    color: {p["btn_disabled_text"]};
}}

/* ===== SUCCESS BUTTON ===== */
QPushButton#successBtn {{
    background-color: {p["success_hover"]};
    color: {p["text_bright"]};
    border: none;
    border-radius: 10px;
    padding: 14px 24px;
    font-size: 15px;
    font-weight: 700;
    min-height: 20px;
}}

QPushButton#successBtn:hover {{
    background-color: {p["success"]};
}}

QPushButton#successBtn:disabled {{
    background-color: {p["btn_disabled_bg"]};
    color: {p["btn_disabled_text"]};
}}

/* ===== DANGER BUTTON ===== */
QPushButton#dangerBtn {{
    background-color: {p["danger"]};
    color: {p["text_bright"]};
    border: none;
    border-radius: 10px;
    padding: 14px 24px;
    font-size: 15px;
    font-weight: 700;
    min-height: 20px;
}}

QPushButton#dangerBtn:hover {{
    background-color: {p["danger_hover"]};
}}

QPushButton#dangerBtn:disabled {{
    background-color: {p["btn_disabled_bg"]};
    color: {p["btn_disabled_text"]};
}}

/* ===== SECONDARY / TOOL BUTTONS ===== */
QPushButton#toolBtn {{
    background-color: {p["bg_elevated"]};
    color: {p["text_primary"]};
    border: 1px solid {p["border_subtle"]};
    border-radius: 8px;
    padding: 10px 16px;
    font-size: 13px;
}}

QPushButton#toolBtn:hover {{
    background-color: {p["bg_hover"]};
    border-color: {p["accent"]};
}}

/* ===== MODAL BUTTONS ===== */
QPushButton#modalPrimary {{
    background-color: {p["accent"]};
    color: {p["text_bright"]};
    border: none;
    border-radius: 8px;
    padding: 10px 16px;
    font-size: 13px;
    font-weight: 600;
}}

QPushButton#modalPrimary:hover {{
    background-color: {p["accent_hover"]};
}}

QPushButton#modalSecondary {{
    background-color: {p["bg_elevated"]};
    color: {p["text_primary"]};
    border: 1px solid {p["border_subtle"]};
    border-radius: 8px;
    padding: 10px 16px;
    font-size: 13px;
}}

QPushButton#modalSecondary:hover {{
    background-color: {p["bg_hover"]};
}}

QPushButton#modalDanger {{
    background-color: {p["danger"]};
    color: {p["text_bright"]};
    border: none;
    border-radius: 8px;
    padding: 10px 16px;
    font-size: 13px;
}}

QPushButton#modalDanger:hover {{
    background-color: {p["danger_hover"]};
}}

/* ===== PROGRESS BAR ===== */
QProgressBar {{
    background-color: {p["bg_elevated"]};
    border: none;
    border-radius: 6px;
    text-align: center;
    color: transparent;
}}

QProgressBar::chunk {{
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 {p["accent"]},
        stop:1 {p["success"]}
    );
    border-radius: 6px;
}}

/* ===== LABELS ===== */
QLabel {{
    background-color: transparent;
    color: {p["text_primary"]};
    border: none;
}}

QLabel#brandLabel {{
    font-size: 20px;
    font-weight: 700;
    color: {p["accent"]};
}}

QLabel#brandSubLabel {{
    font-size: 11px;
    color: {p["text_muted"]};
}}

QLabel#sectionTitle {{
    font-size: 11px;
    font-weight: 600;
    color: {p["text_muted"]};
}}

QLabel#heroTitle {{
    font-size: 26px;
    font-weight: 700;
    color: {p["text_bright"]};
}}

QLabel#heroSubtitle {{
    font-size: 14px;
    color: {p["text_secondary"]};
}}

QLabel#versionBadge {{
    background-color: {p["bg_elevated"]};
    border: 1px solid {p["accent"]};
    border-radius: 10px;
    padding: 3px 10px;
    font-size: 11px;
    color: {p["success"]};
}}

QLabel#successText {{
    color: {p["success"]};
    font-weight: 600;
}}

QLabel#infoText {{
    color: {p["accent_hover"]};
    font-weight: 600;
}}

QLabel#mutedText {{
    color: {p["text_muted"]};
    font-size: 11px;
}}

QLabel#statusDot {{
    color: {p["success"]};
    font-size: 14px;
}}

QLabel#statusText {{
    color: {p["text_secondary"]};
    font-size: 12px;
}}

QLabel#footerText {{
    color: {p["text_muted"]};
    font-size: 11px;
}}

/* ===== SCROLLBAR ===== */
QScrollBar:vertical {{
    background-color: {p["bg_base"]};
    width: 8px;
    border-radius: 4px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background-color: {p["scrollbar_handle"]};
    border-radius: 4px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {p["scrollbar_hover"]};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}

/* ===== SCROLL AREA ===== */
QScrollArea {{
    background-color: transparent;
    border: none;
}}

QScrollArea > QWidget > QWidget {{
    background-color: transparent;
}}

/* ===== LIST WIDGETS ===== */
QListWidget {{
    background-color: {p["bg_elevated"]};
    color: {p["text_primary"]};
    border: 1px solid {p["border_subtle"]};
    border-radius: 8px;
    padding: 4px;
    outline: none;
    font-size: 13px;
}}

QListWidget::item {{
    padding: 6px 8px;
    border-radius: 4px;
}}

QListWidget::item:selected {{
    background-color: {p["accent"]};
    color: {p["text_bright"]};
}}

QListWidget::item:hover {{
    background-color: {p["bg_hover"]};
}}

/* ===== CHECKBOX ===== */
QCheckBox {{
    spacing: 8px;
    color: {p["text_primary"]};
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid {p["checkbox_border"]};
    background-color: {p["bg_elevated"]};
}}

QCheckBox::indicator:checked {{
    background-color: {p["accent"]};
    border-color: {p["accent"]};
    image: none;
}}

QCheckBox::indicator:hover {{
    border-color: {p["accent"]};
}}

/* ===== TOOLTIP ===== */
QToolTip {{
    background-color: {p["bg_elevated"]};
    color: {p["text_primary"]};
    border: 1px solid {p["border_subtle"]};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}}

/* ===== SEPARATOR ===== */
QFrame[frameShape="4"],
QFrame[frameShape="5"] {{
    color: {p["border_subtle"]};
    max-height: 1px;
}}

/* ===== STATUS BAR ===== */
QStatusBar {{
    background-color: {p["bg_sidebar"]};
    color: {p["text_muted"]};
    border-top: 1px solid {p["border_subtle"]};
    font-size: 11px;
}}

QStatusBar::item {{
    border: none;
}}

/* ===== DIALOG ===== */
QDialog {{
    background-color: {p["bg_surface"]};
}}

/* ===== PROFILE CARD ===== */
QFrame#profileCard {{
    background-color: {p["bg_surface"]};
    border: 1px solid {p["border_subtle"]};
    border-radius: 10px;
    padding: 20px;
}}

QLabel#profileTitle {{
    font-size: 11px;
    font-weight: 600;
    color: {p["text_muted"]};
}}

QLabel#profileName {{
    font-size: 16px;
    font-weight: 700;
    color: {p["text_bright"]};
}}

QLabel#profileDetail {{
    font-size: 13px;
    color: {p["text_secondary"]};
}}

QLabel#profileStatus {{
    font-size: 12px;
    font-weight: 600;
}}
"""


# ---------------------------------------------------------------------------
# Theme switching
# ---------------------------------------------------------------------------
def _apply_palette(p: dict):
    """Update module-level constants from a palette dict."""
    global BG_BASE, BG_SURFACE, BG_ELEVATED, BG_HOVER, BG_ACTIVE
    global BORDER_SUBTLE, BORDER_FOCUS
    global ACCENT, ACCENT_HOVER, ACCENT_2
    global SUCCESS, SUCCESS_HOVER, INFO, WARNING, DANGER, DANGER_HOVER
    global TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_BRIGHT
    global BG_SIDEBAR

    BG_BASE = p["bg_base"]
    BG_SURFACE = p["bg_surface"]
    BG_ELEVATED = p["bg_elevated"]
    BG_HOVER = p["bg_hover"]
    BG_ACTIVE = p["bg_active"]
    BG_SIDEBAR = p["bg_sidebar"]

    BORDER_SUBTLE = p["border_subtle"]
    BORDER_FOCUS = p["border_focus"]

    ACCENT = p["accent"]
    ACCENT_HOVER = p["accent_hover"]
    ACCENT_2 = p["accent_2"]

    SUCCESS = p["success"]
    SUCCESS_HOVER = p["success_hover"]
    INFO = p["info"]
    WARNING = p["warning"]
    DANGER = p["danger"]
    DANGER_HOVER = p["danger_hover"]

    TEXT_PRIMARY = p["text_primary"]
    TEXT_SECONDARY = p["text_secondary"]
    TEXT_MUTED = p["text_muted"]
    TEXT_BRIGHT = p["text_bright"]


def set_theme(app, theme_name: str):
    """Switch the active theme and re-apply stylesheet."""
    global CURRENT_THEME
    from gui_qt.themes import THEMES

    if theme_name not in THEMES:
        theme_name = "Indigo"
    CURRENT_THEME = theme_name
    palette = THEMES[theme_name]
    _apply_palette(palette)
    if app:
        app.setStyleSheet(build_qss(palette))


def apply_theme(app):
    """Apply the default theme on startup."""
    app.setStyle("Fusion")
    from config import Config
    config = Config()
    theme_name = config.settings.get("theme", "Indigo")
    set_theme(app, theme_name)
