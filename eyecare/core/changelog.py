"""Read release notes from CHANGELOG.md / GitHub release bodies (English + optional Persian)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

FA_MARKER = "<!-- fa -->"
_SECTION = re.compile(r"^## \[(?P<version>[^\]]+)\][^\n]*\n", re.MULTILINE)
_BULLET = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+(?P<text>.+?)\s*$")


def parse_sections(text: str) -> dict[str, str]:
    """{'0.4.0': body, ...} from a keep-a-changelog style document."""
    matches = list(_SECTION.finditer(text))
    out: dict[str, str] = {}
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        out[m.group("version").strip()] = text[m.end():end].strip()
    return out


def clean_markdown(line: str) -> str:
    line = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", line)   # [text](url) -> text
    line = re.sub(r"(\*\*|__|`)", "", line)                  # bold / code marks
    line = re.sub(r"\s+", " ", line)
    return line.strip()


def extract_bullets(body: str, language: str = "en", limit: int = 8, max_len: int = 140) -> list[str]:
    """Plain-text bullet list. Persian is used when the body has a Persian part."""
    english, _, persian = body.partition(FA_MARKER)
    chosen = persian if language == "fa" and persian.strip() else english
    bullets: list[str] = []
    for raw in chosen.splitlines():
        m = _BULLET.match(raw)
        if not m:
            continue
        text = clean_markdown(m.group("text"))
        if not text or text.lower().startswith(("full changelog", "new contributors")):
            continue
        bullets.append(text if len(text) <= max_len else text[: max_len - 1].rstrip() + "…")
        if len(bullets) >= limit:
            break
    return bullets


def find_changelog() -> Path | None:
    candidates = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "assets" / "CHANGELOG.md")
    here = Path(__file__).resolve()
    candidates += [here.parent.parent / "assets" / "CHANGELOG.md", here.parent.parent.parent / "CHANGELOG.md"]
    return next((p for p in candidates if p.exists()), None)


def notes_for(version: str, language: str = "en", limit: int = 8, path: Path | None = None) -> list[str]:
    """Bullets for ``version`` from the bundled changelog (empty if unknown)."""
    path = path or find_changelog()
    if not path:
        return []
    try:
        body = parse_sections(path.read_text(encoding="utf-8")).get(version.lstrip("vV"), "")
    except OSError:
        return []
    return extract_bullets(body, language, limit)
