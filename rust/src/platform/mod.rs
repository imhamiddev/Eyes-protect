//! Everything that touches the operating system sits behind the [`Platform`] trait, so the
//! engine and the feature logic can be tested with a mock and run on any OS.

use std::path::Path;

use crate::common::colortemp::Ramp;
use crate::features::smartpause::Foreground;

pub mod hotkeys;
#[cfg(windows)]
pub mod windows;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Monitor {
    /// e.g. `\\.\DISPLAY1`
    pub device: String,
    /// Top-left corner on the virtual desktop.
    pub x: i32,
    pub y: i32,
    pub width: u32,
    pub height: u32,
    pub primary: bool,
}

pub trait Platform: Send + Sync {
    /// Seconds since the last keyboard or mouse input.
    fn idle_seconds(&self) -> f64;
    /// Apply a gamma ramp to the primary display. Returns success.
    fn set_gamma_ramp(&self, ramp: &Ramp) -> bool;
    /// Apply a gamma ramp to one specific display.
    fn set_monitor_gamma_ramp(&self, device: &str, ramp: &Ramp) -> bool;
    /// All attached displays.
    fn list_monitors(&self) -> Vec<Monitor>;
    /// `SHQueryUserNotificationState`: 2/3/4/7 = full-screen app, game or presentation,
    /// 6 = quiet time (Focus assist). `None` when unavailable.
    fn notification_state(&self) -> Option<i32>;
    /// Process id, lower-case exe name and title of the foreground window.
    fn foreground_info(&self) -> Option<Foreground>;
    /// Play a WAV asynchronously (returns immediately).
    fn play_sound_file(&self, path: &Path) -> bool;
    /// Add/remove the app from the current user's Run key.
    fn set_autostart(&self, enabled: bool, command: &str) -> bool;
    /// True if Windows apps are currently in light mode.
    fn system_uses_light_theme(&self) -> bool;
    /// Switch Windows apps + system UI between light and dark mode.
    fn set_system_light_theme(&self, light: bool) -> bool;
}

/// Harmless no-op platform: what every call degrades to off Windows.
#[derive(Debug, Default, Clone, Copy)]
pub struct NullPlatform;

impl Platform for NullPlatform {
    fn idle_seconds(&self) -> f64 {
        0.0
    }
    fn set_gamma_ramp(&self, _ramp: &Ramp) -> bool {
        false
    }
    fn set_monitor_gamma_ramp(&self, _device: &str, _ramp: &Ramp) -> bool {
        false
    }
    fn list_monitors(&self) -> Vec<Monitor> {
        vec![Monitor { device: "DISPLAY1".into(), x: 0, y: 0, width: 1920, height: 1080, primary: true }]
    }
    fn notification_state(&self) -> Option<i32> {
        None
    }
    fn foreground_info(&self) -> Option<Foreground> {
        None
    }
    fn play_sound_file(&self, _path: &Path) -> bool {
        false
    }
    fn set_autostart(&self, _enabled: bool, _command: &str) -> bool {
        false
    }
    fn system_uses_light_theme(&self) -> bool {
        false
    }
    fn set_system_light_theme(&self, _light: bool) -> bool {
        false
    }
}

/// Open a web page in the default browser (http/https only).
pub fn open_url(url: &str) -> bool {
    if !(url.starts_with("https://") || url.starts_with("http://")) {
        return false;
    }
    #[cfg(windows)]
    let result = std::process::Command::new("rundll32").args(["url.dll,FileProtocolHandler", url]).spawn();
    #[cfg(target_os = "macos")]
    let result = std::process::Command::new("open").arg(url).spawn();
    #[cfg(all(not(windows), not(target_os = "macos")))]
    let result = std::process::Command::new("xdg-open").arg(url).spawn();
    result.is_ok()
}

/// The platform implementation for the OS we are running on.
pub fn system() -> std::sync::Arc<dyn Platform> {
    #[cfg(windows)]
    {
        std::sync::Arc::new(windows::WindowsPlatform)
    }
    #[cfg(not(windows))]
    {
        std::sync::Arc::new(NullPlatform)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn open_url_refuses_anything_but_web_links() {
        assert!(!open_url("file:///etc/passwd"));
        assert!(!open_url("calc.exe"));
        assert!(!open_url("javascript:alert(1)"));
    }

    #[test]
    fn null_platform_is_inert() {
        let p = NullPlatform;
        assert_eq!(p.idle_seconds(), 0.0);
        assert!(!p.set_gamma_ramp(&crate::common::colortemp::identity_ramp()));
        assert!(!p.play_sound_file(Path::new("x.wav")));
        assert_eq!(p.list_monitors().len(), 1);
        assert_eq!(p.notification_state(), None);
        assert!(p.foreground_info().is_none());
    }
}
