"""Display: night light, screen dimmer profiles and automatic dark mode."""
from __future__ import annotations

from datetime import date

from eyecare.core import i18n
from eyecare.core.cities import CITIES, city_by_key, city_name
from eyecare.core.colortemp import strength_to_kelvin
from eyecare.core.i18n import tr
from eyecare.core.sun import format_minutes, sun_times
from eyecare.features.display import local_utc_offset_hours

from ..widgets import Dropdown, LabeledSlider, Segmented, SettingRow, Stepper, TimeField, Toggle, label
from .base import Page

PROFILE_KEYS = ["day", "night", "study"]


class DisplayPage(Page):
    def __init__(self, engine):
        super().__init__(engine, "nav.display")

        self.section(tr("display.night"))
        self.nl_on = Toggle()
        self.warmth = LabeledSlider(0, 100, 40, "%")
        self.kelvin = label("", "Caption")
        self.nl_schedule = Toggle()
        self.nl_sun = Toggle()
        self.city = Dropdown([city_name(c, i18n.language()) for c in CITIES])
        self.sun_row = SettingRow(tr("display.sun"), tr("display.sun_desc"), self.nl_sun)
        self.city_row = SettingRow(tr("display.city"), "", self.city)
        self.transition = Stepper(0, 60, 30, step=5)
        self.nl_start, self.nl_end = TimeField("20:00"), TimeField("06:30")
        self.start_row = SettingRow(tr("display.from"), "", self.nl_start)
        self.end_row = SettingRow(tr("display.to"), "", self.nl_end)
        self.card(
            SettingRow(tr("display.night"), tr("display.night_desc"), self.nl_on),
            SettingRow(tr("display.warmth"), "", self._with_caption(self.warmth, self.kelvin)),
            SettingRow(tr("display.schedule"), "", self.nl_schedule),
            self.sun_row,
            self.city_row,
            self.start_row,
            self.end_row,
            SettingRow(tr("display.transition"), "", self.transition),
        )

        self.section(tr("display.dimmer"))
        self.dim_on = Toggle()
        self.profile = Segmented([tr("display.day"), tr("display.night_p"), tr("display.study")])
        self.b_day = LabeledSlider(30, 100, 100)
        self.b_night = LabeledSlider(30, 100, 70)
        self.b_study = LabeledSlider(30, 100, 85)
        self.dim_schedule = Toggle()
        self.dim_sun = Toggle()
        self.d_start, self.d_end = TimeField("20:00"), TimeField("06:30")
        self.card(
            SettingRow(tr("display.dimmer"), tr("display.dimmer_desc"), self.dim_on),
            SettingRow(tr("display.profile"), "", self.profile),
            SettingRow(tr("display.day"), "", self.b_day),
            SettingRow(tr("display.night_brightness"), "", self.b_night),
            SettingRow(tr("display.study"), "", self.b_study),
            SettingRow(tr("display.schedule"), "", self.dim_schedule),
            SettingRow(tr("display.sun"), "", self.dim_sun),
            SettingRow(tr("display.from"), "", self.d_start),
            SettingRow(tr("display.to"), "", self.d_end),
        )

        self.section(tr("display.auto_dark"))
        self.ad_on = Toggle()
        self.ad_light, self.ad_dark = TimeField("07:00"), TimeField("19:00")
        self.card(
            SettingRow(tr("display.auto_dark"), tr("display.auto_dark_desc"), self.ad_on),
            SettingRow(tr("display.light_from"), "", self.ad_light),
            SettingRow(tr("display.dark_from"), "", self.ad_dark),
        )
        self.finish()

        for t in (self.nl_on, self.nl_schedule, self.nl_sun, self.dim_on, self.dim_schedule, self.dim_sun,
                  self.ad_on):
            t.toggled.connect(self._save)
        for sl in (self.warmth, self.b_day, self.b_night, self.b_study):
            sl.valueChanged.connect(self._save)
        for tf in (self.nl_start, self.nl_end, self.d_start, self.d_end, self.ad_light, self.ad_dark):
            tf.changed.connect(self._save)
        self.profile.changed.connect(self._save)
        self.city.currentIndexChanged.connect(self._save)
        self.transition.valueChanged.connect(self._save)
        self.load()

    @staticmethod
    def _with_caption(slider, caption):
        from PySide6.QtWidgets import QVBoxLayout, QWidget

        box = QWidget()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        lay.addWidget(slider)
        lay.addWidget(caption)
        box.setMinimumWidth(260)
        return box

    def load(self) -> None:
        s = self.engine.settings
        self._loading = True
        n, d, a = s.night_light, s.dimmer, s.auto_dark
        self.nl_on.setChecked(n.enabled)
        self.warmth.set_value(n.strength)
        self.kelvin.setText(f"{strength_to_kelvin(n.strength)} K")
        self.nl_schedule.setChecked(n.schedule)
        self.nl_start.set_value(n.start)
        self.nl_end.set_value(n.end)
        self.nl_sun.setChecked(n.sun)
        self.transition.set_value(n.transition_min, emit=False)
        keys = [c.key for c in CITIES]
        self.city.setCurrentIndex(keys.index(city_by_key(s.location.city).key))
        self.dim_sun.setChecked(d.sun)
        self.dim_on.setChecked(d.enabled)
        self.profile.set_index(PROFILE_KEYS.index(d.profile) if d.profile in PROFILE_KEYS else 0, emit=False)
        self.b_day.set_value(d.day)
        self.b_night.set_value(d.night)
        self.b_study.set_value(d.study)
        self.dim_schedule.setChecked(d.schedule)
        self.d_start.set_value(d.night_start)
        self.d_end.set_value(d.night_end)
        self.ad_on.setChecked(a.enabled)
        self.ad_light.set_value(a.light_from)
        self.ad_dark.set_value(a.dark_from)
        self._loading = False
        self._update_schedule_rows()

    def _update_schedule_rows(self) -> None:
        n = self.engine.settings.night_light
        sched = n.schedule
        self.sun_row.setEnabled(sched)
        self.city_row.setEnabled(sched and n.sun)
        for row in (self.start_row, self.end_row):
            row.setEnabled(sched and not n.sun)
        self.transition.setEnabled(sched)
        if n.sun:
            st = sun_times(date.today(), city_by_key(self.engine.settings.location.city).lat,
                           city_by_key(self.engine.settings.location.city).lon, local_utc_offset_hours())
            if st.polar == "day":
                info = tr("display.sun_polar_day")
            elif st.polar == "night":
                info = tr("display.sun_polar_night")
            else:
                info = tr("display.sun_info").replace("{s}", format_minutes(st.sunset)).replace(
                    "{r}", format_minutes(st.sunrise))
            self.sun_row.set_texts(tr("display.sun"), info)
        else:
            self.sun_row.set_texts(tr("display.sun"), tr("display.sun_desc"))

    def _save(self, *_args) -> None:
        if self._loading:
            return
        s = self.engine.settings
        n, d, a = s.night_light, s.dimmer, s.auto_dark
        n.enabled, n.strength = self.nl_on.isChecked(), self.warmth.value()
        n.schedule, n.start, n.end = self.nl_schedule.isChecked(), self.nl_start.value(), self.nl_end.value()
        n.sun, n.transition_min = self.nl_sun.isChecked(), self.transition.value()
        s.location.city = CITIES[self.city.currentIndex()].key
        d.sun = self.dim_sun.isChecked()
        self.kelvin.setText(f"{strength_to_kelvin(n.strength)} K")
        d.enabled, d.profile = self.dim_on.isChecked(), PROFILE_KEYS[self.profile.index()]
        d.day, d.night, d.study = self.b_day.value(), self.b_night.value(), self.b_study.value()
        d.schedule, d.night_start, d.night_end = (
            self.dim_schedule.isChecked(), self.d_start.value(), self.d_end.value())
        a.enabled, a.light_from, a.dark_from = self.ad_on.isChecked(), self.ad_light.value(), self.ad_dark.value()
        self.engine.commit_settings()
        self._update_schedule_rows()
