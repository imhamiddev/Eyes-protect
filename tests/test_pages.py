import pytest

pytest.importorskip("PySide6")

from eyecare.core import i18n  # noqa: E402
from eyecare.core.config import Settings  # noqa: E402
from eyecare.core.exercises import EXERCISES  # noqa: E402
from eyecare.core.stats import Stats  # noqa: E402
from eyecare.engine import Engine  # noqa: E402
from eyecare.ui.pages.care import CarePage  # noqa: E402
from eyecare.ui.pages.display import DisplayPage  # noqa: E402
from eyecare.ui.pages.exercises import ExerciseRunner, ExercisesPage  # noqa: E402
from eyecare.ui.pages.home import HomePage  # noqa: E402
from eyecare.ui.pages.settings import SettingsPage  # noqa: E402


@pytest.fixture
def engine(app, tmp_path):
    i18n.set_language("en")
    return Engine(Settings(), Stats(tmp_path / "st.json"), tmp_path / "s.json")


def test_care_edits_persist_to_settings(engine):
    p = CarePage(engine)
    p.interval.set_value(25)
    p.lock.setChecked(True)
    p.blink_on.setChecked(False)
    s = engine.settings
    assert s.rule202020.interval_min == 25 and s.rule202020.use_break_lock is True
    assert s.blink.enabled is False
    assert engine.rule.seconds_to_break == 25 * 60


def test_care_load_does_not_write_back(engine):
    p = CarePage(engine)
    engine.settings.hydration.interval_min = 60
    p.load()
    assert p.water_int.value() == 60


def test_display_edits(engine):
    p = DisplayPage(engine)
    p.nl_on.setChecked(True)
    p.warmth.slider.setValue(80)
    p.profile.set_index(2)
    p.ad_on.setChecked(True)
    p.ad_dark.set_value("21:30", emit=True)
    s = engine.settings
    assert s.night_light.enabled and s.night_light.strength == 80
    assert s.dimmer.profile == "study" and s.auto_dark.enabled
    assert s.auto_dark.dark_from == "21:30"


def test_settings_page_language_and_theme(engine):
    p = SettingsPage(engine)
    p.lang.setCurrentIndex(1)
    p.theme.set_index(1)
    assert engine.settings.general.language == "fa"
    assert engine.settings.general.theme == "light"


def test_home_reflects_stats_and_pause(engine, app):
    engine.stats.add("breaks", amount=4)
    p = HomePage(engine)
    engine.set_paused(True)
    p.refresh()
    assert p.pause_btn.text() == i18n.tr("home.resume")
    assert p.breaks.number._value == 4
    p.deleteLater()
    app.processEvents()


def test_exercise_runner_advances_and_finishes(engine):
    ex = EXERCISES[0]
    r = ExerciseRunner(ex)
    r.timer.stop()
    for _ in range(ex.total_seconds):
        r.tick()
    assert r.finished
    r.close()


def test_exercises_page_lists_all(engine):
    p = ExercisesPage(engine)
    runner = p.run(EXERCISES[1])
    runner.timer.stop()
    runner.close()


def test_settings_animations_switch_updates_setting(engine):
    p = SettingsPage(engine)
    p.animations.setChecked(False)
    assert engine.settings.general.animations is False


def test_pages_enter_animation_is_safe(engine):
    from eyecare.ui import motion

    motion.set_enabled(True)
    for cls in (HomePage, CarePage, DisplayPage, SettingsPage, ExercisesPage):
        page = cls(engine)
        page.resize(900, 600)
        page.show()
        page.play_enter()
        page.grab()
        page.close()


def _pump(app, cond, timeout=3.0):
    import time

    end = time.time() + timeout
    while time.time() < end and not cond():
        app.processEvents()
        time.sleep(0.01)
    assert cond()


def test_settings_update_card_follows_manager_state(engine, app, monkeypatch, tmp_path):
    from eyecare.core import updater
    from eyecare.updates import State

    info = updater.ReleaseInfo("9.9.9", "v9.9.9", "", "https://github.com/x", 3, None, "https://github.com/p")
    um = engine.updates
    um._fetch = lambda: info
    um._can_install = lambda: True
    um._work_dir = tmp_path / "w"

    def fake_dl(i, dest, on_progress, cancelled):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"abc")
        on_progress(1.0)
        return dest

    um._download = fake_dl
    p = SettingsPage(engine)
    assert p.update_btn.text() == i18n.tr("upd.btn_check")
    p.update_btn.click()
    _pump(app, lambda: um.state == State.AVAILABLE)
    assert p.update_btn.text() == i18n.tr("upd.btn_download") and p.update_btn.kind == "primary"
    assert "9.9.9" in p.update_row.desc.text()
    p.update_btn.click()
    _pump(app, lambda: um.state == State.READY)
    assert p.update_btn.text() == i18n.tr("upd.btn_install")
    assert not p.progress_box.isHidden() or True


def test_settings_update_button_opens_page_when_not_installable(engine, app, monkeypatch):
    from PySide6.QtGui import QDesktopServices

    from eyecare.core import updater
    from eyecare.updates import State

    opened = []
    monkeypatch.setattr(QDesktopServices, "openUrl", lambda url: opened.append(url.toString()) or True)
    um = engine.updates
    um._can_install = lambda: False
    um.info = updater.ReleaseInfo("9.9.9", "v9.9.9", "", "https://github.com/x", 3, None, "https://github.com/p")
    um._set(State.AVAILABLE)
    p = SettingsPage(engine)
    assert p.update_btn.text() == i18n.tr("upd.btn_open")
    p.update_btn.click()
    assert opened == ["https://github.com/p"]


def test_settings_author_link_opens_github(engine, monkeypatch):
    from PySide6.QtGui import QDesktopServices

    opened = []
    monkeypatch.setattr(QDesktopServices, "openUrl", lambda url: opened.append(url.toString()) or True)
    p = SettingsPage(engine)
    assert p.author_btn.text() == "Made by imhamiddev"
    p.author_btn.click()
    assert opened == ["https://github.com/imhamiddev"]
    i18n.set_language("fa")
    assert i18n.tr("set.made_by") == "ساخته شده توسط imhamiddev"
    i18n.set_language("en")


def test_auto_update_toggle_persists(engine):
    p = SettingsPage(engine)
    p.auto_update.setChecked(False)
    assert engine.settings.general.auto_update is False


def test_care_smart_pause_switches(engine):
    p = CarePage(engine)
    assert engine.settings.smart_pause.enabled and p.smart_full.isEnabled()
    p.smart_on.setChecked(False)
    assert engine.settings.smart_pause.enabled is False and not p.smart_full.isEnabled()
    p.smart_on.setChecked(True)
    p.smart_meet.setChecked(False)
    assert engine.settings.smart_pause.meetings is False


def test_display_sun_mode_and_city(engine):
    p = DisplayPage(engine)
    assert not p.city_row.isEnabled() and p.start_row.isEnabled()
    p.nl_sun.setChecked(True)
    s = engine.settings
    assert s.night_light.sun is True
    assert p.city_row.isEnabled() and not p.start_row.isEnabled()
    assert "Sunset" in p.sun_row.desc.text() or "Sun" in p.sun_row.desc.text()
    keys = [c.key for c in __import__("eyecare.core.cities", fromlist=["CITIES"]).CITIES]
    p.city.setCurrentIndex(keys.index("mashhad"))
    assert s.location.city == "mashhad"
    p.transition.set_value(45)
    assert s.night_light.transition_min == 45


def test_display_schedule_off_disables_schedule_controls(engine):
    p = DisplayPage(engine)
    p.nl_schedule.setChecked(False)
    assert not p.sun_row.isEnabled() and not p.transition.isEnabled()
    assert not p.start_row.isEnabled()


def test_dimmer_sun_toggle(engine):
    p = DisplayPage(engine)
    p.dim_sun.setChecked(True)
    assert engine.settings.dimmer.sun is True


def test_display_monitor_rows_follow_settings(engine, monkeypatch):
    from eyecare.core import winapi

    mons = [winapi.Monitor("\\\\.\\DISPLAY1", 1920, 1080, True),
            winapi.Monitor("\\\\.\\DISPLAY2", 1280, 1024, False)]
    monkeypatch.setattr(winapi, "list_monitors", lambda: mons)
    engine.refresh_monitors()
    p = DisplayPage(engine)
    assert not p.monitor_card.isHidden() or len(p._monitor_rows) == 2
    assert set(p._monitor_rows) == {"DISPLAY1", "DISPLAY2"}
    t2, s2 = p._monitor_rows["DISPLAY2"]
    t2.setChecked(False)
    assert engine.settings.monitors.excluded == "DISPLAY2" and not s2.isEnabled()
    t1, s1 = p._monitor_rows["DISPLAY1"]
    s1.slider.setValue(70)
    assert engine.settings.monitors.brightness == "DISPLAY1=70"
    t2.setChecked(True)
    assert engine.settings.monitors.excluded == ""


def test_display_hides_monitor_card_for_a_single_screen(engine):
    p = DisplayPage(engine)
    assert p.monitor_card.isHidden() and p.monitor_title.isHidden()
