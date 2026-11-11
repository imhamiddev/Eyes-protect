//! Repeating reminders (blink, hydration).

use crate::common::countdown::Countdown;

/// Don't nag someone who has left the desk.
pub const AWAY_AFTER_SECONDS: f64 = 90.0;

#[derive(Debug, Clone)]
pub struct IntervalReminder {
    pub enabled: bool,
    pub interval_min: i64,
    cd: Countdown,
}

impl IntervalReminder {
    pub fn new(interval_min: i64, enabled: bool) -> Self {
        let interval_min = interval_min.max(1);
        let mut cd = Countdown::new(interval_min * 60);
        cd.start();
        Self { enabled, interval_min, cd }
    }

    pub fn configure(&mut self, interval_min: i64, enabled: bool) {
        let interval_min = interval_min.max(1);
        if interval_min != self.interval_min {
            self.interval_min = interval_min;
            self.cd.start_with(interval_min * 60);
        }
        if enabled && !self.enabled {
            self.cd.start_with(self.interval_min * 60);
        }
        self.enabled = enabled;
    }

    /// Advance time; `true` when the reminder is due.
    pub fn tick(&mut self, dt: f64, idle_seconds: f64, paused: bool) -> bool {
        if !self.enabled || paused || idle_seconds >= AWAY_AFTER_SECONDS {
            return false;
        }
        if self.cd.tick(dt) {
            self.cd.start();
            return true;
        }
        false
    }

    pub fn seconds_left(&self) -> i64 {
        self.cd.seconds_left()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn fire_count(rem: &mut IntervalReminder, seconds: usize, idle: f64, paused: bool) -> usize {
        (0..seconds).filter(|_| rem.tick(1.0, idle, paused)).count()
    }

    #[test]
    fn fires_every_interval() {
        assert_eq!(fire_count(&mut IntervalReminder::new(1, true), 180, 0.0, false), 3);
    }

    #[test]
    fn disabled_never_fires() {
        assert_eq!(fire_count(&mut IntervalReminder::new(1, false), 600, 0.0, false), 0);
    }

    #[test]
    fn paused_and_away_hold_the_clock() {
        let mut rem = IntervalReminder::new(1, true);
        assert_eq!(fire_count(&mut rem, 120, 0.0, true), 0);
        assert_eq!(fire_count(&mut rem, 120, 500.0, false), 0);
        assert_eq!(rem.seconds_left(), 60);
    }

    #[test]
    fn enabling_restarts_clock() {
        let mut rem = IntervalReminder::new(1, false);
        rem.configure(1, true);
        assert_eq!(rem.seconds_left(), 60);
        assert!(rem.enabled);
    }

    #[test]
    fn interval_change_restarts() {
        let mut rem = IntervalReminder::new(1, true);
        rem.configure(3, true);
        assert_eq!(rem.seconds_left(), 180);
    }
}
