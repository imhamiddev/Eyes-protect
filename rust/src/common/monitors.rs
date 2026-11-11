//! Per-monitor settings helpers (stored compactly in the JSON settings).

use std::collections::{BTreeMap, BTreeSet};

/// `"\\.\DISPLAY2"` -> `"DISPLAY2"` (stable, readable settings key).
pub fn key(device: &str) -> String {
    let cleaned: String = device.replace('\\', "");
    let cleaned = cleaned.trim_start_matches('.');
    if cleaned.is_empty() {
        device.to_string()
    } else {
        cleaned.to_string()
    }
}

pub fn parse_set(text: &str) -> BTreeSet<String> {
    text.split(',').map(str::trim).filter(|p| !p.is_empty()).map(String::from).collect()
}

pub fn format_set<I, S>(items: I) -> String
where
    I: IntoIterator<Item = S>,
    S: AsRef<str>,
{
    let sorted: BTreeSet<String> = items.into_iter().map(|s| s.as_ref().to_string()).collect();
    sorted.into_iter().collect::<Vec<_>>().join(",")
}

/// `"DISPLAY1=80;DISPLAY2=100"` -> map (values clamped to 30..=100, bad entries ignored).
pub fn parse_map(text: &str) -> BTreeMap<String, i32> {
    let mut out = BTreeMap::new();
    for part in text.split(';') {
        let (name, _, value) = part.partition_eq();
        if let Ok(v) = value.trim().parse::<i64>() {
            out.insert(name.trim().to_string(), v.clamp(30, 100) as i32);
        }
    }
    out.remove("");
    out
}

pub fn format_map(values: &BTreeMap<String, i32>) -> String {
    values.iter().map(|(k, v)| format!("{k}={v}")).collect::<Vec<_>>().join(";")
}

trait PartitionEq {
    fn partition_eq(&self) -> (&str, &str, &str);
}
impl PartitionEq for str {
    fn partition_eq(&self) -> (&str, &str, &str) {
        match self.find('=') {
            Some(i) => (&self[..i], "=", &self[i + 1..]),
            None => (self, "", ""),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn key_strips_device_prefix() {
        assert_eq!(key("\\\\.\\DISPLAY2"), "DISPLAY2");
        assert_eq!(key("DISPLAY1"), "DISPLAY1");
    }

    #[test]
    fn set_roundtrip_and_junk() {
        let want: BTreeSet<String> = ["DISPLAY1", "DISPLAY2"].into_iter().map(String::from).collect();
        assert_eq!(parse_set("DISPLAY2, DISPLAY1 ,,"), want);
        assert_eq!(format_set(["B", "A"]), "A,B");
        assert!(parse_set("").is_empty());
    }

    #[test]
    fn map_roundtrip_clamps_and_ignores_junk() {
        let m = parse_map("DISPLAY1=80;DISPLAY2=999;X=abc;=5;noeq");
        assert_eq!(m.get("DISPLAY1"), Some(&80));
        assert_eq!(m.get("DISPLAY2"), Some(&100));
        assert_eq!(m.len(), 2);
        assert_eq!(parse_map("D=1").get("D"), Some(&30));
        let mut round = BTreeMap::new();
        round.insert("B".to_string(), 50);
        round.insert("A".to_string(), 90);
        assert_eq!(parse_map(&format_map(&round)), round);
    }
}
