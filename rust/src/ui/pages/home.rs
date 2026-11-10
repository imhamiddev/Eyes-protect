//! Home: next-break ring, quick actions, today's stats and the weekly chart.

use chrono::{Datelike, Duration, Local, TimeZone};
use iced::alignment::Vertical;
use iced::widget::container;
use iced::{Element, Length};

use crate::common::stats::today;
use crate::common::timeutil::format_mmss;
use crate::engine::Engine;
use crate::features::rule202020::Phase;
use crate::ui::app::Message;
use crate::ui::theme::Btn;
use crate::ui::widgets::*;

const WEEKDAYS_EN: [&str; 7] = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const WEEKDAYS_FA: [&str; 7] = ["د", "س", "چ", "پ", "ج", "ش", "ی"]; // Mon..Sun (Persian initials)

pub fn weekday_labels(ctx: Ctx, days: i64) -> Vec<String> {
    let names = if ctx.fa { WEEKDAYS_FA } else { WEEKDAYS_EN };
    let t = today();
    (0..days).rev().map(|i| names[(t - Duration::days(i)).weekday().num_days_from_monday() as usize].to_string()).collect()
}

/// The status line under the ring.
pub fn status_text(ctx: Ctx, e: &Engine) -> String {
    let rule = &e.rule;
    if rule.phase == Phase::Break {
        return ctx.t("break.title");
    }
    if e.paused {
        return ctx.t("home.resume");
    }
    if e.quiet_active() {
        if e.quiet_until.is_infinite() {
            return ctx.t("home.quiet_on");
        }
        let until = Local.timestamp_opt(e.quiet_until as i64, 0).single().map(|d| d.format("%H:%M").to_string()).unwrap_or_default();
        return crate::common::i18n::tr_fmt_in(ctx.lang(), "home.quiet_until", &[("t", &until)]);
    }
    if let Some(reason) = e.busy_reason {
        return ctx.t(&format!("home.busy_{}", reason.as_str()));
    }
    if !e.settings.rule202020.enabled {
        return ctx.t("home.rule_off");
    }
    "20 · 20 · 20".to_string()
}

pub fn view<'a>(ctx: Ctx, e: &'a Engine) -> Element<'a, Message> {
    let rule = &e.rule;
    let (progress, ring_text) = if rule.phase == Phase::Break {
        let total = rule.settings().break_seconds.max(1) as f32;
        (1.0 - rule.break_seconds_left() as f32 / total, format_mmss(rule.break_seconds_left()))
    } else {
        (rule.work_progress() as f32, format_mmss(rule.seconds_to_break()))
    };
    let quiet_label = ctx.t(if e.quiet_active() { "home.quiet_end" } else { "home.quiet_1h" });
    let hero = card_padded(
        ctx,
        28,
        rcol![ctx; 
            label::<Message>(ctx, ctx.t("home.next_break"), Txt::Caption),
            container(ring(ctx, 230.0, progress, ring_text)).center_x(Length::Fill),
            label_center::<Message>(ctx, status_text(ctx, e), Txt::Muted),
            h_row(
                ctx,
                vec![
                    container(action_button(ctx, Some("coffee"), &ctx.t("home.take_break"), Btn::Primary, Message::TakeBreak).width(Length::Fill)).width(Length::Fill).into(),
                    action_button(ctx, Some(if e.paused { "play" } else { "pause" }), &ctx.t(if e.paused { "home.resume" } else { "home.pause" }), Btn::Secondary, Message::TogglePause).into(),
                ],
            )
            .spacing(10),
            container(action_button(ctx, Some("bell"), &quiet_label, Btn::Ghost, Message::ToggleQuiet)).center_x(Length::Fill),
        ]
        .spacing(16),
    );

    let s = &e.stats;
    let tiles = rcol![ctx; 
        h_row(
            ctx,
            vec![
                container(stat_card(ctx, "coffee", &ctx.t("home.breaks"), s.get("breaks", None).to_string())).width(Length::Fill).into(),
                container(stat_card(ctx, "droplet", &ctx.t("home.water"), s.get("water", None).to_string())).width(Length::Fill).into(),
            ],
        )
        .spacing(16),
        stat_card(ctx, "eye", &ctx.t("home.blinks"), s.get("blinks", None).to_string()),
    ]
    .spacing(16);
    let chart = card_padded(
        ctx,
        [18.0, 22.0],
        rcol![ctx; 
            label::<Message>(ctx, ctx.t("home.week"), Txt::Title),
            bar_chart(ctx, s.last_days("breaks", 7, None), weekday_labels(ctx, 7), 150.0),
        ]
        .spacing(10),
    );
    let right = rcol![ctx; tiles, chart].spacing(16).width(Length::FillPortion(6));
    let left = container(hero).width(Length::FillPortion(5));
    h_row(ctx, vec![left.into(), right.into()]).spacing(20).align_y(Vertical::Top).into()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::ui::theme::DARK;

    #[test]
    fn weekday_labels_end_with_today() {
        let ctx = Ctx { p: DARK, fa: false };
        let labels = weekday_labels(ctx, 7);
        assert_eq!(labels.len(), 7);
        let expected = WEEKDAYS_EN[today().weekday().num_days_from_monday() as usize];
        assert_eq!(labels.last().unwrap(), expected);
        let fa = weekday_labels(Ctx { fa: true, ..ctx }, 7);
        assert!(WEEKDAYS_FA.contains(&fa[0].as_str()));
    }
}
