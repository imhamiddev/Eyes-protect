//! System tray icon and menu (Windows). Other platforms get an inert stand-in so the rest of the
//! app does not need `cfg` everywhere.

/// What the user asked for through the tray.
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum TrayCommand {
    Open,
    Break,
    TogglePause,
    ToggleNight,
    /// Quiet mode for N minutes; `None` = until switched off; `Some(0.0)` = end it.
    Quiet(Option<f64>),
    Quit,
}

/// Menu ids <-> commands (kept separate from the OS types so they can be unit tested).
pub fn command_for_id(id: &str) -> Option<TrayCommand> {
    Some(match id {
        "open" => TrayCommand::Open,
        "break" => TrayCommand::Break,
        "pause" => TrayCommand::TogglePause,
        "night" => TrayCommand::ToggleNight,
        "quiet30" => TrayCommand::Quiet(Some(30.0)),
        "quiet60" => TrayCommand::Quiet(Some(60.0)),
        "quiet120" => TrayCommand::Quiet(Some(120.0)),
        "quiet240" => TrayCommand::Quiet(Some(240.0)),
        "quietforever" => TrayCommand::Quiet(None),
        "quietoff" => TrayCommand::Quiet(Some(0.0)),
        "quit" => TrayCommand::Quit,
        _ => return None,
    })
}

#[cfg(windows)]
mod imp {
    use super::{command_for_id, TrayCommand};
    use crate::common::i18n::tr_in;
    use tray_icon::menu::{CheckMenuItem, Menu, MenuEvent, MenuItem, PredefinedMenuItem, Submenu};
    use tray_icon::{Icon, MouseButton, MouseButtonState, TrayIcon, TrayIconBuilder, TrayIconEvent};

    pub struct Tray {
        _icon: TrayIcon,
        open: MenuItem,
        brk: MenuItem,
        pause: MenuItem,
        night: CheckMenuItem,
        quiet: Submenu,
        quiet_items: Vec<(MenuItem, &'static str)>,
        quit: MenuItem,
        last: (String, bool, bool, bool),
    }

    fn load_icon() -> Option<Icon> {
        let img = image::load_from_memory(include_bytes!("../../assets/logo.png")).ok()?.into_rgba8();
        let (w, h) = img.dimensions();
        Icon::from_rgba(img.into_raw(), w, h).ok()
    }

    impl Tray {
        pub fn new(lang: &str) -> Option<Tray> {
            let t = |k: &str| tr_in(lang, k);
            let menu = Menu::new();
            let open = MenuItem::with_id("open", t("tray.open"), true, None);
            let brk = MenuItem::with_id("break", t("tray.break"), true, None);
            let pause = MenuItem::with_id("pause", t("tray.pause"), true, None);
            let night = CheckMenuItem::with_id("night", t("tray.night"), true, false, None);
            let quiet = Submenu::new(t("tray.quiet"), true);
            let spec: [(&'static str, &'static str); 5] = [
                ("quiet30", "quiet.30"),
                ("quiet60", "quiet.60"),
                ("quiet120", "quiet.120"),
                ("quiet240", "quiet.240"),
                ("quietforever", "quiet.forever"),
            ];
            let mut quiet_items = Vec::new();
            for (id, key) in spec {
                let item = MenuItem::with_id(id, t(key), true, None);
                quiet.append(&item).ok()?;
                quiet_items.push((item, key));
            }
            let end = MenuItem::with_id("quietoff", t("tray.quiet_end"), true, None);
            quiet.append(&PredefinedMenuItem::separator()).ok()?;
            quiet.append(&end).ok()?;
            quiet_items.push((end, "tray.quiet_end"));
            let quit = MenuItem::with_id("quit", t("tray.quit"), true, None);
            for item in [&open as &dyn tray_icon::menu::IsMenuItem, &brk, &pause, &night, &quiet, &PredefinedMenuItem::separator(), &quit] {
                menu.append(item).ok()?;
            }
            let mut builder = TrayIconBuilder::new().with_menu(Box::new(menu)).with_tooltip(crate::APP_NAME).with_menu_on_left_click(false);
            if let Some(icon) = load_icon() {
                builder = builder.with_icon(icon);
            }
            let icon = builder.build().ok()?;
            Some(Tray { _icon: icon, open, brk, pause, night, quiet, quiet_items, quit, last: (lang.to_string(), false, false, true) })
        }

        /// Update labels/check state when the language, pause or night-light state changed.
        pub fn sync(&mut self, lang: &str, paused: bool, night_on: bool) {
            let state = (lang.to_string(), paused, night_on, false);
            if (&state.0, state.1, state.2) == (&self.last.0, self.last.1, self.last.2) && !self.last.3 {
                return;
            }
            let t = |k: &str| tr_in(lang, k);
            self.open.set_text(t("tray.open"));
            self.brk.set_text(t("tray.break"));
            self.pause.set_text(t(if paused { "tray.resume" } else { "tray.pause" }));
            self.night.set_text(t("tray.night"));
            self.night.set_checked(night_on);
            self.quiet.set_text(t("tray.quiet"));
            for (item, key) in &self.quiet_items {
                item.set_text(t(key));
            }
            self.quit.set_text(t("tray.quit"));
            self.last = state;
        }

        /// Commands the user triggered since the last call.
        pub fn poll(&self) -> Vec<TrayCommand> {
            let mut out = Vec::new();
            while let Ok(ev) = MenuEvent::receiver().try_recv() {
                if let Some(cmd) = command_for_id(&ev.id.0) {
                    out.push(cmd);
                }
            }
            while let Ok(ev) = TrayIconEvent::receiver().try_recv() {
                if let TrayIconEvent::Click { button: MouseButton::Left, button_state: MouseButtonState::Up, .. } = ev {
                    out.push(TrayCommand::Open);
                }
            }
            out
        }
    }
}

#[cfg(not(windows))]
mod imp {
    use super::TrayCommand;

    /// Stand-in: there is no tray off Windows.
    pub struct Tray;

    impl Tray {
        pub fn new(_lang: &str) -> Option<Tray> {
            None
        }
        pub fn sync(&mut self, _lang: &str, _paused: bool, _night_on: bool) {}
        pub fn poll(&self) -> Vec<TrayCommand> {
            Vec::new()
        }
    }
}

pub use imp::Tray;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn menu_ids_map_to_commands() {
        assert_eq!(command_for_id("open"), Some(TrayCommand::Open));
        assert_eq!(command_for_id("quiet60"), Some(TrayCommand::Quiet(Some(60.0))));
        assert_eq!(command_for_id("quietforever"), Some(TrayCommand::Quiet(None)));
        assert_eq!(command_for_id("quietoff"), Some(TrayCommand::Quiet(Some(0.0))));
        assert_eq!(command_for_id("quit"), Some(TrayCommand::Quit));
        assert_eq!(command_for_id("nope"), None);
    }

    #[test]
    fn every_tray_label_is_translated() {
        for key in [
            "tray.open",
            "tray.break",
            "tray.pause",
            "tray.resume",
            "tray.night",
            "tray.quiet",
            "tray.quiet_end",
            "tray.quit",
            "quiet.30",
            "quiet.60",
            "quiet.120",
            "quiet.240",
            "quiet.forever",
        ] {
            for lang in ["en", "fa"] {
                assert_ne!(crate::common::i18n::tr_in(lang, key), key, "{lang} {key}");
            }
        }
    }
}
