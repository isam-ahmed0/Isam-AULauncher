# Isam AULauncher — GUI Reference for Animation Expert

## Overview

PySide6 (Qt6) dark-theme launcher for Among Us. Steam/Epic-style sidebar layout with stacked pages. 7 color themes. Currently has almost no animations — needs premium feel.

---

## Tech Stack

- **Framework**: PySide6 (Qt6 for Python)
- **Language**: Python 3.10+
- **Styling**: QSS (Qt Style Sheets) — generated dynamically from palette dicts
- **Rendering**: Custom `paintEvent()` on HeroBanner and ThemeCard (not QLabel)
- **Animations**: Only 3 exist: opacity hover on nav buttons, splash fade-out, slideshow timer

---

## File Structure

```
src/launcher/gui_qt/
├── __init__.py
├── theme.py              # QSS builder, palette globals, set_theme()
├── widgets.py            # HeroBanner, enable_hover_glow(), SIDEBAR_W
├── splash.py             # SplashScreen (PNG-based, fade-out only)
├── video_splash.py       # VideoSplash (WebM video splash)
├── login.py              # LoginWindow + _RightSidebar (OAuth, slideshow)
├── game.py               # GameManager (download, launch, process mgmt)
├── regions.py            # RegionManager
├── profiles.py           # ProfileManager (directory junctions)
├── mod_details.py        # ModDetailsDialog
├── mod_warnings.py       # ModWarningsDialog
├── worker.py             # Worker thread + _UISignaler
├── themes/
│   ├── __init__.py       # THEMES dict, exports 7 palettes
│   ├── violet.py         # PALETTE dict (28 keys)
│   ├── coral.py
│   ├── slate.py
│   ├── ember.py
│   ├── forest.py
│   ├── plum.py
│   └── mono.py
├── window/
│   ├── __init__.py
│   ├── main.py           # LauncherApp (main window, all pages)
│   ├── game_actions.py   # GameActionsMixin
│   ├── region_editor.py  # RegionEditorMixin
│   ├── mod_manager.py    # ModManagerMixin
│   ├── itch_profile.py   # ItchProfileMixin
│   └── updater.py        # UpdaterMixin
└── assets_manager/       # DISABLED (coming soon)
    ├── __init__.py
    ├── models.py
    ├── profile_manager.py
    ├── pack_io.py
    ├── tab.py
    └── mixin.py
```

---

## Window Layout

```
┌─────────────────────────────────────────────────────────┐
│                    QMainWindow                           │
│  ┌──────────┬──────────────────────────────────────────┐│
│  │ SIDEBAR  │              QStackedWidget              ││
│  │ (200px)  │                                          ││
│  │          │  ┌──────────────────────────────────────┐││
│  │ [Brand]  │  │           PAGE CONTENT               │││
│  │ [Sub]    │  │                                      │││
│  │ ──────── │  │  (HeroBanner at top of Game/Profile) │││
│  │ [Game] ◄ │  │                                      │││
│  │ [Tools]  │  │  (ScrollArea for Tools/Mods/Profile) │││
│  │ [Profile]│  │                                      │││
│  │ [Mods]   │  │  (Settings/About inline)             │││
│  │ [Settings│  │                                      │││
│  │ [About]  │  └──────────────────────────────────────┘││
│  │ [Assets] │                                          ││
│  │ ──────── │                                          ││
│  │ (stretch)│                                          ││
│  └──────────┴──────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────┐│
│  │  QStatusBar: ● Status text          App v0.7 ──── ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

### Key Dimensions
- Window: min 960×580, default 1100×680
- Sidebar: 200px fixed width
- Hero banner: 180px fixed height (custom painted)
- Nav buttons: 42px height
- Tool/secondary buttons: 38px height
- Progress bars: 16px height

---

## Page Structure (Index → Page)

| Index | Name | Builder Method | ScrollArea? | Has Hero? |
|-------|------|---------------|-------------|-----------|
| 0 | Game | `_build_game_page()` | No | Yes |
| 1 | Tools | `_build_tools_page()` | Yes | No |
| 2 | Profile | `_build_profile_page()` | Yes | Yes |
| 3 | Mods | `_build_mods_page()` | Yes | No |
| 4 | Settings | `SettingsPage` (dialogs.py) | Yes | No |
| 5 | About | `AboutPage` (dialogs.py) | Yes | No |
| 6 | Assets | Placeholder QWidget | No | No |

### Page Margins
- Game/Profile: 32, 20, 32, 20 (content below hero)
- Tools/Mods/Settings/About: 32, 20, 32, 20

---

## Current Animations (Only 3)

### 1. Nav Button Hover Glow (widgets.py:25-48)
```python
def enable_hover_glow(widget, duration=150):
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)
    anim = QPropertyAnimation(effect, b"opacity", widget)
    anim.setDuration(duration)
    anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
    # On enter: fade to 0.85 (DIMS — unconventional)
    # On leave: fade back to 1.0
```
Applied to: All 7 nav buttons in sidebar
**Problem**: Dims on hover instead of brightening. Most launchers brighten/glow.

### 2. Splash Fade-Out (splash.py:66-75)
```python
fade_out = QPropertyAnimation(self, b"windowOpacity", self)
fade_out.setDuration(150)
fade_out.setStartValue(1.0)
fade_out.setEndValue(0.0)
fade_out.setEasingCurve(QEasingCurve.Type.InCubic)
```
**Missing**: No fade-IN. Splash appears instantly at full opacity.

### 3. Login Slideshow Timer (login.py:140)
```python
self._slide_timer.start(5000)  # 5 second interval
```
**Missing**: No cross-fade between slides. Hard cut.

---

## QSS Pseudo-States Used

| State | Elements | Effect |
|-------|----------|--------|
| `:hover` | Nav buttons, Primary/Success/Danger/Tool/Modal buttons, Scrollbar, List items, Checkbox, Theme cards | Background color change |
| `:checked` | Nav buttons, Checkbox | Accent color background |
| `:disabled` | Primary/Success/Danger buttons | Muted colors |
| `:selected` | List items | Accent background |

### Missing QSS States (Not Used Anywhere)
- `:pressed` — No click feedback on any button
- `:focus` — No focus ring styling
- `:active` — No active window styling

---

## Palette Structure (28 keys per theme)

```python
PALETTE = {
    # Backgrounds (6)
    "bg_base": "#0a0b0f",        # Main background
    "bg_surface": "#111318",     # Cards, dialogs
    "bg_elevated": "#181b22",    # Panels, list widgets
    "bg_hover": "#1f232c",       # Hover states
    "bg_active": "#272b36",      # Active/pressed
    "bg_sidebar": "#08090c",     # Sidebar background

    # Borders (3)
    "border_subtle": "#22252d",
    "border_default": "#2c303a",
    "border_focus": "#7c6cf6",

    # Accent (4)
    "accent": "#7c6cf6",         # Primary accent
    "accent_hover": "#9284f9",   # Accent hover
    "accent_muted": "#4c3fb8",   # Muted accent
    "accent_2": "#2dd4bf",       # Secondary accent

    # Status (6)
    "success": "#2dd4bf",
    "success_hover": "#14b8a6",
    "info": "#60a5fa",
    "warning": "#fbbf24",
    "danger": "#fb7185",
    "danger_hover": "#f43f5e",

    # Text (4)
    "text_primary": "#e8e9ed",
    "text_secondary": "#a1a5b0",
    "text_muted": "#666b78",
    "text_bright": "#ffffff",

    # Controls (5)
    "btn_disabled_bg": "#22252d",
    "btn_disabled_text": "#565b66",
    "scrollbar_handle": "#2c303a",
    "scrollbar_hover": "#3a3f4b",
    "checkbox_border": "#3a3f4b",
}
```

### 7 Themes
| Name | Accent | Style |
|------|--------|-------|
| Violet | #7c6cf6 | Deep violet + teal |
| Coral | #ff6b4a | Burnt coral + amber |
| Slate | #5b8def | Steel blue + gray |
| Ember | #ff6b4a | Warm coral + amber |
| Forest | #4ade80 | Green + lime |
| Plum | #c77dff | Purple + pink |
| Mono | #e5e5e5 | White/gray |

---

## Module-Level Color Globals (theme.py)

These are imported by other modules as `theme.ACCENT`, `theme.BG_BASE`, etc. and updated when theme switches:

```python
BG_BASE, BG_SURFACE, BG_ELEVATED, BG_HOVER, BG_ACTIVE, BG_SIDEBAR
BORDER_SUBTLE, BORDER_FOCUS
ACCENT, ACCENT_HOVER, ACCENT_2
SUCCESS, SUCCESS_HOVER, INFO, WARNING, DANGER, DANGER_HOVER
TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_BRIGHT
CURRENT_THEME
```

---

## Key Classes

### LauncherApp (window/main.py)
- Main window controller
- Inherits: GameActionsMixin, RegionEditorMixin, ModManagerMixin, ItchProfileMixin, UpdaterMixin
- Has: `self.window` (QMainWindow), `self.pages` (QStackedWidget), `self.nav_buttons` dict
- Page switch: `_switch_page(index, label)` — instant swap, no animation

### HeroBanner (widgets.py)
- Custom `paintEvent()` — draws gradient bg, glow orbs, accent line, title, subtitle, version badge
- Fixed 180px height
- Painted elements: title (24pt), subtitle (13pt), badge (11pt)
- No animation — entirely static

### SplashScreen (splash.py)
- PNG-based splash (700×400)
- Shows status text at bottom
- Fade-out only (150ms)
- No fade-in

### LoginWindow (login.py)
- Split: left content (40px margins) + right sidebar (400px fixed)
- Right sidebar: image/GIF/slideshow with gradient fallback
- Slideshow: 5s interval, hard cut between slides
- OAuth flow opens browser, polls localhost

### _ThemeCard (dialogs.py)
- Fixed 140×78px clickable frame
- Custom `paintEvent()` — gradient bar, theme name, accent hex
- Hover: border color changes (CSS only, no animation)

---

## Animation Opportunities (Ranked by Impact)

### Tier 1 — High Impact, Low Effort

1. **Page cross-fade transition**
   - Where: `_switch_page()` in main.py:722
   - How: Fade old page opacity 1→0, new page 0→1 using QGraphicsOpacityEffect
   - Effort: ~20 lines
   - Impact: HIGH — pages currently swap instantly

2. **Button :pressed state**
   - Where: theme.py QSS
   - How: Add `:pressed` rules with subtle brightness shift or transform
   - Effort: ~5 lines per button type
   - Impact: HIGH — no click feedback exists

3. **Splash fade-in**
   - Where: splash.py:59
   - How: Animate windowOpacity 0→1 over 300ms on show
   - Effort: ~5 lines
   - Impact: HIGH — splash appears abruptly

4. **Slideshow cross-fade**
   - Where: login.py _RightSidebar
   - How: Two overlaid QLabels with opposing opacity animations
   - Effort: ~30 lines
   - Impact: HIGH — slides change with hard cut

### Tier 2 — Medium Impact, Medium Effort

5. **Nav button slide-in on startup** — Stagger-animate from left with delays
6. **Progress bar shimmer** — Animated gradient pulse during download
7. **Button hover glow (shadow)** — Replace opacity dim with QGraphicsDropShadowEffect
8. **Theme switch cross-fade** — Global opacity dip during theme change
9. **Main action button pulse** — Breathing glow when game is "PLAYING"

### Tier 3 — Polish

10. **Hero banner animated gradient** — Subtle glow orb movement via QTimer repaint
11. **Stagger list item fade-in** — Sequential opacity animation on page load
12. **Status dot pulse** — Breathing opacity on status indicator
13. **Window open animation** — Scale from 95% to 100% on first show

---

## Animation Classes Available in PySide6

```python
from PySide6.QtCore import (
    QPropertyAnimation,        # Animate any Qt property
    QEasingCurve,              # InOutQuad, OutBack, OutElastic, etc.
    QParallelAnimationGroup,   # Run multiple animations simultaneously
    QSequentialAnimationGroup, # Chain animations in sequence
    QTimeLine,                 # Timeline-based control
    QVariantAnimation,         # Generic value interpolation
)
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,    # Opacity animation
    QGraphicsDropShadowEffect, # Animated shadow
    QGraphicsBlurEffect,       # Blur transitions
    QGraphicsColorizeEffect,   # Color wash
)
```

### Useful Easing Curves
- `QEasingCurve.Type.InOutQuad` — Smooth acceleration/deceleration
- `QEasingCurve.Type.OutBack` — Overshoot then settle (bouncy)
- `QEasingCurve.Type.OutElastic` — Spring-like bounce
- `QEasingCurve.Type.OutCubic` — Fast start, smooth stop
- `QEasingCurve.Type.InOutCubic` — Smooth S-curve

---

## Current Button Types & Heights

| Type | ObjectName | Height | Padding | Font |
|------|-----------|--------|---------|------|
| Nav | (none) | 42px | 10px 16px | 14px |
| Primary | primaryBtn | 38px | 10px 20px | 14px bold |
| Success | successBtn | 38px | 10px 20px | 14px bold |
| Danger | dangerBtn | 38px | 10px 20px | 14px bold |
| Tool | toolBtn | 38px | 10px 16px | 14px |
| Modal Primary | modalPrimary | auto | 10px 16px | 13px bold |
| Modal Secondary | modalSecondary | auto | 10px 16px | 13px |
| Modal Danger | modalDanger | auto | 10px 16px | 13px |

---

## Modules That Import theme.* Globals

| File | Globals Used |
|------|-------------|
| widgets.py | ACCENT, ACCENT_2, BG_BASE, BG_SURFACE, BG_ELEVATED, TEXT_BRIGHT, TEXT_SECONDARY |
| login.py | ACCENT, ACCENT_2, BG_BASE, BG_SURFACE, WARNING |
| mod_warnings.py | DANGER, WARNING, BG_SURFACE, BORDER_SUBTLE, BG_ELEVATED, TEXT_PRIMARY, BG_BASE, TEXT_SECONDARY |
| mod_details.py | BG_SURFACE, BORDER_SUBTLE, BG_ELEVATED, TEXT_PRIMARY, TEXT_BRIGHT, ACCENT, TEXT_SECONDARY, TEXT_MUTED |
| window/main.py | TEXT_MUTED, SUCCESS, INFO, DANGER, WARNING, TEXT_SECONDARY |
| window/region_editor.py | SUCCESS, WARNING, INFO, DANGER |

---

## Notes for Animation Expert

1. **QSS cannot animate** — Qt Style Sheets are static. All transitions must use QPropertyAnimation in Python.
2. **QStackedWidget has no built-in transition** — Must manually animate opacity/position of pages.
3. **Custom paintEvent widgets** (HeroBanner, ThemeCard) — Cannot use QSS pseudo-states; animations must be in Python.
4. **Theme switching is instant** — app.setStyleSheet() replaces all QSS at once. Cross-fade requires global opacity animation.
5. **Worker threads** — Network calls run in QThread via Worker class. UI updates must be dispatched to main thread via `_invoke_main()`.
6. **Sidebar is fixed 200px** — Do not make responsive.
7. **Hero is fixed 180px** — Do not make responsive.
8. **7 nav buttons** — Game, Tools, Profile, Mods, Settings, About, Assets (Assets is disabled).
