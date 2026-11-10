//! Settings: appearance, updates, sounds, shortcuts and about.

use std::collections::HashMap;

use iced::widget::text_input;
use iced::Element;

use crate::common::changelog;
use crate::common::hotkeys::ACTIONS;
use crate::common::i18n::tr_fmt_in;
use crate::engine::Engine;
use crate::ui::actions::{BoolKey, IntKey, Setting, StrKey};
use crate::ui::app::Message;
use crate::ui::theme::Btn;
use crate::ui::widgets::*;
use crate::updates::{UpdateManager, UpdateState};

fn sw<'a>(ctx: Ctx, on: bool, key: BoolKey) -> Element<'a, Message> {
    toggle(ctx, on, move |v| Message::Set(Setting::Bool(key, v)))
}

fn update_row<'a>(ctx: Ctx, um: &UpdateManager) -> Element<'a, Message> {
    let v = um.release.as_ref().map(|r| r.version.clone()).unwrap_or_default();
    let fmt = |key: &str, args: &[(&str, &str)]| tr_fmt_in(ctx.lang(), key, args);
    let can_self_update = crate::common::updater::can_self_update();
    let (desc, button): (String, Element<'a, Message>) = match um.state {
        UpdateState::Idle => (ctx.t("upd.idle"), action_button(ctx, Some("refresh"), &ctx.t("upd.btn_check"), Btn::Secondary, Message::CheckUpdates).into()),
        UpdateState::Checking => (ctx.t("upd.checking"), styled_button(ctx, label::<Message>(ctx, ctx.t("upd.btn_checking"), Txt::Muted), Btn::Secondary, None).into()),
        UpdateState::UpToDate => (ctx.t("upd.up_to_date"), action_button(ctx, Some("refresh"), &ctx.t("upd.btn_check"), Btn::Secondary, Message::CheckUpdates).into()),
        UpdateState::Available if can_self_update => (fmt("upd.available", &[("v", &v)]), action_button(ctx, Some("download"), &ctx.t("upd.btn_download"), Btn::Primary, Message::DownloadUpdate).into()),
        UpdateState::Available => (fmt("upd.manual_only", &[("v", &v)]), action_button(ctx, Some("external-link"), &ctx.t("upd.btn_open"), Btn::Secondary, Message::OpenReleasePage).into()),
        UpdateState::Downloading => (
            fmt("upd.downloading", &[("p", &((um.progress * 100.0) as i64).to_string())]),
            styled_button(ctx, label::<Message>(ctx, ctx.t("upd.btn_downloading"), Txt::Muted), Btn::Secondary, None).into(),
        ),
        UpdateState::Ready => (fmt("upd.ready", &[("v", &v)]), action_button(ctx, Some("power"), &ctx.t("upd.btn_install"), Btn::Primary, Message::InstallUpdate).into()),
        UpdateState::Error => (ctx.t("upd.error"), action_button(ctx, Some("refresh"), &ctx.t("upd.btn_retry"), Btn::Secondary, Message::CheckUpdates).into()),
    };
    setting_row(ctx, &fmt("upd.version", &[("v", crate::VERSION)]), &desc, button)
}

fn shortcut_field<'a>(ctx: Ctx, index: usize, current: &str, drafts: &'a HashMap<String, String>, error: Option<&String>) -> Element<'a, Message> {
    let id = format!("{:?}", StrKey::Hotkey(index));
    let shown = drafts.get(&id).cloned().unwrap_or_else(|| current.to_string());
    let p = ctx.p;
    let bad = error.is_some();
    let field = text_input("Ctrl+Alt+N", &shown)
        .on_input(move |v| Message::TimeDraft(StrKey::Hotkey(index), v))
        .width(170)
        .padding(8)
        .style(move |_, _| iced::widget::text_input::Style {
            background: iced::Background::Color(p.surface_raised),
            border: iced::Border { color: if bad { p.danger } else { p.border }, width: 1.0, radius: 10.0.into() },
            icon: p.text_muted,
            placeholder: p.text_faint,
            value: p.text,
            selection: p.accent_soft,
        });
    match error {
        Some(msg) => rcol![ctx; field, label::<Message>(ctx, msg.clone(), Txt::Caption).color(p.danger)].spacing(4).into(),
        None => field.into(),
    }
}

pub fn view<'a>(ctx: Ctx, e: &'a Engine, um: &UpdateManager, drafts: &'a HashMap<String, String>, hk_errors: &'a HashMap<usize, String>) -> Element<'a, Message> {
    let s = &e.settings;
    let g = &s.general;
    let t = |k: &str| ctx.t(k);

    let appearance = card_rows(
        ctx,
        vec![
            setting_row(ctx, &t("set.theme"), "", segmented(ctx, &[("dark", t("set.dark")), ("light", t("set.light")), ("system", t("set.system"))], &g.theme, |k| Message::Set(Setting::Str(StrKey::Theme, k)))),
            setting_row(ctx, &t("set.language"), "", segmented(ctx, &[("en", "English".to_string()), ("fa", "فارسی".to_string())], &g.language, |k| Message::Set(Setting::Str(StrKey::Language, k)))),
            setting_row(ctx, &t("set.autostart"), &t("set.autostart_desc"), sw(ctx, g.autostart, BoolKey::Autostart)),
            setting_row(ctx, &t("set.animations"), &t("set.animations_desc"), sw(ctx, g.animations, BoolKey::Animations)),
        ],
    );

    let mut update_rows = vec![update_row(ctx, um), setting_row(ctx, &t("set.auto_update"), &t("set.auto_update_desc"), sw(ctx, g.auto_update, BoolKey::AutoUpdate))];
    if let Some(r) = um.release.as_ref().filter(|_| matches!(um.state, UpdateState::Available | UpdateState::Ready | UpdateState::Downloading)) {
        let notes = crate::common::updater::summarize_notes(&r.notes, ctx.lang(), 5);
        if !notes.is_empty() {
            let mut col = rcol![ctx; label::<Message>(ctx, tr_fmt_in(ctx.lang(), "upd.whats_new", &[("v", &r.version)]), Txt::Title)].spacing(6);
            for n in notes {
                col = col.push(label::<Message>(ctx, format!("• {n}"), Txt::Muted));
            }
            update_rows.push(iced::widget::container(col).padding([14.0, 0.0]).into());
        }
    }
    let _ = changelog::BUNDLED;
    let updates = card_rows(ctx, update_rows);

    let sound = &s.sound;
    let mut sound_rows = vec![setting_row(ctx, &t("set.sound"), &t("set.sound_desc"), sw(ctx, sound.enabled, BoolKey::SoundOn))];
    if sound.enabled {
        sound_rows.push(setting_row(ctx, &t("set.sound_volume"), "", slider_row(ctx, 0..=100, sound.volume as i32, "%", |v| Message::Set(Setting::Int(IntKey::Volume, i64::from(v))))));
        sound_rows.push(setting_row(ctx, &t("set.sound_reminders"), &t("set.sound_reminders_desc"), sw(ctx, sound.reminder_sounds, BoolKey::ReminderSounds)));
        sound_rows.push(setting_row(ctx, &t("set.sound_test"), "", action_button(ctx, Some("play"), &t("set.sound_test"), Btn::Secondary, Message::PlaySample).into()));
    }

    let hk = &s.hotkeys;
    let mut hk_rows = vec![setting_row(ctx, &t("set.hotkeys"), &t("set.hotkeys_desc"), sw(ctx, hk.enabled, BoolKey::HkEnabled))];
    if hk.enabled {
        let combos = [&hk.night_light, &hk.break_now, &hk.pause, &hk.quiet];
        for (i, action) in ACTIONS.iter().enumerate() {
            hk_rows.push(setting_row(ctx, &t(&format!("hk.{action}")), "", shortcut_field(ctx, i, combos[i], drafts, hk_errors.get(&i))));
        }
    }

    let about = card_rows(ctx, vec![setting_row(ctx, &t("set.made_by"), &format!("Eye Care {}", crate::VERSION), action_button(ctx, Some("external-link"), &t("set.open_github"), Btn::Ghost, Message::OpenAuthor).into())]);

    rcol![ctx; 
        section(ctx, &t("set.system")),
        appearance,
        section(ctx, &t("set.updates")),
        updates,
        section(ctx, &t("set.sound")),
        card_rows(ctx, sound_rows),
        section(ctx, &t("set.hotkeys")),
        card_rows(ctx, hk_rows),
        section(ctx, &t("set.about")),
        about
    ]
    .spacing(12)
    .into()
}
