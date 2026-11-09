//! Daily usage statistics (breaks taken, water, blinks) persisted as JSON.

use chrono::{Duration, Local, NaiveDate};
use std::collections::BTreeMap;
use std::path::PathBuf;

use super::config::config_dir;

pub const KINDS: &[&str] = &["breaks", "water", "blinks", "skipped", "active_s", "longest_run_s", "stretches"];

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct UnknownStat(pub String);
impl std::fmt::Display for UnknownStat {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "unknown stat: {}", self.0)
    }
}
impl std::error::Error for UnknownStat {}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WeekSummary {
    pub breaks: i64,
    pub active_s: i64,
    pub avg_active_s: i64,
    pub best_day: Option<NaiveDate>,
    pub best_day_breaks: i64,
    pub longest_run_s: i64,
    pub water: i64,
    pub stretches: i64,
}

pub fn today() -> NaiveDate {
    Local::now().date_naive()
}

#[derive(Debug, Clone)]
pub struct Stats {
    pub path: PathBuf,
    pub data: BTreeMap<String, BTreeMap<String, i64>>,
}

impl Stats {
    pub fn new() -> Self {
        Self::open(config_dir().join("stats.json"))
    }

    pub fn open(path: PathBuf) -> Self {
        let mut stats = Self { path, data: BTreeMap::new() };
        stats.load();
        stats
    }

    pub fn load(&mut self) {
        self.data = std::fs::read_to_string(&self.path)
            .ok()
            .and_then(|t| serde_json::from_str(&t).ok())
            .unwrap_or_default();
    }

    pub fn save(&self) {
        if let Ok(text) = serde_json::to_string(&self.data) {
            let _ = std::fs::write(&self.path, text);
        }
    }

    fn check(kind: &str) -> Result<(), UnknownStat> {
        if KINDS.contains(&kind) { Ok(()) } else { Err(UnknownStat(kind.to_string())) }
    }

    pub fn add(&mut self, kind: &str, day: Option<NaiveDate>, amount: i64, save: bool) -> Result<(), UnknownStat> {
        Self::check(kind)?;
        let key = day.unwrap_or_else(today).to_string();
        *self.data.entry(key).or_default().entry(kind.to_string()).or_insert(0) += amount;
        if save {
            self.save();
        }
        Ok(())
    }

    /// Keep the largest value seen for the day (e.g. the longest stretch without a break).
    pub fn record_max(&mut self, kind: &str, value: i64, day: Option<NaiveDate>, save: bool) -> Result<(), UnknownStat> {
        Self::check(kind)?;
        let entry = self.data.entry(day.unwrap_or_else(today).to_string()).or_default();
        if value > entry.get(kind).copied().unwrap_or(0) {
            entry.insert(kind.to_string(), value);
            if save {
                self.save();
            }
        }
        Ok(())
    }

    pub fn get(&self, kind: &str, day: Option<NaiveDate>) -> i64 {
        let key = day.unwrap_or_else(today).to_string();
        self.data.get(&key).and_then(|d| d.get(kind)).copied().unwrap_or(0)
    }

    /// Oldest first, ending with `today`.
    pub fn last_days(&self, kind: &str, days: i64, today_: Option<NaiveDate>) -> Vec<i64> {
        let t = today_.unwrap_or_else(today);
        (0..days).rev().map(|i| self.get(kind, Some(t - Duration::days(i)))).collect()
    }

    /// Consecutive days with at least `goal` breaks. A day still in progress never breaks it.
    pub fn streak(&self, goal: i64, today_: Option<NaiveDate>) -> i64 {
        let t = today_.unwrap_or_else(today);
        let mut day = if self.get("breaks", Some(t)) >= goal { t } else { t - Duration::days(1) };
        let mut count = 0;
        while goal > 0 && self.get("breaks", Some(day)) >= goal {
            count += 1;
            day -= Duration::days(1);
        }
        count
    }

    pub fn week_summary(&self, today_: Option<NaiveDate>) -> WeekSummary {
        let t = today_.unwrap_or_else(today);
        let days: Vec<NaiveDate> = (0..7).rev().map(|i| t - Duration::days(i)).collect();
        let breaks: Vec<i64> = days.iter().map(|d| self.get("breaks", Some(*d))).collect();
        let active: Vec<i64> = days.iter().map(|d| self.get("active_s", Some(*d))).collect();
        let best = if breaks.iter().any(|b| *b != 0) {
            // Latest day wins a tie, like Python's max over (breaks, index).
            (0..7).max_by_key(|i| (breaks[*i], *i))
        } else {
            None
        };
        WeekSummary {
            breaks: breaks.iter().sum(),
            active_s: active.iter().sum(),
            avg_active_s: active.iter().sum::<i64>() / 7,
            best_day: best.map(|i| days[i]),
            best_day_breaks: best.map(|i| breaks[i]).unwrap_or(0),
            longest_run_s: days.iter().map(|d| self.get("longest_run_s", Some(*d))).max().unwrap_or(0),
            water: days.iter().map(|d| self.get("water", Some(*d))).sum(),
            stretches: days.iter().map(|d| self.get("stretches", Some(*d))).sum(),
        }
    }
}

impl Default for Stats {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn d(y: i32, m: u32, day: u32) -> NaiveDate {
        NaiveDate::from_ymd_opt(y, m, day).unwrap()
    }
    fn fresh() -> (tempfile::TempDir, Stats) {
        let dir = tempfile::tempdir().unwrap();
        let stats = Stats::open(dir.path().join("st.json"));
        (dir, stats)
    }

    #[test]
    fn add_and_get() {
        let (_g, mut s) = fresh();
        s.add("breaks", None, 1, true).unwrap();
        s.add("breaks", None, 1, true).unwrap();
        s.add("water", None, 3, true).unwrap();
        assert_eq!((s.get("breaks", None), s.get("water", None), s.get("blinks", None)), (2, 3, 0));
    }

    #[test]
    fn persists() {
        let (g, mut s) = fresh();
        s.add("blinks", None, 1, true).unwrap();
        assert_eq!(Stats::open(g.path().join("st.json")).get("blinks", None), 1);
    }

    #[test]
    fn last_days_order() {
        let (_g, mut s) = fresh();
        let today = d(2026, 11, 6);
        s.add("breaks", Some(today), 4, true).unwrap();
        s.add("breaks", Some(today - Duration::days(2)), 1, true).unwrap();
        assert_eq!(s.last_days("breaks", 3, Some(today)), vec![1, 0, 4]);
    }

    #[test]
    fn unknown_kind_is_rejected() {
        let (_g, mut s) = fresh();
        assert!(s.add("coffee", None, 1, true).is_err());
        assert!(s.record_max("nope", 1, None, true).is_err());
    }

    #[test]
    fn record_max_keeps_the_largest() {
        let (_g, mut s) = fresh();
        for v in [300, 120, 900] {
            s.record_max("longest_run_s", v, None, true).unwrap();
        }
        assert_eq!(s.get("longest_run_s", None), 900);
    }

    #[test]
    fn deferred_save_writes_nothing_until_saved() {
        let (g, mut s) = fresh();
        let path = g.path().join("st.json");
        s.add("active_s", None, 1, false).unwrap();
        assert!(!path.exists());
        s.save();
        assert_eq!(Stats::open(path).get("active_s", None), 1);
    }

    #[test]
    fn streak_counts_consecutive_goal_days() {
        let (_g, mut s) = fresh();
        let today = d(2026, 11, 8);
        for back in 1..=3 {
            s.add("breaks", Some(today - Duration::days(back)), 6, true).unwrap();
        }
        assert_eq!(s.streak(6, Some(today)), 3); // today unfinished: streak not broken
        s.add("breaks", Some(today), 6, true).unwrap();
        assert_eq!(s.streak(6, Some(today)), 4); // today reached the goal: it counts
        s.data.remove(&(today - Duration::days(2)).to_string());
        assert_eq!(s.streak(6, Some(today)), 2); // a missed day ends it
    }

    #[test]
    fn streak_zero_goal_and_empty() {
        let (_g, s) = fresh();
        assert_eq!(s.streak(6, Some(d(2026, 1, 1))), 0);
        assert_eq!(s.streak(0, Some(d(2026, 1, 1))), 0);
    }

    #[test]
    fn week_summary() {
        let (_g, mut s) = fresh();
        let today = d(2026, 11, 8);
        s.add("breaks", Some(today), 5, true).unwrap();
        s.add("breaks", Some(today - Duration::days(2)), 9, true).unwrap();
        s.add("active_s", Some(today), 7 * 3600, true).unwrap();
        s.add("water", Some(today - Duration::days(1)), 4, true).unwrap();
        s.record_max("longest_run_s", 4000, Some(today - Duration::days(3)), true).unwrap();
        let w = s.week_summary(Some(today));
        assert_eq!((w.breaks, w.active_s, w.avg_active_s), (14, 7 * 3600, 3600));
        assert_eq!((w.best_day, w.best_day_breaks), (Some(today - Duration::days(2)), 9));
        assert_eq!((w.longest_run_s, w.water), (4000, 4));
        assert!(s.week_summary(Some(d(2020, 1, 1))).best_day.is_none());
    }

    #[test]
    fn corrupt_file_starts_empty() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("st.json");
        std::fs::write(&path, "[1,2").unwrap();
        assert!(Stats::open(path).data.is_empty());
    }
}
