//! Typed, JSON-backed application settings.
//!
//! The on-disk format is identical to the Python app (`%APPDATA%\EyeCare\settings.json`), so
//! both versions can share one settings file while the rewrite is being evaluated. Loading is
//! deliberately forgiving: unknown keys are ignored and a value of the wrong type only resets
//! that one field to its default.

use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::path::{Path, PathBuf};

pub fn config_dir() -> PathBuf {
    let base = std::env::var_os("APPDATA")
        .map(PathBuf::from)
        .or_else(|| std::env::var_os("HOME").or_else(|| std::env::var_os("USERPROFILE")).map(|h| PathBuf::from(h).join(".config")))
        .unwrap_or_else(|| PathBuf::from("."));
    let path = base.join("EyeCare");
    let _ = std::fs::create_dir_all(&path);
    path
}

pub fn settings_path() -> PathBuf {
    config_dir().join("settings.json")
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct General {
    pub theme: String, // dark | light | system
    pub language: String, // en | fa
    pub autostart: bool,
    pub start_minimized: bool,
    pub animations: bool,
    pub auto_update: bool,
    pub last_update_check: f64,
    pub daily_break_goal: i64,
    pub last_seen_version: String,
}
impl Default for General {
    fn default() -> Self {
        Self {
            theme: "dark".into(),
            language: "en".into(),
            autostart: true,
            start_minimized: true,
            animations: true,
            auto_update: true,
            last_update_check: 0.0,
            daily_break_goal: 6,
            last_seen_version: String::new(),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Rule202020 {
    pub enabled: bool,
    pub interval_min: i64,
    pub break_seconds: i64,
    pub snooze_min: i64,
    pub detect_natural_breaks: bool,
    pub use_break_lock: bool,
}
impl Default for Rule202020 {
    fn default() -> Self {
        Self {
            enabled: true,
            interval_min: 20,
            break_seconds: 20,
            snooze_min: 5,
            detect_natural_breaks: true,
            use_break_lock: false,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Blink {
    pub enabled: bool,
    pub interval_min: i64,
}
impl Default for Blink {
    fn default() -> Self {
        Self { enabled: true, interval_min: 5 }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Hydration {
    pub enabled: bool,
    pub interval_min: i64,
}
impl Default for Hydration {
    fn default() -> Self {
        Self { enabled: true, interval_min: 45 }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Posture {
    pub enabled: bool,
    pub interval_min: i64,
}
impl Default for Posture {
    fn default() -> Self {
        Self { enabled: true, interval_min: 45 }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct NightLight {
    pub enabled: bool,
    /// 0..100 warmth.
    pub strength: i64,
    pub schedule: bool,
    pub start: String,
    pub end: String,
    /// Follow sunset/sunrise of the chosen city instead of fixed times.
    pub sun: bool,
    /// Gradual fade in/out at the edges of the schedule.
    pub transition_min: i64,
}
impl Default for NightLight {
    fn default() -> Self {
        Self {
            enabled: false,
            strength: 40,
            schedule: true,
            start: "20:00".into(),
            end: "06:30".into(),
            sun: false,
            transition_min: 30,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Dimmer {
    pub enabled: bool,
    pub profile: String, // day | night | study
    pub day: i64,
    pub night: i64,
    pub study: i64,
    pub schedule: bool,
    pub night_start: String,
    pub night_end: String,
    pub sun: bool,
}
impl Default for Dimmer {
    fn default() -> Self {
        Self {
            enabled: false,
            profile: "day".into(),
            day: 100,
            night: 70,
            study: 85,
            schedule: true,
            night_start: "20:00".into(),
            night_end: "06:30".into(),
            sun: false,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct AutoDarkMode {
    pub enabled: bool,
    pub light_from: String,
    pub dark_from: String,
}
impl Default for AutoDarkMode {
    fn default() -> Self {
        Self { enabled: false, light_from: "07:00".into(), dark_from: "19:00".into() }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct BreakLock {
    pub skippable: bool,
    pub skip_after_seconds: i64,
    pub show_exercise: bool,
}
impl Default for BreakLock {
    fn default() -> Self {
        Self { skippable: true, skip_after_seconds: 3, show_exercise: true }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SmartPause {
    pub enabled: bool,
    /// Full-screen apps, games, presentations.
    pub fullscreen: bool,
    /// Zoom / Teams / Meet / Webex ...
    pub meetings: bool,
    /// Respect Windows Focus assist (quiet hours).
    pub focus_assist: bool,
}
impl Default for SmartPause {
    fn default() -> Self {
        Self { enabled: true, fullscreen: true, meetings: true, focus_assist: true }
    }
}

#[derive(Debug, Clone, PartialEq, Default, Serialize, Deserialize)]
pub struct Monitors {
    /// Comma-separated monitor keys the filters should NOT touch.
    pub excluded: String,
    /// `DISPLAY1=80;DISPLAY2=100` per-monitor brightness multiplier (%).
    pub brightness: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Hotkeys {
    pub enabled: bool,
    pub night_light: String,
    pub break_now: String,
    pub pause: String,
    pub quiet: String,
}
impl Default for Hotkeys {
    fn default() -> Self {
        Self {
            enabled: true,
            night_light: "Ctrl+Alt+N".into(),
            break_now: "Ctrl+Alt+B".into(),
            pause: "Ctrl+Alt+P".into(),
            quiet: "Ctrl+Alt+Q".into(),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Sound {
    /// Start/end chimes around breaks.
    pub enabled: bool,
    pub volume: i64,
    /// Also a soft ping for reminders and prompts.
    pub reminder_sounds: bool,
}
impl Default for Sound {
    fn default() -> Self {
        Self { enabled: true, volume: 50, reminder_sounds: false }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Location {
    pub city: String,
}
impl Default for Location {
    fn default() -> Self {
        Self { city: "tehran".into() }
    }
}

#[derive(Debug, Clone, PartialEq, Default, Serialize, Deserialize)]
pub struct Settings {
    pub general: General,
    pub rule202020: Rule202020,
    pub blink: Blink,
    pub hydration: Hydration,
    pub posture: Posture,
    pub night_light: NightLight,
    pub dimmer: Dimmer,
    pub auto_dark: AutoDarkMode,
    pub break_lock: BreakLock,
    pub smart_pause: SmartPause,
    pub location: Location,
    pub monitors: Monitors,
    pub hotkeys: Hotkeys,
    pub sound: Sound,
}

/// Copy values from `input` into `target` only where the key exists in `target` and the JSON
/// type matches (an integer is accepted for a float field; a bool is never an int).
fn overlay(target: &mut Value, input: &Value) {
    match (target, input) {
        (Value::Object(t), Value::Object(i)) => {
            for (key, slot) in t.iter_mut() {
                if let Some(v) = i.get(key) {
                    overlay(slot, v);
                }
            }
        }
        (slot @ Value::String(_), Value::String(_)) | (slot @ Value::Bool(_), Value::Bool(_)) => {
            *slot = input.clone();
        }
        (slot @ Value::Number(_), Value::Number(n)) => {
            let want_float = slot.as_f64().is_some() && !(slot.is_i64() || slot.is_u64());
            if want_float {
                if let Some(f) = n.as_f64() {
                    *slot = Value::from(f);
                }
            } else if n.is_i64() || n.is_u64() {
                *slot = input.clone();
            }
        }
        _ => {}
    }
}

pub fn settings_from_value(data: &Value) -> Settings {
    let mut base = serde_json::to_value(Settings::default()).expect("defaults serialize");
    overlay(&mut base, data);
    serde_json::from_value(base).unwrap_or_default()
}

pub fn load_settings_from(path: &Path) -> Settings {
    std::fs::read_to_string(path)
        .ok()
        .and_then(|text| serde_json::from_str::<Value>(&text).ok())
        .map(|v| settings_from_value(&v))
        .unwrap_or_default()
}

pub fn load_settings() -> Settings {
    load_settings_from(&settings_path())
}

pub fn save_settings_to(settings: &Settings, path: &Path) -> std::io::Result<()> {
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    let payload = serde_json::to_string_pretty(settings).map_err(std::io::Error::other)?;
    // Write next to the target, then rename: a crash never leaves a half-written file.
    let tmp = path.with_extension("json.tmp");
    std::fs::write(&tmp, payload)?;
    let result = std::fs::rename(&tmp, path);
    if result.is_err() {
        let _ = std::fs::remove_file(&tmp);
    }
    result
}

pub fn save_settings(settings: &Settings) -> std::io::Result<()> {
    save_settings_to(settings, &settings_path())
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn defaults() {
        let s = Settings::default();
        assert_eq!(s.rule202020.interval_min, 20);
        assert_eq!(s.rule202020.break_seconds, 20);
        assert_eq!(s.general.theme, "dark");
    }

    #[test]
    fn roundtrip() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("s.json");
        let mut s = Settings::default();
        s.night_light.strength = 77;
        s.general.language = "fa".into();
        save_settings_to(&s, &path).unwrap();
        let loaded = load_settings_from(&path);
        assert_eq!(loaded.night_light.strength, 77);
        assert_eq!(loaded.general.language, "fa");
        assert!(!dir.path().join("s.json.tmp").exists());
    }

    #[test]
    fn missing_file_gives_defaults() {
        let dir = tempfile::tempdir().unwrap();
        assert_eq!(load_settings_from(&dir.path().join("nope.json")), Settings::default());
    }

    #[test]
    fn corrupt_file_gives_defaults() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("bad.json");
        std::fs::write(&path, "{not json").unwrap();
        assert_eq!(load_settings_from(&path), Settings::default());
    }

    #[test]
    fn wrong_types_and_unknown_keys_are_ignored() {
        let s = settings_from_value(&json!({"blink": {"interval_min": "soon", "enabled": false, "bogus": 1}, "zzz": {}}));
        assert_eq!(s.blink.interval_min, 5);
        assert!(!s.blink.enabled);
    }

    #[test]
    fn bool_is_not_accepted_as_int() {
        let s = settings_from_value(&json!({"blink": {"interval_min": true}}));
        assert_eq!(s.blink.interval_min, 5);
    }

    #[test]
    fn float_is_not_accepted_as_int() {
        let s = settings_from_value(&json!({"blink": {"interval_min": 7.5}}));
        assert_eq!(s.blink.interval_min, 5);
    }

    #[test]
    fn partial_file_keeps_other_defaults() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("p.json");
        std::fs::write(&path, json!({"hydration": {"interval_min": 30}}).to_string()).unwrap();
        let s = load_settings_from(&path);
        assert_eq!(s.hydration.interval_min, 30);
        assert_eq!(s.rule202020.interval_min, 20);
    }

    #[test]
    fn update_settings_defaults_and_int_to_float() {
        let s = Settings::default();
        assert!(s.general.auto_update);
        assert_eq!(s.general.last_update_check, 0.0);
        let s2 = settings_from_value(&json!({"general": {"last_update_check": 1700000000, "auto_update": false}}));
        assert_eq!(s2.general.last_update_check, 1_700_000_000.0);
        assert!(!s2.general.auto_update);
        assert_eq!(settings_from_value(&json!({"general": {"last_update_check": true}})).general.last_update_check, 0.0);
    }

    #[test]
    fn reads_a_file_written_by_the_python_app() {
        // Shape produced by `json.dumps(asdict(Settings()), indent=2, ensure_ascii=False)`.
        let python_json = r#"{
          "general": {"theme": "light", "language": "fa", "autostart": false, "start_minimized": true,
                      "animations": true, "auto_update": true, "last_update_check": 1700000000.5,
                      "daily_break_goal": 8, "last_seen_version": "0.3.0"},
          "night_light": {"enabled": true, "strength": 55, "schedule": true, "start": "21:00",
                          "end": "06:00", "sun": true, "transition_min": 20},
          "location": {"city": "isfahan"}
        }"#;
        let s = settings_from_value(&serde_json::from_str(python_json).unwrap());
        assert_eq!(s.general.theme, "light");
        assert_eq!(s.general.daily_break_goal, 8);
        assert_eq!(s.general.last_update_check, 1_700_000_000.5);
        assert!(s.night_light.enabled && s.night_light.sun);
        assert_eq!(s.location.city, "isfahan");
    }
}
