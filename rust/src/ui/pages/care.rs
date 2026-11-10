//! Care: 20-20-20 rule, smart pause and the blink / hydration / stretch reminders.

use iced::widget::column;
use iced::Element;

use crate::engine::Engine;
use crate::ui::actions::{BoolKey, IntKey, Setting};
use crate::ui::app::Message;
use crate::ui::widgets::*;

fn sw<'a>(ctx: Ctx, on: bool, key: BoolKey) -> Element<'a, Message> {
    toggle(ctx, on, move |v| Message::Set(Setting::Bool(key, v)))
}
fn num<'a>(ctx: Ctx, v: i64, min: i64, max: i64, step: i64, key: IntKey) -> Element<'a, Message> {
    stepper(ctx, v, min, max, step, move |n| Message::Set(Setting::Int(key, n)))
}

pub fn view<'a>(ctx: Ctx, e: &'a Engine) -> Element<'a, Message> {
    let s = &e.settings;
    let t = |k: &str| ctx.t(k);
    let rule = &s.rule202020;

    let mut rule_rows = vec![setting_row(ctx, &t("care.rule"), &t("care.rule_desc"), sw(ctx, rule.enabled, BoolKey::RuleEnabled))];
    if rule.enabled {
        rule_rows.push(setting_row(ctx, &t("care.interval"), "", num(ctx, rule.interval_min, 1, 120, 1, IntKey::Interval)));
        rule_rows.push(setting_row(ctx, &t("care.break_len"), "", num(ctx, rule.break_seconds, 5, 300, 5, IntKey::BreakLen)));
        rule_rows.push(setting_row(ctx, &t("care.snooze"), "", num(ctx, rule.snooze_min, 1, 30, 1, IntKey::Snooze)));
        rule_rows.push(setting_row(ctx, &t("care.natural"), "", sw(ctx, rule.detect_natural_breaks, BoolKey::Natural)));
        rule_rows.push(setting_row(ctx, &t("care.break_lock"), "", sw(ctx, rule.use_break_lock, BoolKey::Lock)));
        if rule.use_break_lock {
            rule_rows.push(setting_row(ctx, &t("care.skippable"), "", sw(ctx, s.break_lock.skippable, BoolKey::Skippable)));
        }
    }

    let sp = &s.smart_pause;
    let mut smart_rows = vec![setting_row(ctx, &t("care.smart"), &t("care.smart_desc"), sw(ctx, sp.enabled, BoolKey::SmartOn))];
    if sp.enabled {
        smart_rows.push(setting_row(ctx, &t("care.smart_fullscreen"), "", sw(ctx, sp.fullscreen, BoolKey::SmartFull)));
        smart_rows.push(setting_row(ctx, &t("care.smart_meetings"), "", sw(ctx, sp.meetings, BoolKey::SmartMeet)));
        smart_rows.push(setting_row(ctx, &t("care.smart_focus"), "", sw(ctx, sp.focus_assist, BoolKey::SmartFocus)));
    }

    let mut other = vec![setting_row(ctx, &t("care.blink"), &t("care.blink_desc"), sw(ctx, s.blink.enabled, BoolKey::BlinkOn))];
    if s.blink.enabled {
        other.push(setting_row(ctx, &t("care.interval"), "", num(ctx, s.blink.interval_min, 1, 60, 1, IntKey::BlinkInt)));
    }
    other.push(setting_row(ctx, &t("care.hydration"), &t("care.hydration_desc"), sw(ctx, s.hydration.enabled, BoolKey::WaterOn)));
    if s.hydration.enabled {
        other.push(setting_row(ctx, &t("care.interval"), "", num(ctx, s.hydration.interval_min, 5, 240, 5, IntKey::WaterInt)));
    }
    other.push(setting_row(ctx, &t("care.posture"), &t("care.posture_desc"), sw(ctx, s.posture.enabled, BoolKey::PostureOn)));
    if s.posture.enabled {
        other.push(setting_row(ctx, &t("care.interval"), "", num(ctx, s.posture.interval_min, 10, 180, 5, IntKey::PostureInt)));
    }

    column![card_rows(ctx, rule_rows), card_rows(ctx, smart_rows), card_rows(ctx, other)].spacing(16).into()
}
