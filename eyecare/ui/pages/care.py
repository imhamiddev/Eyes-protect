"""Care: 20-20-20 rule, break lock, blink and hydration reminders."""
from __future__ import annotations

from eyecare.core import i18n
from eyecare.core.i18n import tr

from ..widgets import SettingRow, Stepper, Toggle, secondary_button
from .base import Page


class CarePage(Page):
    def __init__(self, engine):
        super().__init__(engine, "nav.care")
        s = engine.settings

        self.section(tr("care.rule"))
        self.rule_on = Toggle()
        self.interval = Stepper(1, 120, s.rule202020.interval_min)
        self.length = Stepper(5, 300, s.rule202020.break_seconds, step=5)
        self.snooze = Stepper(1, 30, s.rule202020.snooze_min)
        self.natural = Toggle()
        self.card(
            SettingRow(tr("care.rule"), tr("care.rule_desc"), self.rule_on),
            SettingRow(tr("care.interval"), "", self.interval),
            SettingRow(tr("care.break_len"), "", self.length),
            SettingRow(tr("care.snooze"), "", self.snooze),
            SettingRow(tr("care.natural"), "", self.natural),
        )

        self.section(tr("care.break_lock"))
        self.lock = Toggle()
        self.skippable = Toggle()
        self.card(
            SettingRow(tr("care.break_lock"), "", self.lock),
            SettingRow(tr("care.skippable"), "", self.skippable),
        )

        self.section(tr("care.smart"))
        self.smart_on = Toggle()
        self.smart_full = Toggle()
        self.smart_meet = Toggle()
        self.smart_focus = Toggle()
        self.card(
            SettingRow(tr("care.smart"), tr("care.smart_desc"), self.smart_on),
            SettingRow(tr("care.smart_fullscreen"), "", self.smart_full),
            SettingRow(tr("care.smart_meetings"), "", self.smart_meet),
            SettingRow(tr("care.smart_focus"), "", self.smart_focus),
        )

        self.section(tr("care.blink"))
        self.blink_on = Toggle()
        self.blink_int = Stepper(1, 60, s.blink.interval_min)
        self.card(
            SettingRow(tr("care.blink"), tr("care.blink_desc"), self.blink_on),
            SettingRow(tr("care.interval"), "", self.blink_int),
        )

        self.section(tr("care.posture"))
        self.posture_on = Toggle()
        self.posture_int = Stepper(10, 180, s.posture.interval_min, step=5)
        self.card(
            SettingRow(tr("care.posture"), tr("care.posture_desc"), self.posture_on),
            SettingRow(tr("care.interval"), "", self.posture_int),
        )

        self.section(tr("care.hydration"))
        self.water_on = Toggle()
        self.water_int = Stepper(5, 240, s.hydration.interval_min, step=5)
        self.drank = secondary_button(tr("toast.drank"), "droplet")
        self.card(
            SettingRow(tr("care.hydration"), tr("care.hydration_desc"), self.water_on),
            SettingRow(tr("care.interval"), "", self.water_int),
            SettingRow(tr("toast.water_title"), "", self.drank),
        )
        self.finish()

        for toggle in (self.rule_on, self.natural, self.lock, self.skippable, self.blink_on, self.water_on,
                       self.smart_on, self.smart_full, self.smart_meet, self.smart_focus,
                       self.posture_on):
            toggle.toggled.connect(self._save)
        for stepper in (self.interval, self.length, self.snooze, self.blink_int, self.water_int, self.posture_int):
            stepper.valueChanged.connect(self._save)
        self.drank.clicked.connect(self.engine.record_water)
        self.load()

    def load(self) -> None:
        s = self.engine.settings
        self._loading = True
        self.rule_on.setChecked(s.rule202020.enabled)
        self.interval.set_value(s.rule202020.interval_min, emit=False)
        self.length.set_value(s.rule202020.break_seconds, emit=False)
        self.snooze.set_value(s.rule202020.snooze_min, emit=False)
        self.natural.setChecked(s.rule202020.detect_natural_breaks)
        self.lock.setChecked(s.rule202020.use_break_lock)
        self.skippable.setChecked(s.break_lock.skippable)
        sp = s.smart_pause
        self.smart_on.setChecked(sp.enabled)
        self.smart_full.setChecked(sp.fullscreen)
        self.smart_meet.setChecked(sp.meetings)
        self.smart_focus.setChecked(sp.focus_assist)
        for t in (self.smart_full, self.smart_meet, self.smart_focus):
            t.setEnabled(sp.enabled)
        self.blink_on.setChecked(s.blink.enabled)
        self.blink_int.set_value(s.blink.interval_min, emit=False)
        self.posture_on.setChecked(s.posture.enabled)
        self.posture_int.set_value(s.posture.interval_min, emit=False)
        self.water_on.setChecked(s.hydration.enabled)
        self.water_int.set_value(s.hydration.interval_min, emit=False)
        self._loading = False

    def _save(self, *_args) -> None:
        if self._loading:
            return
        s = self.engine.settings
        s.rule202020.enabled = self.rule_on.isChecked()
        s.rule202020.interval_min = self.interval.value()
        s.rule202020.break_seconds = self.length.value()
        s.rule202020.snooze_min = self.snooze.value()
        s.rule202020.detect_natural_breaks = self.natural.isChecked()
        s.rule202020.use_break_lock = self.lock.isChecked()
        s.break_lock.skippable = self.skippable.isChecked()
        sp = s.smart_pause
        sp.enabled, sp.fullscreen = self.smart_on.isChecked(), self.smart_full.isChecked()
        sp.meetings, sp.focus_assist = self.smart_meet.isChecked(), self.smart_focus.isChecked()
        for t in (self.smart_full, self.smart_meet, self.smart_focus):
            t.setEnabled(sp.enabled)
        s.blink.enabled = self.blink_on.isChecked()
        s.blink.interval_min = self.blink_int.value()
        s.posture.enabled = self.posture_on.isChecked()
        s.posture.interval_min = self.posture_int.value()
        s.hydration.enabled = self.water_on.isChecked()
        s.hydration.interval_min = self.water_int.value()
        self.engine.commit_settings()
