//! A pausable, snoozable countdown driven by explicit ticks (easy to test).

#[derive(Debug, Clone)]
pub struct Countdown {
    pub duration: i64,
    pub remaining: f64,
    pub running: bool,
}

impl Countdown {
    pub fn new(duration_seconds: i64) -> Self {
        let duration = duration_seconds.max(1);
        Self { duration, remaining: duration as f64, running: false }
    }

    pub fn start(&mut self) {
        self.remaining = self.duration as f64;
        self.running = true;
    }

    /// Restart with a new length.
    pub fn start_with(&mut self, duration_seconds: i64) {
        self.duration = duration_seconds.max(1);
        self.start();
    }

    pub fn stop(&mut self) {
        self.running = false;
    }
    pub fn pause(&mut self) {
        self.running = false;
    }
    pub fn resume(&mut self) {
        self.running = true;
    }
    pub fn reset(&mut self) {
        self.remaining = self.duration as f64;
    }

    pub fn snooze(&mut self, seconds: i64) {
        self.remaining = seconds.max(1) as f64;
        self.running = true;
    }

    /// 0.0 right after a reset, 1.0 when finished.
    pub fn progress(&self) -> f64 {
        1.0 - (self.remaining / self.duration as f64).clamp(0.0, 1.0)
    }

    pub fn seconds_left(&self) -> i64 {
        ((self.remaining + 0.999) as i64).max(0)
    }

    /// Advance time; returns `true` exactly once, when the countdown elapses.
    pub fn tick(&mut self, dt: f64) -> bool {
        if !self.running {
            return false;
        }
        self.remaining -= dt;
        if self.remaining <= 0.0 {
            self.remaining = 0.0;
            self.running = false;
            return true;
        }
        false
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn fires_once() {
        let mut c = Countdown::new(3);
        c.start();
        let fired: Vec<bool> = (0..4).map(|_| c.tick(1.0)).collect();
        assert_eq!(fired, [false, false, true, false]);
    }

    #[test]
    fn pause_blocks_ticks() {
        let mut c = Countdown::new(2);
        c.start();
        c.pause();
        assert!(!c.tick(5.0));
        assert_eq!(c.seconds_left(), 2);
        c.resume();
        assert!(c.tick(5.0));
    }

    #[test]
    fn snooze_restarts_with_new_length() {
        let mut c = Countdown::new(60);
        c.start();
        c.tick(59.0);
        c.snooze(10);
        assert_eq!(c.seconds_left(), 10);
        assert!(c.running);
    }

    #[test]
    fn progress() {
        let mut c = Countdown::new(10);
        c.start();
        assert_eq!(c.progress(), 0.0);
        c.tick(5.0);
        assert!((c.progress() - 0.5).abs() < 1e-9);
        c.tick(5.0);
        assert_eq!(c.progress(), 1.0);
    }

    #[test]
    fn restart_with_duration() {
        let mut c = Countdown::new(5);
        c.start_with(20);
        assert_eq!(c.seconds_left(), 20);
    }

    #[test]
    fn duration_never_below_one_second() {
        assert_eq!(Countdown::new(0).duration, 1);
        assert_eq!(Countdown::new(-4).duration, 1);
    }
}
