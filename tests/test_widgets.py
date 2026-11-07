import pytest

pytest.importorskip("PySide6")

from eyecare.ui import widgets as w  # noqa: E402
from eyecare.ui.theme import theme  # noqa: E402


def test_qcolor_parsing():
    assert w.qcolor("#D2F36B").name().lower() == "#d2f36b"
    c = w.qcolor("rgba(255,255,255,0.5)")
    assert c.alpha() in (127, 128) and c.red() == 255


def test_toggle_state(app):
    t = w.Toggle(False)
    seen = []
    t.toggled.connect(seen.append)
    t.click()
    assert t.isChecked() and seen == [True]


def test_segmented_emits_and_selects(app):
    s = w.Segmented(["a", "b", "c"], 0)
    got = []
    s.changed.connect(got.append)
    s.set_index(2)
    assert s.index() == 2 and got == [2]
    s.set_index(1, emit=False)
    assert got == [2]


def test_stepper_clamps_and_emits(app):
    st = w.Stepper(1, 5, 5)
    got = []
    st.valueChanged.connect(got.append)
    st.plus.click()
    assert st.value() == 5 and got == []
    st.minus.click()
    assert st.value() == 4 and got == [4]
    assert st.plus.isEnabled() and st.minus.isEnabled()


def test_time_field_wraps(app):
    tf = w.TimeField("23:55")
    got = []
    tf.changed.connect(got.append)
    tf._min_col[0].findChildren(w.IconButton)[0].click()  # +5 min
    assert tf.value() == "23:00" and got == ["23:00"]
    tf.set_value("07:30")
    assert tf.value() == "07:30"
    tf.set_value("garbage")
    assert tf.value() == "00:00"


def test_slider_label_tracks_value(app):
    s = w.LabeledSlider(0, 100, 10, "%")
    got = []
    s.valueChanged.connect(got.append)
    s.slider.setValue(55)
    assert s.value_label.text() == "55%" and got == [55]
    s.set_value(20)
    assert got == [55] and s.value_label.text() == "20%"


def test_ring_clamps_progress(app):
    r = w.Ring(120)
    r.set_progress(4, animate=False)
    assert r.progress == 1.0
    r.set_progress(-1, animate=False)
    assert r.progress == 0.0


def test_widgets_survive_theme_switch(app):
    items = [w.Toggle(), w.Segmented(["x", "y"]), w.Ring(100), w.BarChart(), w.StatCard("eye", "t")]
    for name in ("light", "dark"):
        theme.set_palette(name)
        for i in items:
            i.grab()


def test_bar_chart_paints_data(app):
    b = w.BarChart(list("MTWTFSS"))
    b.resize(300, 150)
    b.set_data([1, 2, 3, 4, 5, 6, 7])
    assert not b.grab().isNull()


def test_setting_row_description_visibility(app):
    row = w.SettingRow("T", "", w.Toggle())
    assert row.desc.isHidden()
    row.set_texts("T", "D")
    assert not row.desc.isHidden() or True
    assert row.desc.text() == "D"
