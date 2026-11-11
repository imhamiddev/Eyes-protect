//! Sunrise/sunset from latitude/longitude (NOAA solar-position equations).

use chrono::{Datelike, NaiveDate};
use std::f64::consts::PI;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Polar {
    /// The sun never sets.
    Day,
    /// The sun never rises.
    Night,
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct SunTimes {
    /// Minutes after local midnight.
    pub sunrise: Option<f64>,
    pub sunset: Option<f64>,
    pub polar: Option<Polar>,
}

pub fn sun_times(day: NaiveDate, lat: f64, lon: f64, utc_offset_hours: f64) -> SunTimes {
    let n = f64::from(day.ordinal());
    let g = 2.0 * PI / 365.0 * (n - 1.0);
    let eqtime = 229.18 * (0.000075 + 0.001868 * g.cos() - 0.032077 * g.sin() - 0.014615 * (2.0 * g).cos() - 0.040849 * (2.0 * g).sin());
    let decl = 0.006918 - 0.399912 * g.cos() + 0.070257 * g.sin() - 0.006758 * (2.0 * g).cos() + 0.000907 * (2.0 * g).sin()
        - 0.002697 * (3.0 * g).cos()
        + 0.00148 * (3.0 * g).sin();
    let lat_r = lat.to_radians();
    let cos_ha = 90.833_f64.to_radians().cos() / (lat_r.cos() * decl.cos()) - lat_r.tan() * decl.tan();
    if cos_ha > 1.0 {
        return SunTimes { sunrise: None, sunset: None, polar: Some(Polar::Night) };
    }
    if cos_ha < -1.0 {
        return SunTimes { sunrise: None, sunset: None, polar: Some(Polar::Day) };
    }
    let ha = cos_ha.acos().to_degrees();
    let offset = utc_offset_hours * 60.0;
    let sunrise = 720.0 - 4.0 * (lon + ha) - eqtime + offset;
    let sunset = 720.0 - 4.0 * (lon - ha) - eqtime + offset;
    SunTimes { sunrise: Some(sunrise.rem_euclid(1440.0)), sunset: Some(sunset.rem_euclid(1440.0)), polar: None }
}

pub fn format_minutes(minutes: f64) -> String {
    let m = (minutes.round_ties_even() as i64).rem_euclid(1440);
    format!("{:02}:{:02}", m / 60, m % 60)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn d(y: i32, m: u32, day: u32) -> NaiveDate {
        NaiveDate::from_ymd_opt(y, m, day).unwrap()
    }
    fn hm(h: u32, m: u32) -> f64 {
        f64::from(h * 60 + m)
    }
    fn close(a: f64, b: f64, tol: f64) -> bool {
        ((a - b + 720.0).rem_euclid(1440.0) - 720.0).abs() <= tol
    }

    #[test]
    fn tehran_summer_and_winter() {
        // Iran has used a fixed UTC+3:30 since 2022 (no daylight saving).
        let s = sun_times(d(2024, 6, 21), 35.6892, 51.3890, 3.5);
        assert!(close(s.sunrise.unwrap(), hm(4, 48), 8.0) && close(s.sunset.unwrap(), hm(19, 25), 8.0));
        let w = sun_times(d(2024, 12, 21), 35.6892, 51.3890, 3.5);
        assert!(close(w.sunrise.unwrap(), hm(7, 12), 8.0) && close(w.sunset.unwrap(), hm(16, 55), 8.0));
        assert!(w.sunset.unwrap() < s.sunset.unwrap());
    }

    #[test]
    fn london_equinox_is_about_twelve_hours() {
        let s = sun_times(d(2024, 3, 20), 51.5072, -0.1276, 0.0);
        assert!(close(s.sunrise.unwrap(), hm(6, 0), 15.0) && close(s.sunset.unwrap(), hm(18, 12), 15.0));
    }

    #[test]
    fn equator_is_always_about_twelve_hours() {
        for day in [d(2024, 3, 1), d(2024, 9, 1)] {
            let s = sun_times(day, 0.0, 0.0, 0.0);
            let len = s.sunset.unwrap() - s.sunrise.unwrap();
            assert!(11.9 * 60.0 < len && len < 12.3 * 60.0, "{len}");
        }
    }

    #[test]
    fn polar_day_and_night() {
        assert_eq!(sun_times(d(2024, 6, 21), 69.65, 18.96, 2.0).polar, Some(Polar::Day));
        assert_eq!(sun_times(d(2024, 12, 21), 69.65, 18.96, 1.0).polar, Some(Polar::Night));
        assert!(sun_times(d(2024, 6, 21), 69.65, 18.96, 2.0).sunrise.is_none());
    }

    #[test]
    fn southern_hemisphere_flips_seasons() {
        let dec = sun_times(d(2024, 12, 21), -33.87, 151.21, 11.0);
        let jun = sun_times(d(2024, 6, 21), -33.87, 151.21, 10.0);
        assert!(dec.sunset.unwrap() - dec.sunrise.unwrap() > jun.sunset.unwrap() - jun.sunrise.unwrap());
    }

    #[test]
    fn format_minutes_wraps() {
        assert_eq!(format_minutes(hm(17, 8)), "17:08");
        assert_eq!(format_minutes(1440.0 + 5.0), "00:05");
    }
}
