"""Parsing of global shortcut strings like 'Ctrl+Alt+N' into Win32 RegisterHotKey arguments."""
from __future__ import annotations

MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN, MOD_NOREPEAT = 0x1, 0x2, 0x4, 0x8, 0x4000

ACTIONS = ("night_light", "break_now", "pause", "quiet")
DEFAULTS = {
    "night_light": "Ctrl+Alt+N",
    "break_now": "Ctrl+Alt+B",
    "pause": "Ctrl+Alt+P",
    "quiet": "Ctrl+Alt+Q",
}

_MODIFIERS = {
    "ctrl": ("Ctrl", MOD_CONTROL), "control": ("Ctrl", MOD_CONTROL),
    "alt": ("Alt", MOD_ALT),
    "shift": ("Shift", MOD_SHIFT),
    "win": ("Win", MOD_WIN), "meta": ("Win", MOD_WIN), "super": ("Win", MOD_WIN),
}
_ORDER = ["Ctrl", "Alt", "Shift", "Win"]
_NAMED = {
    "space": 0x20, "tab": 0x09, "return": 0x0D, "enter": 0x0D, "backspace": 0x08,
    "pgup": 0x21, "pageup": 0x21, "pgdown": 0x22, "pagedown": 0x22, "end": 0x23, "home": 0x24,
    "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28, "ins": 0x2D, "insert": 0x2D,
    "del": 0x2E, "delete": 0x2E,
}


def _key_code(name: str) -> tuple[str, int]:
    n = name.strip().lower()
    if len(n) == 1 and n.isascii() and n.isalpha():
        return n.upper(), ord(n.upper())
    if len(n) == 1 and n.isdigit():
        return n, ord(n)
    if n.startswith("f") and n[1:].isdigit() and 1 <= int(n[1:]) <= 24:
        return f"F{int(n[1:])}", 0x70 + int(n[1:]) - 1
    if n in _NAMED:
        return name.strip().title(), _NAMED[n]
    raise ValueError(f"unsupported key: {name!r}")


def parse_combo(text: str) -> tuple[int, int]:
    """'Ctrl+Alt+N' -> (modifier flags, virtual-key code). Needs at least one modifier."""
    mods, vk = 0, None
    for part in [p for p in text.replace(" ", "").split("+") if p]:
        low = part.lower()
        if low in _MODIFIERS:
            mods |= _MODIFIERS[low][1]
        elif vk is None:
            vk = _key_code(part)[1]
        else:
            raise ValueError(f"more than one key in {text!r}")
    if vk is None:
        raise ValueError("no key")
    if not mods:
        raise ValueError("a shortcut needs Ctrl, Alt, Shift or Win")
    return mods, vk


def normalize(text: str) -> str:
    """Canonical spelling: modifiers in Ctrl, Alt, Shift, Win order, key upper-cased."""
    names, key = [], None
    for part in [p for p in text.replace(" ", "").split("+") if p]:
        low = part.lower()
        if low in _MODIFIERS:
            names.append(_MODIFIERS[low][0])
        else:
            key = _key_code(part)[0]
    parse_combo(text)  # validate
    names = [m for m in _ORDER if m in names]
    return "+".join(names + [key])


def is_valid(text: str) -> bool:
    try:
        parse_combo(text)
        return True
    except ValueError:
        return False
