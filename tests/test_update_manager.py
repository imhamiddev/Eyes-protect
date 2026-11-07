import time

import pytest

pytest.importorskip("PySide6")

from eyecare.core import updater  # noqa: E402
from eyecare.core.config import Settings  # noqa: E402
from eyecare.core.stats import Stats  # noqa: E402
from eyecare.engine import Engine  # noqa: E402
from eyecare.updates import CHECK_EVERY_SECONDS, State, UpdateManager  # noqa: E402


def info(version="0.9.0"):
    return updater.ReleaseInfo(version, "v" + version, "", "https://github.com/x", 3, None, "p")


@pytest.fixture
def engine(app, tmp_path):
    return Engine(Settings(), Stats(tmp_path / "st.json"), tmp_path / "s.json")


def make(engine, tmp_path, fetch, can_install=True, launch=None, download=None):
    def fake_download(i, dest, on_progress, cancelled):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"abc")
        on_progress(0.5)
        on_progress(1.0)
        return dest

    return UpdateManager(engine, "0.2.0", fetch=fetch, download=download or fake_download,
                         launch=launch or (lambda p: None), can_install=lambda: can_install,
                         work_dir=tmp_path / "w")


def wait_for(app, cond, timeout=3.0):
    end = time.time() + timeout
    while time.time() < end and not cond():
        app.processEvents()
        time.sleep(0.01)
    assert cond()


def test_manual_flow_available_download_install(app, engine, tmp_path):
    launched = []
    m = make(engine, tmp_path, lambda: info(), launch=launched.append)
    quits = []
    m.quit_requested.connect(lambda: quits.append(1))
    m.check()
    assert m.state == State.CHECKING
    wait_for(app, lambda: m.state == State.AVAILABLE)
    m.download()
    wait_for(app, lambda: m.state == State.READY)
    assert m.progress == 1.0 and m.installer.exists()
    assert m.install() is True
    assert launched == [m.installer] and quits == [1]


def test_up_to_date(app, engine, tmp_path):
    m = make(engine, tmp_path, lambda: info("0.2.0"))
    m.check()
    wait_for(app, lambda: m.state == State.UP_TO_DATE)
    assert m.info is None


def test_no_release_counts_as_up_to_date(app, engine, tmp_path):
    m = make(engine, tmp_path, lambda: None)
    m.check()
    wait_for(app, lambda: m.state == State.UP_TO_DATE)


def test_check_error_and_retry(app, engine, tmp_path):
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) == 1:
            raise updater.UpdateError("offline")
        return info()

    m = make(engine, tmp_path, flaky)
    m.check()
    wait_for(app, lambda: m.state == State.ERROR)
    assert m.error == "offline"
    m.check()
    wait_for(app, lambda: m.state == State.AVAILABLE)


def test_download_error(app, engine, tmp_path):
    def bad(i, dest, on_progress, cancelled):
        raise updater.UpdateError("checksum mismatch")

    m = make(engine, tmp_path, lambda: info(), download=bad)
    m.check()
    wait_for(app, lambda: m.state == State.AVAILABLE)
    m.download()
    wait_for(app, lambda: m.state == State.ERROR)
    assert "checksum" in m.error


def test_auto_flow_downloads_and_announces(app, engine, tmp_path):
    m = make(engine, tmp_path, lambda: info())
    ready = []
    m.update_ready.connect(ready.append)
    m.check(auto=True)
    wait_for(app, lambda: m.state == State.READY)
    wait_for(app, lambda: len(ready) == 1)
    assert ready[0].version == "0.9.0"


def test_auto_flow_does_not_download_when_cannot_install(app, engine, tmp_path):
    m = make(engine, tmp_path, lambda: info(), can_install=False)
    m.check(auto=True)
    wait_for(app, lambda: m.state == State.AVAILABLE)
    app.processEvents()
    assert m.state == State.AVAILABLE


def test_last_check_is_recorded(app, engine, tmp_path):
    m = make(engine, tmp_path, lambda: info("0.2.0"))
    before = time.time()
    m.check()
    wait_for(app, lambda: m.state == State.UP_TO_DATE)
    assert engine.settings.general.last_update_check >= before


def test_auto_tick_respects_setting_and_interval(app, engine, tmp_path):
    m = make(engine, tmp_path, lambda: info("0.2.0"))
    engine.settings.general.auto_update = False
    m._auto_tick()
    assert m.state == State.IDLE
    engine.settings.general.auto_update = True
    engine.settings.general.last_update_check = time.time()
    m._auto_tick()
    assert m.state == State.IDLE
    engine.settings.general.last_update_check = time.time() - CHECK_EVERY_SECONDS - 1
    m._auto_tick()
    assert m.state == State.CHECKING
    wait_for(app, lambda: m.state == State.UP_TO_DATE)


def test_install_requires_ready_state(app, engine, tmp_path):
    m = make(engine, tmp_path, lambda: info())
    assert m.install() is False


def test_install_failure_reports_error(app, engine, tmp_path):
    def boom(p):
        raise OSError("denied")

    m = make(engine, tmp_path, lambda: info(), launch=boom)
    m.check()
    wait_for(app, lambda: m.state == State.AVAILABLE)
    m.download()
    wait_for(app, lambda: m.state == State.READY)
    assert m.install() is False and m.state == State.ERROR
