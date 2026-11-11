//! Eye Care entry point.
//!
//! `--background` starts hidden in the tray (this is what autostart uses).
#![cfg_attr(all(windows, not(debug_assertions)), windows_subsystem = "windows")]

/// Name the installer waits on (`AppMutex` in `installer/*.iss`).
#[cfg(windows)]
const SINGLE_INSTANCE_MUTEX: &str = "EyeCareSingleInstanceMutex";

fn main() -> iced::Result {
    #[cfg(windows)]
    if eyecare::platform::windows::claim_single_instance(SINGLE_INSTANCE_MUTEX) == eyecare::platform::windows::Instance::AlreadyRunning {
        return Ok(()); // the running copy keeps the tray icon; nothing to do
    }
    let background = std::env::args().any(|a| a == "--background");
    eyecare::ui::app::run(background)
}
