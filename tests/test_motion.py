import pytest

pytest.importorskip("PySide6")

from eyecare.ui import motion  # noqa: E402


@pytest.fixture(autouse=True)
def _restore():
    yield
    motion.set_enabled(True)


def test_ms_respects_switch():
    assert motion.ms(200) == 200
    motion.set_enabled(False)
    assert motion.ms(200) == 0


def test_qcolor_and_lerp():
    assert motion.qcolor("#D2F36B").name().lower() == "#d2f36b"
    mid = motion.lerp_color(motion.qcolor("#000000"), motion.qcolor("#ffffff"), 0.5)
    assert 126 <= mid.red() <= 129
    assert motion.lerp_color(motion.qcolor("#000000"), motion.qcolor("#ffffff"), 9).red() == 255


def test_tween_jumps_when_disabled(app):
    hits = []
    t = motion.Tween(None, lambda: hits.append(1))
    motion.set_enabled(False)
    t.to(1.0)
    assert t.value == 1.0 and hits


def test_tween_animates_when_enabled(app):
    t = motion.Tween(None, lambda: None, duration=500)
    t.to(1.0)
    assert t.running and t.value < 1.0
    t.jump(0.25)
    assert not t.running and t.value == 0.25


def test_fade_in_noop_when_disabled(app):
    from PySide6.QtWidgets import QWidget

    w = QWidget()
    motion.set_enabled(False)
    motion.fade_in(w)
    assert w.graphicsEffect() is None
    motion.set_enabled(True)
    motion.fade_in(w, delay=5000)
    assert w.graphicsEffect() is not None
