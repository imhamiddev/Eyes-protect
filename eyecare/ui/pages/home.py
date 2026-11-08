"""Home: next-break ring, quick actions, today's stats and the weekly chart."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QVBoxLayout, QWidget

from eyecare.core import i18n
from eyecare.core.timeutil import format_mmss
from eyecare.features.rule202020 import Phase

from ..widgets import BarChart, Card, Ring, StatCard, ghost_button, label, primary_button, secondary_button
from .base import Page

WEEKDAYS_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
WEEKDAYS_FA = ["د", "س", "چ", "پ", "ج", "ش", "ی"]  # Mon..Sun (Persian initials)


class HomePage(Page):
    def __init__(self, engine):
        super().__init__(engine, "app", i18n.tr("tagline"))
        row = QHBoxLayout()
        row.setSpacing(20)

        hero = Card()
        hl = QVBoxLayout(hero)
        hl.setContentsMargins(28, 28, 28, 28)
        hl.setSpacing(16)
        hl.addWidget(label(i18n.tr("home.next_break"), "Caption"))
        self.ring = Ring(230, 11)
        hl.addWidget(self.ring, 0, Qt.AlignmentFlag.AlignHCenter)
        self.status = label("", "Muted")
        hl.addWidget(self.status, 0, Qt.AlignmentFlag.AlignHCenter)
        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        self.break_btn = primary_button(i18n.tr("home.take_break"), "coffee")
        self.pause_btn = secondary_button(i18n.tr("home.pause"), "pause")
        buttons.addWidget(self.break_btn, 1)
        buttons.addWidget(self.pause_btn)
        hl.addLayout(buttons)
        self.quiet_btn = ghost_button(i18n.tr("home.quiet_1h"))
        self.quiet_btn.icon_name = "bell"
        hl.addWidget(self.quiet_btn, 0, Qt.AlignmentFlag.AlignHCenter)
        row.addWidget(hero, 5)

        right = QVBoxLayout()
        right.setSpacing(16)
        grid = QGridLayout()
        grid.setSpacing(16)
        self.breaks = StatCard("coffee", i18n.tr("home.breaks"))
        self.water = StatCard("droplet", i18n.tr("home.water"))
        self.blinks = StatCard("eye", i18n.tr("home.blinks"))
        grid.addWidget(self.breaks, 0, 0)
        grid.addWidget(self.water, 0, 1)
        grid.addWidget(self.blinks, 1, 0, 1, 2)
        right.addLayout(grid)
        chart_card = Card()
        cl = QVBoxLayout(chart_card)
        cl.setContentsMargins(22, 18, 22, 14)
        cl.addWidget(label(i18n.tr("home.week"), "Title"))
        self.chart = BarChart()
        cl.addWidget(self.chart)
        right.addWidget(chart_card, 1)
        row.addLayout(right, 6)
        self.col.addLayout(row)
        self.finish()

        self.break_btn.clicked.connect(self.engine.start_break)
        self.pause_btn.clicked.connect(lambda: self.engine.set_paused(not self.engine.paused))
        self.quiet_btn.clicked.connect(lambda: self.engine.toggle_quiet(60))
        self.refresh()

    def refresh(self) -> None:
        e, rule = self.engine, self.engine.rule
        if rule.phase == Phase.BREAK:
            self.ring.set_progress(1 - rule.break_seconds_left / max(1, rule.rest.duration))
            self.ring.set_text(format_mmss(rule.break_seconds_left))
            self.status.setText(i18n.tr("break.title"))
        else:
            self.ring.set_progress(rule.work_progress)
            self.ring.set_text(format_mmss(rule.seconds_to_break))
            if e.paused:
                self.status.setText(i18n.tr("home.resume"))
            elif e.quiet_active:
                if e.quiet_until == float("inf"):
                    self.status.setText(i18n.tr("home.quiet_on"))
                else:
                    until = datetime.fromtimestamp(e.quiet_until).strftime("%H:%M")
                    self.status.setText(i18n.tr("home.quiet_until").replace("{t}", until))
            elif e.busy_reason:
                self.status.setText(i18n.tr("home.busy_" + e.busy_reason))
            elif not e.settings.rule202020.enabled:
                self.status.setText(i18n.tr("home.rule_off"))
            else:
                self.status.setText("20 · 20 · 20")
        self.quiet_btn.setText(i18n.tr("home.quiet_end" if e.quiet_active else "home.quiet_1h"))
        paused = e.paused
        self.pause_btn.setText(i18n.tr("home.resume" if paused else "home.pause"))
        s = e.stats
        self.breaks.number.set_value(s.get("breaks"))
        self.water.number.set_value(s.get("water"))
        self.blinks.number.set_value(s.get("blinks"))
        labels = WEEKDAYS_FA if i18n.language() == "fa" else WEEKDAYS_EN
        today = date.today()
        days = [(today - timedelta(days=6 - i)).weekday() for i in range(7)]
        self.chart.set_data(s.last_days("breaks", 7), [labels[d] for d in days])
