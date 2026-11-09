"""Write the GitHub release body for a version from CHANGELOG.md.

usage: python tools/release_notes.py 0.4.0 release-notes.md
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from eyecare.core.changelog import FA_MARKER, parse_sections  # noqa: E402


def build(version: str) -> str:
    body = parse_sections((ROOT / "CHANGELOG.md").read_text(encoding="utf-8")).get(version.lstrip("vV"))
    if not body:
        raise SystemExit(f"CHANGELOG.md has no section for {version}")
    english, _, persian = body.partition(FA_MARKER)
    text = english.strip()
    if persian.strip():
        text += "\n\n---\n\n" + persian.strip()
    return text + "\n"


if __name__ == "__main__":
    version, out = sys.argv[1], sys.argv[2]
    Path(out).write_text(build(version), encoding="utf-8")
    print(f"wrote {out}")
