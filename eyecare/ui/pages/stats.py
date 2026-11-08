"""Stats: screen time, longest stretch, streak, daily goal, 7-day trends and a weekly report."""
from __future__ import annotations

from datetime import date, timedelta

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from eyecare.core import i18n
from eyecare.core.i18n import tr
from eyecare.core.timeutil import format_duration

from .. import icons
from ..controls import ValueLabel
from ..theme import current
from ..widgets import BarChart, Card, Ring, Segmented, Stepper, label
from .base import Page

WEEKDAY_INITIALS_EN = ["M", "T", "W", "T", "F", "S", "S"]
WEEKDAY_INITIALS_FA = ["د", "س", "چ", "پ", "ج", "ش", "ی"]
METRICS = ["breaks", "active", "water"]


def dur(seconds: int) -> str:
    return format_duration(seconds, tr("unit.h"), tr("unit.m"))


class ValueTile(Card):
    """Icon + big animated value + caption."""

    def __init__(self, icon_name: str, caption: str):
        super().__init__(hoverable=True)
        self._icon_name = icon_name
        self.icon = label()
        self.value = ValueLabel("0", 90, px=26, align=Qt.AlignmentFlag.AlignLeading)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 18, 20, 18)
        lay.setSpacing(6)
        lay.addWidget(self.icon)
        lay.addSpacing(4)
        lay.addWidget(self.value)
        lay.addWidget(label(caption, "Muted", wrap=True))
        self.icon.setPixmap(icons.pixmap(icon_name, current().accent, 20))

    def set_value(self, text: str) -> None:
        self.value.setText(text)


class StatsPage(Page):
    def __init__(self, engine):
        super().__init__(engine, "nav.stats")
        self.metric_index = 0

        tiles = QHBoxLayout()
        tiles.setSpacing(16)
        self.t_active = ValueTile("clock", tr("stats.active"))
        self.t_longest = ValueTile("timer", tr("stats.longest"))
        self.t_streak = ValueTile("flame", tr("stats.streak"))
        for t in (self.t_active, self.t_longest, self.t_streak):
            tiles.addWidget(t, 1)
        self.col.addLayout(tiles)

        row = QHBoxLayout()
        row.setSpacing(16)
        goal = Card()
        gl = QVBoxLayout(goal)
        gl.setContentsMargins(22, 20, 22, 20)
        gl.setSpacing(12)
        gl.addWidget(label(tr("stats.goal"), "Title"))
        gl.addWidget(label(tr("stats.goal_desc"), "Muted", wrap=True))
        self.ring = Ring(150, 9)
        gl.addWidget(self.ring, 0, Qt.AlignmentFlag.AlignHCenter)
        self.goal = Stepper(1, 40, engine.settings.general.daily_break_goal)
        gl.addWidget(self.goal, 0, Qt.AlignmentFlag.AlignHCenter)
        row.addWidget(goal, 4)

        chart_card = Card()
        cl = QVBoxLayout(chart_card)
        cl.setContentsMargins(22, 18, 22, 16)
        top = QHBoxLayout()
        top.addWidget(label(tr("stats.trend"), "Title"), 1)
        self.seg = Segmented([tr("stats.m_breaks"), tr("stats.m_active"), tr("stats.m_water")])
        top.addWidget(self.seg)
        cl.addLayout(top)
        self.chart = BarChart()
        self.chart.setMinimumHeight(190)
        cl.addWidget(self.chart, 1)
        row.addWidget(chart_card, 7)
        self.col.addLayout(row)

        self.section(tr("stats.week"))
        self.report_box = QWidget()
        rl = QVBoxLayout(self.report_box)
        rl.setContentsMargins(0, 14, 0, 14)
        rl.setSpacing(8)
        self.r_totals = label("", "Title", wrap=True)
        self.r_best = label("", "Muted", wrap=True)
        self.r_longest = label("", "Muted", wrap=True)
        self.r_water = label("", "Muted", wrap=True)
        for w in (self.r_totals, self.r_best, self.r_longest, self.r_water):
            rl.addWidget(w)
        self.card(self.report_box)
        self.finish()

        self.seg.changed.connect(self._metric_changed)
        self.goal.valueChanged.connect(self._goal_changed)
        self.refresh()

    # -- interaction ---------------------------------------------------------
    def _metric_changed(self, index: int) -> None:
        self.metric_index = index
        self.refresh()

    def _goal_changed(self, value: int) -> None:
        self.engine.settings.general.daily_break_goal = value
        self.engine.commit_settings()
        self.refresh()

    def load(self) -> None:
        self.goal.set_value(self.engine.settings.general.daily_break_goal, emit=False)

    # -- data ----------------------------------------------------------------
    def refresh(self) -> None:
        st = self.engine.stats
        goal = self.engine.settings.general.daily_break_goal
        today = date.today()
        self.t_active.set_value(dur(st.get("active_s")))
        self.t_longest.set_value(dur(st.get("longest_run_s")))
        streak = st.streak(goal)
        self.t_streak.set_value(f"{streak} {tr('stats.days')}")
        done = st.get("breaks")
        self.ring.set_progress(min(1.0, done / max(1, goal)))
        self.ring.set_text(f"{done}/{goal}", tr("stats.today_breaks"))

        key = METRICS[self.metric_index]
        if key == "breaks":
            values = st.last_days("breaks", 7)
        elif key == "water":
            values = st.last_days("water", 7)
        else:
            values = [s // 60 for s in st.last_days("active_s", 7)]  # minutes
        initials = WEEKDAY_INITIALS_FA if i18n.language() == "fa" else WEEKDAY_INITIALS_EN
        labels = [initials[(today - timedelta(days=6 - i)).weekday()] for i in range(7)]
        self.chart.set_data(values, labels)

        w = st.week_summary(today)
        if not (w["breaks"] or w["active_s"]):
            self.r_totals.setText(tr("stats.no_data"))
            for lab in (self.r_best, self.r_longest, self.r_water):
                lab.setText("")
                lab.setVisible(False)
            return
        for lab in (self.r_best, self.r_longest, self.r_water):
            lab.setVisible(True)
        self.r_totals.setText(tr("stats.week_totals").replace("{b}", str(w["breaks"]))
                              .replace("{a}", dur(w["active_s"])).replace("{avg}", dur(w["avg_active_s"])))
        if w["best_day"]:
            name = tr(f"day.{w['best_day'].weekday()}")
            self.r_best.setText(tr("stats.best").replace("{d}", name).replace("{n}", str(w["best_day_breaks"])))
        else:
            self.r_best.setText("")
        self.r_longest.setText(tr("stats.longest_week").replace("{t}", dur(w["longest_run_s"])))
        self.r_water.setText(tr("stats.water_week").replace("{n}", str(w["water"])))
