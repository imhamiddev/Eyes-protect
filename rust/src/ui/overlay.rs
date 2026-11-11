//! Full-screen break screen and the small reminder toast.

use iced::alignment::Vertical;
use iced::widget::{container, Space};
use iced::{Element, Length};

use crate::common::exercises::{Exercise, Step, EXERCISES};
use crate::common::timeutil::format_mmss;
use crate::engine::Engine;
use crate::ui::app::Message;
use crate::ui::theme::{self, Btn};
use crate::ui::widgets::*;

/// What a toast asks the user.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ToastKind {
    /// 20-20-20 prompt: start the break or snooze.
    Rule,
    Blink,
    Water,
    Posture,
    /// An update was downloaded: restart now or later.
    Update,
}

impl ToastKind {
    /// How long the toast stays before it closes itself (the rule prompt is closed by the engine).
    pub fn lifetime_seconds(self) -> Option<u32> {
        match self {
            ToastKind::Rule => None,
            ToastKind::Blink => Some(8),
            ToastKind::Water | ToastKind::Posture => Some(20),
            ToastKind::Update => Some(30),
        }
    }

    fn keys(self) -> (&'static str, &'static str, &'static str) {
        match self {
            ToastKind::Rule => ("toast.rule_title", "toast.rule_body", "eye"),
            ToastKind::Blink => ("toast.blink_title", "toast.blink_body", "eye"),
            ToastKind::Water => ("toast.water_title", "toast.water_body", "droplet"),
            ToastKind::Posture => ("toast.posture_title", "toast.posture_body", "activity"),
            ToastKind::Update => ("upd.toast_title", "upd.toast_body", "download"),
        }
    }
}

/// The exercise step to show `elapsed` seconds into a break (routines repeat if the break is longer).
pub fn step_at(exercise: &Exercise, elapsed: f64) -> (usize, &Step) {
    let total: f64 = exercise.steps.iter().map(|s| f64::from(s.seconds)).sum::<f64>().max(1.0);
    let mut t = elapsed.max(0.0) % total;
    for (i, step) in exercise.steps.iter().enumerate() {
        if t < f64::from(step.seconds) {
            return (i, step);
        }
        t -= f64::from(step.seconds);
    }
    (exercise.steps.len() - 1, exercise.steps.last().expect("exercises have steps"))
}

/// Which eye exercise accompanies today's n-th break.
pub fn exercise_for(break_index: i64) -> &'static Exercise {
    &EXERCISES[break_index.rem_euclid(EXERCISES.len() as i64) as usize]
}

pub fn break_view<'a>(ctx: Ctx, e: &'a Engine) -> Element<'a, Message> {
    let p = ctx.p;
    let cfg = &e.settings.rule202020;
    let total = cfg.break_seconds.max(1);
    let left = e.rule.break_seconds_left();
    let elapsed = (total - left).max(0);
    let progress = elapsed as f32 / total as f32;
    let mut body = rcol![
        ctx;
        label_center::<Message>(ctx, ctx.t("break.title"), Txt::H1),
        label_center::<Message>(ctx, ctx.t("break.hint"), Txt::Muted),
        Space::new(0.0, 12.0),
        ring(ctx, 260.0, progress, format_mmss(left)),
    ]
    .spacing(10)
    .align_x(iced::Alignment::Center);
    if e.settings.break_lock.show_exercise {
        let ex = exercise_for(e.stats.get("breaks", None));
        let (_, step) = step_at(ex, elapsed as f64);
        let text = if ctx.fa { step.fa } else { step.en };
        body = body.push(Space::new(0.0, 8.0)).push(label_center::<Message>(ctx, text.to_string(), Txt::Title));
    }
    let can_skip = e.settings.break_lock.skippable && elapsed >= e.settings.break_lock.skip_after_seconds;
    if can_skip {
        body = body.push(Space::new(0.0, 12.0)).push(action_button(
            ctx,
            Some("skip"),
            &ctx.t("break.skip"),
            Btn::Secondary,
            Message::SkipBreak,
        ));
    }
    container(container(body).center(Length::Fill)).width(Length::Fill).height(Length::Fill).style(move |_| theme::overlay(p)).into()
}

pub fn toast_view<'a>(ctx: Ctx, kind: ToastKind, version: &str) -> Element<'a, Message> {
    let p = ctx.p;
    let (title_key, body_key, icon_name) = kind.keys();
    let body_text =
        if kind == ToastKind::Update { crate::common::i18n::tr_fmt_in(ctx.lang(), body_key, &[("v", version)]) } else { ctx.t(body_key) };
    let head = h_row(ctx, vec![icon(icon_name, 22.0, p.accent), label::<Message>(ctx, ctx.t(title_key), Txt::Title).into()])
        .spacing(10)
        .align_y(Vertical::Center);
    let buttons: Vec<Element<'a, Message>> = match kind {
        ToastKind::Rule => vec![
            action_button(ctx, Some("coffee"), &ctx.t("toast.start"), Btn::Primary, Message::ToastStartBreak).into(),
            action_button(ctx, None, &ctx.t("toast.snooze"), Btn::Secondary, Message::ToastSnooze).into(),
        ],
        ToastKind::Water => vec![
            action_button(ctx, Some("droplet"), &ctx.t("toast.drank"), Btn::Primary, Message::ToastDrank).into(),
            action_button(ctx, None, &ctx.t("toast.dismiss"), Btn::Secondary, Message::DismissToast).into(),
        ],
        ToastKind::Posture => vec![
            action_button(ctx, Some("activity"), &ctx.t("toast.posture_start"), Btn::Primary, Message::ToastShowStretch).into(),
            action_button(ctx, None, &ctx.t("toast.dismiss"), Btn::Secondary, Message::DismissToast).into(),
        ],
        ToastKind::Update => vec![
            action_button(ctx, Some("power"), &ctx.t("upd.toast_install"), Btn::Primary, Message::InstallUpdate).into(),
            action_button(ctx, None, &ctx.t("upd.toast_later"), Btn::Secondary, Message::DismissToast).into(),
        ],
        ToastKind::Blink => vec![action_button(ctx, None, &ctx.t("toast.dismiss"), Btn::Secondary, Message::DismissToast).into()],
    };
    let content = rcol![ctx; head, label::<Message>(ctx, body_text, Txt::Muted), h_row(ctx, buttons).spacing(10)].spacing(12);
    container(content).padding(20).width(Length::Fill).height(Length::Fill).style(move |_| theme::toast(p)).into()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::common::exercises::by_id;

    #[test]
    fn steps_follow_elapsed_time_and_repeat() {
        let palming = by_id("palming").unwrap();
        assert_eq!(step_at(palming, 0.0).0, 0);
        let first = f64::from(palming.steps[0].seconds);
        assert_eq!(step_at(palming, first - 0.1).0, 0);
        assert_eq!(step_at(palming, first).0, 1);
        let total = f64::from(palming.total_seconds());
        assert_eq!(step_at(palming, total + 1.0).0, 0, "a longer break starts the routine again");
        assert_eq!(step_at(palming, -5.0).0, 0);
    }

    #[test]
    fn exercise_choice_cycles() {
        assert_eq!(exercise_for(0).id, EXERCISES[0].id);
        assert_eq!(exercise_for(EXERCISES.len() as i64).id, EXERCISES[0].id);
        assert_eq!(exercise_for(-1).id, EXERCISES[EXERCISES.len() - 1].id);
    }

    #[test]
    fn toast_lifetimes() {
        assert_eq!(ToastKind::Rule.lifetime_seconds(), None);
        assert!(ToastKind::Blink.lifetime_seconds().unwrap() < ToastKind::Water.lifetime_seconds().unwrap());
    }
}
