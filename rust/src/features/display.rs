//! Decides the screen colour/brightness and system theme from settings + time.

use chrono::{Local, NaiveDate, NaiveTime};

use crate::common::cities::City;
use crate::common::colortemp::{strength_to_kelvin, NEUTRAL_KELVIN};
use crate::common::config::{AutoDarkMode, Dimmer, NightLight};
use crate::common::sun::{sun_times, Polar};
use crate::common::timeutil::{in_window, minutes_precise, parse_hhmm};

pub const PROFILES: [&str; 3] = ["day", "night", "study"];

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct DisplayState {
    pub kelvin: i32,
    pub brightness: f64,
}

impl Default for DisplayState {
    fn default() -> Self {
        Self { kelvin: NEUTRAL_KELVIN, brightness: 1.0 }
    }
}

impl DisplayState {
    pub fn is_neutral(&self) -> bool {
        self.kelvin >= NEUTRAL_KELVIN && self.brightness >= 1.0
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum WindowKind {
    Range,
    Always,
    Never,
}

/// A daily window in minutes after midnight.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Window {
    pub start: f64,
    pub end: f64,
    pub kind: WindowKind,
}

impl Window {
    pub fn range(start: f64, end: f64) -> Self {
        Self { start, end, kind: WindowKind::Range }
    }
    pub fn always() -> Self {
        Self { start: 0.0, end: 0.0, kind: WindowKind::Always }
    }
    pub fn never() -> Self {
        Self { start: 0.0, end: 0.0, kind: WindowKind::Never }
    }
}

/// Optional inputs of [`compute_display_state`]; the defaults mean "now, in this time zone".
#[derive(Debug, Clone, Copy, Default)]
pub struct DisplayContext<'a> {
    pub city: Option<&'a City>,
    pub today: Option<NaiveDate>,
    pub utc_offset: Option<f64>,
}

pub fn local_utc_offset_hours() -> f64 {
    f64::from(Local::now().offset().local_minus_utc()) / 3600.0
}

pub fn resolve_window(start: &str, end: &str, sun: bool, city: Option<&City>, today: NaiveDate, utc_offset: f64) -> Window {
    if let (true, Some(city)) = (sun, city) {
        let st = sun_times(today, city.lat, city.lon, utc_offset);
        return match (st.polar, st.sunset, st.sunrise) {
            (Some(Polar::Day), _, _) => Window::never(),
            (Some(Polar::Night), _, _) => Window::always(),
            (None, Some(set), Some(rise)) => Window::range(set, rise),
            _ => Window::never(),
        };
    }
    match (parse_hhmm(start), parse_hhmm(end)) {
        (Ok(s), Ok(e)) => Window::range(minutes_of(s), minutes_of(e)),
        _ => Window::never(),
    }
}

fn minutes_of(t: NaiveTime) -> f64 {
    f64::from(crate::common::timeutil::minutes_of_day(t))
}

/// 0..1 strength of a scheduled effect: fades in after `start` and out before `end`.
pub fn schedule_factor(now_min: f64, window: &Window, transition_min: f64) -> f64 {
    match window.kind {
        WindowKind::Never => return 0.0,
        WindowKind::Always => return 1.0,
        WindowKind::Range => {}
    }
    let length = (window.end - window.start).rem_euclid(1440.0);
    if length == 0.0 {
        return 0.0;
    }
    let pos = (now_min - window.start).rem_euclid(1440.0);
    if pos >= length {
        return 0.0;
    }
    let ramp = transition_min.min(length / 2.0);
    if ramp <= 0.0 {
        return 1.0;
    }
    let f = (pos / ramp).min(1.0) * ((length - pos) / ramp).min(1.0);
    f * f * (3.0 - 2.0 * f) // smoothstep: gentle at both ends
}

fn safe_window(now: NaiveTime, start: &str, end: &str) -> bool {
    match (parse_hhmm(start), parse_hhmm(end)) {
        (Ok(s), Ok(e)) => in_window(now, s, e),
        _ => false,
    }
}

pub fn night_light_active(cfg: &NightLight, now: NaiveTime) -> bool {
    if !cfg.enabled {
        return false;
    }
    if cfg.schedule {
        safe_window(now, &cfg.start, &cfg.end)
    } else {
        true
    }
}

/// The profile in force: study is always manual; day/night follow the clock.
pub fn effective_profile(cfg: &Dimmer, now: NaiveTime) -> &'static str {
    let known = |p: &str| PROFILES.iter().copied().find(|k| *k == p).unwrap_or("day");
    if cfg.profile == "study" || !cfg.schedule {
        return known(&cfg.profile);
    }
    if safe_window(now, &cfg.night_start, &cfg.night_end) {
        "night"
    } else {
        "day"
    }
}

pub fn profile_brightness(cfg: &Dimmer, profile: &str) -> i64 {
    match profile {
        "day" => cfg.day,
        "night" => cfg.night,
        "study" => cfg.study,
        _ => 100,
    }
}

pub fn compute_display_state(night: &NightLight, dimmer: &Dimmer, now: NaiveTime, ctx: &DisplayContext) -> DisplayState {
    let today = ctx.today.unwrap_or_else(|| Local::now().date_naive());
    let tz = ctx.utc_offset.unwrap_or_else(local_utc_offset_hours);
    let now_min = minutes_precise(now);

    let mut f_night = 0.0;
    if night.enabled {
        if night.schedule {
            let win = resolve_window(&night.start, &night.end, night.sun, ctx.city, today, tz);
            f_night = schedule_factor(now_min, &win, night.transition_min as f64);
        } else {
            f_night = 1.0;
        }
    }
    let warm = f64::from(strength_to_kelvin(night.strength as i32));
    let neutral = f64::from(NEUTRAL_KELVIN);
    let kelvin = (neutral - (neutral - warm) * f_night).round_ties_even() as i32;

    let mut brightness = 1.0;
    if dimmer.enabled {
        if dimmer.profile == "study" || !dimmer.schedule {
            let profile = if PROFILES.contains(&dimmer.profile.as_str()) { dimmer.profile.as_str() } else { "day" };
            brightness = profile_brightness(dimmer, profile) as f64 / 100.0;
        } else {
            let win = resolve_window(&dimmer.night_start, &dimmer.night_end, dimmer.sun, ctx.city, today, tz);
            let f = schedule_factor(now_min, &win, night.transition_min as f64);
            brightness = (dimmer.day as f64 + (dimmer.night - dimmer.day) as f64 * f) / 100.0;
        }
    }
    DisplayState { kelvin, brightness: brightness.clamp(0.0, 1.0) }
}

/// `Some(true)`/`Some(false)` for the desired Windows theme (light/dark), `None` when off.
pub fn wants_light_theme(cfg: &AutoDarkMode, now: NaiveTime) -> Option<bool> {
    if !cfg.enabled {
        return None;
    }
    let (light_from, dark_from) = (parse_hhmm(&cfg.light_from).ok()?, parse_hhmm(&cfg.dark_from).ok()?);
    Some(in_window(now, light_from, dark_from))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::common::cities::city_by_key;

    fn t(h: u32, m: u32) -> NaiveTime {
        NaiveTime::from_hms_opt(h, m, 0).unwrap()
    }
    fn d(y: i32, m: u32, day: u32) -> NaiveDate {
        NaiveDate::from_ymd_opt(y, m, day).unwrap()
    }
    fn night_cfg() -> NightLight {
        NightLight::default()
    }
    const WIN: Window = Window { start: 1200.0, end: 390.0, kind: WindowKind::Range }; // 20:00 -> 06:30
    fn plain() -> DisplayContext<'static> {
        DisplayContext::default()
    }

    #[test]
    fn night_light_off_by_default() {
        assert!(!night_light_active(&night_cfg(), t(22, 0)));
    }

    #[test]
    fn night_light_schedule_window() {
        let cfg = NightLight { enabled: true, schedule: true, ..night_cfg() };
        assert!(night_light_active(&cfg, t(22, 0)) && !night_light_active(&cfg, t(12, 0)));
    }

    #[test]
    fn night_light_without_schedule_is_always_on() {
        let cfg = NightLight { enabled: true, schedule: false, ..night_cfg() };
        assert!(night_light_active(&cfg, t(12, 0)));
    }

    #[test]
    fn bad_schedule_strings_do_not_crash() {
        let cfg = NightLight { enabled: true, start: "x".into(), end: "y".into(), ..night_cfg() };
        assert!(!night_light_active(&cfg, t(12, 0)));
    }

    #[test]
    fn dimmer_profiles_follow_clock() {
        let dim = Dimmer { enabled: true, day: 100, night: 60, schedule: true, ..Dimmer::default() };
        assert_eq!(effective_profile(&dim, t(22, 0)), "night");
        assert_eq!(effective_profile(&dim, t(12, 0)), "day");
    }

    #[test]
    fn study_profile_is_manual() {
        let dim = Dimmer { enabled: true, profile: "study".into(), study: 80, schedule: true, ..Dimmer::default() };
        assert_eq!(effective_profile(&dim, t(22, 0)), "study");
    }

    #[test]
    fn manual_profile_without_schedule() {
        let dim = Dimmer { enabled: true, profile: "night".into(), schedule: false, ..Dimmer::default() };
        assert_eq!(effective_profile(&dim, t(12, 0)), "night");
    }

    #[test]
    fn display_state_combines_both() {
        let n = NightLight { enabled: true, strength: 100, schedule: false, ..night_cfg() };
        let dim = Dimmer { enabled: true, schedule: false, profile: "study".into(), study: 85, ..Dimmer::default() };
        let s = compute_display_state(&n, &dim, t(12, 0), &plain());
        assert_eq!(s.kelvin, 1900);
        assert!((s.brightness - 0.85).abs() < 1e-9);
        assert!(!s.is_neutral());
    }

    #[test]
    fn everything_off_is_neutral() {
        assert!(compute_display_state(&night_cfg(), &Dimmer::default(), t(12, 0), &plain()).is_neutral());
    }

    #[test]
    fn auto_dark_mode() {
        let cfg = AutoDarkMode { enabled: true, light_from: "07:00".into(), dark_from: "19:00".into() };
        assert_eq!(wants_light_theme(&cfg, t(12, 0)), Some(true));
        assert_eq!(wants_light_theme(&cfg, t(22, 0)), Some(false));
        assert_eq!(wants_light_theme(&AutoDarkMode::default(), t(12, 0)), None);
    }

    // ---- sunrise/sunset windows and gradual transitions --------------------------------
    #[test]
    fn factor_is_zero_outside_and_full_inside() {
        assert_eq!(schedule_factor(12.0 * 60.0, &WIN, 30.0), 0.0);
        assert_eq!(schedule_factor(23.0 * 60.0, &WIN, 30.0), 1.0);
        assert_eq!(schedule_factor(3.0 * 60.0, &WIN, 30.0), 1.0);
    }

    #[test]
    fn factor_ramps_up_after_start_and_down_before_end() {
        let up: Vec<f64> = [0.0, 5.0, 15.0, 25.0, 30.0].iter().map(|m| schedule_factor(1200.0 + m, &WIN, 30.0)).collect();
        assert!(up[0] == 0.0 && up[4] == 1.0);
        assert!(up.windows(2).all(|w| w[0] <= w[1]) && 0.0 < up[2] && up[2] < 1.0);
        let down: Vec<f64> = [0.0, 15.0, 25.0, 30.0].iter().map(|m| schedule_factor(360.0 + m, &WIN, 30.0)).collect();
        assert!(down[0] == 1.0 && down[3] == 0.0);
        assert!(down.windows(2).all(|w| w[0] >= w[1]));
    }

    #[test]
    fn zero_transition_is_a_hard_edge() {
        assert_eq!(schedule_factor(1200.0, &WIN, 0.0), 1.0);
        assert_eq!(schedule_factor(389.0, &WIN, 0.0), 1.0);
        assert_eq!(schedule_factor(390.0, &WIN, 0.0), 0.0);
    }

    #[test]
    fn short_window_caps_the_ramp() {
        let w = Window::range(600.0, 620.0); // 20 minutes
        assert_eq!(schedule_factor(610.0, &w, 60.0), 1.0);
        assert_eq!(schedule_factor(600.0, &w, 60.0), 0.0);
    }

    #[test]
    fn window_kinds_and_degenerate_windows() {
        assert_eq!(schedule_factor(100.0, &Window::always(), 30.0), 1.0);
        assert_eq!(schedule_factor(100.0, &Window::never(), 30.0), 0.0);
        assert_eq!(schedule_factor(100.0, &Window::range(480.0, 480.0), 30.0), 0.0);
    }

    #[test]
    fn resolve_window_fixed_times_and_bad_input() {
        let w = resolve_window("21:00", "05:30", false, None, d(2024, 1, 1), 0.0);
        assert_eq!((w.start, w.end, w.kind), (21.0 * 60.0, 5.0 * 60.0 + 30.0, WindowKind::Range));
        assert_eq!(resolve_window("zz", "05:30", false, None, d(2024, 1, 1), 0.0).kind, WindowKind::Never);
    }

    #[test]
    fn resolve_window_sun_uses_sunset_to_sunrise() {
        let w = resolve_window("", "", true, Some(city_by_key("tehran")), d(2024, 12, 21), 3.5);
        assert!(16.0 * 60.0 + 40.0 < w.start && w.start < 17.0 * 60.0 + 15.0);
        assert!(6.0 * 60.0 + 50.0 < w.end && w.end < 7.0 * 60.0 + 30.0);
    }

    #[test]
    fn resolve_window_polar() {
        let stockholm = city_by_key("stockholm");
        assert_eq!(resolve_window("", "", true, Some(stockholm), d(2024, 6, 21), 2.0).kind, WindowKind::Range);
        let arctic = City { key: "x", en: "x", fa: "x", lat: 69.65, lon: 18.96 };
        assert_eq!(resolve_window("", "", true, Some(&arctic), d(2024, 6, 21), 2.0).kind, WindowKind::Never);
        assert_eq!(resolve_window("", "", true, Some(&arctic), d(2024, 12, 21), 1.0).kind, WindowKind::Always);
    }

    #[test]
    fn night_light_fades_gradually_through_the_evening() {
        let n = NightLight { enabled: true, strength: 100, schedule: true, transition_min: 30, ..night_cfg() };
        let ks: Vec<i32> =
            [0, 10, 20, 30].iter().map(|m| compute_display_state(&n, &Dimmer::default(), t(20, *m), &plain()).kelvin).collect();
        assert!(ks[0] == 6500 && ks[3] == 1900);
        assert!(ks.windows(2).all(|w| w[0] >= w[1]) && 1900 < ks[1] && ks[1] < 6500);
    }

    #[test]
    fn night_light_follows_sunset_in_winter_vs_summer() {
        let n = NightLight { enabled: true, strength: 100, schedule: true, sun: true, transition_min: 0, ..night_cfg() };
        let tehran = city_by_key("tehran");
        let ctx = |day| DisplayContext { city: Some(tehran), today: Some(day), utc_offset: Some(3.5) };
        let evening = t(18, 30);
        let winter = compute_display_state(&n, &Dimmer::default(), evening, &ctx(d(2024, 12, 21)));
        let summer = compute_display_state(&n, &Dimmer::default(), evening, &ctx(d(2024, 6, 21)));
        assert_eq!((winter.kelvin, summer.kelvin), (1900, 6500));
    }

    #[test]
    fn dimmer_blends_day_and_night_brightness_across_the_transition() {
        let dim = Dimmer { enabled: true, schedule: true, day: 100, night: 60, ..Dimmer::default() };
        let n = NightLight { transition_min: 30, ..night_cfg() };
        let vals: Vec<f64> = [0, 15, 30].iter().map(|m| compute_display_state(&n, &dim, t(20, *m), &plain()).brightness).collect();
        assert!(vals[0] == 1.0 && (vals[2] - 0.6).abs() < 1e-9 && 0.6 < vals[1] && vals[1] < 1.0);
        assert_eq!(compute_display_state(&n, &dim, t(12, 0), &plain()).brightness, 1.0);
    }

    #[test]
    fn dimmer_sun_mode() {
        let dim = Dimmer { enabled: true, schedule: true, sun: true, day: 100, night: 70, ..Dimmer::default() };
        let n = NightLight { transition_min: 0, ..night_cfg() };
        let ctx = DisplayContext { city: Some(city_by_key("tehran")), today: Some(d(2024, 12, 21)), utc_offset: Some(3.5) };
        let s = compute_display_state(&n, &dim, t(18, 30), &ctx);
        assert!((s.brightness - 0.7).abs() < 1e-9);
    }
}
