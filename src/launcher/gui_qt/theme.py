"""
Theme — Steam-like dark theme for Isam AULauncher (PySide6).
QSS-based styling with the same color palette as the DPG version.
"""

# ---------------------------------------------------------------------------
# Palette — Steam-like minimal dark
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
ACCENT_2 = "#06b6d4"

SUCCESS = "#34d399"
SUCCESS_HOVER = "#10b981"
INFO = "#60a5fa"
INFO_HOVER = "#3b82f6"
WARNING = "#fbbf24"
WARNING_HOVER = "#f59e0b"
DANGER = "#f87171"
DANGER_HOVER = "#ef4444"

TEXT_PRIMARY = "#e5e7eb"
TEXT_SECONDARY = "#9ca3af"
TEXT_MUTED = "#6b7280"
TEXT_BRIGHT = "#ffffff"

BG_SIDEBAR = "#0e1016"

# ---------------------------------------------------------------------------
# QSS Stylesheet
# ---------------------------------------------------------------------------
DARK_THEME_QSS = f"""
/* ===== GLOBAL ===== */
QWidget {{
    background-color: {BG_BASE};
    color: {TEXT_PRIMARY};
    font-family: "Segoe UI", "Inter", "Helvetica Neue", Arial;
    font-size: 13px;
}}

/* ===== SIDEBAR ===== */
#sidebar {{
    background-color: {BG_SIDEBAR};
    border-right: 1px solid {BORDER_SUBTLE};
}}

/* ===== NAV BUTTONS ===== */
#sidebar QPushButton {{
    background-color: transparent;
    color: {TEXT_SECONDARY};
    border: none;
    border-radius: 8px;
    padding: 10px 16px;
    text-align: left;
    font-size: 13px;
    font-weight: 500;
}}

#sidebar QPushButton:hover {{
    background-color: {BG_HOVER};
    color: {TEXT_PRIMARY};
}}

#sidebar QPushButton:checked {{
    background-color: {ACCENT};
    color: {TEXT_BRIGHT};
}}

/* ===== PRIMARY ACTION BUTTON ===== */
QPushButton#primaryBtn {{
    background-color: {ACCENT};
    color: {TEXT_BRIGHT};
    border: none;
    border-radius: 10px;
    padding: 14px 24px;
    font-size: 15px;
    font-weight: 700;
    min-height: 20px;
}}

QPushButton#primaryBtn:hover {{
    background-color: {ACCENT_HOVER};
}}

QPushButton#primaryBtn:pressed {{
    background-color: #4f46e5;
}}

QPushButton#primaryBtn:disabled {{
    background-color: #374151;
    color: #6b7280;
}}

/* ===== SUCCESS BUTTON ===== */
QPushButton#successBtn {{
    background-color: {SUCCESS_HOVER};
    color: {TEXT_BRIGHT};
    border: none;
    border-radius: 10px;
    padding: 14px 24px;
    font-size: 15px;
    font-weight: 700;
    min-height: 20px;
}}

QPushButton#successBtn:hover {{
    background-color: {SUCCESS};
}}

QPushButton#successBtn:disabled {{
    background-color: #374151;
    color: #6b7280;
}}

/* ===== DANGER BUTTON ===== */
QPushButton#dangerBtn {{
    background-color: {DANGER};
    color: {TEXT_BRIGHT};
    border: none;
    border-radius: 10px;
    padding: 14px 24px;
    font-size: 15px;
    font-weight: 700;
    min-height: 20px;
}}

QPushButton#dangerBtn:hover {{
    background-color: #dc2626;
}}

QPushButton#dangerBtn:disabled {{
    background-color: #374151;
    color: #6b7280;
}}

/* ===== SECONDARY / TOOL BUTTONS ===== */
QPushButton#toolBtn {{
    background-color: {BG_ELEVATED};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_SUBTLE};
    border-radius: 8px;
    padding: 10px 16px;
    font-size: 13px;
}}

QPushButton#toolBtn:hover {{
    background-color: {BG_HOVER};
    border-color: {ACCENT};
}}

/* ===== DANGER BUTTON ===== */
QPushButton#dangerBtn {{
    background-color: #dc2626;
    color: {TEXT_BRIGHT};
    border: none;
    border-radius: 8px;
    padding: 10px 16px;
    font-size: 13px;
}}

QPushButton#dangerBtn:hover {{
    background-color: {DANGER_HOVER};
}}

/* ===== MODAL BUTTONS ===== */
QPushButton#modalPrimary {{
    background-color: {ACCENT};
    color: {TEXT_BRIGHT};
    border: none;
    border-radius: 8px;
    padding: 10px 16px;
    font-size: 13px;
    font-weight: 600;
}}

QPushButton#modalPrimary:hover {{
    background-color: {ACCENT_HOVER};
}}

QPushButton#modalSecondary {{
    background-color: {BG_ELEVATED};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_SUBTLE};
    border-radius: 8px;
    padding: 10px 16px;
    font-size: 13px;
}}

QPushButton#modalSecondary:hover {{
    background-color: {BG_HOVER};
}}

QPushButton#modalDanger {{
    background-color: #dc2626;
    color: {TEXT_BRIGHT};
    border: none;
    border-radius: 8px;
    padding: 10px 16px;
    font-size: 13px;
}}

QPushButton#modalDanger:hover {{
    background-color: {DANGER_HOVER};
}}

/* ===== PROGRESS BAR ===== */
QProgressBar {{
    background-color: {BG_ELEVATED};
    border: none;
    border-radius: 6px;
    min-height: 12px;
    max-height: 12px;
    text-align: center;
    color: transparent;
}}

QProgressBar::chunk {{
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 {ACCENT},
        stop:1 {ACCENT_2}
    );
    border-radius: 6px;
}}

/* ===== LABELS ===== */
QLabel {{
    background-color: transparent;
    color: {TEXT_PRIMARY};
    border: none;
}}

QLabel#brandLabel {{
    font-size: 20px;
    font-weight: 700;
    color: {ACCENT};
}}

QLabel#brandSubLabel {{
    font-size: 11px;
    color: {TEXT_MUTED};
}}

QLabel#sectionTitle {{
    font-size: 11px;
    font-weight: 600;
    color: {TEXT_MUTED};
    letter-spacing: 1px;
}}

QLabel#heroTitle {{
    font-size: 26px;
    font-weight: 700;
    color: {TEXT_BRIGHT};
}}

QLabel#heroSubtitle {{
    font-size: 14px;
    color: {TEXT_SECONDARY};
}}

QLabel#versionBadge {{
    background-color: {BG_ELEVATED};
    border: 1px solid {ACCENT};
    border-radius: 10px;
    padding: 3px 10px;
    font-size: 11px;
    color: {ACCENT_2};
}}

QLabel#successText {{
    color: {SUCCESS};
    font-weight: 600;
}}

QLabel#infoText {{
    color: {INFO};
    font-weight: 600;
}}

QLabel#mutedText {{
    color: {TEXT_MUTED};
    font-size: 11px;
}}

QLabel#statusDot {{
    color: {SUCCESS};
    font-size: 14px;
}}

QLabel#statusText {{
    color: {TEXT_SECONDARY};
    font-size: 12px;
}}

QLabel#footerText {{
    color: {TEXT_MUTED};
    font-size: 11px;
}}

/* ===== FRAME / CARDS ===== */
QFrame#card {{
    background-color: {BG_SURFACE};
    border: 1px solid {BORDER_SUBTLE};
    border-radius: 10px;
    padding: 20px;
}}

/* ===== SCROLLBAR ===== */
QScrollBar:vertical {{
    background-color: {BG_BASE};
    width: 8px;
    border-radius: 4px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background-color: #374151;
    border-radius: 4px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: #4b5563;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}

/* ===== CHECKBOX ===== */
QCheckBox {{
    spacing: 8px;
    color: {TEXT_PRIMARY};
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid #374151;
    background-color: {BG_ELEVATED};
}}

QCheckBox::indicator:checked {{
    background-color: {ACCENT};
    border-color: {ACCENT};
}}

QCheckBox::indicator:hover {{
    border-color: {ACCENT};
}}

/* ===== TOOLTIP ===== */
QToolTip {{
    background-color: {BG_ELEVATED};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_SUBTLE};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}}

/* ===== SEPARATOR ===== */
QFrame[frameShape="4"],
QFrame[frameShape="5"] {{
    color: {BORDER_SUBTLE};
    max-height: 1px;
}}

/* ===== STATUS BAR ===== */
QStatusBar {{
    background-color: {BG_SIDEBAR};
    color: {TEXT_MUTED};
    border-top: 1px solid {BORDER_SUBTLE};
    font-size: 11px;
}}

QStatusBar::item {{
    border: none;
}}

/* ===== DIALOG ===== */
QDialog {{
    background-color: {BG_SURFACE};
}}

/* ===== PROFILE CARD ===== */
QFrame#profileCard {{
    background-color: {BG_SURFACE};
    border: 1px solid {BORDER_SUBTLE};
    border-radius: 10px;
    padding: 20px;
}}

QLabel#profileTitle {{
    font-size: 11px;
    font-weight: 600;
    color: {TEXT_MUTED};
}}

QLabel#profileName {{
    font-size: 16px;
    font-weight: 700;
    color: {TEXT_BRIGHT};
}}

QLabel#profileDetail {{
    font-size: 13px;
    color: {TEXT_SECONDARY};
}}

QLabel#profileStatus {{
    font-size: 12px;
    font-weight: 600;
}}

/* ===== MOD CARD ===== */
QFrame#modCard {{
    background-color: {BG_SURFACE};
    border: 1px solid {BORDER_SUBTLE};
    border-radius: 8px;
}}

QFrame#modCard:hover {{
    border: 1px solid {ACCENT};
    background-color: {BG_ELEVATED};
}}
"""


def apply_theme(app):
    """Apply the dark theme to the QApplication."""
    app.setStyle("Fusion")
    app.setStyleSheet(DARK_THEME_QSS)
