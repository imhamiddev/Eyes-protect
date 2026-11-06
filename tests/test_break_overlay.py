import pytest

pytest.importorskip("PySide6")

from eyecare.ui.break_overlay import BreakOverlay  # noqa: E402


def test_countdown_and_skip(app):
    ov = BreakOverlay()
    hits = []
    ov.skipped.connect(lambda: hits.append(1))
    ov.begin(20, skippable=True, skip_after=0, show_exercise=True)
    assert ov.active and ov.ring.progress == 0.0
    ov.update_left(10)
    ov._anim_done = ov.ring._anim.stop()
    ov.skip_btn.click()
    assert hits == [1]
    ov.end()
    assert not ov.active


def test_skip_locked_until_delay(app):
    ov = BreakOverlay()
    ov.begin(20, skippable=True, skip_after=60, show_exercise=False)
    assert not ov.skip_btn.isEnabled()
    ov._skip()
    ov.end()


def test_not_skippable_hides_button(app):
    ov = BreakOverlay()
    hits = []
    ov.skipped.connect(lambda: hits.append(1))
    ov.begin(5, skippable=False, skip_after=0, show_exercise=False)
    assert ov.skip_btn.isHidden()
    ov._skip()
    assert hits == []
    ov.end()
