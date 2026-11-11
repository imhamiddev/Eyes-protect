//! Tiny English/Persian translation table.

use std::sync::atomic::{AtomicU8, Ordering};

use super::i18n_strings::{EN, FA};

pub const RTL_LANGUAGES: [&str; 1] = ["fa"];

static CURRENT: AtomicU8 = AtomicU8::new(0); // 0 = en, 1 = fa

fn table(code: &str) -> Option<&'static [(&'static str, &'static str)]> {
    match code {
        "en" => Some(EN),
        "fa" => Some(FA),
        _ => None,
    }
}

fn lookup(table: &'static [(&'static str, &'static str)], key: &str) -> Option<&'static str> {
    table.binary_search_by_key(&key, |(k, _)| k).ok().map(|i| table[i].1).filter(|v| !v.is_empty())
}

/// Translate `key` into `language` (falls back to English, then to the key itself).
pub fn tr_in(language: &str, key: &str) -> String {
    table(language).and_then(|t| lookup(t, key)).or_else(|| lookup(EN, key)).map(String::from).unwrap_or_else(|| key.to_string())
}

/// Like [`tr_in`], then replace each `{name}` placeholder with its value.
pub fn tr_fmt_in(language: &str, key: &str, args: &[(&str, &str)]) -> String {
    let mut text = tr_in(language, key);
    for (name, value) in args {
        text = text.replace(&format!("{{{name}}}"), value);
    }
    text
}

pub fn set_language(code: &str) {
    CURRENT.store(u8::from(code == "fa"), Ordering::Relaxed);
}

pub fn language() -> &'static str {
    if CURRENT.load(Ordering::Relaxed) == 1 {
        "fa"
    } else {
        "en"
    }
}

pub fn is_rtl() -> bool {
    RTL_LANGUAGES.contains(&language())
}

/// Translate into the current language.
pub fn tr(key: &str) -> String {
    tr_in(language(), key)
}

pub fn tr_fmt(key: &str, args: &[(&str, &str)]) -> String {
    tr_fmt_in(language(), key, args)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::BTreeSet;

    fn placeholders(text: &str) -> BTreeSet<String> {
        let mut out = BTreeSet::new();
        let mut rest = text;
        while let Some(start) = rest.find('{') {
            let Some(len) = rest[start..].find('}') else { break };
            out.insert(rest[start + 1..start + len].to_string());
            rest = &rest[start + len + 1..];
        }
        out
    }

    #[test]
    fn tables_are_sorted_and_cover_the_same_keys() {
        for t in [EN, FA] {
            assert!(t.windows(2).all(|w| w[0].0 < w[1].0), "table must be sorted and unique");
        }
        let en: Vec<_> = EN.iter().map(|(k, _)| k).collect();
        let fa: Vec<_> = FA.iter().map(|(k, _)| k).collect();
        assert_eq!(en, fa);
        assert_eq!(EN.len(), 197);
    }

    #[test]
    fn no_empty_translations_and_placeholders_match() {
        for ((key, en), (_, fa)) in EN.iter().zip(FA.iter()) {
            assert!(!en.is_empty() && !fa.is_empty(), "{key}");
            assert_eq!(placeholders(en), placeholders(fa), "placeholders differ for {key}");
        }
    }

    #[test]
    fn translates_and_falls_back() {
        assert_eq!(tr_in("en", "nav.home"), "Home");
        assert_ne!(tr_in("fa", "nav.home"), "Home");
        assert_eq!(tr_in("de", "nav.home"), "Home"); // unknown language -> English
        assert_eq!(tr_in("en", "no.such.key"), "no.such.key");
    }

    #[test]
    fn formats_placeholders() {
        let s = tr_fmt_in("en", "stats.best", &[("d", "Friday"), ("n", "9")]);
        assert_eq!(s, "Best day: Friday (9 breaks)");
    }

    #[test]
    fn rtl_follows_the_current_language() {
        set_language("fa");
        assert!(is_rtl() && language() == "fa");
        set_language("en");
        assert!(!is_rtl() && language() == "en");
        set_language("xx"); // unknown codes behave like English
        assert_eq!(language(), "en");
    }
}
