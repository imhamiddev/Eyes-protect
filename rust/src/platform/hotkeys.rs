//! Global shortcuts: planning (pure, tested) and the service that owns the OS registration.

use crate::common::config::Hotkeys;
use crate::common::hotkeys::{parse_combo, ACTIONS, MOD_NOREPEAT};

/// One shortcut to register: `(action index, Win32 modifier flags, virtual-key code)`.
pub type Binding = (usize, u32, u32);

/// Shortcuts that should be active for `cfg` (none when disabled; invalid ones are skipped).
pub fn plan(cfg: &Hotkeys) -> Vec<Binding> {
    if !cfg.enabled {
        return Vec::new();
    }
    let combos = [&cfg.night_light, &cfg.break_now, &cfg.pause, &cfg.quiet];
    combos.iter().enumerate().filter_map(|(i, combo)| parse_combo(combo).ok().map(|(mods, vk)| (i, mods | MOD_NOREPEAT, vk))).collect()
}

pub fn action_name(index: usize) -> &'static str {
    ACTIONS.get(index).copied().unwrap_or("")
}

#[cfg(windows)]
pub use super::windows::HotkeyService;

/// Stand-in off Windows.
#[cfg(not(windows))]
pub struct HotkeyService;

#[cfg(not(windows))]
impl HotkeyService {
    /// Returns the service and the action indexes that could not be registered.
    pub fn start(_bindings: &[Binding]) -> (HotkeyService, Vec<usize>) {
        (HotkeyService, Vec::new())
    }
    /// Action indexes pressed since the last call.
    pub fn poll(&self) -> Vec<usize> {
        Vec::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::common::hotkeys::{MOD_ALT, MOD_CONTROL};

    #[test]
    fn plans_all_four_defaults() {
        let plan = plan(&Hotkeys::default());
        assert_eq!(plan.len(), 4);
        assert_eq!(plan[0], (0, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, 'N' as u32));
        assert_eq!(plan.iter().map(|b| b.0).collect::<Vec<_>>(), [0, 1, 2, 3]);
    }

    #[test]
    fn disabled_plans_nothing_and_bad_combos_are_skipped() {
        assert!(plan(&Hotkeys { enabled: false, ..Hotkeys::default() }).is_empty());
        let plan = plan(&Hotkeys { pause: "nonsense".into(), ..Hotkeys::default() });
        assert_eq!(plan.iter().map(|b| b.0).collect::<Vec<_>>(), [0, 1, 3]);
    }

    #[test]
    fn action_names() {
        assert_eq!(action_name(1), "break_now");
        assert_eq!(action_name(9), "");
    }
}
