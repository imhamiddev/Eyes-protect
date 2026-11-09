import subprocess
import sys
from pathlib import Path

import pytest

import eyecare
from eyecare.core import changelog as cl
from eyecare.core import updater

ROOT = Path(__file__).resolve().parent.parent
TEXT = """# Changelog

## [1.2.0] - 2026-01-01
- First **bold** change with `code`
* Second [linked](https://x.y/z) change
Not a bullet
1. Numbered change
<!-- fa -->
- تغییر اول
- تغییر دوم

## [1.1.0] - 2025-12-01
- Old change
"""


def test_parse_sections():
    s = cl.parse_sections(TEXT)
    assert list(s) == ["1.2.0", "1.1.0"]
    assert "Old change" in s["1.1.0"] and "Old change" not in s["1.2.0"]


def test_extract_bullets_strips_markdown_and_ignores_prose():
    b = cl.extract_bullets(cl.parse_sections(TEXT)["1.2.0"])
    assert b == ["First bold change with code", "Second linked change", "Numbered change"]


def test_persian_part_used_when_requested_and_present():
    body = cl.parse_sections(TEXT)["1.2.0"]
    assert cl.extract_bullets(body, "fa") == ["تغییر اول", "تغییر دوم"]
    assert cl.extract_bullets(cl.parse_sections(TEXT)["1.1.0"], "fa") == ["Old change"]  # falls back


def test_limit_truncation_and_github_boilerplate():
    body = "\n".join(f"- item {i}" for i in range(20)) + "\n- **Full Changelog**: https://x"
    assert len(cl.extract_bullets(body, limit=5)) == 5
    assert cl.extract_bullets("- " + "x" * 300, max_len=50)[0].endswith("…")
    assert cl.extract_bullets("- Full Changelog: a\n- New Contributors\n- real") == ["real"]


def test_notes_for_reads_a_file(tmp_path):
    p = tmp_path / "CHANGELOG.md"
    p.write_text(TEXT, encoding="utf-8")
    assert cl.notes_for("v1.2.0", "en", path=p)[0].startswith("First bold")
    assert cl.notes_for("9.9.9", path=p) == []
    assert cl.notes_for("1.2.0", path=tmp_path / "missing.md") == []


def test_release_notes_are_summarized_like_the_changelog():
    assert updater.summarize_notes("- a\n- b\n- c", limit=2) == ["a", "b"]


def test_current_version_has_bilingual_notes_in_the_real_changelog():
    """Guards releases: a version bump without changelog entries fails the tests."""
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    body = cl.parse_sections(text).get(eyecare.__version__)
    assert body, f"CHANGELOG.md needs a section for {eyecare.__version__}"
    assert cl.extract_bullets(body, "en") and cl.extract_bullets(body, "fa")
    assert cl.extract_bullets(body, "fa") != cl.extract_bullets(body, "en")


def test_release_notes_tool_writes_both_languages(tmp_path):
    out = tmp_path / "notes.md"
    subprocess.run([sys.executable, str(ROOT / "tools" / "release_notes.py"), eyecare.__version__, str(out)],
                   check=True, capture_output=True)
    text = out.read_text(encoding="utf-8")
    assert "---" in text and "Smart pause" in text and "توقف هوشمند" in text


def test_release_notes_tool_fails_for_unknown_version(tmp_path):
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "release_notes.py"), "99.0.0",
                        str(tmp_path / "x.md")], capture_output=True)
    assert r.returncode != 0
