"""Colour-temperature maths used by the night light and the dimmer."""
from __future__ import annotations

import math

NEUTRAL_KELVIN = 6500
MIN_KELVIN = 1900
MIN_BRIGHTNESS = 0.30  # Windows rejects gamma ramps that are too dark.


def kelvin_to_rgb(kelvin: float) -> tuple[float, float, float]:
    """Approximate black-body colour as RGB multipliers in 0..1 (Tanner Helland)."""
    t = max(1000.0, min(40000.0, float(kelvin))) / 100.0
    if t <= 66:
        r = 255.0
        g = 99.4708025861 * math.log(t) - 161.1195681661
    else:
        r = 329.698727446 * ((t - 60) ** -0.1332047592)
        g = 288.1221695283 * ((t - 60) ** -0.0755148492)
    if t >= 66:
        b = 255.0
    elif t <= 19:
        b = 0.0
    else:
        b = 138.5177312231 * math.log(t - 10) - 305.0447927307
    clamp = lambda v: max(0.0, min(255.0, v)) / 255.0  # noqa: E731
    return clamp(r), clamp(g), clamp(b)


def strength_to_kelvin(strength: int) -> int:
    """Map a 0..100 warmth slider onto 6500K (off) .. 1900K (very warm)."""
    strength = max(0, min(100, int(strength)))
    return round(NEUTRAL_KELVIN - (NEUTRAL_KELVIN - MIN_KELVIN) * strength / 100)


def kelvin_to_strength(kelvin: int) -> int:
    span = NEUTRAL_KELVIN - MIN_KELVIN
    return max(0, min(100, round((NEUTRAL_KELVIN - kelvin) * 100 / span)))


def channel_multipliers(kelvin: float, brightness: float) -> tuple[float, float, float]:
    """Combine warmth and brightness (0..1) into per-channel gamma multipliers."""
    brightness = max(MIN_BRIGHTNESS, min(1.0, brightness))
    r, g, b = kelvin_to_rgb(kelvin)
    nr, ng, nb = kelvin_to_rgb(NEUTRAL_KELVIN)
    return (
        min(1.0, r / nr) * brightness,
        min(1.0, g / ng) * brightness,
        min(1.0, b / nb) * brightness,
    )


def build_ramp(multipliers: tuple[float, float, float]) -> list[list[int]]:
    """Build a 3x256 16-bit gamma ramp (the layout SetDeviceGammaRamp expects)."""
    ramp: list[list[int]] = []
    for m in multipliers:
        ramp.append([min(65535, int(round(i * 257 * m))) for i in range(256)])
    return ramp
