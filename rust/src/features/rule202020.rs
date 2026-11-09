//! 20-20-20 rule state machine (pure logic, no UI).

use crate::common::config::Rule202020 as RuleSettings;
use crate::common::countdown::Countdown;

pub const PROMPT_TIMEOUT_SECONDS: f64 = 30.0;

/// Events returned from `tick()` and the actions.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Event {
    Prompt,
    BreakStart,
    BreakDone,
    BreakSkipped,
    NaturalBreak,
    Snoozed,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Phase {
    Working,
    Prompt,
    Break,
}

#[derive(Debug, Clone)]
pub struct Rule202020 {
    cfg: RuleSettings,
    pub phase: Phase,
    pub paused: bool,
    work: Countdown,
    rest: Countdown,
    prompt_left: f64,
    idle_credited: bool,
}

impl Rule202020 {
    pub fn new(cfg: &RuleSettings) -> Self {
        let mut work = Countdown::new(cfg.interval_min * 60);
        work.start();
        Self {
            cfg: cfg.clone(),
            phase: Phase::Working,
            paused: false,
            work,
            rest: Countdown::new(cfg.break_seconds),
            prompt_left: 0.0,
            idle_credited: false,
        }
    }

    // -- configuration ----------------------------------------------------
    pub fn reload(&mut self, cfg: &RuleSettings) {
        let old = std::mem::replace(&mut self.cfg, cfg.clone());
        if old.enabled && !cfg.enabled && self.phase != Phase::Working {
            self.phase = Phase::Working; // switching the rule off cancels any pending prompt/break
            self.rest.stop();
        }
        if cfg.interval_min != old.interval_min || (cfg.enabled && !old.enabled) {
            self.work.start_with(cfg.interval_min * 60);
            self.work.running = self.phase == Phase::Working;
        }
        if cfg.break_seconds != old.break_seconds {
            self.rest.duration = cfg.break_seconds.max(1);
        }
    }

    // -- queries ----------------------------------------------------------
    pub fn seconds_to_break(&self) -> i64 {
        self.work.seconds_left()
    }
    pub fn break_seconds_left(&self) -> i64 {
        self.rest.seconds_left()
    }
    pub fn work_progress(&self) -> f64 {
        self.work.progress()
    }
    pub fn settings(&self) -> &RuleSettings {
        &self.cfg
    }

    // -- actions ----------------------------------------------------------
    pub fn set_paused(&mut self, paused: bool) {
        self.paused = paused;
    }

    pub fn start_break(&mut self) -> Vec<Event> {
        self.phase = Phase::Break;
        self.rest.start_with(self.cfg.break_seconds);
        vec![Event::BreakStart]
    }

    pub fn snooze(&mut self) -> Vec<Event> {
        self.phase = Phase::Working;
        self.work.snooze(self.cfg.snooze_min * 60);
        vec![Event::Snoozed]
    }

    pub fn skip_break(&mut self) -> Vec<Event> {
        self.back_to_work();
        vec![Event::BreakSkipped]
    }

    fn back_to_work(&mut self) {
        self.phase = Phase::Working;
        self.rest.stop();
        self.work.start_with(self.cfg.interval_min * 60);
    }

    // -- time -------------------------------------------------------------
    /// Advance time. `hold` (quiet mode, full-screen app...) freezes the work clock and
    /// swallows a pending prompt; a break that is already running continues.
    pub fn tick(&mut self, dt: f64, idle_seconds: f64, hold: bool) -> Vec<Event> {
        if self.paused {
            return vec![];
        }
        match self.phase {
            Phase::Working => {
                if hold || !self.cfg.enabled {
                    return vec![];
                }
                self.tick_working(dt, idle_seconds)
            }
            Phase::Prompt => {
                self.prompt_left -= dt;
                if hold || self.prompt_left <= 0.0 || !self.cfg.enabled {
                    return self.snooze();
                }
                vec![]
            }
            Phase::Break => {
                if self.rest.tick(dt) {
                    self.back_to_work();
                    return vec![Event::BreakDone];
                }
                vec![]
            }
        }
    }

    fn tick_working(&mut self, dt: f64, idle: f64) -> Vec<Event> {
        if self.cfg.detect_natural_breaks && idle >= self.cfg.break_seconds as f64 {
            if !self.idle_credited {
                self.idle_credited = true;
                self.work.start_with(self.cfg.interval_min * 60);
                return vec![Event::NaturalBreak];
            }
            return vec![]; // still away: the clock is held at full
        }
        if idle < 2.0 {
            self.idle_credited = false;
        }
        if !self.work.tick(dt) {
            return vec![];
        }
        if self.cfg.use_break_lock {
            return self.start_break();
        }
        self.phase = Phase::Prompt;
        self.prompt_left = PROMPT_TIMEOUT_SECONDS;
        vec![Event::Prompt]
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn cfg(enabled: bool, use_break_lock: bool, detect: bool) -> RuleSettings {
        RuleSettings {
            enabled,
            interval_min: 1,
            break_seconds: 5,
            snooze_min: 1,
            detect_natural_breaks: detect,
            use_break_lock,
        }
    }
    fn make() -> Rule202020 {
        Rule202020::new(&cfg(true, false, true))
    }
    fn run(rule: &mut Rule202020, seconds: usize, idle: f64) -> Vec<Event> {
        (0..seconds).flat_map(|_| rule.tick(1.0, idle, false)).collect()
    }

    #[test]
    fn prompt_after_interval() {
        let mut rule = make();
        assert_eq!(run(&mut rule, 60, 0.0), [Event::Prompt]);
        assert_eq!(rule.phase, Phase::Prompt);
    }

    #[test]
    fn full_cycle() {
        let mut rule = make();
        run(&mut rule, 60, 0.0);
        assert_eq!(rule.start_break(), [Event::BreakStart]);
        assert_eq!(run(&mut rule, 5, 0.0), [Event::BreakDone]);
        assert_eq!(rule.phase, Phase::Working);
        assert_eq!(rule.seconds_to_break(), 60);
    }

    #[test]
    fn snooze_returns_to_working() {
        let mut rule = make();
        run(&mut rule, 60, 0.0);
        assert_eq!(rule.snooze(), [Event::Snoozed]);
        assert_eq!(rule.phase, Phase::Working);
        assert_eq!(rule.seconds_to_break(), 60);
    }

    #[test]
    fn prompt_times_out_into_snooze() {
        let mut rule = make();
        run(&mut rule, 60, 0.0);
        assert!(run(&mut rule, PROMPT_TIMEOUT_SECONDS as usize, 0.0).contains(&Event::Snoozed));
        assert_eq!(rule.phase, Phase::Working);
    }

    #[test]
    fn break_lock_skips_prompt() {
        let mut rule = Rule202020::new(&cfg(true, true, true));
        assert_eq!(run(&mut rule, 60, 0.0), [Event::BreakStart]);
        assert_eq!(rule.phase, Phase::Break);
    }

    #[test]
    fn skip_break() {
        let mut rule = Rule202020::new(&cfg(true, true, true));
        run(&mut rule, 60, 0.0);
        assert_eq!(rule.skip_break(), [Event::BreakSkipped]);
        assert_eq!(rule.phase, Phase::Working);
    }

    #[test]
    fn natural_break_resets_once_and_holds_clock() {
        let mut rule = make();
        run(&mut rule, 30, 0.0);
        assert_eq!(rule.seconds_to_break(), 30);
        assert_eq!(run(&mut rule, 1, 6.0), [Event::NaturalBreak]);
        assert_eq!(rule.seconds_to_break(), 60);
        assert_eq!(run(&mut rule, 20, 30.0), []); // still away
        assert_eq!(rule.seconds_to_break(), 60);
    }

    #[test]
    fn natural_break_can_trigger_again_after_return() {
        let mut rule = make();
        run(&mut rule, 1, 6.0);
        run(&mut rule, 3, 0.0);
        assert_eq!(run(&mut rule, 1, 6.0), [Event::NaturalBreak]);
    }

    #[test]
    fn natural_break_detection_can_be_disabled() {
        let mut rule = Rule202020::new(&cfg(true, false, false));
        assert_eq!(run(&mut rule, 1, 100.0), []);
    }

    #[test]
    fn paused_does_nothing() {
        let mut rule = make();
        rule.set_paused(true);
        assert_eq!(run(&mut rule, 120, 0.0), []);
        assert_eq!(rule.seconds_to_break(), 60);
    }

    #[test]
    fn reload_changes_interval() {
        let mut rule = make();
        rule.reload(&RuleSettings { interval_min: 2, ..cfg(true, false, true) });
        assert_eq!(rule.seconds_to_break(), 120);
    }

    #[test]
    fn disabled_rule_never_prompts_or_locks_screen() {
        let mut rule = Rule202020::new(&cfg(false, true, true));
        assert_eq!(run(&mut rule, 300, 0.0), []);
        assert_eq!(rule.phase, Phase::Working);
    }

    #[test]
    fn disabling_cancels_a_pending_prompt() {
        let mut rule = make();
        run(&mut rule, 60, 0.0);
        assert_eq!(rule.phase, Phase::Prompt);
        rule.reload(&cfg(false, false, true));
        assert_eq!(rule.phase, Phase::Working);
        assert_eq!(run(&mut rule, 120, 0.0), []);
    }

    #[test]
    fn reenabling_restarts_the_clock() {
        let mut rule = Rule202020::new(&cfg(false, false, true));
        run(&mut rule, 100, 0.0);
        rule.reload(&cfg(true, false, true));
        assert_eq!(rule.seconds_to_break(), 60);
        assert_eq!(run(&mut rule, 60, 0.0), [Event::Prompt]);
    }

    #[test]
    fn manual_break_still_works_when_disabled() {
        let mut rule = Rule202020::new(&cfg(false, false, true));
        assert_eq!(rule.start_break(), [Event::BreakStart]);
        assert_eq!(run(&mut rule, 5, 0.0), [Event::BreakDone]);
    }

    #[test]
    fn hold_freezes_clock_and_drops_prompt() {
        let mut rule = make();
        for _ in 0..30 {
            rule.tick(1.0, 0.0, true);
        }
        assert_eq!(rule.seconds_to_break(), 60);
        run(&mut rule, 60, 0.0);
        assert_eq!(rule.phase, Phase::Prompt);
        assert_eq!(rule.tick(1.0, 0.0, true), [Event::Snoozed]);
        assert_eq!(rule.phase, Phase::Working);
    }

    #[test]
    fn hold_does_not_interrupt_a_running_break() {
        let mut rule = Rule202020::new(&cfg(true, true, true));
        run(&mut rule, 60, 0.0);
        assert_eq!(rule.phase, Phase::Break);
        let events: Vec<Event> = (0..5).flat_map(|_| rule.tick(1.0, 0.0, true)).collect();
        assert_eq!(events, [Event::BreakDone]);
    }

    #[test]
    fn break_length_changes_apply_to_the_next_break() {
        let mut rule = make();
        rule.reload(&RuleSettings { break_seconds: 9, ..cfg(true, false, true) });
        rule.start_break();
        assert_eq!(rule.break_seconds_left(), 9);
    }
}
