import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402


@pytest.fixture(scope="session")
def app():
    """One QApplication for the whole run (mixing Core/GUI apps crashes Qt)."""
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])
