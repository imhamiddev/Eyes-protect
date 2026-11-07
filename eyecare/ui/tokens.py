"""Design tokens: the single source of truth for the Eye Care visual identity."""
from __future__ import annotations

from dataclasses import dataclass

ACCENT = "#D2F36B"


@dataclass(frozen=True)
class Palette:
    name: str
    bg: str
    surface: str          # secondary background / cards
    surface_hover: str
    surface_raised: str   # inputs, segmented tracks
    border: str           # subtle, low-opacity
    text: str
    text_muted: str
    text_faint: str
    accent: str
    on_accent: str
    accent_soft: str      # low-opacity accent wash
    danger: str
    shadow: str
    overlay: str


DARK = Palette(
    name="dark",
    bg="#111318", surface="#1C2028", surface_hover="#232833", surface_raised="#171A21",
    border="rgba(255,255,255,0.07)", text="#FFFFFF", text_muted="#A1A1AA", text_faint="#6B6F7A",
    accent=ACCENT, on_accent="#14180A", accent_soft="rgba(210,243,107,0.14)",
    danger="#F08A7E", shadow="rgba(0,0,0,0.35)", overlay="rgba(10,12,16,0.94)",
)

LIGHT = Palette(
    name="light",
    bg="#F6F4EF", surface="#FFFFFF", surface_hover="#F0EDE6", surface_raised="#EFECE5",
    border="rgba(30,28,20,0.09)", text="#1B1D22", text_muted="#6B6B72", text_faint="#9A9AA0",
    accent=ACCENT, on_accent="#1B2208", accent_soft="rgba(150,185,30,0.18)",
    danger="#C4574A", shadow="rgba(60,50,20,0.10)", overlay="rgba(246,244,239,0.96)",
)

PALETTES = {"dark": DARK, "light": LIGHT}

# Spacing scale (px)
SP = {"xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 24, "xxl": 32}

# Corner radii (px)
RADIUS = {"sm": 8, "md": 12, "lg": 16, "xl": 22, "pill": 999}

# Typography (px sizes, weights)
FONT_SIZE = {"caption": 11, "label": 12, "body": 13, "title": 15, "h2": 20, "h1": 28, "display": 64}

# Component dimensions
SIZE = {
    "sidebar": 208, "control_h": 36, "button_h": 40, "icon_btn": 36, "toggle_w": 42,
    "toggle_h": 24, "slider_h": 22, "window_w": 980, "window_h": 660,
}

# Animation timing (ms)
MOTION = {"fast": 120, "base": 200, "slow": 360}

SHADOW = {"blur": 28, "y": 8}
