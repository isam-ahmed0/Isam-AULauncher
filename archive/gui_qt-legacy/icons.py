"""Phosphor icon helpers for the launcher UI.

Phosphor's SVG files use ``currentColor`` for their stroke/fill, so they can be
re-tinted at runtime to match the active theme. Qt cannot resolve CSS
``currentColor`` inside an SVG, so each icon is rendered to a pixmap after
replacing ``currentColor`` with the desired hex color.

Rendering happens at 2x and the pixmap reports a device-pixel-ratio of 2 so the
icons stay crisp on HiDPI displays while ``QIcon``/widgets can treat them as
20-26px logical sizes.
"""
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap, QTransform
from PySide6.QtSvg import QSvgRenderer

import gui_qt.theme as theme

_PHOSPHOR_DIR = Path(__file__).parent.parent / "resources" / "phosphor-icons" / "SVGs" / "regular"

_pixmap_cache = {}
_icon_cache = {}


def render_svg(name: str, color: str, size: int = 20, mirror: bool = False) -> QPixmap:
    """Render one Phosphor SVG to a HiDPI pixmap tinted with ``color``."""
    key = (name, color.lower(), size, mirror)
    cached = _pixmap_cache.get(key)
    if cached is not None:
        return cached

    path = _PHOSPHOR_DIR / f"{name}.svg"
    if not path.exists():
        pm = QPixmap(size * 2, size * 2)
        pm.fill(Qt.GlobalColor.transparent)
        pm.setDevicePixelRatio(2.0)
        _pixmap_cache[key] = pm
        return pm

    svg = path.read_text(encoding="utf-8").replace("currentColor", color)

    pm = QPixmap(size * 2, size * 2)
    pm.fill(Qt.GlobalColor.transparent)
    renderer = QSvgRenderer(svg.encode("utf-8"))
    painter = QPainter(pm)
    renderer.render(painter)
    painter.end()
    if mirror:
        pm = pm.transformed(QTransform(-1, 0, 0, 1, 0, 0).translate(-pm.width(), 0))
    pm.setDevicePixelRatio(2.0)
    _pixmap_cache[key] = pm
    return pm


def icon_for(name: str, color: str, size: int = 20, mirror: bool = False) -> QIcon:
    """Single-state icon helper."""
    return QIcon(render_svg(name, color, size, mirror=mirror))


def nav_icon(name: str) -> QIcon:
    """Build a theme-aware multi-state QIcon for a sidebar nav button.

    States: regular=text_secondary, hover=text_primary, checked/pressed=
    text_bright, disabled=text_muted.
    """
    cache_key = (name, theme.CURRENT_THEME)
    cached = _icon_cache.get(cache_key)
    if cached is not None:
        return cached

    ic = QIcon()
    ic.addPixmap(render_svg(name, theme.TEXT_SECONDARY), QIcon.Mode.Normal, QIcon.State.Off)
    ic.addPixmap(render_svg(name, theme.TEXT_PRIMARY), QIcon.Mode.Active, QIcon.State.Off)
    ic.addPixmap(render_svg(name, theme.TEXT_BRIGHT), QIcon.Mode.Normal, QIcon.State.On)
    ic.addPixmap(render_svg(name, theme.TEXT_BRIGHT), QIcon.Mode.Active, QIcon.State.On)
    ic.addPixmap(render_svg(name, theme.TEXT_MUTED), QIcon.Mode.Disabled, QIcon.State.Off)
    _icon_cache[cache_key] = ic
    return ic


def refresh_nav_buttons(window):
    """Rebuild nav button icons from the current theme."""
    buttons = getattr(window, "nav_buttons", None)
    if not buttons:
        return
    for btn in buttons.values():
        name = getattr(btn, "_nav_icon_name", None)
        if name:
            btn.setIcon(nav_icon(name))


def clear_caches():
    _pixmap_cache.clear()
    _icon_cache.clear()