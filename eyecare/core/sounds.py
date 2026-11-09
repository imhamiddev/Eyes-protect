"""Soft synthesized chimes (no bundled audio files) played through the Windows sound API."""
from __future__ import annotations

import io
import math
import struct
import wave
from pathlib import Path

from . import winapi
from .config import config_dir

RATE = 44100
KINDS = ("start", "end", "notify")
# (frequency Hz, start offset s, length s) for every note of each chime
NOTES: dict[str, list[tuple[float, float, float]]] = {
    "start": [(523.25, 0.00, 0.60), (659.25, 0.18, 0.70)],
    "end": [(659.25, 0.00, 0.55), (523.25, 0.20, 0.55), (392.00, 0.40, 0.80)],
    "notify": [(783.99, 0.00, 0.50)],
}
PEAK = 0.55  # leave headroom: never full scale


def _tone(freq: float, length: float, gain: float) -> list[float]:
    n = int(RATE * length)
    out = []
    for i in range(n):
        t = i / RATE
        attack = min(1.0, t / 0.012)                      # 12 ms fade-in avoids a click
        decay = math.exp(-5.0 * t / length)               # bell-like fade-out
        wave_ = math.sin(2 * math.pi * freq * t) + 0.25 * math.sin(2 * math.pi * 2 * freq * t)
        out.append(wave_ * attack * decay * gain)
    return out


def synth(kind: str, volume: int) -> bytes:
    """Return a mono 16-bit WAV for ``kind`` at volume 0..100."""
    if kind not in NOTES:
        raise ValueError(f"unknown sound: {kind}")
    volume = max(0, min(100, int(volume)))
    notes = NOTES[kind]
    total = max(start + length for _f, start, length in notes)
    mix = [0.0] * int(RATE * total)
    for freq, start, length in notes:
        offset = int(RATE * start)
        for i, v in enumerate(_tone(freq, length, 1.0 / len(notes) ** 0.5)):
            mix[offset + i] += v
    peak = max(1e-9, max(abs(v) for v in mix))
    scale = PEAK * (volume / 100) / peak
    frames = b"".join(struct.pack("<h", int(max(-1.0, min(1.0, v * scale)) * 32767)) for v in mix)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(frames)
    return buf.getvalue()


class SoundPlayer:
    def __init__(self, cache_dir: Path | None = None):
        self.cache_dir = cache_dir or config_dir() / "sounds"

    def path_for(self, kind: str, volume: int) -> Path:
        step = max(0, min(100, round(int(volume) / 10) * 10))   # at most 11 cached files per sound
        path = self.cache_dir / f"{kind}-{step}.wav"
        if not path.exists():
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            path.write_bytes(synth(kind, step))
        return path

    def play(self, kind: str, volume: int) -> bool:
        if volume <= 0 or kind not in NOTES:
            return False
        try:
            return winapi.play_sound_file(self.path_for(kind, volume))
        except OSError:
            return False
