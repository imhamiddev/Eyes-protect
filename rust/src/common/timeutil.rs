//! Small, dependency-free helpers for working with times of day.

use chrono::{Local, NaiveTime, Timelike};

/// Error returned by [`parse_hhmm`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TimeParseError(pub String);

impl std::fmt::Display for TimeParseError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "invalid time of day: {:?}", self.0)
    }
}
impl std::error::Error for TimeParseError {}

/// Parse `"HH:MM"` into a [`NaiveTime`].
pub fn parse_hhmm(value: &str) -> Result<NaiveTime, TimeParseError> {
    let err = || TimeParseError(value.to_string());
    let (h, m) = value.trim().split_once(':').ok_or_else(err)?;
    let h: u32 = h.trim().parse().map_err(|_| err())?;
    let m: u32 = m.trim().parse().map_err(|_| err())?;
    NaiveTime::from_hms_opt(h, m, 0).ok_or_else(err)
}

pub fn format_hhmm(value: NaiveTime) -> String {
    format!("{:02}:{:02}", value.hour(), value.minute())
}

pub fn minutes_of_day(value: NaiveTime) -> u32 {
    value.hour() * 60 + value.minute()
}

/// True when `now` is inside `[start, end)`. Windows may wrap past midnight.
pub fn in_window(now: NaiveTime, start: NaiveTime, end: NaiveTime) -> bool {
    let (n, s, e) = (minutes_of_day(now), minutes_of_day(start), minutes_of_day(end));
    if s == e {
        return false;
    }
    if s < e {
        s <= n && n < e
    } else {
        n >= s || n < e
    }
}

/// Current local time truncated to the minute.
pub fn now_time() -> NaiveTime {
    Local::now().time().with_second(0).and_then(|t| t.with_nanosecond(0)).unwrap_or_default()
}

/// Current local time including seconds (for smooth schedule fades).
pub fn now_precise() -> NaiveTime {
    Local::now().time().with_nanosecond(0).unwrap_or_default()
}

pub fn minutes_precise(value: NaiveTime) -> f64 {
    f64::from(value.hour() * 60 + value.minute()) + f64::from(value.second()) / 60.0
}

/// `75 -> "01:15"`; negative values clamp to `00:00`.
pub fn format_mmss(total_seconds: i64) -> String {
    let t = total_seconds.max(0);
    format!("{:02}:{:02}", t / 60, t % 60)
}

/// `'3 h 25 min'`, `'48 min'`, `'0 min'` (seconds are dropped).
pub fn format_duration(total_seconds: i64, hour_unit: &str, minute_unit: &str) -> String {
    let minutes = total_seconds.max(0) / 60;
    let (hours, minutes) = (minutes / 60, minutes % 60);
    if hours > 0 {
        if minutes > 0 {
            format!("{hours} {hour_unit} {minutes} {minute_unit}")
        } else {
            format!("{hours} {hour_unit}")
        }
    } else {
        format!("{minutes} {minute_unit}")
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn t(h: u32, m: u32) -> NaiveTime {
        NaiveTime::from_hms_opt(h, m, 0).unwrap()
    }

    #[test]
    fn parses_hhmm() {
        assert_eq!(parse_hhmm("07:05").unwrap(), t(7, 5));
        assert_eq!(parse_hhmm(" 23:59 ").unwrap(), t(23, 59));
    }

    #[test]
    fn rejects_invalid_hhmm() {
        for bad in ["nope", "", "25:00", "12:60", "12", "a:b"] {
            assert!(parse_hhmm(bad).is_err(), "{bad}");
        }
    }

    #[test]
    fn window_same_day() {
        assert!(in_window(t(10, 0), t(9, 0), t(17, 0)));
        assert!(!in_window(t(17, 0), t(9, 0), t(17, 0)));
        assert!(!in_window(t(8, 59), t(9, 0), t(17, 0)));
    }

    #[test]
    fn window_wraps_midnight() {
        assert!(in_window(t(23, 0), t(20, 0), t(6, 0)));
        assert!(in_window(t(3, 0), t(20, 0), t(6, 0)));
        assert!(!in_window(t(12, 0), t(20, 0), t(6, 0)));
    }

    #[test]
    fn empty_window_is_never_active() {
        assert!(!in_window(t(12, 0), t(8, 0), t(8, 0)));
    }

    #[test]
    fn mmss() {
        assert_eq!(format_mmss(0), "00:00");
        assert_eq!(format_mmss(75), "01:15");
        assert_eq!(format_mmss(-5), "00:00");
    }

    #[test]
    fn durations() {
        assert_eq!(format_duration(0, "h", "min"), "0 min");
        assert_eq!(format_duration(59, "h", "min"), "0 min");
        assert_eq!(format_duration(48 * 60, "h", "min"), "48 min");
        assert_eq!(format_duration(3 * 3600 + 25 * 60, "h", "min"), "3 h 25 min");
        assert_eq!(format_duration(2 * 3600, "h", "min"), "2 h");
        assert_eq!(format_duration(90, "ساعت", "دقیقه"), "1 دقیقه");
        assert_eq!(format_duration(-5, "h", "min"), "0 min");
    }

    #[test]
    fn formats_and_precise_minutes() {
        assert_eq!(format_hhmm(t(7, 5)), "07:05");
        assert_eq!(minutes_of_day(t(1, 30)), 90);
        let with_secs = NaiveTime::from_hms_opt(1, 30, 30).unwrap();
        assert!((minutes_precise(with_secs) - 90.5).abs() < 1e-9);
    }
}
