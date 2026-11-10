//! Display: night light, dimmer, per-monitor control and auto dark mode.

use iced::widget::{pick_list, text_input};
use iced::Element;

use crate::common::cities::{city_by_key, city_name, CITIES};
use crate::common::i18n::tr_fmt_in;
use crate::common::monitors as mon;
use crate::common::sun::{format_minutes, sun_times, Polar};
use crate::engine::Engine;
use crate::features::display::local_utc_offset_hours;
use crate::ui::actions::{BoolKey, IntKey, Setting, StrKey};
use crate::ui::app::Message;
use crate::ui::theme::Btn;
use crate::ui::widgets::*;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CityOption {
    pub key: &'static str,
    pub name: &'static str,
}
impl std::fmt::Display for CityOption {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.name)
    }
}

fn sw<'a>(ctx: Ctx, on: bool, key: BoolKey) -> Element<'a, Message> {
    toggle(ctx, on, move |v| Message::Set(Setting::Bool(key, v)))
}

/// A text box for `HH:MM`; invalid text is kept as a draft until it parses.
fn time_field<'a>(ctx: Ctx, key: StrKey, current: &str, drafts: &'a std::collections::HashMap<String, String>) -> Element<'a, Message> {
    let id = format!("{key:?}");
    let shown = drafts.get(&id).cloned().unwrap_or_else(|| current.to_string());
    let valid = drafts.get(&id).is_none();
    let p = ctx.p;
    text_input("HH:MM", &shown)
        .on_input(move |v| Message::TimeDraft(key, v))
        .width(84)
        .padding(8)
        .style(move |_, _| iced::widget::text_input::Style {
            background: iced::Background::Color(p.surface_raised),
            border: iced::Border { color: if valid { p.border } else { p.danger }, width: 1.0, radius: 10.0.into() },
            icon: p.text_muted,
            placeholder: p.text_faint,
            value: p.text,
            selection: p.accent_soft,
        })
        .into()
}

pub fn view<'a>(ctx: Ctx, e: &'a Engine, drafts: &'a std::collections::HashMap<String, String>) -> Element<'a, Message> {
    let s = &e.settings;
    let t = |k: &str| ctx.t(k);
    let nl = &s.night_light;
    let city = city_by_key(&s.location.city);
    let options: Vec<CityOption> = CITIES.iter().map(|c| CityOption { key: c.key, name: city_name(c, ctx.lang()) }).collect();
    let selected = Some(CityOption { key: city.key, name: city_name(city, ctx.lang()) });
    let picker = pick_list(options, selected, |o: CityOption| Message::Set(Setting::Str(StrKey::City, o.key.to_string()))).width(180);

    // ---- night light --------------------------------------------------------------------------
    let mut night = vec![setting_row(ctx, &t("display.night"), &t("display.night_desc"), sw(ctx, nl.enabled, BoolKey::NlOn))];
    if nl.enabled {
        night.push(setting_row(ctx, &t("display.warmth"), "", slider_row(ctx, 0..=100, nl.strength as i32, "%", |v| Message::Set(Setting::Int(IntKey::Warmth, i64::from(v))))));
        night.push(setting_row(ctx, &t("display.schedule"), "", sw(ctx, nl.schedule, BoolKey::NlSchedule)));
        if nl.schedule {
            night.push(setting_row(ctx, &t("display.sun"), &t("display.sun_desc"), sw(ctx, nl.sun, BoolKey::NlSun)));
            if nl.sun {
                night.push(setting_row(ctx, &t("display.city"), "", picker.into()));
                let st = sun_times(chrono::Local::now().date_naive(), city.lat, city.lon, local_utc_offset_hours());
                let info = match (st.polar, st.sunset, st.sunrise) {
                    (Some(Polar::Day), _, _) => t("display.sun_polar_day"),
                    (Some(Polar::Night), _, _) => t("display.sun_polar_night"),
                    (None, Some(set), Some(rise)) => tr_fmt_in(ctx.lang(), "display.sun_info", &[("s", &format_minutes(set)), ("r", &format_minutes(rise))]),
                    _ => String::new(),
                };
                night.push(setting_row(ctx, "", &info, iced::widget::Space::new(0, 0).into()));
            } else {
                night.push(setting_row(ctx, &t("display.from"), "", time_field(ctx, StrKey::NlStart, &nl.start, drafts)));
                night.push(setting_row(ctx, &t("display.to"), "", time_field(ctx, StrKey::NlEnd, &nl.end, drafts)));
            }
            night.push(setting_row(ctx, &t("display.transition"), "", stepper(ctx, nl.transition_min, 0, 60, 5, |v| Message::Set(Setting::Int(IntKey::Transition, v)))));
        }
    }

    // ---- dimmer -------------------------------------------------------------------------------
    let d = &s.dimmer;
    let mut dim = vec![setting_row(ctx, &t("display.dimmer"), &t("display.dimmer_desc"), sw(ctx, d.enabled, BoolKey::DimOn))];
    if d.enabled {
        let profiles = [("day", t("display.day")), ("night", t("display.night_p")), ("study", t("display.study"))];
        dim.push(setting_row(ctx, &t("display.profile"), "", segmented(ctx, &profiles, &d.profile, |k| Message::Set(Setting::Str(StrKey::Profile, k)))));
        let bright = |key: IntKey, v: i64| slider_row(ctx, 30..=100, v as i32, "%", move |n| Message::Set(Setting::Int(key, i64::from(n))));
        dim.push(setting_row(ctx, &t("display.day"), "", bright(IntKey::BDay, d.day)));
        dim.push(setting_row(ctx, &t("display.night_brightness"), "", bright(IntKey::BNight, d.night)));
        dim.push(setting_row(ctx, &t("display.study"), "", bright(IntKey::BStudy, d.study)));
        dim.push(setting_row(ctx, &t("display.schedule"), "", sw(ctx, d.schedule, BoolKey::DimSchedule)));
        if d.schedule {
            dim.push(setting_row(ctx, &t("display.sun"), "", sw(ctx, d.sun, BoolKey::DimSun)));
            if !d.sun {
                dim.push(setting_row(ctx, &t("display.from"), "", time_field(ctx, StrKey::DStart, &d.night_start, drafts)));
                dim.push(setting_row(ctx, &t("display.to"), "", time_field(ctx, StrKey::DEnd, &d.night_end, drafts)));
            }
        }
    }

    // ---- monitors -----------------------------------------------------------------------------
    let excluded = mon::parse_set(&s.monitors.excluded);
    let factors = mon::parse_map(&s.monitors.brightness);
    let mut monitors = vec![setting_row(ctx, &t("display.monitors"), &t("display.monitors_desc"), iced::widget::Space::new(0, 0).into())];
    for (i, m) in e.monitors.iter().enumerate() {
        let key = mon::key(&m.device);
        let on = !excluded.contains(&key);
        let factor = i64::from(factors.get(&key).copied().unwrap_or(100));
        let mut name = tr_fmt_in(ctx.lang(), "display.monitor", &[("n", &(i + 1).to_string())]);
        if m.primary {
            name = format!("{name} · {}", t("display.main"));
        }
        let k1 = key.clone();
        let k2 = key.clone();
        let mut controls = vec![toggle(ctx, on, move |v| Message::Set(Setting::MonitorOn(k1.clone(), v)))];
        if on {
            controls.insert(0, slider_row(ctx, 30..=100, factor as i32, "%", move |n| Message::Set(Setting::MonitorBrightness(k2.clone(), i64::from(n)))));
        }
        monitors.push(setting_row(ctx, &name, &format!("{}×{}", m.width, m.height), h_row(ctx, controls).spacing(16).into()));
    }

    // ---- auto dark ---------------------------------------------------------------------------
    let ad = &s.auto_dark;
    let mut auto = vec![setting_row(ctx, &t("display.auto_dark"), &t("display.auto_dark_desc"), sw(ctx, ad.enabled, BoolKey::AdOn))];
    if ad.enabled {
        auto.push(setting_row(ctx, &t("display.light_from"), "", time_field(ctx, StrKey::AdLight, &ad.light_from, drafts)));
        auto.push(setting_row(ctx, &t("display.dark_from"), "", time_field(ctx, StrKey::AdDark, &ad.dark_from, drafts)));
    }
    let _ = Btn::Primary;
    rcol![ctx; card_rows(ctx, night), card_rows(ctx, dim), card_rows(ctx, monitors), card_rows(ctx, auto)].spacing(16).into()
}
