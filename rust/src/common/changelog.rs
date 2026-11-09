//! Read release notes from CHANGELOG.md / GitHub release bodies (English + optional Persian).

use regex::Regex;
use std::collections::BTreeMap;
use std::sync::OnceLock;

pub const FA_MARKER: &str = "<!-- fa -->";

/// The repository changelog, embedded at build time so the installed app can show "What's new".
pub const BUNDLED: &str = include_str!("../../../CHANGELOG.md");

fn section_re() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| Regex::new(r"(?m)^## \[(?P<version>[^\]]+)\][^\n]*\n").unwrap())
}
fn bullet_re() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| Regex::new(r"^\s*(?:[-*+]|\d+\.)\s+(?P<text>.+?)\s*$").unwrap())
}

/// `{"0.4.0": body, ...}` from a keep-a-changelog style document, in document order.
pub fn parse_sections(text: &str) -> Vec<(String, String)> {
    let matches: Vec<_> = section_re().captures_iter(text).collect();
    let mut out = Vec::new();
    for (i, caps) in matches.iter().enumerate() {
        let whole = caps.get(0).unwrap();
        let end = matches.get(i + 1).map(|n| n.get(0).unwrap().start()).unwrap_or(text.len());
        out.push((caps["version"].trim().to_string(), text[whole.end()..end].trim().to_string()));
    }
    out
}

pub fn sections_map(text: &str) -> BTreeMap<String, String> {
    parse_sections(text).into_iter().collect()
}

pub fn clean_markdown(line: &str) -> String {
    static LINK: OnceLock<Regex> = OnceLock::new();
    static MARKS: OnceLock<Regex> = OnceLock::new();
    static SPACE: OnceLock<Regex> = OnceLock::new();
    let link = LINK.get_or_init(|| Regex::new(r"\[([^\]]+)\]\([^)]*\)").unwrap());
    let marks = MARKS.get_or_init(|| Regex::new(r"(\*\*|__|`)").unwrap());
    let space = SPACE.get_or_init(|| Regex::new(r"\s+").unwrap());
    let line = link.replace_all(line, "$1");
    let line = marks.replace_all(&line, "");
    space.replace_all(&line, " ").trim().to_string()
}

/// Plain-text bullet list. Persian is used when the body has a Persian part.
pub fn extract_bullets(body: &str, language: &str, limit: usize, max_len: usize) -> Vec<String> {
    let (english, persian) = body.split_once(FA_MARKER).unwrap_or((body, ""));
    let chosen = if language == "fa" && !persian.trim().is_empty() { persian } else { english };
    let mut bullets = Vec::new();
    for raw in chosen.lines() {
        let Some(caps) = bullet_re().captures(raw) else { continue };
        let text = clean_markdown(&caps["text"]);
        let lower = text.to_lowercase();
        if text.is_empty() || lower.starts_with("full changelog") || lower.starts_with("new contributors") {
            continue;
        }
        if text.chars().count() <= max_len {
            bullets.push(text);
        } else {
            let cut: String = text.chars().take(max_len.saturating_sub(1)).collect();
            bullets.push(format!("{}…", cut.trim_end()));
        }
        if bullets.len() >= limit {
            break;
        }
    }
    bullets
}

/// [`extract_bullets`] with the defaults used by the UI (8 bullets, 140 characters).
pub fn bullets(body: &str, language: &str) -> Vec<String> {
    extract_bullets(body, language, 8, 140)
}

/// Bullets for `version` from a changelog text (empty if unknown).
pub fn notes_from_text(text: &str, version: &str, language: &str, limit: usize) -> Vec<String> {
    let wanted = version.trim_start_matches(['v', 'V']);
    sections_map(text)
        .get(wanted)
        .map(|body| extract_bullets(body, language, limit, 140))
        .unwrap_or_default()
}

/// Bullets for `version` from the embedded changelog.
pub fn notes_for(version: &str, language: &str, limit: usize) -> Vec<String> {
    notes_from_text(BUNDLED, version, language, limit)
}

#[cfg(test)]
mod tests {
    use super::*;

    const TEXT: &str = "# Changelog\n\n## [1.2.0] - 2026-01-01\n- First **bold** change with `code`\n* Second [linked](https://x.y/z) change\nNot a bullet\n1. Numbered change\n<!-- fa -->\n- تغییر اول\n- تغییر دوم\n\n## [1.1.0] - 2025-12-01\n- Old change\n";

    #[test]
    fn parses_sections() {
        let s = parse_sections(TEXT);
        let versions: Vec<_> = s.iter().map(|(v, _)| v.as_str()).collect();
        assert_eq!(versions, ["1.2.0", "1.1.0"]);
        let m = sections_map(TEXT);
        assert!(m["1.1.0"].contains("Old change") && !m["1.2.0"].contains("Old change"));
    }

    #[test]
    fn strips_markdown_and_ignores_prose() {
        let body = &sections_map(TEXT)["1.2.0"];
        assert_eq!(bullets(body, "en"), ["First bold change with code", "Second linked change", "Numbered change"]);
    }

    #[test]
    fn persian_part_used_when_requested_and_present() {
        let m = sections_map(TEXT);
        assert_eq!(bullets(&m["1.2.0"], "fa"), ["تغییر اول", "تغییر دوم"]);
        assert_eq!(bullets(&m["1.1.0"], "fa"), ["Old change"]); // falls back to English
    }

    #[test]
    fn limit_truncation_and_github_boilerplate() {
        let mut body: String = (0..20).map(|i| format!("- item {i}\n")).collect();
        body.push_str("- **Full Changelog**: https://x");
        assert_eq!(extract_bullets(&body, "en", 5, 140).len(), 5);
        let long = format!("- {}", "x".repeat(300));
        assert!(extract_bullets(&long, "en", 8, 50)[0].ends_with('…'));
        assert_eq!(bullets("- Full Changelog: a\n- New Contributors\n- real", "en"), ["real"]);
    }

    #[test]
    fn notes_come_from_text_and_unknown_versions_are_empty() {
        assert!(notes_from_text(TEXT, "v1.2.0", "en", 8)[0].starts_with("First bold"));
        assert!(notes_from_text(TEXT, "9.9.9", "en", 8).is_empty());
    }

    #[test]
    fn release_notes_are_summarized_like_the_changelog() {
        assert_eq!(extract_bullets("- a\n- b\n- c", "en", 2, 140), ["a", "b"]);
    }

    /// Guards releases: a version bump without changelog entries fails the tests.
    #[test]
    fn current_version_has_bilingual_notes_in_the_real_changelog() {
        let body = sections_map(BUNDLED)
            .get(crate::VERSION)
            .cloned()
            .unwrap_or_else(|| panic!("CHANGELOG.md needs a section for {}", crate::VERSION));
        let (en, fa) = (bullets(&body, "en"), bullets(&body, "fa"));
        assert!(!en.is_empty() && !fa.is_empty());
        assert_ne!(en, fa);
    }
}
