"""Qt-facing controller: owns settings, timers and all side effects."""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal

from eyecare.core import winapi
from eyecare.core.colortemp import build_ramp, channel_multipliers
from eyecare.core.config import Settings, load_settings, save_settings
from eyecare.core.stats import Stats
from eyecare.core.timeutil import now_time
from eyecare.features import rule202020 as rule_mod
from eyecare.features.display import DisplayState, compute_display_state, wants_light_theme
from eyecare.features.interval import IntervalReminder
from eyecare.updates import UpdateManager

DISPLAY_REAPPLY_SECONDS = 60


def launch_command() -> str:
    """Command line stored in the Windows Run key."""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --background'
    return f'"{sys.executable}" -m eyecare --background'


class Engine(QObject):
    prompt_requested = Signal()          # show the 20-20-20 toast
    break_started = Signal(int)          # seconds, show break screen/mini window
    break_tick = Signal(int)             # seconds left
    break_finished = Signal(bool)        # True = completed, False = skipped
    blink_requested = Signal()
    water_requested = Signal()
    natural_break = Signal()
    state_changed = Signal()             # anything the UI may want to redraw
    settings_changed = Signal()
    display_changed = Signal(object)     # DisplayState

    def __init__(self, settings: Settings | None = None, stats: Stats | None = None,
                 settings_path: Path | None = None, parent: QObject | None = None):
        super().__init__(parent)
        self._settings_path = settings_path
        self.settings = settings or load_settings(settings_path)
        self.stats = stats or Stats()
        self.paused = False
        s = self.settings
        self.rule = rule_mod.Rule202020(s.rule202020)
        self.blink = IntervalReminder(s.blink.interval_min, s.blink.enabled)
        self.water = IntervalReminder(s.hydration.interval_min, s.hydration.enabled)
        self.display_state = DisplayState()
        self._last_applied: tuple | None = None
        self._since_apply = DISPLAY_REAPPLY_SECONDS
        self._last_theme_target: bool | None = None
        self.updates = UpdateManager(self)
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self.on_tick)

    # -- lifecycle --------------------------------------------------------
    def start(self) -> None:
        self.apply_display(force=True)
        self.sync_autostart()
        self._timer.start()
        self.updates.start_background()

    def shutdown(self) -> None:
        self._timer.stop()
        winapi.reset_gamma()
        save_settings(self.settings, self._settings_path)
        self.stats.save()

    # -- settings ---------------------------------------------------------
    def save_quietly(self) -> None:
        """Persist settings without re-applying or notifying the UI."""
        save_settings(self.settings, self._settings_path)

    def commit_settings(self) -> None:
        """Call after mutating ``self.settings``; persists and re-applies."""
        s = self.settings
        self.rule.reload(s.rule202020)
        self.blink.configure(s.blink.interval_min, s.blink.enabled)
        self.water.configure(s.hydration.interval_min, s.hydration.enabled)
        save_settings(s, self._settings_path)
        self.apply_display(force=True)
        self.sync_autostart()
        self._last_theme_target = None
        self.settings_changed.emit()
        self.state_changed.emit()

    def sync_autostart(self) -> None:
        winapi.set_autostart(self.settings.general.autostart, launch_command())

    # -- display ----------------------------------------------------------
    def apply_display(self, force: bool = False) -> None:
        state = compute_display_state(self.settings.night_light, self.settings.dimmer, now_time())
        key = (state.kelvin, round(state.brightness, 3))
        if force or key != self._last_applied or self._since_apply >= DISPLAY_REAPPLY_SECONDS:
            if state.is_neutral:
                winapi.reset_gamma()
            else:
                winapi.set_gamma_ramp(build_ramp(channel_multipliers(state.kelvin, state.brightness)))
            self._since_apply = 0
        if key != self._last_applied:
            self._last_applied = key
            self.display_state = state
            self.display_changed.emit(state)

    def toggle_night_light(self) -> bool:
        nl = self.settings.night_light
        nl.enabled = not nl.enabled
        if nl.enabled:
            nl.schedule = False  # a quick manual toggle means "on right now"
        self.commit_settings()
        return nl.enabled

    def _apply_auto_theme(self) -> None:
        want_light = wants_light_theme(self.settings.auto_dark, now_time())
        if want_light is not None and want_light != self._last_theme_target:
            self._last_theme_target = want_light
            if winapi.system_uses_light_theme() != want_light:
                winapi.set_system_light_theme(want_light)

    # -- reminders --------------------------------------------------------
    def set_paused(self, paused: bool) -> None:
        self.paused = paused
        self.rule.set_paused(paused)
        self.state_changed.emit()

    def on_tick(self) -> None:
        idle = winapi.idle_seconds()
        self._since_apply += 1
        self.apply_display()
        self._apply_auto_theme()
        self._handle(self.rule.tick(1.0, idle))
        if self.rule.phase == rule_mod.Phase.BREAK and not self.paused:
            self.break_tick.emit(self.rule.break_seconds_left)
        if self.blink.tick(1.0, idle, self.paused):
            self.blink_requested.emit()
        if self.water.tick(1.0, idle, self.paused):
            self.water_requested.emit()
        self.state_changed.emit()

    def _handle(self, events: list[str]) -> None:
        for event in events:
            if event == rule_mod.PROMPT:
                self.prompt_requested.emit()
            elif event == rule_mod.BREAK_START:
                self.break_started.emit(self.settings.rule202020.break_seconds)
            elif event == rule_mod.BREAK_DONE:
                self.stats.add("breaks")
                self.break_finished.emit(True)
            elif event == rule_mod.BREAK_SKIPPED:
                self.stats.add("skipped")
                self.break_finished.emit(False)
            elif event == rule_mod.NATURAL_BREAK:
                self.stats.add("breaks")
                self.natural_break.emit()

    # -- user actions -----------------------------------------------------
    def start_break(self) -> None:
        self._handle(self.rule.start_break())

    def snooze(self) -> None:
        self._handle(self.rule.snooze())
        self.state_changed.emit()

    def skip_break(self) -> None:
        self._handle(self.rule.skip_break())

    def record_blink_shown(self) -> None:
        self.stats.add("blinks")

    def record_water(self) -> None:
        self.stats.add("water")
        self.state_changed.emit()
