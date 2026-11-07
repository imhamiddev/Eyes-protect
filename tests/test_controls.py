import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QEvent, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QEnterEvent  # noqa: E402

from eyecare.ui import motion  # noqa: E402
from eyecare.ui.controls import AnimatedButton, IconButton, SmoothSlider, ValueLabel  # noqa: E402


@pytest.fixture(autouse=True)
def _motion_on():
    motion.set_enabled(True)
    yield
    motion.set_enabled(True)


def test_button_hover_tween_and_click(app):
    b = AnimatedButton("Go", "play", "primary")
    b.resize(120, 40)
    hits = []
    b.clicked.connect(lambda: hits.append(1))
    b.enterEvent(QEnterEvent(QPointF(5, 5), QPointF(5, 5), QPointF(5, 5)))
    assert b._hover.running or b._hover.value > 0
    b.click()
    assert hits == [1]
    assert not b.grab().isNull()


def test_button_instant_when_motion_off(app):
    motion.set_enabled(False)
    b = AnimatedButton("x", None, "secondary")
    b.enterEvent(QEnterEvent(QPointF(1, 1), QPointF(1, 1), QPointF(1, 1)))
    assert b._hover.value == 1.0
    b.leaveEvent(QEvent(QEvent.Type.Leave))
    assert b._hover.value == 0.0


@pytest.mark.parametrize("kind", ["primary", "secondary", "ghost", "nav"])
def test_every_kind_paints_in_both_directions(app, kind):
    for direction in (Qt.LayoutDirection.LeftToRight, Qt.LayoutDirection.RightToLeft):
        b = AnimatedButton("متن Text", "eye", kind, align="start" if kind == "nav" else "center")
        b.setCheckable(True)
        b.setChecked(True)
        b.setLayoutDirection(direction)
        b.resize(180, 40)
        assert not b.grab().isNull()


def test_nav_check_animates(app):
    b = AnimatedButton("Home", "eye", "nav", align="start")
    b.setCheckable(True)
    b.setChecked(True)
    assert b._check.running or b._check.value == 1.0


def test_icon_button_toggle_and_paint(app):
    b = IconButton("moon", checkable=True)
    b.resize(36, 36)
    b.click()
    assert b.isChecked() and not b.grab().isNull()
    b.set_icon_name("sun")


def test_slider_click_jumps_and_programmatic_animates(app):
    s = SmoothSlider()
    s.setRange(0, 100)
    s.resize(212, 30)
    s.setValue(0)
    s._dragging = True
    assert s._value_at(12) == 0 and s._value_at(200) == 100
    assert 45 <= s._value_at(106) <= 55
    s._dragging = False
    s.setValue(80)
    assert s._pos.state() == s._pos.State.Running
    assert not s.grab().isNull()


def test_slider_snaps_when_motion_off(app):
    motion.set_enabled(False)
    s = SmoothSlider()
    s.setRange(0, 10)
    s.setValue(7)
    assert s._shown == 7.0


def test_value_label_direction_and_instant_when_hidden(app):
    v = ValueLabel("5")
    v.setText("9")  # not visible: no animation
    assert v._t.value == 1.0 and v.text() == "9"
    v.show()
    v.setText("3")
    assert v._dir == -1 and v._t.running
    v.setText("x")
    assert v._dir == 1
    assert not v.grab().isNull()
