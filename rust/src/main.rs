//! Eye Care entry point.
//!
//! `--background` starts hidden in the tray (this is what autostart uses).

fn main() -> iced::Result {
    let background = std::env::args().any(|a| a == "--background");
    eyecare::ui::app::run(background)
}
