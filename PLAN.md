# Isam AULauncher — Premium GUI Redesign (Completed)

## What Was Done

### 1. Custom Fonts Bundled
- **Inter** font family (Regular, Medium, SemiBold, Bold) added to `src/launcher/resources/fonts/`
- Font loading system in `theme.py` with size constants: `FONT_TITLE=28`, `FONT_HEADING=20`, `FONT_SUBHEADING=16`, `FONT_BODY=14`, `FONT_SMALL=12`, `FONT_LABEL=11`

### 2. Steam-Like Minimal Palette (`theme.py`)
- Muted dark backgrounds: `BG_BASE(18,20,26)` → `BG_SURFACE(24,27,34)` → `BG_ELEVATED(32,36,46)`
- Subtle hover/active states: `BG_HOVER(40,44,56)` → `BG_ACTIVE(48,52,66)`
- Accent: Indigo `(99,102,241)` used sparingly
- Semantic colors: `SUCCESS(52,211,153)`, `INFO(96,165,250)`, `WARNING(251,191,36)`, `DANGER(248,113,113)`
- Enhanced global theme: 10px window rounding, 8px frame rounding, more padding, thinner scrollbar

### 3. Animated Hero Banner (`window.py`)
- 18 floating particles drifting upward with subtle alpha
- 3 pulsing glow orbs using `sin(time)` oscillation
- 2px gradient accent line (indigo → cyan) at bottom
- Version badge as rounded pill (not rectangle)
- ~30fps animation via threading timer

### 4. Card-Based Game Tab Layout
- Version info card (BG_SURFACE, 10px rounding, 24px padding)
- Status & progress card with animated dot indicator
- Full-width primary action button (56px height)
- Quick Actions row: **Open Folder**, **Change Location**, **Verify Files**, **Create Shortcut**
- AUnlocker install card with accent button

### 5. Redesigned Modals
- All modals: BG_SURFACE background, 12px rounding, colored header with separator
- Settings: Clean checkbox layout with descriptions, full-width Save button
- About: Proper typography hierarchy, link buttons in horizontal row
- Confirm (Yes/No): Warning-colored header, right-aligned No/Yes buttons
- Kebab/Options: Categorized sections (Game, Shortcuts, Other), each button 36px height

### 6. Bug Fixes
- **Duplicate tags fixed**: Game tab status uses `game_status_icon`/`game_status_text`, status bar uses `sb_status_icon`/`sb_status_text`
- `_set_status()` updates both locations
- File dialog now properly created in `_build_ui()`

### 7. Top Bar Redesign
- Vertical separator between brand name and app name
- Tab buttons with accent theme (not full background fill)
- Settings + "..." buttons in elevated style

### 8. Status Bar
- BG_SURFACE background, 36px height
- Pulsing dot indicator when busy
- Clean typography with version + credit

## Files Modified
- `src/launcher/theme.py` — Complete rewrite (336 lines)
- `src/launcher/window.py` — Complete rewrite (1140 lines)
- `src/launcher/resources/fonts/` — Inter TTF files added (4 files)
