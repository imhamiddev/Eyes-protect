//! Stats: streak, today's numbers, the last 7 days and weekly totals.


use iced::{Element, Length};

use crate::common::i18n::tr_fmt_in;
use crate::common::stats::today;
use crate::common::timeutil::format_duration;
use crate::engine::Engine;
use crate::ui::actions::{IntKey, Setting};
use crate::ui::app::Message;
use crate::ui::pages::home::weekday_labels;
use crate::ui::widgets::*;

fn duration(ctx: Ctx, seconds: i64) -> String {
    format_duration(seconds, &ctx.t("unit.h"), &ctx.t("unit.m"))
}

pub fn view<'a>(ctx: Ctx, e: &'a Engine) -> Element<'a, Message> {
    let s = &e.stats;
    let goal = e.settings.general.daily_break_goal;
    let streak = s.streak(goal, None);
    let week = s.week_summary(None);
    let tiles = h_row(
        ctx,
        vec![
            iced::widget::container(stat_card(ctx, "flame", &ctx.t("stats.streak"), format!("{streak} {}", ctx.t("stats.days")))).width(Length::Fill).into(),
            iced::widget::container(stat_card(ctx, "coffee", &ctx.t("stats.today_breaks"), format!("{} / {goal}", s.get("breaks", None)))).width(Length::Fill).into(),
            iced::widget::container(stat_card(ctx, "monitor", &ctx.t("stats.active"), duration(ctx, s.get("active_s", None)))).width(Length::Fill).into(),
        ],
    )
    .spacing(16);

    let chart = card_padded(
        ctx,
        [18.0, 22.0],
        rcol![ctx; label::<Message>(ctx, ctx.t("stats.trend"), Txt::Title), bar_chart(ctx, s.last_days("breaks", 7, None), weekday_labels(ctx, 7), 170.0)].spacing(10),
    );

    let mut lines = rcol![ctx; label::<Message>(ctx, ctx.t("stats.week"), Txt::Title)].spacing(8);
    if week.breaks == 0 && week.active_s == 0 {
        lines = lines.push(label::<Message>(ctx, ctx.t("stats.no_data"), Txt::Muted));
    } else {
        let totals = tr_fmt_in(ctx.lang(), "stats.week_totals", &[("b", &week.breaks.to_string()), ("a", &duration(ctx, week.active_s)), ("avg", &duration(ctx, week.avg_active_s))]);
        lines = lines.push(label::<Message>(ctx, totals, Txt::Muted));
        if let Some(day) = week.best_day {
            let names = ["day.0", "day.1", "day.2", "day.3", "day.4", "day.5", "day.6"];
            use chrono::Datelike;
            let name = ctx.t(names[day.weekday().num_days_from_monday() as usize]);
            lines = lines.push(label::<Message>(ctx, tr_fmt_in(ctx.lang(), "stats.best", &[("d", &name), ("n", &week.best_day_breaks.to_string())]), Txt::Muted));
        }
        if week.longest_run_s > 0 {
            lines = lines.push(label::<Message>(ctx, tr_fmt_in(ctx.lang(), "stats.longest_week", &[("t", &duration(ctx, week.longest_run_s))]), Txt::Muted));
        }
        if week.water > 0 {
            lines = lines.push(label::<Message>(ctx, tr_fmt_in(ctx.lang(), "stats.water_week", &[("n", &week.water.to_string())]), Txt::Muted));
        }
    }
    let goal_row = setting_row(ctx, &ctx.t("stats.goal"), &ctx.t("stats.goal_desc"), stepper(ctx, goal, 1, 50, 1, |v| Message::Set(Setting::Int(IntKey::DailyGoal, v))));
    let _ = today();
    rcol![ctx; tiles, chart, card_padded(ctx, [18.0, 22.0], lines), card(ctx, goal_row)].spacing(16).into()
}
