import pytest

pytest.importorskip("PySide6")

from eyecare.ui.toast import ToastManager  # noqa: E402


def test_action_runs_callback_and_dismisses(app):
    mgr, hits = ToastManager(), []
    t = mgr.show("bell", "Title", "Body", [("Go", lambda: hits.append(1), True)])
    assert mgr.count() == 1
    t.findChildren(type(t.findChildren(__import__("PySide6.QtWidgets", fromlist=["QPushButton"]).QPushButton)[0]))
    from PySide6.QtWidgets import QPushButton

    [b for b in t.findChildren(QPushButton) if b.text() == "Go"][0].click()
    assert hits == [1]
    t._fade.stop()
    t._finish()
    assert mgr.count() == 0


def test_stacking_positions_differ(app):
    mgr = ToastManager()
    a = mgr.show("bell", "A", "a")
    b = mgr.show("bell", "B", "b")
    assert mgr._slot(0, a) != mgr._slot(1, b)
    mgr.clear()
    for t in list(mgr._toasts):
        t._fade.stop()
        t._finish()
