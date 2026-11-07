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
