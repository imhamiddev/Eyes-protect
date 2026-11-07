import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402


@pytest.fixture(scope="session")
def app():
    """One QApplication for the whole run (mixing Core/GUI apps crashes Qt)."""
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _cleanup_widgets(request):
    """Destroy leftover widgets after each test so Qt tears down cleanly."""
    yield
    if "app" not in request.fixturenames:
        return
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    for widget in app.topLevelWidgets():
        widget.close()
        widget.deleteLater()
    app.processEvents()
