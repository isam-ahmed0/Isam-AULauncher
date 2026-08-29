"""
Theme — palette, gradient cache, texture generators, widget helpers.
Gaming-grade aesthetic: deep darks, vivid accents, soft glows, grain texture.
"""
import colorsys
import math
import tkinter as tk
from tkinter import ttk
from typing import Dict, Tuple, Optional

# Lazy-import PIL only when needed (saves ~200ms at startup)
_PIL = None
_PhotoImage = None


def _pil():
    global _PIL
    if _PIL is None:
        from PIL import Image, ImageDraw, ImageFilter, ImageTk
        _PIL = Image
    return _PIL


def _photo_image():
    global _PhotoImage
    if _PhotoImage is None:
        from PIL import ImageTk
        _PhotoImage = ImageTk.PhotoImage
    return _PhotoImage


# ---------------------------------------------------------------------------
# Palette — gaming aesthetic
# ---------------------------------------------------------------------------
class Pal:
    FONT = "Segoe UI"

    # Backgrounds — deep, rich, not flat
    BG_DARK = "#0c0e14"
    BG_MEDIUM = "#12151e"
    BG_LIGHT = "#1a1f2e"
    BG_HOVER = "#222840"
    BG_CARD = "#151a28"
    BG_SIDEBAR = "#10131c"

    # Borders & shadows
    BORDER = "#1e2a42"
    BORDER_LIGHT = "#2a3554"
    SHADOW = "#06080e"
    GLOW_PURPLE = "#7c5cff"
    GLOW_BLUE = "#00d4ff"

    # Accents — vivid, punchy
    ACCENT = "#8b5cf6"
    ACCENT_2 = "#06b6d4"
    GREEN = "#10b981"
    GREEN_HOVER = "#059669"
    GREEN_GLOW = "#1a3828"
    BLUE = "#3b82f6"
    BLUE_HOVER = "#2563eb"
    BLUE_GLOW = "#1a2840"
    RED = "#ef4444"
    RED_HOVER = "#dc2626"
    RED_GLOW = "#3a1a1a"
    PURPLE = "#a855f7"
    PURPLE_HOVER = "#9333ea"
    PURPLE_GLOW = "#2a1a38"
    ORANGE = "#f59e0b"
    ORANGE_HOVER = "#d97706"
    CYAN = "#22d3ee"

    # Text
    TEXT = "#f1f5f9"
    TEXT_DIM = "#64748b"
    TEXT_BRIGHT = "#ffffff"
    TEXT_MUTED = "#475569"

    # Titlebar
    TITLEBAR_H = 40
    BORDER_W = 1

    # Gradients (start, end) for various elements
    GRAD_HERO = ("#1a1040", "#0c1220")
    GRAD_STRIP = ("#06b6d4", "#8b5cf6")
    GRAD_BTN_GREEN = ("#10b981", "#059669")
    GRAD_BTN_BLUE = ("#3b82f6", "#2563eb")
    GRAD_BTN_PURPLE = ("#a855f7", "#7c3aed")
    GRAD_CARD = ("#1a1f2e", "#12151e")


# ---------------------------------------------------------------------------
# Gradient cache — avoid re-rendering identical gradients
# ---------------------------------------------------------------------------
_GRADIENT_CACHE: Dict[tuple, object] = {}
_GRADIENT_CACHE_ORDER: list = []
_GRADIENT_CACHE_MAX = 32


def _hex_rgb(v: str) -> Tuple[int, int, int]:
    v = v.lstrip("#")
    return (int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16))


def cached_gradient(width: int, height: int, c1: str, c2: str):
    """Return a PhotoImage of a linear gradient. Cached by (w,h,c1,c2)."""
    key = (width, height, c1, c2)
    if key in _GRADIENT_CACHE:
        return _GRADIENT_CACHE[key]

    Image = _pil()
    PhotoImage = _photo_image()

    r1, g1, b1 = _hex_rgb(c1)
    r2, g2, b2 = _hex_rgb(c2)

    palette = Image.new("RGB", (256, 1))
    px = palette.load()
    for i in range(256):
        t = i / 255
        px[i, 0] = (
            int(r1 + (r2 - r1) * t),
            int(g1 + (g2 - g1) * t),
            int(b1 + (b2 - b1) * t),
        )

    img = palette.resize((max(width, 2), max(height, 2)))
    photo = PhotoImage(img)

    _GRADIENT_CACHE[key] = photo
    _GRADIENT_CACHE_ORDER.append(key)
    while len(_GRADIENT_CACHE_ORDER) > _GRADIENT_CACHE_MAX:
        old = _GRADIENT_CACHE_ORDER.pop(0)
        _GRADIENT_CACHE.pop(old, None)

    return photo


def cached_multistop_gradient(width: int, height: int, stops: list):
    """Gradient with multiple color stops. stops = [(pos, "#hex"), ...]"""
    key = ("multi", width, height) + tuple(stops)
    if key in _GRADIENT_CACHE:
        return _GRADIENT_CACHE[key]

    Image = _pil()
    PhotoImage = _photo_image()

    palette = Image.new("RGB", (512, 1))
    px = palette.load()

    for i in range(512):
        t = i / 511
        seg = 0
        for s in range(len(stops) - 1):
            if t >= stops[s][0]:
                seg = s
        p1, c1 = stops[seg]
        p2, c2 = stops[min(seg + 1, len(stops) - 1)]
        seg_len = max(p2 - p1, 0.001)
        local_t = min(max((t - p1) / seg_len, 0), 1)
        r1, g1, b1 = _hex_rgb(c1)
        r2, g2, b2 = _hex_rgb(c2)
        px[i, 0] = (
            int(r1 + (r2 - r1) * local_t),
            int(g1 + (g2 - g1) * local_t),
            int(b1 + (b2 - b1) * local_t),
        )

    img = palette.resize((max(width, 2), max(height, 2)))
    photo = PhotoImage(img)

    _GRADIENT_CACHE[key] = photo
    _GRADIENT_CACHE_ORDER.append(key)
    while len(_GRADIENT_CACHE_ORDER) > _GRADIENT_CACHE_MAX:
        old = _GRADIENT_CACHE_ORDER.pop(0)
        _GRADIENT_CACHE.pop(old, None)

    return photo


# ---------------------------------------------------------------------------
# Noise / grain texture — generated once, reused
# ---------------------------------------------------------------------------
_NOISE_CACHE = None


def get_noise_texture(width: int, height: int, alpha: int = 12):
    """Semi-transparent grain overlay. Generated once and tiled."""
    global _NOISE_CACHE
    if _NOISE_CACHE is not None:
        return _NOISE_CACHE

    Image = _pil()
    import random
    random.seed(42)
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    px = img.load()
    for y in range(height):
        for x in range(width):
            v = random.randint(0, 255)
            px[x, y] = (v, v, v, alpha)
    _NOISE_CACHE = img
    return img


# ---------------------------------------------------------------------------
# Glow effect — soft blurred circle behind an element
# ---------------------------------------------------------------------------
def make_glow(width: int, height: int, color: str, radius: int = 40):
    """Create a soft radial glow Image."""
    Image = _pil()
    from PIL import ImageFilter
    r, g, b = _hex_rgb(color)
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    from PIL import ImageDraw as ID
    draw = ID.Draw(img)
    cx, cy = width // 2, height // 2
    draw.ellipse(
        [cx - radius, cy - radius, cx + radius, cy + radius],
        fill=(r, g, b, 40)
    )
    img = img.filter(ImageFilter.GaussianBlur(radius // 2))
    return img


# ---------------------------------------------------------------------------
# Rounded rectangle mask
# ---------------------------------------------------------------------------
def rounded_rect_mask(width: int, height: int, radius: int = 8):
    """Return a PIL mask image with rounded corners."""
    Image = _pil()
    from PIL import ImageDraw as ID
    mask = Image.new("L", (width, height), 0)
    draw = ID.Draw(mask)
    draw.rounded_rectangle([0, 0, width - 1, height - 1], radius=radius, fill=255)
    return mask


# ---------------------------------------------------------------------------
# Animated accent strip helper
# ---------------------------------------------------------------------------
class HueAnimator:
    """Cycles hue for an accent strip. Call step() on a timer."""

    def __init__(self, canvas, y0=0, height=3, speed=0.3):
        self.canvas = canvas
        self.y0 = y0
        self.height = height
        self.speed = speed
        self.hue = 0.0
        self._running = False

    def start(self):
        self._running = True
        self._step()

    def stop(self):
        self._running = False

    def _step(self):
        if not self._running:
            return
        self.hue = (self.hue + self.speed) % 360
        c1 = _hue_to_hex(self.hue)
        c2 = _hue_to_hex((self.hue + 60) % 360)
        w = max(self.canvas.winfo_width(), 2)
        photo = cached_gradient(w, self.height, c1, c2)
        self.canvas.delete("all")
        self.canvas.create_image(0, self.y0, image=photo, anchor="nw")
        self.canvas.after(50, self._step)


def _hue_to_hex(h: float) -> str:
    r, g, b = colorsys.hsv_to_rgb(h / 360, 0.7, 0.85)
    return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"


# ---------------------------------------------------------------------------
# Widget helpers
# ---------------------------------------------------------------------------
def make_title_button(parent, text, cmd, hover_bg, font_size=13):
    """Titlebar control button (minimize, close, etc)."""
    btn = tk.Button(
        parent, text=text, font=(Pal.FONT, font_size, "bold"),
        bg=Pal.BG_DARK, fg=Pal.TEXT_DIM,
        activebackground=hover_bg, activeforeground=Pal.TEXT_BRIGHT,
        relief=tk.FLAT, bd=0, cursor="hand2", command=cmd, width=3,
    )
    btn.pack(side=tk.RIGHT, fill=tk.Y)
    btn.bind("<Enter>", lambda e, b=btn, c=hover_bg: b.config(bg=c, fg=Pal.TEXT_BRIGHT))
    btn.bind("<Leave>", lambda e, b=btn: b.config(bg=Pal.BG_DARK, fg=Pal.TEXT_DIM))
    return btn


def make_side_button(parent, text, cmd, accent, font_size=10):
    """Sidebar action button with hover glow."""
    btn = tk.Button(
        parent, text=text, font=(Pal.FONT, font_size, "bold"),
        bg=Pal.BG_LIGHT, fg=Pal.TEXT,
        activebackground=accent, activeforeground="white",
        relief=tk.FLAT, cursor="hand2", command=cmd,
        anchor=tk.W, padx=14, pady=9, borderwidth=0,
    )
    btn.bind("<Enter>", lambda e, b=btn, c=accent: b.config(bg=c))
    btn.bind("<Leave>", lambda e, b=btn: b.config(bg=Pal.BG_LIGHT))
    return btn


def make_action_button(parent, text, cmd, bg_color, hover_color, font_size=11, wide=False):
    """Main action button with gradient-like feel."""
    btn = tk.Button(
        parent, text=text, font=(Pal.FONT, font_size, "bold"),
        bg=bg_color, fg=Pal.TEXT_BRIGHT,
        activebackground=hover_color, activeforeground="white",
        relief=tk.FLAT, cursor="hand2", command=cmd,
        padx=22 if not wide else 32, pady=14 if not wide else 16,
        borderwidth=0,
    )
    btn.bind("<Enter>", lambda e, b=btn, c=hover_color: b.config(bg=c))
    btn.bind("<Leave>", lambda e, b=btn, c=bg_color: b.config(bg=c))
    return btn


def make_divider(parent):
    """Thin horizontal divider."""
    tk.Frame(parent, bg=Pal.BG_LIGHT, height=1).pack(fill=tk.X, padx=14, pady=6)


def make_section_label(parent, text):
    """Small uppercase section header."""
    tk.Label(
        parent, text=text, font=(Pal.FONT, 9, "bold"),
        bg=Pal.BG_SIDEBAR, fg=Pal.TEXT_MUTED, anchor=tk.W,
    ).pack(anchor=tk.W, pady=(0, 6))


def setup_ttk_styles():
    """Configure ttk styles for progress bars, scrollbars."""
    s = ttk.Style()
    s.theme_use("clam")
    s.configure(
        "Custom.Horizontal.TProgressbar",
        troughcolor=Pal.BG_MEDIUM,
        background=Pal.ACCENT,
        borderwidth=0,
        thickness=8,
    )
    s.configure(
        "TScrollbar",
        background=Pal.BG_LIGHT,
        troughcolor=Pal.BG_DARK,
        borderwidth=0,
        arrowcolor=Pal.TEXT_DIM,
    )
