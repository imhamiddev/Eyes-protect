//! Typed settings changes: every control in the UI sends one of these.

use crate::common::cities::CITIES;
use crate::common::hotkeys;
use crate::common::monitors as mon;
use crate::common::timeutil::parse_hhmm;
use crate::engine::Engine;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum BoolKey {
    Autostart,
    Animations,
    AutoUpdate,
    RuleEnabled,
    Natural,
    Lock,
    Skippable,
    SmartOn,
    SmartFull,
    SmartMeet,
    SmartFocus,
    BlinkOn,
    PostureOn,
    WaterOn,
    NlOn,
    NlSchedule,
    NlSun,
    DimOn,
    DimSchedule,
    DimSun,
    AdOn,
    HkEnabled,
    SoundOn,
    ReminderSounds,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum IntKey {
    DailyGoal,
    Interval,
    BreakLen,
    Snooze,
    BlinkInt,
    PostureInt,
    WaterInt,
    Warmth,
    Transition,
    BDay,
    BNight,
    BStudy,
    Volume,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum StrKey {
    Theme,
    Language,
    City,
    Profile,
    NlStart,
    NlEnd,
    DStart,
    DEnd,
    AdLight,
    AdDark,
    /// A global shortcut, by index into [`hotkeys::ACTIONS`].
    Hotkey(usize),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Setting {
    Bool(BoolKey, bool),
    Int(IntKey, i64),
    Str(StrKey, String),
    /// Per-monitor on/off (key, enabled).
    MonitorOn(String, bool),
    /// Per-monitor brightness multiplier in % (key, value).
    MonitorBrightness(String, i64),
}

/// Why a change was not applied (shown next to the control).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Rejected {
    BadTime,
    BadShortcut(String),
    Unknown,
}

fn clamp(v: i64, lo: i64, hi: i64) -> i64 {
    v.clamp(lo, hi)
}

/// Apply `change` to the engine's settings and re-apply everything that depends on them.
pub fn apply(engine: &mut Engine, change: &Setting) -> Result<(), Rejected> {
    let s = &mut engine.settings;
    match change {
        Setting::Bool(key, v) => {
            let v = *v;
            match key {
                BoolKey::Autostart => s.general.autostart = v,
                BoolKey::Animations => s.general.animations = v,
                BoolKey::AutoUpdate => s.general.auto_update = v,
                BoolKey::RuleEnabled => s.rule202020.enabled = v,
                BoolKey::Natural => s.rule202020.detect_natural_breaks = v,
                BoolKey::Lock => s.rule202020.use_break_lock = v,
                BoolKey::Skippable => s.break_lock.skippable = v,
                BoolKey::SmartOn => s.smart_pause.enabled = v,
                BoolKey::SmartFull => s.smart_pause.fullscreen = v,
                BoolKey::SmartMeet => s.smart_pause.meetings = v,
                BoolKey::SmartFocus => s.smart_pause.focus_assist = v,
                BoolKey::BlinkOn => s.blink.enabled = v,
                BoolKey::PostureOn => s.posture.enabled = v,
                BoolKey::WaterOn => s.hydration.enabled = v,
                BoolKey::NlOn => s.night_light.enabled = v,
                BoolKey::NlSchedule => s.night_light.schedule = v,
                BoolKey::NlSun => s.night_light.sun = v,
                BoolKey::DimOn => s.dimmer.enabled = v,
                BoolKey::DimSchedule => s.dimmer.schedule = v,
                BoolKey::DimSun => s.dimmer.sun = v,
                BoolKey::AdOn => s.auto_dark.enabled = v,
                BoolKey::HkEnabled => s.hotkeys.enabled = v,
                BoolKey::SoundOn => s.sound.enabled = v,
                BoolKey::ReminderSounds => s.sound.reminder_sounds = v,
            }
        }
        Setting::Int(key, v) => {
            let v = *v;
            match key {
                IntKey::DailyGoal => s.general.daily_break_goal = clamp(v, 1, 50),
                IntKey::Interval => s.rule202020.interval_min = clamp(v, 1, 120),
                IntKey::BreakLen => s.rule202020.break_seconds = clamp(v, 5, 300),
                IntKey::Snooze => s.rule202020.snooze_min = clamp(v, 1, 30),
                IntKey::BlinkInt => s.blink.interval_min = clamp(v, 1, 60),
                IntKey::PostureInt => s.posture.interval_min = clamp(v, 10, 180),
                IntKey::WaterInt => s.hydration.interval_min = clamp(v, 5, 240),
                IntKey::Warmth => s.night_light.strength = clamp(v, 0, 100),
                IntKey::Transition => s.night_light.transition_min = clamp(v, 0, 60),
                IntKey::BDay => s.dimmer.day = clamp(v, 30, 100),
                IntKey::BNight => s.dimmer.night = clamp(v, 30, 100),
                IntKey::BStudy => s.dimmer.study = clamp(v, 30, 100),
                IntKey::Volume => s.sound.volume = clamp(v, 0, 100),
            }
        }
        Setting::Str(key, v) => match key {
            StrKey::Theme => s.general.theme = if ["dark", "light", "system"].contains(&v.as_str()) { v.clone() } else { "dark".into() },
            StrKey::Language => s.general.language = if v == "fa" { "fa".into() } else { "en".into() },
            StrKey::City => {
                if !CITIES.iter().any(|c| c.key == v) {
                    return Err(Rejected::Unknown);
                }
                s.location.city = v.clone();
            }
            StrKey::Profile => {
                if !["day", "night", "study"].contains(&v.as_str()) {
                    return Err(Rejected::Unknown);
                }
                s.dimmer.profile = v.clone();
            }
            StrKey::NlStart | StrKey::NlEnd | StrKey::DStart | StrKey::DEnd | StrKey::AdLight | StrKey::AdDark => {
                let t = parse_hhmm(v).map_err(|_| Rejected::BadTime)?;
                let text = crate::common::timeutil::format_hhmm(t);
                match key {
                    StrKey::NlStart => s.night_light.start = text,
                    StrKey::NlEnd => s.night_light.end = text,
                    StrKey::DStart => s.dimmer.night_start = text,
                    StrKey::DEnd => s.dimmer.night_end = text,
                    StrKey::AdLight => s.auto_dark.light_from = text,
                    _ => s.auto_dark.dark_from = text,
                }
            }
            StrKey::Hotkey(index) => {
                let action = hotkeys::ACTIONS.get(*index).ok_or(Rejected::Unknown)?;
                let normalized = hotkeys::normalize(v).map_err(|e| Rejected::BadShortcut(e.to_string()))?;
                // Two actions must not share one shortcut.
                let others = [
                    ("night_light", &s.hotkeys.night_light),
                    ("break_now", &s.hotkeys.break_now),
                    ("pause", &s.hotkeys.pause),
                    ("quiet", &s.hotkeys.quiet),
                ];
                if others.iter().any(|(a, combo)| a != action && combo.eq_ignore_ascii_case(&normalized)) {
                    return Err(Rejected::BadShortcut("already used by another action".into()));
                }
                match *action {
                    "night_light" => s.hotkeys.night_light = normalized,
                    "break_now" => s.hotkeys.break_now = normalized,
                    "pause" => s.hotkeys.pause = normalized,
                    _ => s.hotkeys.quiet = normalized,
                }
            }
        },
        Setting::MonitorOn(key, on) => {
            let mut excluded = mon::parse_set(&s.monitors.excluded);
            if *on { excluded.remove(key) } else { excluded.insert(key.clone()) };
            s.monitors.excluded = mon::format_set(excluded);
        }
        Setting::MonitorBrightness(key, v) => {
            let mut factors = mon::parse_map(&s.monitors.brightness);
            if *v < 100 { factors.insert(key.clone(), clamp(*v, 30, 100) as i32) } else { factors.remove(key) };
            s.monitors.brightness = mon::format_map(&factors);
        }
    }
    engine.commit_settings();
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::common::config::Settings;
    use crate::common::stats::Stats;
    use crate::platform::NullPlatform;
    use std::sync::Arc;

    fn engine() -> (tempfile::TempDir, Engine) {
        let dir = tempfile::tempdir().unwrap();
        let e = Engine::new(Settings::default(), Stats::open(dir.path().join("st.json")), Some(dir.path().join("s.json")), Arc::new(NullPlatform));
        (dir, e)
    }

    #[test]
    fn toggles_and_numbers_are_applied_and_clamped() {
        let (_d, mut e) = engine();
        apply(&mut e, &Setting::Bool(BoolKey::NlOn, true)).unwrap();
        assert!(e.settings.night_light.enabled);
        apply(&mut e, &Setting::Int(IntKey::Interval, 500)).unwrap();
        assert_eq!(e.settings.rule202020.interval_min, 120);
        apply(&mut e, &Setting::Int(IntKey::BDay, 5)).unwrap();
        assert_eq!(e.settings.dimmer.day, 30);
        apply(&mut e, &Setting::Int(IntKey::Interval, 25)).unwrap();
        assert_eq!(e.rule.seconds_to_break(), 25 * 60, "the engine is reloaded");
    }

    #[test]
    fn times_are_validated_and_normalised() {
        let (_d, mut e) = engine();
        apply(&mut e, &Setting::Str(StrKey::NlStart, " 7:05 ".into())).unwrap();
        assert_eq!(e.settings.night_light.start, "07:05");
        assert_eq!(apply(&mut e, &Setting::Str(StrKey::NlEnd, "25:00".into())), Err(Rejected::BadTime));
        assert_eq!(e.settings.night_light.end, "06:30");
    }

    #[test]
    fn cities_and_profiles_must_exist() {
        let (_d, mut e) = engine();
        apply(&mut e, &Setting::Str(StrKey::City, "paris".into())).unwrap();
        assert_eq!(e.settings.location.city, "paris");
        assert_eq!(apply(&mut e, &Setting::Str(StrKey::City, "atlantis".into())), Err(Rejected::Unknown));
        assert_eq!(apply(&mut e, &Setting::Str(StrKey::Profile, "disco".into())), Err(Rejected::Unknown));
        apply(&mut e, &Setting::Str(StrKey::Profile, "study".into())).unwrap();
        assert_eq!(e.settings.dimmer.profile, "study");
    }

    #[test]
    fn theme_and_language_fall_back_to_safe_values() {
        let (_d, mut e) = engine();
        apply(&mut e, &Setting::Str(StrKey::Theme, "neon".into())).unwrap();
        assert_eq!(e.settings.general.theme, "dark");
        apply(&mut e, &Setting::Str(StrKey::Language, "fa".into())).unwrap();
        assert_eq!(e.settings.general.language, "fa");
        apply(&mut e, &Setting::Str(StrKey::Language, "xx".into())).unwrap();
        assert_eq!(e.settings.general.language, "en");
    }

    #[test]
    fn hotkeys_are_normalised_and_conflicts_rejected() {
        let (_d, mut e) = engine();
        apply(&mut e, &Setting::Str(StrKey::Hotkey(0), "shift + ctrl + n".into())).unwrap();
        assert_eq!(e.settings.hotkeys.night_light, "Ctrl+Shift+N");
        assert!(matches!(apply(&mut e, &Setting::Str(StrKey::Hotkey(1), "N".into())), Err(Rejected::BadShortcut(_))));
        // Ctrl+Alt+P belongs to "pause"
        assert!(matches!(apply(&mut e, &Setting::Str(StrKey::Hotkey(1), "ctrl+alt+p".into())), Err(Rejected::BadShortcut(_))));
        assert_eq!(e.settings.hotkeys.break_now, "Ctrl+Alt+B");
        assert_eq!(apply(&mut e, &Setting::Str(StrKey::Hotkey(9), "Ctrl+Alt+X".into())), Err(Rejected::Unknown));
    }

    #[test]
    fn per_monitor_settings_roundtrip() {
        let (_d, mut e) = engine();
        apply(&mut e, &Setting::MonitorOn("DISPLAY2".into(), false)).unwrap();
        apply(&mut e, &Setting::MonitorBrightness("DISPLAY1".into(), 60)).unwrap();
        assert_eq!(e.settings.monitors.excluded, "DISPLAY2");
        assert_eq!(e.settings.monitors.brightness, "DISPLAY1=60");
        apply(&mut e, &Setting::MonitorOn("DISPLAY2".into(), true)).unwrap();
        apply(&mut e, &Setting::MonitorBrightness("DISPLAY1".into(), 100)).unwrap();
        assert_eq!((e.settings.monitors.excluded.as_str(), e.settings.monitors.brightness.as_str()), ("", ""));
    }

    #[test]
    fn changes_are_persisted() {
        let (d, mut e) = engine();
        apply(&mut e, &Setting::Int(IntKey::DailyGoal, 9)).unwrap();
        let on_disk = crate::common::config::load_settings_from(&d.path().join("s.json"));
        assert_eq!(on_disk.general.daily_break_goal, 9);
    }
}
