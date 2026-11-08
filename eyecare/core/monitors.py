"""Per-monitor settings helpers (stored compactly in the JSON settings)."""
from __future__ import annotations


def key(device: str) -> str:
    """'\\\\.\\DISPLAY2' -> 'DISPLAY2' (stable, readable settings key)."""
    return device.replace("\\", "").lstrip(".") or device


def parse_set(text: str) -> set[str]:
    return {p.strip() for p in text.split(",") if p.strip()}


def format_set(items) -> str:
    return ",".join(sorted(items))


def parse_map(text: str) -> dict[str, int]:
    """'DISPLAY1=80;DISPLAY2=100' -> {'DISPLAY1': 80, 'DISPLAY2': 100} (bad entries ignored)."""
    out: dict[str, int] = {}
    for part in text.split(";"):
        name, _, value = part.partition("=")
        try:
            out[name.strip()] = max(30, min(100, int(value)))
        except ValueError:
            continue
    out.pop("", None)
    return out


def format_map(values: dict[str, int]) -> str:
    return ";".join(f"{k}={v}" for k, v in sorted(values.items()))
