//! Design tokens and widget styles: the single source of truth for the Eye Care look.

use iced::widget::{button, container};
use iced::{Background, Border, Color, Shadow, Vector};

pub const ACCENT: Color = Color::from_rgb(0xD2 as f32 / 255.0, 0xF3 as f32 / 255.0, 0x6B as f32 / 255.0);

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Palette {
    pub dark: bool,
    pub bg: Color,
    /// Secondary background / cards.
    pub surface: Color,
    pub surface_hover: Color,
    /// Inputs, segmented tracks.
    pub surface_raised: Color,
    pub border: Color,
    pub text: Color,
    pub text_muted: Color,
    pub text_faint: Color,
    pub accent: Color,
    pub on_accent: Color,
    pub accent_soft: Color,
    pub danger: Color,
    pub overlay: Color,
}

const fn rgb(hex: u32) -> Color {
    Color::from_rgb(((hex >> 16) & 0xFF) as f32 / 255.0, ((hex >> 8) & 0xFF) as f32 / 255.0, (hex & 0xFF) as f32 / 255.0)
}
const fn rgba(hex: u32, a: f32) -> Color {
    let c = rgb(hex);
    Color { a, ..c }
}

pub const DARK: Palette = Palette {
    dark: true,
    bg: rgb(0x111318),
    surface: rgb(0x1C2028),
    surface_hover: rgb(0x232833),
    surface_raised: rgb(0x171A21),
    border: rgba(0xFFFFFF, 0.07),
    text: rgb(0xFFFFFF),
    text_muted: rgb(0xA1A1AA),
    text_faint: rgb(0x6B6F7A),
    accent: ACCENT,
    on_accent: rgb(0x14180A),
    accent_soft: rgba(0xD2F36B, 0.14),
    danger: rgb(0xF08A7E),
    overlay: rgba(0x0A0C10, 0.94),
};

pub const LIGHT: Palette = Palette {
    dark: false,
    bg: rgb(0xF6F4EF),
    surface: rgb(0xFFFFFF),
    surface_hover: rgb(0xF0EDE6),
    surface_raised: rgb(0xEFECE5),
    border: rgba(0x1E1C14, 0.09),
    text: rgb(0x1B1D22),
    text_muted: rgb(0x6B6B72),
    text_faint: rgb(0x9A9AA0),
    accent: ACCENT,
    on_accent: rgb(0x1B2208),
    accent_soft: rgba(0x96B91E, 0.18),
    danger: rgb(0xC4574A),
    overlay: rgba(0xF6F4EF, 0.96),
};

pub fn palette(name: &str, system_dark: bool) -> Palette {
    match name {
        "light" => LIGHT,
        "system" if !system_dark => LIGHT,
        _ => DARK,
    }
}

// Spacing, radii and type scale (px)
pub const SP_XS: f32 = 4.0;
pub const SP_SM: f32 = 8.0;
pub const SP_MD: f32 = 12.0;
pub const SP_LG: f32 = 16.0;
pub const SP_XL: f32 = 24.0;
pub const R_SM: f32 = 8.0;
pub const R_MD: f32 = 12.0;
pub const R_LG: f32 = 16.0;
pub const F_CAPTION: f32 = 11.0;
pub const F_LABEL: f32 = 12.0;
pub const F_BODY: f32 = 13.0;
pub const F_TITLE: f32 = 15.0;
pub const F_H2: f32 = 20.0;
pub const F_H1: f32 = 28.0;
pub const F_DISPLAY: f32 = 64.0;
pub const SIDEBAR_W: f32 = 208.0;
pub const CONTROL_H: f32 = 36.0;
pub const BUTTON_H: f32 = 40.0;

fn border(color: Color, radius: f32) -> Border {
    Border { color, width: 1.0, radius: radius.into() }
}

pub fn root(p: Palette) -> container::Style {
    container::Style { background: Some(Background::Color(p.bg)), text_color: Some(p.text), ..Default::default() }
}

pub fn card(p: Palette) -> container::Style {
    container::Style {
        background: Some(Background::Color(p.surface)),
        border: border(p.border, R_LG),
        text_color: Some(p.text),
        shadow: if p.dark {
            Shadow::default()
        } else {
            Shadow { color: Color { a: 0.06, ..Color::BLACK }, offset: Vector::new(0.0, 4.0), blur_radius: 14.0 }
        },
    }
}

pub fn card_flat(p: Palette) -> container::Style {
    container::Style {
        background: Some(Background::Color(p.surface_raised)),
        border: Border { radius: R_MD.into(), ..Border::default() },
        text_color: Some(p.text),
        ..Default::default()
    }
}

pub fn sidebar(p: Palette) -> container::Style {
    container::Style {
        background: Some(Background::Color(p.bg)),
        border: Border { color: p.border, width: 0.0, radius: 0.0.into() },
        text_color: Some(p.text),
        ..Default::default()
    }
}

pub fn divider(p: Palette) -> container::Style {
    container::Style { background: Some(Background::Color(p.border)), ..Default::default() }
}

pub fn pill(p: Palette) -> container::Style {
    container::Style {
        background: Some(Background::Color(p.accent_soft)),
        border: Border { radius: 999.0.into(), ..Border::default() },
        text_color: Some(p.text),
        ..Default::default()
    }
}

pub fn overlay(p: Palette) -> container::Style {
    container::Style { background: Some(Background::Color(p.overlay)), text_color: Some(p.text), ..Default::default() }
}

pub fn toast(p: Palette) -> container::Style {
    container::Style {
        background: Some(Background::Color(p.surface)),
        border: border(p.border, R_LG),
        text_color: Some(p.text),
        shadow: Shadow { color: Color { a: 0.35, ..Color::BLACK }, offset: Vector::new(0.0, 8.0), blur_radius: 28.0 },
    }
}

fn mix(a: Color, b: Color, t: f32) -> Color {
    Color { r: a.r + (b.r - a.r) * t, g: a.g + (b.g - a.g) * t, b: a.b + (b.b - a.b) * t, a: a.a + (b.a - a.a) * t }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Btn {
    Primary,
    Secondary,
    Ghost,
    Nav { active: bool },
    Danger,
}

pub fn button_style(p: Palette, kind: Btn, status: button::Status) -> button::Style {
    let hovered = matches!(status, button::Status::Hovered);
    let pressed = matches!(status, button::Status::Pressed);
    let disabled = matches!(status, button::Status::Disabled);
    let radius = R_MD;
    let (bg, fg, brd) = match kind {
        Btn::Primary => {
            let base = p.accent;
            let bg = if pressed {
                rgb(0xC2E357)
            } else if hovered {
                rgb(0xDDF88A)
            } else {
                base
            };
            (Some(bg), p.on_accent, Border { radius: radius.into(), ..Border::default() })
        }
        Btn::Secondary => {
            let bg = if pressed {
                p.surface_raised
            } else if hovered {
                p.surface_hover
            } else {
                p.surface
            };
            (Some(bg), p.text, border(p.border, radius))
        }
        Btn::Ghost => {
            let bg = if hovered || pressed { Some(p.surface_hover) } else { None };
            (bg, if hovered { p.text } else { p.text_muted }, Border { radius: radius.into(), ..Border::default() })
        }
        Btn::Nav { active } => {
            let bg = if active || hovered { Some(p.surface) } else { None };
            (bg, if active || hovered { p.text } else { p.text_muted }, Border { radius: radius.into(), ..Border::default() })
        }
        Btn::Danger => {
            let bg = if hovered { p.surface_hover } else { p.surface };
            (Some(bg), p.danger, border(p.border, radius))
        }
    };
    let style = button::Style { background: bg.map(Background::Color), text_color: fg, border: brd, shadow: Shadow::default() };
    if disabled {
        button::Style {
            text_color: p.text_faint,
            background: Some(Background::Color(if kind == Btn::Primary { p.accent_soft } else { p.surface_raised })),
            ..style
        }
    } else {
        style
    }
}

/// Mix two colours (used for hover fades).
pub fn blend(a: Color, b: Color, t: f32) -> Color {
    mix(a, b, t)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn palettes_follow_the_selected_theme() {
        assert!(palette("dark", false).dark);
        assert!(!palette("light", true).dark);
        assert!(!palette("system", false).dark);
        assert!(palette("system", true).dark);
        assert!(palette("nonsense", false).dark);
    }

    #[test]
    fn accent_matches_the_brand_colour() {
        let c = ACCENT;
        assert_eq!(((c.r * 255.0).round() as u8, (c.g * 255.0).round() as u8, (c.b * 255.0).round() as u8), (0xD2, 0xF3, 0x6B));
    }
}
