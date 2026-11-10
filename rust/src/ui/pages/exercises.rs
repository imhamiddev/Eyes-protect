//! Exercises: guided eye routines and body stretches with a step-by-step runner.

use iced::widget::container;
use iced::{Element, Length};

use crate::common::exercises::{by_id, Exercise, Kind, EXERCISES, STRETCHES};
use crate::common::timeutil::format_mmss;
use crate::ui::app::Message;
use crate::ui::theme::Btn;
use crate::ui::widgets::*;

/// A routine that is currently running.
#[derive(Debug, Clone, PartialEq)]
pub struct Run {
    pub id: &'static str,
    pub step: usize,
    pub left: f64,
}

impl Run {
    pub fn start(id: &'static str) -> Option<Run> {
        let ex = by_id(id)?;
        Some(Run { id: ex.id, step: 0, left: f64::from(ex.steps.first()?.seconds) })
    }

    pub fn exercise(&self) -> &'static Exercise {
        by_id(self.id).expect("a Run is only created for known exercises")
    }

    /// Advance by `dt` seconds. Returns `false` once the routine is finished.
    pub fn tick(&mut self, dt: f64) -> bool {
        self.left -= dt;
        if self.left <= 0.0 {
            return self.next();
        }
        true
    }

    /// Jump to the next step; `false` when there is none.
    pub fn next(&mut self) -> bool {
        let steps = self.exercise().steps;
        self.step += 1;
        match steps.get(self.step) {
            Some(s) => {
                self.left = f64::from(s.seconds);
                true
            }
            None => false,
        }
    }
}

fn pick<'a>(ctx: Ctx, en: &'a str, fa: &'a str) -> &'a str {
    if ctx.fa { fa } else { en }
}

fn list_card<'a>(ctx: Ctx, items: &'static [Exercise]) -> Element<'a, Message> {
    let p = ctx.p;
    let mut rows: Vec<Element<'a, Message>> = Vec::new();
    for ex in items {
        let info = rcol![ctx; 
            label::<Message>(ctx, pick(ctx, ex.title_en, ex.title_fa).to_string(), Txt::Body),
            label::<Message>(ctx, format!("{} {}", ex.total_seconds(), ctx.t("ex.seconds")), Txt::Caption),
        ]
        .spacing(3);
        let r = h_row(
            ctx,
            vec![
                icon(ex.icon, 20.0, p.accent),
                container(info).width(Length::Fill).into(),
                action_button(ctx, Some("play"), &ctx.t("ex.start"), Btn::Secondary, Message::StartExercise(ex.id)).into(),
            ],
        )
        .spacing(14)
        .align_y(iced::alignment::Vertical::Center);
        rows.push(container(r).padding([12.0, 0.0]).width(Length::Fill).into());
    }
    card_rows(ctx, rows)
}

pub fn view<'a>(ctx: Ctx, run: Option<&Run>) -> Element<'a, Message> {
    let mut page = rcol![ctx; label::<Message>(ctx, ctx.t("ex.subtitle"), Txt::Muted)].spacing(16);
    if let Some(run) = run {
        let ex = run.exercise();
        let step = &ex.steps[run.step];
        let total = f64::from(step.seconds);
        let body = rcol![ctx; 
            label::<Message>(ctx, format!("{} · {}/{}", pick(ctx, ex.title_en, ex.title_fa), run.step + 1, ex.steps.len()), Txt::Caption),
            container(ring(ctx, 200.0, (1.0 - run.left / total) as f32, format_mmss(run.left.ceil() as i64))).center_x(Length::Fill),
            label_center::<Message>(ctx, pick(ctx, step.en, step.fa).to_string(), Txt::Title),
            container(
                h_row(
                    ctx,
                    vec![
                        action_button(ctx, Some("skip"), &ctx.t("ex.next"), Btn::Primary, Message::NextExerciseStep).into(),
                        action_button(ctx, None, &ctx.t("ex.done"), Btn::Secondary, Message::StopExercise).into(),
                    ],
                )
                .spacing(10),
            )
            .center_x(Length::Fill),
        ]
        .spacing(14);
        page = page.push(card_padded(ctx, 24, body));
    }
    page = page.push(label::<Message>(ctx, ctx.t("ex.eyes"), Txt::Caption)).push(list_card(ctx, EXERCISES));
    page = page.push(label::<Message>(ctx, ctx.t("ex.body"), Txt::Caption)).push(list_card(ctx, STRETCHES));
    let _ = Kind::Eyes;
    page.into()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn run_walks_through_every_step_then_finishes() {
        let mut run = Run::start("palming").unwrap();
        let steps = run.exercise().steps.len();
        let mut seen = 1;
        while run.tick(1.0) {
            if run.left == f64::from(run.exercise().steps[run.step].seconds) {
                seen += 1;
            }
        }
        assert_eq!(seen, steps);
        assert_eq!(Run::start("nope"), None);
    }

    #[test]
    fn next_skips_the_rest_of_a_step() {
        let mut run = Run::start("palming").unwrap();
        assert!(run.next());
        assert_eq!(run.step, 1);
        while run.next() {}
        assert!(!run.next());
    }
}
