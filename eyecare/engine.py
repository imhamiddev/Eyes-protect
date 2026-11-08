"""Qt-facing controller: owns settings, timers and all side effects."""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QObject, QTimer, QVariantAnimation, Signal

from eyecare.core import winapi
from eyecare.core.colortemp import build_ramp, channel_multipliers
from eyecare.core.config import Settings, load_settings, save_settings
from eyecare.core.stats import Stats
from eyecare.core import monitors as mon
from eyecare.core.cities import city_by_key
from eyecare.core.timeutil import now_precise, now_time
from eyecare.features import rule202020 as rule_mod
from eyecare.features.display import DisplayState, compute_display_state, wants_light_theme
from eyecare.features.interval import IntervalReminder
from eyecare.features.smartpause import Debouncer, classify
from eyecare.ui import motion
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
    posture_requested = Signal()
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
        self.quiet_until = 0.0           # epoch seconds; inf = until switched off
        self.busy_reason: str | None = None   # set by smart pause (e.g. 'fullscreen')
        s = self.settings
        self.rule = rule_mod.Rule202020(s.rule202020)
        self.blink = IntervalReminder(s.blink.interval_min, s.blink.enabled)
        self.water = IntervalReminder(s.hydration.interval_min, s.hydration.enabled)
        self.posture = IntervalReminder(s.posture.interval_min, s.posture.enabled)
        self.display_state = DisplayState()
        self._shown: DisplayState | None = None
        self.monitors = winapi.list_monitors()
        self._from = self._to = DisplayState()
        self._tween = QVariantAnimation(self)
        self._tween.setStartValue(0.0)
        self._tween.setEndValue(1.0)
        self._tween.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._tween.valueChanged.connect(self._on_tween)
        self._tween.finished.connect(lambda: self._push(self._to) if self._shown != self._to else None)
        self._since_apply = DISPLAY_REAPPLY_SECONDS
        self._last_theme_target: bool | None = None
        self.updates = UpdateManager(self)
        self._smart = Debouncer(2)
        self._poll_count = 0
        self._run_seconds = 0   # continuous screen time since the last break
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
        self.posture.configure(s.posture.interval_min, s.posture.enabled)
        save_settings(s, self._settings_path)
        self.refresh_monitors()
        self.apply_display(force=True)
        self.sync_autostart()
        self._last_theme_target = None
        if not self.settings.smart_pause.enabled:
            self._smart.update(None)
            self.set_busy(None)
        self.settings_changed.emit()
        self.state_changed.emit()

    def sync_autostart(self) -> None:
        winapi.set_autostart(self.settings.general.autostart, launch_command())

    # -- display ----------------------------------------------------------
    def _target_state(self) -> DisplayState:
        city = city_by_key(self.settings.location.city)
        return compute_display_state(self.settings.night_light, self.settings.dimmer,
                                     now_precise(), city)

    def refresh_monitors(self) -> bool:
        """Re-read the attached displays; True if the set changed."""
        current = winapi.list_monitors()
        changed = current != self.monitors
        self.monitors = current
        return changed

    def _apply_gamma(self, state: DisplayState) -> None:
        excluded = mon.parse_set(self.settings.monitors.excluded)
        factors = mon.parse_map(self.settings.monitors.brightness)
        for m in self.monitors:
            k = mon.key(m.device)
            f = factors.get(k, 100) / 100
            if k in excluded or (state.is_neutral and f >= 1.0):
                ramp = winapi.IDENTITY_RAMP
            else:
                ramp = build_ramp(channel_multipliers(state.kelvin, state.brightness * f))
            if not winapi.set_monitor_gamma_ramp(m.device, ramp) and m.primary:
                winapi.set_gamma_ramp(ramp)  # fallback for drivers that reject per-device DCs

    def _push(self, state: DisplayState) -> None:
        """Send ``state`` to the screen now."""
        changed = self._shown is None or (state.kelvin, round(state.brightness, 3)) != (
            self._shown.kelvin, round(self._shown.brightness, 3))
        self._apply_gamma(state)
        self._since_apply = 0
        self._shown = state
        if changed:
            self.display_state = state
            self.display_changed.emit(state)

    def apply_display(self, force: bool = False) -> None:
        target = self._target_state()
        if self._tween.state() == QVariantAnimation.State.Running:
            self._tween.stop()
        shown = self._shown
        if shown is None:
            self._push(target)
            return
        if target == shown:
            if force or self._since_apply >= DISPLAY_REAPPLY_SECONDS:
                self._push(shown)  # some drivers/apps silently reset the ramp
            return
        big = abs(target.kelvin - shown.kelvin) > 150 or abs(target.brightness - shown.brightness) > 0.08
        if big and motion.ms(1):
            self._from, self._to = shown, target
            self._tween.setDuration(700)
            self._tween.start()
        else:
            self._push(target)

    def _on_tween(self, t) -> None:
        a, b, t = self._from, self._to, float(t)
        self._push(DisplayState(round(a.kelvin + (b.kelvin - a.kelvin) * t),
                                a.brightness + (b.brightness - a.brightness) * t))

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

    # -- smart pause --------------------------------------------------------
    def poll_smart_pause(self) -> None:
        cfg = self.settings.smart_pause
        observed = classify(cfg, winapi.notification_state(), winapi.foreground_info(), os.getpid()) \
            if cfg.enabled else None
        self.set_busy(self._smart.update(observed))

    # -- quiet mode / holding ---------------------------------------------
    @property
    def quiet_active(self) -> bool:
        return time.time() < self.quiet_until

    @property
    def holding(self) -> bool:
        """True while reminders must stay silent (quiet mode or a busy full-screen/meeting app)."""
        return self.quiet_active or self.busy_reason is not None

    def set_quiet(self, minutes: float | None) -> None:
        """Silence reminders for ``minutes`` (None = until switched off, <=0 = end quiet mode)."""
        if minutes is None:
            self.quiet_until = float("inf")
        elif minutes <= 0:
            self.quiet_until = 0.0
        else:
            self.quiet_until = time.time() + minutes * 60
        self.state_changed.emit()

    def toggle_quiet(self, minutes: float = 60) -> bool:
        if self.quiet_active:
            self.set_quiet(0)
        else:
            self.set_quiet(minutes)
        return self.quiet_active

    def set_busy(self, reason: str | None) -> None:
        if reason != self.busy_reason:
            self.busy_reason = reason
            self.state_changed.emit()

    # -- reminders --------------------------------------------------------
    def set_paused(self, paused: bool) -> None:
        self.paused = paused
        self.rule.set_paused(paused)
        self.state_changed.emit()

    def on_tick(self) -> None:
        idle = winapi.idle_seconds()
        self._since_apply += 1
        self._poll_count += 1
        if self._poll_count % 2 == 0:
            self.poll_smart_pause()
        if self._poll_count % 15 == 0 and self.refresh_monitors():
            self.apply_display(force=True)
            self.state_changed.emit()
        self.apply_display()
        self._apply_auto_theme()
        self._track_activity(idle)
        if self.quiet_until and not self.quiet_active:
            self.quiet_until = 0.0  # quiet period ran out
        hold = self.holding
        self._handle(self.rule.tick(1.0, idle, hold))
        if self.rule.phase == rule_mod.Phase.BREAK and not self.paused:
            self.break_tick.emit(self.rule.break_seconds_left)
        silent = self.paused or hold
        if self.blink.tick(1.0, idle, silent):
            self.blink_requested.emit()
        if self.water.tick(1.0, idle, silent):
            self.water_requested.emit()
        if self.posture.tick(1.0, idle, silent):
            self.posture_requested.emit()
        self.state_changed.emit()

    def _track_activity(self, idle: float) -> None:
        """Screen time and the longest stretch without a break (kept even while quiet)."""
        if idle >= self.settings.rule202020.break_seconds:
            self._run_seconds = 0      # away long enough: counts as a rest
        if idle < 60:
            self.stats.add("active_s", save=False)
        if idle < 5:
            self._run_seconds += 1
            self.stats.record_max("longest_run_s", self._run_seconds, save=False)
        if self._poll_count % 30 == 0:
            self.stats.save()

    def _handle(self, events: list[str]) -> None:
        for event in events:
            if event == rule_mod.PROMPT:
                self.prompt_requested.emit()
            elif event == rule_mod.BREAK_START:
                self.break_started.emit(self.settings.rule202020.break_seconds)
            elif event == rule_mod.BREAK_DONE:
                self._run_seconds = 0
                self.stats.add("breaks")
                self.break_finished.emit(True)
            elif event == rule_mod.BREAK_SKIPPED:
                self._run_seconds = 0
                self.stats.add("skipped")
                self.break_finished.emit(False)
            elif event == rule_mod.NATURAL_BREAK:
                self._run_seconds = 0
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

    def record_stretch(self) -> None:
        self.stats.add("stretches")

    def record_water(self) -> None:
        self.stats.add("water")
        self.state_changed.emit()
