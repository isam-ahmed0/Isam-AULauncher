"""Theme palettes for Isam AULauncher."""
import json
import os
import logging
from pathlib import Path
from .violet import PALETTE as VIOLET
from .coral import PALETTE as CORAL
from .slate import PALETTE as SLATE
from .ember import PALETTE as EMBER
from .forest import PALETTE as FOREST
from .plum import PALETTE as PLUM
from .mono import PALETTE as MONO

BUILTIN = {
    "Violet": VIOLET,
    "Coral": CORAL,
    "Slate": SLATE,
    "Ember": EMBER,
    "Forest": FOREST,
    "Plum": PLUM,
    "Mono": MONO,
}

THEMES = dict(BUILTIN)

CUSTOM_THEMES_DIR = Path(os.environ.get("APPDATA", "")) / "IsamAULauncher" / "themes"


def load_custom_themes():
    """Load custom theme JSON files from the user themes directory."""
    if not CUSTOM_THEMES_DIR.exists():
        return
    for f in sorted(CUSTOM_THEMES_DIR.glob("*.json")):
        try:
            with open(f, "r") as fh:
                palette = json.load(fh)
            name = f.stem
            if _valid_palette(palette):
                THEMES[name] = palette
        except Exception as e:
            logging.warning(f"Failed to load custom theme {f.name}: {e}")


def save_custom_theme(name: str, palette: dict) -> bool:
    """Save a custom theme to the user themes directory."""
    try:
        CUSTOM_THEMES_DIR.mkdir(parents=True, exist_ok=True)
        path = CUSTOM_THEMES_DIR / f"{name}.json"
        with open(path, "w") as f:
            json.dump(palette, f, indent=2)
        THEMES[name] = palette
        return True
    except Exception as e:
        logging.error(f"Failed to save custom theme {name}: {e}")
        return False


def delete_custom_theme(name: str) -> bool:
    """Delete a custom theme file and remove from THEMES dict."""
    if name in BUILTIN:
        return False
    path = CUSTOM_THEMES_DIR / f"{name}.json"
    try:
        if path.exists():
            path.unlink()
        THEMES.pop(name, None)
        return True
    except Exception as e:
        logging.error(f"Failed to delete custom theme {name}: {e}")
        return False


def is_custom_theme(name: str) -> bool:
    return name in THEMES and name not in BUILTIN


def _valid_palette(p: dict) -> bool:
    """Check that a palette dict has all required keys."""
    required = {
        "bg_base", "bg_surface", "bg_elevated", "bg_hover", "bg_active",
        "bg_sidebar", "border_subtle", "border_default", "border_focus",
        "accent", "accent_hover", "accent_muted", "accent_2",
        "success", "success_hover", "info", "warning",
        "danger", "danger_hover",
        "text_primary", "text_secondary", "text_muted", "text_bright",
        "btn_disabled_bg", "btn_disabled_text",
        "scrollbar_handle", "scrollbar_hover", "checkbox_border",
    }
    return required.issubset(p.keys())
