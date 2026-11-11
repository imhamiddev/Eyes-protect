//! The controller: owns settings, reminders and every side effect.
//!
//! It is UI-agnostic. A frontend calls [`Engine::on_tick`] once per second, advances the display
//! fade with [`Engine::advance_tween`] while [`Engine::is_animating`], and reacts to the
//! [`EngineEvent`]s returned by [`Engine::drain_events`].

use std::collections::BTreeSet;
use std::path::PathBuf;
use std::sync::Arc;
use std::time::{SystemTime, UNIX_EPOCH};

use chrono::NaiveTime;

use crate::common::cities::city_by_key;
use crate::common::colortemp::{build_ramp, channel_multipliers, identity_ramp};
use crate::common::config::{save_settings_to, settings_path, load_settings_from, Settings};
use crate::common::monitors as mon;
use crate::common::sounds::SoundPlayer;
use crate::common::stats::Stats;
use crate::common::timeutil::{now_precise, now_time};
use crate::features::display::{compute_display_state, wants_light_theme, DisplayContext, DisplayState};
use crate::features::interval::IntervalReminder;
use crate::features::rule202020::{Event as RuleEvent, Phase, Rule202020};
use crate::features::smartpause::{classify, Debouncer, Reason};
use crate::platform::{Monitor, Platform};

pub const DISPLAY_REAPPLY_SECONDS: i64 = 60;
pub const TWEEN_MS: f64 = 700.0;

/// Things the UI may want to react to.
#[derive(Debug, Clone, PartialEq)]
pub enum EngineEvent {
    /// Show the 20-20-20 toast.
    PromptRequested,
    /// Show the break screen / mini window (seconds).
    BreakStarted(i64),
    /// Seconds left of the running break.
    BreakTick(i64),
    /// `true` = completed, `false` = skipped.
    BreakFinished(bool),
    BlinkRequested,
    PostureRequested,
    WaterRequested,
    NaturalBreak,
    /// Anything the UI may want to redraw.
    StateChanged,
    SettingsChanged,
    DisplayChanged(DisplayState),
}

#[derive(Debug, Clone, Copy)]
struct Tween {
    from: DisplayState,
    to: DisplayState,
    elapsed_ms: f64,
}

fn ease_in_out_cubic(t: f64) -> f64 {
    if t < 0.5 { 4.0 * t * t * t } else { 1.0 - (-2.0 * t + 2.0).powi(3) / 2.0 }
}

/// Command line stored in the Windows Run key.
pub fn launch_command() -> String {
    let exe = std::env::current_exe().map(|p| p.display().to_string()).unwrap_or_else(|_| "eyecare".into());
    format!("\"{exe}\" --background")
}

pub struct Engine {
    pub settings: Settings,
    pub stats: Stats,
    pub sounds: SoundPlayer,
    pub paused: bool,
    /// Actions whose shortcut could not be registered.
    pub hotkey_failures: BTreeSet<String>,
    /// Epoch seconds; infinity = until switched off.
    pub quiet_until: f64,
    /// Set by smart pause (e.g. fullscreen).
    pub busy_reason: Option<Reason>,
    pub rule: Rule202020,
    pub blink: IntervalReminder,
    pub water: IntervalReminder,
    pub posture: IntervalReminder,
    pub display_state: DisplayState,
    pub monitors: Vec<Monitor>,
    settings_path: Option<PathBuf>,
    platform: Arc<dyn Platform>,
    shown: Option<DisplayState>,
    tween: Option<Tween>,
    since_apply: i64,
    last_theme_target: Option<bool>,
    smart: Debouncer,
    poll_count: u64,
    run_seconds: i64,
    events: Vec<EngineEvent>,
    clock: Box<dyn Fn() -> f64 + Send>,
    time_of_day: Box<dyn Fn() -> NaiveTime + Send>,
}

impl Engine {
    /// Load settings and stats from the config folder.
    pub fn load(platform: Arc<dyn Platform>) -> Self {
        Self::new(load_settings_from(&settings_path()), Stats::new(), None, platform)
    }

    /// `settings_path = None` means the default location.
    pub fn new(settings: Settings, stats: Stats, settings_path: Option<PathBuf>, platform: Arc<dyn Platform>) -> Self {
        let s = &settings;
        let sounds = match &settings_path {
            Some(p) => SoundPlayer::with_cache_dir(p.parent().map(|d| d.join("sounds")).unwrap_or_default()),
            None => SoundPlayer::new(),
        };
        let monitors = platform.list_monitors();
        Self {
            rule: Rule202020::new(&s.rule202020),
            blink: IntervalReminder::new(s.blink.interval_min, s.blink.enabled),
            water: IntervalReminder::new(s.hydration.interval_min, s.hydration.enabled),
            posture: IntervalReminder::new(s.posture.interval_min, s.posture.enabled),
            settings,
            stats,
            sounds,
            paused: false,
            hotkey_failures: BTreeSet::new(),
            quiet_until: 0.0,
            busy_reason: None,
            display_state: DisplayState::default(),
            monitors,
            settings_path,
            platform,
            shown: None,
            tween: None,
            since_apply: DISPLAY_REAPPLY_SECONDS,
            last_theme_target: None,
            smart: Debouncer::new(2),
            poll_count: 0,
            run_seconds: 0,
            events: Vec::new(),
            clock: Box::new(|| SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_secs_f64()).unwrap_or(0.0)),
            time_of_day: Box::new(now_precise),
        }
    }

    /// Replace the wall clock (tests).
    pub fn set_clock(&mut self, clock: impl Fn() -> f64 + Send + 'static) {
        self.clock = Box::new(clock);
    }

    /// Replace the time-of-day source (tests).
    pub fn set_time_of_day(&mut self, f: impl Fn() -> NaiveTime + Send + 'static) {
        self.time_of_day = Box::new(f);
    }

    pub fn platform(&self) -> &Arc<dyn Platform> {
        &self.platform
    }

    pub fn drain_events(&mut self) -> Vec<EngineEvent> {
        std::mem::take(&mut self.events)
    }

    fn emit(&mut self, e: EngineEvent) {
        self.events.push(e);
    }

    fn save_settings_now(&self) {
        let path = self.settings_path.clone().unwrap_or_else(settings_path);
        let _ = save_settings_to(&self.settings, &path);
    }

    // -- lifecycle --------------------------------------------------------
    pub fn start(&mut self) {
        self.apply_display(true);
        self.sync_autostart();
    }

    pub fn shutdown(&mut self) {
        self.reset_gamma();
        self.save_settings_now();
        self.stats.save();
    }

    fn reset_gamma(&self) {
        let identity = identity_ramp();
        self.platform.set_gamma_ramp(&identity);
        for m in self.platform.list_monitors() {
            self.platform.set_monitor_gamma_ramp(&m.device, &identity);
        }
    }

    // -- settings ---------------------------------------------------------
    /// Persist settings without re-applying or notifying the UI.
    pub fn save_quietly(&self) {
        self.save_settings_now();
    }

    /// Call after mutating `self.settings`; persists and re-applies.
    pub fn commit_settings(&mut self) {
        let s = self.settings.clone();
        self.rule.reload(&s.rule202020);
        self.blink.configure(s.blink.interval_min, s.blink.enabled);
        self.water.configure(s.hydration.interval_min, s.hydration.enabled);
        self.posture.configure(s.posture.interval_min, s.posture.enabled);
        self.save_settings_now();
        self.refresh_monitors();
        self.apply_display(true);
        self.sync_autostart();
        self.last_theme_target = None;
        if !s.smart_pause.enabled {
            self.smart.update(None);
            self.set_busy(None);
        }
        self.emit(EngineEvent::SettingsChanged);
        self.emit(EngineEvent::StateChanged);
    }

    pub fn sync_autostart(&self) {
        self.platform.set_autostart(self.settings.general.autostart, &launch_command());
    }

    // -- display ----------------------------------------------------------
    fn target_state(&self) -> DisplayState {
        let city = city_by_key(&self.settings.location.city);
        let ctx = DisplayContext { city: Some(city), ..Default::default() };
        compute_display_state(&self.settings.night_light, &self.settings.dimmer, (self.time_of_day)(), &ctx)
    }

    /// Re-read the attached displays; `true` if the set changed.
    pub fn refresh_monitors(&mut self) -> bool {
        let current = self.platform.list_monitors();
        let changed = current != self.monitors;
        self.monitors = current;
        changed
    }

    fn apply_gamma(&self, state: DisplayState) {
        let excluded = mon::parse_set(&self.settings.monitors.excluded);
        let factors = mon::parse_map(&self.settings.monitors.brightness);
        for m in &self.monitors {
            let key = mon::key(&m.device);
            let f = f64::from(factors.get(&key).copied().unwrap_or(100)) / 100.0;
            let ramp = if excluded.contains(&key) || (state.is_neutral() && f >= 1.0) {
                identity_ramp()
            } else {
                build_ramp(channel_multipliers(f64::from(state.kelvin), state.brightness * f))
            };
            if !self.platform.set_monitor_gamma_ramp(&m.device, &ramp) && m.primary {
                self.platform.set_gamma_ramp(&ramp); // fallback for drivers that reject per-device DCs
            }
        }
    }

    /// Send `state` to the screen now.
    fn push(&mut self, state: DisplayState) {
        let round3 = |b: f64| (b * 1000.0).round() as i64;
        let changed = match self.shown {
            None => true,
            Some(s) => (state.kelvin, round3(state.brightness)) != (s.kelvin, round3(s.brightness)),
        };
        self.apply_gamma(state);
        self.since_apply = 0;
        self.shown = Some(state);
        if changed {
            self.display_state = state;
            self.emit(EngineEvent::DisplayChanged(state));
        }
    }

    pub fn apply_display(&mut self, force: bool) {
        let target = self.target_state();
        self.tween = None; // a running fade is replaced by the new target
        let Some(shown) = self.shown else {
            self.push(target);
            return;
        };
        if target == shown {
            if force || self.since_apply >= DISPLAY_REAPPLY_SECONDS {
                self.push(shown); // some drivers/apps silently reset the ramp
            }
            return;
        }
        let big = (target.kelvin - shown.kelvin).abs() > 150 || (target.brightness - shown.brightness).abs() > 0.08;
        if big && self.settings.general.animations {
            self.tween = Some(Tween { from: shown, to: target, elapsed_ms: 0.0 });
        } else {
            self.push(target);
        }
    }

    pub fn is_animating(&self) -> bool {
        self.tween.is_some()
    }

    /// Advance the display fade; returns `true` while it is still running.
    pub fn advance_tween(&mut self, dt_ms: f64) -> bool {
        let Some(mut tw) = self.tween else { return false };
        tw.elapsed_ms += dt_ms;
        let done = tw.elapsed_ms >= TWEEN_MS;
        let e = ease_in_out_cubic((tw.elapsed_ms / TWEEN_MS).min(1.0));
        let (a, b) = (tw.from, tw.to);
        self.tween = if done { None } else { Some(tw) };
        self.push(DisplayState {
            kelvin: (f64::from(a.kelvin) + f64::from(b.kelvin - a.kelvin) * e).round_ties_even() as i32,
            brightness: a.brightness + (b.brightness - a.brightness) * e,
        });
        if done && self.shown != Some(b) {
            self.push(b);
        }
        !done
    }

    pub fn toggle_night_light(&mut self) -> bool {
        let nl = &mut self.settings.night_light;
        nl.enabled = !nl.enabled;
        if nl.enabled {
            nl.schedule = false; // a quick manual toggle means "on right now"
        }
        let enabled = nl.enabled;
        self.commit_settings();
        enabled
    }

    fn apply_auto_theme(&mut self) {
        let want = wants_light_theme(&self.settings.auto_dark, now_time());
        if let Some(light) = want {
            if Some(light) != self.last_theme_target {
                self.last_theme_target = Some(light);
                if self.platform.system_uses_light_theme() != light {
                    self.platform.set_system_light_theme(light);
                }
            }
        }
    }

    // -- smart pause --------------------------------------------------------
    pub fn poll_smart_pause(&mut self) {
        let cfg = &self.settings.smart_pause;
        let observed = if cfg.enabled {
            classify(cfg, self.platform.notification_state(), self.platform.foreground_info().as_ref(), Some(std::process::id()))
        } else {
            None
        };
        let reason = self.smart.update(observed);
        self.set_busy(reason);
    }

    // -- quiet mode / holding ---------------------------------------------
    pub fn quiet_active(&self) -> bool {
        (self.clock)() < self.quiet_until
    }

    /// `true` while reminders must stay silent (quiet mode or a busy full-screen/meeting app).
    pub fn holding(&self) -> bool {
        self.quiet_active() || self.busy_reason.is_some()
    }

    /// Silence reminders for `minutes` (`None` = until switched off, `<= 0` = end quiet mode).
    pub fn set_quiet(&mut self, minutes: Option<f64>) {
        self.quiet_until = match minutes {
            None => f64::INFINITY,
            Some(m) if m <= 0.0 => 0.0,
            Some(m) => (self.clock)() + m * 60.0,
        };
        self.emit(EngineEvent::StateChanged);
    }

    pub fn toggle_quiet(&mut self, minutes: f64) -> bool {
        if self.quiet_active() {
            self.set_quiet(Some(0.0));
        } else {
            self.set_quiet(Some(minutes));
        }
        self.quiet_active()
    }

    pub fn set_busy(&mut self, reason: Option<Reason>) {
        if reason != self.busy_reason {
            self.busy_reason = reason;
            self.emit(EngineEvent::StateChanged);
        }
    }

    // -- reminders --------------------------------------------------------
    pub fn set_paused(&mut self, paused: bool) {
        self.paused = paused;
        self.rule.set_paused(paused);
        self.emit(EngineEvent::StateChanged);
    }

    /// Call once per second.
    pub fn on_tick(&mut self) {
        let idle = self.platform.idle_seconds();
        self.since_apply += 1;
        self.poll_count += 1;
        if self.poll_count % 2 == 0 {
            self.poll_smart_pause();
        }
        if self.poll_count % 15 == 0 && self.refresh_monitors() {
            self.apply_display(true);
            self.emit(EngineEvent::StateChanged);
        }
        self.apply_display(false);
        self.apply_auto_theme();
        self.track_activity(idle);
        if self.quiet_until != 0.0 && !self.quiet_active() {
            self.quiet_until = 0.0; // quiet period ran out
        }
        let hold = self.holding();
        let events = self.rule.tick(1.0, idle, hold);
        self.handle(events);
        if self.rule.phase == Phase::Break && !self.paused {
            let left = self.rule.break_seconds_left();
            self.emit(EngineEvent::BreakTick(left));
        }
        let silent = self.paused || hold;
        if self.blink.tick(1.0, idle, silent) {
            self.emit(EngineEvent::BlinkRequested);
        }
        if self.water.tick(1.0, idle, silent) {
            self.emit(EngineEvent::WaterRequested);
        }
        if self.posture.tick(1.0, idle, silent) {
            self.emit(EngineEvent::PostureRequested);
        }
        self.emit(EngineEvent::StateChanged);
    }

    /// Screen time and the longest stretch without a break (kept even while quiet).
    fn track_activity(&mut self, idle: f64) {
        if idle >= self.settings.rule202020.break_seconds as f64 {
            self.run_seconds = 0; // away long enough: counts as a rest
        }
        if idle < 60.0 {
            let _ = self.stats.add("active_s", None, 1, false);
        }
        if idle < 5.0 {
            self.run_seconds += 1;
            let _ = self.stats.record_max("longest_run_s", self.run_seconds, None, false);
        }
        if self.poll_count % 30 == 0 {
            self.stats.save();
        }
    }

    fn handle(&mut self, events: Vec<RuleEvent>) {
        for event in events {
            match event {
                RuleEvent::Prompt => self.emit(EngineEvent::PromptRequested),
                RuleEvent::BreakStart => {
                    let secs = self.settings.rule202020.break_seconds;
                    self.emit(EngineEvent::BreakStarted(secs));
                }
                RuleEvent::BreakDone => {
                    self.run_seconds = 0;
                    let _ = self.stats.add("breaks", None, 1, true);
                    self.emit(EngineEvent::BreakFinished(true));
                }
                RuleEvent::BreakSkipped => {
                    self.run_seconds = 0;
                    let _ = self.stats.add("skipped", None, 1, true);
                    self.emit(EngineEvent::BreakFinished(false));
                }
                RuleEvent::NaturalBreak => {
                    self.run_seconds = 0;
                    let _ = self.stats.add("breaks", None, 1, true);
                    self.emit(EngineEvent::NaturalBreak);
                }
                RuleEvent::Snoozed => {}
            }
        }
    }

    // -- user actions -----------------------------------------------------
    pub fn start_break(&mut self) {
        let events = self.rule.start_break();
        self.handle(events);
    }

    pub fn snooze(&mut self) {
        let events = self.rule.snooze();
        self.handle(events);
        self.emit(EngineEvent::StateChanged);
    }

    pub fn skip_break(&mut self) {
        let events = self.rule.skip_break();
        self.handle(events);
    }

    pub fn record_blink_shown(&mut self) {
        let _ = self.stats.add("blinks", None, 1, true);
    }

    /// Play a chime if sounds are on (`reminder` chimes also need the reminder switch).
    pub fn play_sound(&self, kind: &str, reminder: bool, force: bool) -> bool {
        let cfg = &self.settings.sound;
        if !force && (!cfg.enabled || (reminder && !cfg.reminder_sounds)) {
            return false;
        }
        let platform = Arc::clone(&self.platform);
        self.sounds.play(kind, cfg.volume as i32, &move |p| platform.play_sound_file(p))
    }

    pub fn record_stretch(&mut self) {
        let _ = self.stats.add("stretches", None, 1, true);
    }

    pub fn record_water(&mut self) {
        let _ = self.stats.add("water", None, 1, true);
        self.emit(EngineEvent::StateChanged);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::common::colortemp::Ramp;
    use crate::features::smartpause::Foreground;
    use std::collections::HashMap;
    use std::path::Path;
    use std::sync::Mutex;

    /// Records what the engine asks the OS to do.
    struct Mock {
        idle: Mutex<f64>,
        state: Mutex<Option<i32>>,
        monitors: Mutex<Vec<Monitor>>,
        monitor_ramps: Mutex<HashMap<String, Ramp>>,
        primary_ramps: Mutex<Vec<Ramp>>,
        per_device_ok: bool,
    }
    impl Mock {
        fn new() -> Arc<Self> {
            Arc::new(Self {
                idle: Mutex::new(0.0),
                state: Mutex::new(Some(5)),
                monitors: Mutex::new(vec![Monitor { device: "DISPLAY1".into(), x: 0, y: 0, width: 1920, height: 1080, primary: true }]),
                monitor_ramps: Mutex::new(HashMap::new()),
                primary_ramps: Mutex::new(Vec::new()),
                per_device_ok: true,
            })
        }
        fn two() -> Arc<Self> {
            let m = Self::new();
            *m.monitors.lock().unwrap() = vec![
                Monitor { device: "\\\\.\\DISPLAY1".into(), x: 0, y: 0, width: 1920, height: 1080, primary: true },
                Monitor { device: "\\\\.\\DISPLAY2".into(), x: 1920, y: 0, width: 2560, height: 1440, primary: false },
            ];
            m
        }
    }
    impl Platform for Mock {
        fn idle_seconds(&self) -> f64 {
            *self.idle.lock().unwrap()
        }
        fn set_gamma_ramp(&self, ramp: &Ramp) -> bool {
            self.primary_ramps.lock().unwrap().push(*ramp);
            true
        }
        fn set_monitor_gamma_ramp(&self, device: &str, ramp: &Ramp) -> bool {
            self.monitor_ramps.lock().unwrap().insert(device.to_string(), *ramp);
            self.per_device_ok
        }
        fn list_monitors(&self) -> Vec<Monitor> {
            self.monitors.lock().unwrap().clone()
        }
        fn notification_state(&self) -> Option<i32> {
            *self.state.lock().unwrap()
        }
        fn foreground_info(&self) -> Option<Foreground> {
            None
        }
        fn play_sound_file(&self, _p: &Path) -> bool {
            true
        }
        fn set_autostart(&self, _e: bool, _c: &str) -> bool {
            true
        }
        fn system_uses_light_theme(&self) -> bool {
            false
        }
        fn set_system_light_theme(&self, _l: bool) -> bool {
            true
        }
    }

    struct Fixture {
        _dir: tempfile::TempDir,
        engine: Engine,
        mock: Arc<Mock>,
    }

    fn fixture(mock: Arc<Mock>, tweak: impl FnOnce(&mut Settings)) -> Fixture {
        let dir = tempfile::tempdir().unwrap();
        let mut s = Settings::default();
        s.rule202020.interval_min = 1;
        s.rule202020.break_seconds = 3;
        s.blink.enabled = false;
        s.hydration.enabled = false;
        s.posture.enabled = false;
        s.general.animations = false;
        tweak(&mut s);
        let stats = Stats::open(dir.path().join("st.json"));
        let engine = Engine::new(s, stats, Some(dir.path().join("s.json")), mock.clone());
        Fixture { _dir: dir, engine, mock }
    }
    fn make(tweak: impl FnOnce(&mut Settings)) -> Fixture {
        fixture(Mock::new(), tweak)
    }
    fn ticks(e: &mut Engine, n: usize) {
        for _ in 0..n {
            e.on_tick();
        }
    }
    fn kinds(e: &mut Engine) -> Vec<EngineEvent> {
        e.drain_events().into_iter().filter(|ev| !matches!(ev, EngineEvent::StateChanged | EngineEvent::BreakTick(_) | EngineEvent::DisplayChanged(_))).collect()
    }

    #[test]
    fn prompt_then_break_updates_stats() {
        let mut f = make(|_| {});
        let e = &mut f.engine;
        ticks(e, 60);
        e.start_break();
        ticks(e, 3);
        assert_eq!(kinds(e), [EngineEvent::PromptRequested, EngineEvent::BreakStarted(3), EngineEvent::BreakFinished(true)]);
        assert_eq!(e.stats.get("breaks", None), 1);
    }

    #[test]
    fn skip_is_counted() {
        let mut f = make(|s| s.rule202020.use_break_lock = true);
        ticks(&mut f.engine, 60);
        f.engine.skip_break();
        assert_eq!(f.engine.stats.get("skipped", None), 1);
    }

    #[test]
    fn pause_stops_prompts() {
        let mut f = make(|_| {});
        f.engine.set_paused(true);
        ticks(&mut f.engine, 120);
        assert!(!kinds(&mut f.engine).contains(&EngineEvent::PromptRequested));
    }

    #[test]
    fn quick_night_light_toggle() {
        let mut f = make(|_| {});
        assert!(f.engine.toggle_night_light());
        assert!(!f.engine.settings.night_light.schedule);
        assert!(!f.engine.toggle_night_light());
    }

    #[test]
    fn commit_settings_persists() {
        let mut f = make(|_| {});
        f.engine.settings.hydration.interval_min = 33;
        f.engine.commit_settings();
        assert!(f._dir.path().join("s.json").exists());
        assert_eq!(f.engine.water.interval_min, 33);
    }

    #[test]
    fn manual_night_light_toggle_fades_smoothly() {
        let mut f = make(|s| {
            s.general.animations = true;
            s.night_light.strength = 100;
        });
        let e = &mut f.engine;
        e.apply_display(true);
        let before = f.mock.monitor_ramps.lock().unwrap().len();
        let pushes = std::cell::Cell::new(0);
        e.toggle_night_light();
        assert!(e.is_animating(), "eased, not an instant jump");
        while e.advance_tween(50.0) {
            pushes.set(pushes.get() + 1);
        }
        assert!(pushes.get() > 3);
        assert_eq!(e.display_state.kelvin, 1900);
        assert!(!e.is_animating());
        let _ = before;
    }

    #[test]
    fn manual_toggle_is_instant_without_animations() {
        let mut f = make(|s| s.night_light.strength = 100);
        f.engine.apply_display(true);
        f.engine.toggle_night_light();
        assert!(!f.engine.is_animating());
        assert_eq!(f.engine.display_state.kelvin, 1900);
    }

    #[test]
    fn filters_apply_to_every_monitor_by_default() {
        let mut f = fixture(Mock::two(), |s| {
            s.night_light.enabled = true;
            s.night_light.strength = 100;
            s.night_light.schedule = false;
        });
        f.engine.commit_settings();
        let ramps = f.mock.monitor_ramps.lock().unwrap();
        assert_eq!(ramps.len(), 2);
        for ramp in ramps.values() {
            assert!(ramp[2][255] < ramp[0][255], "blue reduced -> warm");
        }
    }

    #[test]
    fn excluded_monitor_stays_neutral_and_brightness_is_per_monitor() {
        let mut f = fixture(Mock::two(), |s| {
            s.night_light.enabled = true;
            s.night_light.strength = 100;
            s.night_light.schedule = false;
            s.monitors.excluded = "DISPLAY2".into();
            s.monitors.brightness = "DISPLAY1=50".into();
        });
        f.engine.commit_settings();
        let ramps = f.mock.monitor_ramps.lock().unwrap();
        assert_eq!(ramps["\\\\.\\DISPLAY2"], identity_ramp());
        assert!(ramps["\\\\.\\DISPLAY1"][0][255] < identity_ramp()[0][255]);
    }

    #[test]
    fn neutral_monitor_factor_dims_even_without_filters() {
        let mut f = fixture(Mock::two(), |s| s.monitors.brightness = "DISPLAY2=60".into());
        f.engine.commit_settings();
        let ramps = f.mock.monitor_ramps.lock().unwrap();
        assert_eq!(ramps["\\\\.\\DISPLAY1"], identity_ramp());
        assert!(ramps["\\\\.\\DISPLAY2"][0][255] < 65535);
    }

    #[test]
    fn primary_falls_back_to_the_device_context_when_per_monitor_fails() {
        let mock = Arc::new(Mock { per_device_ok: false, ..Arc::try_unwrap(Mock::new()).ok().unwrap() });
        let mut f = fixture(mock, |s| {
            s.night_light.enabled = true;
            s.night_light.schedule = false;
        });
        f.engine.commit_settings();
        assert!(!f.mock.primary_ramps.lock().unwrap().is_empty());
    }

    #[test]
    fn monitor_hotplug_is_detected() {
        let mut f = fixture(Mock::two(), |_| {});
        assert_eq!(f.engine.monitors.len(), 2);
        f.mock.monitors.lock().unwrap().truncate(1);
        assert!(f.engine.refresh_monitors());
        assert_eq!(f.engine.monitors.len(), 1);
        assert!(!f.engine.refresh_monitors());
    }

    #[test]
    fn active_time_and_longest_stretch_are_tracked() {
        let mut f = make(|s| s.rule202020.detect_natural_breaks = false);
        ticks(&mut f.engine, 90);
        assert_eq!((f.engine.stats.get("active_s", None), f.engine.stats.get("longest_run_s", None)), (90, 90));
    }

    #[test]
    fn idle_time_is_not_counted_and_resets_the_run() {
        let mut f = make(|s| s.rule202020.detect_natural_breaks = false);
        ticks(&mut f.engine, 40);
        *f.mock.idle.lock().unwrap() = 300.0;
        ticks(&mut f.engine, 30);
        *f.mock.idle.lock().unwrap() = 0.0;
        ticks(&mut f.engine, 10);
        assert_eq!(f.engine.stats.get("active_s", None), 50); // the idle 30 s are excluded
        assert_eq!(f.engine.stats.get("longest_run_s", None), 40); // the run restarted after the rest
    }

    #[test]
    fn taking_a_break_restarts_the_stretch() {
        let mut f = make(|s| s.rule202020.detect_natural_breaks = false);
        ticks(&mut f.engine, 30);
        f.engine.start_break();
        ticks(&mut f.engine, 3);
        assert!(f.engine.run_seconds <= 1);
    }

    // ---- quiet mode and smart pause ---------------------------------------------------------
    fn quiet_fixture() -> Fixture {
        make(|s| {
            s.blink.interval_min = 1;
            s.blink.enabled = true;
        })
    }

    #[test]
    fn quiet_blocks_prompts_and_blinks() {
        let mut f = quiet_fixture();
        f.engine.set_quiet(Some(60.0));
        assert!(f.engine.quiet_active() && f.engine.holding());
        ticks(&mut f.engine, 200);
        assert_eq!(kinds(&mut f.engine), []);
        assert_eq!(f.engine.rule.seconds_to_break(), 60);
    }

    #[test]
    fn ending_quiet_resumes_reminders() {
        let mut f = make(|_| {});
        f.engine.set_quiet(Some(60.0));
        ticks(&mut f.engine, 30);
        f.engine.set_quiet(Some(0.0));
        assert!(!f.engine.quiet_active());
        ticks(&mut f.engine, 60);
        assert_eq!(kinds(&mut f.engine), [EngineEvent::PromptRequested]);
    }

    #[test]
    fn quiet_expires_by_itself() {
        let mut f = make(|_| {});
        f.engine.quiet_until = (f.engine.clock)() - 1.0;
        assert!(!f.engine.quiet_active());
        f.engine.on_tick();
        assert_eq!(f.engine.quiet_until, 0.0);
    }

    #[test]
    fn quiet_runs_out_with_an_injected_clock() {
        let mut f = make(|_| {});
        let now = Arc::new(Mutex::new(1_000.0));
        let shared = Arc::clone(&now);
        f.engine.set_clock(move || *shared.lock().unwrap());
        f.engine.set_quiet(Some(30.0));
        assert!(f.engine.quiet_active());
        *now.lock().unwrap() += 30.0 * 60.0 + 1.0;
        assert!(!f.engine.quiet_active());
    }

    #[test]
    fn quiet_forever_and_toggle() {
        let mut f = make(|_| {});
        f.engine.set_quiet(None);
        assert!(f.engine.quiet_active() && f.engine.quiet_until.is_infinite());
        assert!(!f.engine.toggle_quiet(60.0));
        assert!(f.engine.toggle_quiet(30.0));
    }

    #[test]
    fn busy_reason_holds_like_quiet() {
        let mut f = make(|_| {});
        *f.mock.state.lock().unwrap() = Some(2); // a full-screen app is running
        ticks(&mut f.engine, 120);
        assert_eq!(kinds(&mut f.engine), []);
        assert!(f.engine.holding());
        assert_eq!(f.engine.busy_reason, Some(Reason::Fullscreen));
        *f.mock.state.lock().unwrap() = Some(5); // back to normal
        ticks(&mut f.engine, 60);
        assert_eq!(kinds(&mut f.engine), [EngineEvent::PromptRequested]);
        assert_eq!(f.engine.busy_reason, None);
    }

    #[test]
    fn quiet_does_not_stop_a_manual_break() {
        let mut f = make(|_| {});
        f.engine.set_quiet(Some(60.0));
        f.engine.start_break();
        ticks(&mut f.engine, 3);
        assert!(kinds(&mut f.engine).contains(&EngineEvent::BreakFinished(true)));
    }

    #[test]
    fn disabling_smart_pause_clears_the_busy_state() {
        let mut f = make(|_| {});
        *f.mock.state.lock().unwrap() = Some(2);
        ticks(&mut f.engine, 4);
        assert!(f.engine.busy_reason.is_some());
        f.engine.settings.smart_pause.enabled = false;
        f.engine.commit_settings();
        assert_eq!(f.engine.busy_reason, None);
    }

    #[test]
    fn sounds_respect_switches() {
        let mut f = make(|s| s.sound.reminder_sounds = false);
        f.engine.settings.sound.enabled = false;
        assert!(!f.engine.play_sound("start", false, false));
        assert!(f.engine.play_sound("start", false, true)); // force (the Settings test button)
        f.engine.settings.sound.enabled = true;
        assert!(f.engine.play_sound("start", false, false));
        assert!(!f.engine.play_sound("notify", true, false)); // reminder pings are off
    }
}
