//! Parsing of global shortcut strings like `Ctrl+Alt+N` into Win32 `RegisterHotKey` arguments.

pub const MOD_ALT: u32 = 0x1;
pub const MOD_CONTROL: u32 = 0x2;
pub const MOD_SHIFT: u32 = 0x4;
pub const MOD_WIN: u32 = 0x8;
pub const MOD_NOREPEAT: u32 = 0x4000;

pub const ACTIONS: [&str; 4] = ["night_light", "break_now", "pause", "quiet"];
pub const DEFAULTS: [(&str, &str); 4] =
    [("night_light", "Ctrl+Alt+N"), ("break_now", "Ctrl+Alt+B"), ("pause", "Ctrl+Alt+P"), ("quiet", "Ctrl+Alt+Q")];

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HotkeyError(pub String);
impl std::fmt::Display for HotkeyError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(&self.0)
    }
}
impl std::error::Error for HotkeyError {}

fn err<T>(msg: impl Into<String>) -> Result<T, HotkeyError> {
    Err(HotkeyError(msg.into()))
}

fn modifier(low: &str) -> Option<(&'static str, u32)> {
    Some(match low {
        "ctrl" | "control" => ("Ctrl", MOD_CONTROL),
        "alt" => ("Alt", MOD_ALT),
        "shift" => ("Shift", MOD_SHIFT),
        "win" | "meta" | "super" => ("Win", MOD_WIN),
        _ => return None,
    })
}

const ORDER: [&str; 4] = ["Ctrl", "Alt", "Shift", "Win"];

fn named(low: &str) -> Option<u32> {
    Some(match low {
        "space" => 0x20,
        "tab" => 0x09,
        "return" | "enter" => 0x0D,
        "backspace" => 0x08,
        "pgup" | "pageup" => 0x21,
        "pgdown" | "pagedown" => 0x22,
        "end" => 0x23,
        "home" => 0x24,
        "left" => 0x25,
        "up" => 0x26,
        "right" => 0x27,
        "down" => 0x28,
        "ins" | "insert" => 0x2D,
        "del" | "delete" => 0x2E,
        _ => return None,
    })
}

fn title(name: &str) -> String {
    let mut chars = name.trim().chars();
    match chars.next() {
        Some(first) => first.to_uppercase().collect::<String>() + &chars.as_str().to_lowercase(),
        None => String::new(),
    }
}

fn key_code(name: &str) -> Result<(String, u32), HotkeyError> {
    let n = name.trim().to_lowercase();
    let mut chars = n.chars();
    if let (Some(c), None) = (chars.next(), chars.next()) {
        if c.is_ascii_alphabetic() {
            let up = c.to_ascii_uppercase();
            return Ok((up.to_string(), up as u32));
        }
        if c.is_ascii_digit() {
            return Ok((c.to_string(), c as u32));
        }
    }
    if let Some(rest) = n.strip_prefix('f') {
        if let Ok(num) = rest.parse::<u32>() {
            if rest.chars().all(|c| c.is_ascii_digit()) && (1..=24).contains(&num) {
                return Ok((format!("F{num}"), 0x70 + num - 1));
            }
        }
    }
    if let Some(vk) = named(&n) {
        return Ok((title(name), vk));
    }
    err(format!("unsupported key: {name:?}"))
}

fn parts(text: &str) -> Vec<String> {
    text.replace(' ', "").split('+').filter(|p| !p.is_empty()).map(String::from).collect()
}

/// `"Ctrl+Alt+N"` -> `(modifier flags, virtual-key code)`. Needs at least one modifier.
pub fn parse_combo(text: &str) -> Result<(u32, u32), HotkeyError> {
    let (mut mods, mut vk) = (0u32, None);
    for part in parts(text) {
        if let Some((_, flag)) = modifier(&part.to_lowercase()) {
            mods |= flag;
        } else if vk.is_none() {
            vk = Some(key_code(&part)?.1);
        } else {
            return err(format!("more than one key in {text:?}"));
        }
    }
    let Some(vk) = vk else { return err("no key") };
    if mods == 0 {
        return err("a shortcut needs Ctrl, Alt, Shift or Win");
    }
    Ok((mods, vk))
}

/// Canonical spelling: modifiers in Ctrl, Alt, Shift, Win order, key upper-cased.
pub fn normalize(text: &str) -> Result<String, HotkeyError> {
    parse_combo(text)?; // validate first
    let (mut names, mut key) = (Vec::new(), None);
    for part in parts(text) {
        match modifier(&part.to_lowercase()) {
            Some((name, _)) => names.push(name),
            None => key = Some(key_code(&part)?.0),
        }
    }
    let mut out: Vec<String> = ORDER.iter().filter(|m| names.contains(m)).map(|m| m.to_string()).collect();
    out.push(key.expect("validated above"));
    Ok(out.join("+"))
}

pub fn is_valid(text: &str) -> bool {
    parse_combo(text).is_ok()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_basic_combos() {
        assert_eq!(parse_combo("Ctrl+Alt+N").unwrap(), (MOD_CONTROL | MOD_ALT, 'N' as u32));
        assert_eq!(parse_combo("shift+ctrl+f5").unwrap(), (MOD_SHIFT | MOD_CONTROL, 0x74));
        assert_eq!(parse_combo("Win+Space").unwrap(), (MOD_WIN, 0x20));
        assert_eq!(parse_combo("Meta+9").unwrap(), (MOD_WIN, '9' as u32));
        assert_eq!(parse_combo("Ctrl+Left").unwrap().1, 0x25);
    }

    #[test]
    fn rejects_invalid_combos() {
        for bad in ["N", "Ctrl", "Ctrl+Alt", "Ctrl+N+M", "Ctrl+Nope", "Alt+F25", "", "+"] {
            assert!(parse_combo(bad).is_err(), "{bad:?}");
            assert!(!is_valid(bad));
        }
    }

    #[test]
    fn normalize_orders_modifiers_and_cases_the_key() {
        assert_eq!(normalize("alt + ctrl + n").unwrap(), "Ctrl+Alt+N");
        assert_eq!(normalize("Meta+Shift+f12").unwrap(), "Shift+Win+F12");
        assert_eq!(normalize("Ctrl+Alt+Space").unwrap(), "Ctrl+Alt+Space");
        assert!(normalize("N").is_err());
    }

    #[test]
    fn defaults_are_valid_and_unique() {
        let names: Vec<_> = DEFAULTS.iter().map(|(a, _)| *a).collect();
        assert_eq!(names, ACTIONS);
        let parsed: Vec<_> = DEFAULTS.iter().map(|(_, v)| parse_combo(v).unwrap()).collect();
        let unique: std::collections::HashSet<_> = parsed.iter().collect();
        assert_eq!(unique.len(), parsed.len());
    }
}
