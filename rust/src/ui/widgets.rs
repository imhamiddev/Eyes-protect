//! Reusable building blocks (cards, setting rows, toggles, ring, bar chart...).

use std::collections::HashMap;
use std::sync::OnceLock;

use iced::alignment::{Horizontal, Vertical};
use iced::font::{Family, Weight};
use iced::widget::{button, column, container, row, slider, stack, svg, text, toggler, Space};
use iced::{Background, Border, Color, Element, Font, Length, Padding, Renderer, Theme};

use super::icon_data::ICONS;
use super::theme::{self, Btn, Palette};

/// `column!` whose children are right-aligned for RTL languages.
macro_rules! rcol {
    ($ctx:expr; $($x:expr),+ $(,)?) => {
        iced::widget::column![$($x),+].align_x(if $ctx.fa { iced::alignment::Horizontal::Right } else { iced::alignment::Horizontal::Left })
    };
}
pub(crate) use rcol;

/// Per-frame rendering context: palette + language direction.
#[derive(Debug, Clone, Copy)]
pub struct Ctx {
    pub p: Palette,
    pub fa: bool,
}

impl Ctx {
    pub fn lang(&self) -> &'static str {
        if self.fa {
            "fa"
        } else {
            "en"
        }
    }

    /// Translate `key` into the UI language.
    pub fn t(&self, key: &str) -> String {
        crate::common::i18n::tr_in(self.lang(), key)
    }

    /// Like [`Ctx::font`], but text containing Arabic-script characters always uses Vazirmatn
    /// (e.g. the "فارسی" language button while the UI is in English).
    pub fn font_for(&self, content: &str, weight: Weight) -> Font {
        let arabic = content.chars().any(|c| ('\u{0600}'..='\u{06FF}').contains(&c));
        Ctx { fa: self.fa || arabic, ..*self }.font(weight)
    }

    pub fn font(&self, weight: Weight) -> Font {
        Font { family: Family::Name(if self.fa { "Vazirmatn" } else { "Inter" }), weight, ..Font::DEFAULT }
    }
}

// -- text ---------------------------------------------------------------------------------
/// True if `content` contains Arabic-script characters (Persian).
pub fn is_rtl_text(content: &str) -> bool {
    content.chars().any(|c| ('\u{0600}'..='\u{06FF}').contains(&c))
}

/// Rough rendered width of `content` at `size` px, used where a widget must shrink to its text.
/// (iced 0.13 draws right-to-left text outside the bounds of a shrink-wrapped widget, so such
/// widgets get an explicit, slightly generous width and centre the text inside it.)
pub fn estimate_width(content: &str, size: f32) -> f32 {
    content.chars().count() as f32 * size * 0.46 + 4.0
}

/// A text widget with the right font/shaping and, for Persian, a width that renders correctly.
pub fn shrink_text<'a>(ctx: Ctx, content: &str, size: f32, weight: Weight) -> iced::widget::Text<'a, Theme, Renderer> {
    let t = text(content.to_string()).size(size).font(ctx.font_for(content, weight)).shaping(text::Shaping::Advanced);
    if is_rtl_text(content) {
        t.width(estimate_width(content, size))
    } else {
        t
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Txt {
    H1,
    H2,
    Title,
    Body,
    Muted,
    Caption,
    Accent,
    Display,
}

pub fn label<'a, M: 'a>(ctx: Ctx, content: impl text::IntoFragment<'a>, kind: Txt) -> iced::widget::Text<'a, Theme, Renderer> {
    let p = ctx.p;
    let (size, color, weight) = match kind {
        Txt::H1 => (theme::F_H1, p.text, Weight::Semibold),
        Txt::H2 => (theme::F_H2, p.text, Weight::Semibold),
        Txt::Title => (theme::F_TITLE, p.text, Weight::Semibold),
        Txt::Body => (theme::F_BODY, p.text, Weight::Normal),
        Txt::Muted => (theme::F_BODY, p.text_muted, Weight::Normal),
        Txt::Caption => (theme::F_CAPTION, p.text_faint, Weight::Medium),
        Txt::Accent => (theme::F_BODY, p.accent, Weight::Normal),
        Txt::Display => (theme::F_DISPLAY, p.text, Weight::Semibold),
    };
    let content = content.into_fragment();
    let content_copy = content.to_string();
    let font = ctx.font_for(&content, weight);
    let rtl = is_rtl_text(&content);
    let t = text(content).size(size).color(color).font(font).shaping(text::Shaping::Advanced);
    if rtl {
        t.width(estimate_width(&content_copy, size))
    } else {
        t
    }
}

/// Like [`label`], centred (for use inside a centred container).
pub fn label_center<'a, M: 'a>(ctx: Ctx, content: impl text::IntoFragment<'a>, kind: Txt) -> iced::widget::Text<'a, Theme, Renderer> {
    let content = content.into_fragment();
    let rtl = is_rtl_text(&content);
    let t = label::<M>(ctx, content, kind);
    if rtl {
        t
    } else {
        t.width(Length::Fill).align_x(Horizontal::Center)
    }
}

// -- icons --------------------------------------------------------------------------------
fn handles() -> &'static HashMap<&'static str, svg::Handle> {
    static CELL: OnceLock<HashMap<&'static str, svg::Handle>> = OnceLock::new();
    CELL.get_or_init(|| {
        ICONS
            .iter()
            .map(|(name, body)| {
                let markup = format!(
                    r##"<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{body}</svg>"##
                );
                (*name, svg::Handle::from_memory(markup.into_bytes()))
            })
            .collect()
    })
}

pub fn icon<'a, M: 'a>(name: &str, size: f32, color: Color) -> Element<'a, M> {
    match handles().get(name) {
        Some(h) => svg(h.clone()).width(size).height(size).style(move |_: &Theme, _| svg::Style { color: Some(color) }).into(),
        None => Space::new(size, size).into(),
    }
}

// -- layout helpers -------------------------------------------------------------------------
/// A row whose children are laid out right-to-left for RTL languages.
pub fn h_row<'a, M: 'a>(ctx: Ctx, mut items: Vec<Element<'a, M>>) -> iced::widget::Row<'a, M> {
    if ctx.fa {
        items.reverse();
    }
    row(items)
}

pub fn card<'a, M: 'a>(ctx: Ctx, content: impl Into<Element<'a, M>>) -> Element<'a, M> {
    let p = ctx.p;
    container(content).padding(Padding::from([10.0, 22.0])).width(Length::Fill).style(move |_| theme::card(p)).into()
}

pub fn card_padded<'a, M: 'a>(ctx: Ctx, pad: impl Into<Padding>, content: impl Into<Element<'a, M>>) -> Element<'a, M> {
    let p = ctx.p;
    container(content).padding(pad).width(Length::Fill).style(move |_| theme::card(p)).into()
}

pub fn divider<'a, M: 'a>(ctx: Ctx) -> Element<'a, M> {
    let p = ctx.p;
    container(Space::new(Length::Fill, 1.0)).height(1.0).style(move |_| theme::divider(p)).into()
}

/// A card made of rows separated by dividers.
pub fn card_rows<'a, M: 'a>(ctx: Ctx, rows: Vec<Element<'a, M>>) -> Element<'a, M> {
    let mut col = column![].spacing(0);
    for (i, r) in rows.into_iter().enumerate() {
        if i > 0 {
            col = col.push(divider(ctx));
        }
        col = col.push(r);
    }
    card(ctx, col)
}

pub fn section<'a, M: 'a>(ctx: Ctx, title: &str) -> Element<'a, M> {
    rcol![ctx; Space::new(0.0, 6.0), label::<M>(ctx, title.to_string(), Txt::Caption)].into()
}

/// Label (+ optional description) on one side, a control on the other.
pub fn setting_row<'a, M: Clone + 'a>(ctx: Ctx, title: &str, desc: &str, control: Element<'a, M>) -> Element<'a, M> {
    let mut text_col = rcol![ctx; label::<M>(ctx, title.to_string(), Txt::Body)].spacing(3);
    if !desc.is_empty() {
        text_col = text_col.push(label::<M>(ctx, desc.to_string(), Txt::Caption));
    }
    let r = h_row(ctx, vec![container(text_col).width(Length::Fill).into(), container(control).align_y(Vertical::Center).into()])
        .spacing(16)
        .align_y(Vertical::Center);
    container(r).padding(Padding::from([14.0, 0.0])).width(Length::Fill).into()
}

// -- controls -------------------------------------------------------------------------------
pub fn toggle<'a, M: 'a>(ctx: Ctx, on: bool, msg: impl Fn(bool) -> M + 'a) -> Element<'a, M> {
    let p = ctx.p;
    toggler(on)
        .on_toggle(msg)
        .size(24.0)
        .style(move |_: &Theme, status| {
            let active = matches!(status, toggler::Status::Active { is_toggled: true } | toggler::Status::Hovered { is_toggled: true });
            toggler::Style {
                background: if active { p.accent } else { p.surface_raised },
                background_border_width: 1.0,
                background_border_color: if active { p.accent } else { p.border },
                foreground: if active { p.on_accent } else { p.text_muted },
                foreground_border_width: 0.0,
                foreground_border_color: Color::TRANSPARENT,
            }
        })
        .into()
}

pub fn styled_button<'a, M: Clone + 'a>(ctx: Ctx, content: impl Into<Element<'a, M>>, kind: Btn, msg: Option<M>) -> button::Button<'a, M> {
    let p = ctx.p;
    let b =
        button(content).padding(Padding::from([0.0, 18.0])).height(theme::BUTTON_H).style(move |_, st| theme::button_style(p, kind, st));
    match msg {
        Some(m) => b.on_press(m),
        None => b,
    }
}

/// A button with an optional leading icon.
pub fn action_button<'a, M: Clone + 'a>(ctx: Ctx, icon_name: Option<&str>, text_: &str, kind: Btn, msg: M) -> button::Button<'a, M> {
    let p = ctx.p;
    let fg = match kind {
        Btn::Primary => p.on_accent,
        Btn::Danger => p.danger,
        Btn::Ghost => p.text_muted,
        _ => p.text,
    };
    let weight = if kind == Btn::Primary { Weight::Semibold } else { Weight::Medium };
    let mut items: Vec<Element<'a, M>> = Vec::new();
    if let Some(name) = icon_name {
        items.push(icon(name, 18.0, fg));
    }
    items.push(shrink_text(ctx, text_, theme::F_BODY, weight).wrapping(text::Wrapping::None).into());
    let content = h_row(ctx, items).spacing(8).align_y(Vertical::Center);
    styled_button(ctx, container(content).center_y(Length::Fill), kind, Some(msg))
}

/// Slider with a value read-out: `[----o----] 40`.
pub fn slider_row<'a, M: Clone + 'a>(
    ctx: Ctx,
    range: std::ops::RangeInclusive<i32>,
    value: i32,
    suffix: &str,
    msg: impl Fn(i32) -> M + 'a,
) -> Element<'a, M> {
    let p = ctx.p;
    let s = slider(range, value, msg).width(220).style(move |_: &Theme, status| {
        let hovered = matches!(status, slider::Status::Hovered | slider::Status::Dragged);
        slider::Style {
            rail: slider::Rail {
                backgrounds: (Background::Color(p.accent), Background::Color(p.surface_raised)),
                width: 6.0,
                border: Border { radius: 3.0.into(), ..Border::default() },
            },
            handle: slider::Handle {
                shape: slider::HandleShape::Circle { radius: 9.0 },
                background: Background::Color(if hovered { p.accent } else { p.text }),
                border_width: 3.0,
                border_color: p.surface,
            },
        }
    });
    let readout = container(label::<M>(ctx, format!("{value}{suffix}"), Txt::Muted)).width(52).align_x(if ctx.fa {
        Horizontal::Left
    } else {
        Horizontal::Right
    });
    h_row(ctx, vec![s.into(), readout.into()]).spacing(12).align_y(Vertical::Center).into()
}

/// Number stepper: `[-] 20 [+]`.
pub fn stepper<'a, M: Clone + 'a>(
    ctx: Ctx,
    value: i64,
    min: i64,
    max: i64,
    step: i64,
    msg: impl Fn(i64) -> M + Clone + 'a,
) -> Element<'a, M> {
    let p = ctx.p;
    let small = move |name: &str, target: i64, enabled: bool, m: M| {
        let b = button(container(icon(name, 16.0, if enabled { p.text } else { p.text_faint })).center(Length::Fill))
            .width(theme::CONTROL_H)
            .height(theme::CONTROL_H)
            .style(move |_, st| theme::button_style(p, Btn::Secondary, st));
        let _ = target;
        if enabled {
            b.on_press(m)
        } else {
            b
        }
    };
    let dec = (value - step).max(min);
    let inc = (value + step).min(max);
    let value_box = container(label::<M>(ctx, value.to_string(), Txt::Body))
        .width(56)
        .center_x(56)
        .center_y(theme::CONTROL_H)
        .style(move |_| theme::card_flat(p));
    row![small("minus", dec, value > min, msg(dec)), value_box, small("plus", inc, value < max, msg(inc)),]
        .spacing(6)
        .align_y(Vertical::Center)
        .into()
}

/// Segmented control: one option is active.
pub fn segmented<'a, M: Clone + 'a>(ctx: Ctx, options: &[(&str, String)], active: &str, msg: impl Fn(String) -> M) -> Element<'a, M> {
    let p = ctx.p;
    let mut items: Vec<Element<'a, M>> = Vec::new();
    for (key, caption) in options {
        let on = *key == active;
        let b = button(container(shrink_text(ctx, caption, theme::F_BODY, Weight::Medium)).center_y(Length::Fill))
            .padding(Padding::from([0.0, 14.0]))
            .height(theme::CONTROL_H - 6.0)
            .style(move |_, st| {
                let hovered = matches!(st, button::Status::Hovered);
                button::Style {
                    background: Some(Background::Color(if on {
                        p.accent
                    } else if hovered {
                        p.surface_hover
                    } else {
                        Color::TRANSPARENT
                    })),
                    text_color: if on { p.on_accent } else { p.text_muted },
                    border: Border { radius: 9.0.into(), ..Border::default() },
                    ..Default::default()
                }
            })
            .on_press(msg(key.to_string()));
        items.push(b.into());
    }
    container(h_row(ctx, items).spacing(2)).padding(3).style(move |_| theme::card_flat(p)).into()
}

// -- stat card --------------------------------------------------------------------------------
pub fn stat_card<'a, M: 'a>(ctx: Ctx, icon_name: &str, caption: &str, value: String) -> Element<'a, M> {
    let p = ctx.p;
    let head = h_row(ctx, vec![icon(icon_name, 18.0, p.accent), label::<M>(ctx, caption.to_string(), Txt::Muted).into()])
        .spacing(8)
        .align_y(Vertical::Center);
    card_padded(ctx, Padding::from([18.0, 22.0]), rcol![ctx; head, label::<M>(ctx, value, Txt::H1)].spacing(10))
}

// -- ring ---------------------------------------------------------------------------------------
// Drawn as SVG + text: custom canvas geometry was not reliably visible under the software renderer.
fn hex(c: Color) -> String {
    format!("#{:02X}{:02X}{:02X}", (c.r * 255.0).round() as u8, (c.g * 255.0).round() as u8, (c.b * 255.0).round() as u8)
}

/// SVG markup of a progress ring (`size` px, stroke `thickness`), progress clamped to 0..=1.
pub fn ring_svg(size: f32, thickness: f32, progress: f32, track: Color, fill: Color) -> String {
    let r = size / 2.0 - thickness;
    let c = std::f32::consts::TAU * r;
    let p = progress.clamp(0.0, 1.0);
    let arc = if p > 0.0 {
        format!(
            r#"<circle cx="{h}" cy="{h}" r="{r}" fill="none" stroke="{f}" stroke-width="{t}" stroke-linecap="round" stroke-dasharray="{d} {c}" transform="rotate(-90 {h} {h})"/>"#,
            h = size / 2.0,
            r = r,
            f = hex(fill),
            t = thickness,
            d = (c * p).max(0.01),
            c = c
        )
    } else {
        String::new()
    };
    format!(
        r#"<svg xmlns="http://www.w3.org/2000/svg" width="{s}" height="{s}" viewBox="0 0 {s} {s}"><circle cx="{h}" cy="{h}" r="{r}" fill="none" stroke="{tr}" stroke-width="{t}"/>{arc}</svg>"#,
        s = size,
        h = size / 2.0,
        r = r,
        tr = hex(track),
        t = thickness,
        arc = arc
    )
}

pub fn ring<'a, M: 'a>(ctx: Ctx, size: f32, progress: f32, text_: String) -> Element<'a, M> {
    let markup = ring_svg(size, 11.0, progress, ctx.p.surface_raised, ctx.p.accent);
    let handle = svg::Handle::from_memory(markup.into_bytes());
    let center = container(text(text_).size(46).color(ctx.p.text).font(ctx.font(Weight::Semibold))).center(Length::Fill);
    stack![svg(handle).width(size).height(size), center].width(size).height(size).into()
}

// -- bar chart ----------------------------------------------------------------------------------
/// Height in px of a bar: proportional to `value`, at least 4 px when non-zero.
pub fn bar_height(value: i64, max: i64, full: f32) -> f32 {
    if value <= 0 || max <= 0 {
        return 0.0;
    }
    (full * value as f32 / max as f32).max(4.0)
}

pub fn bar_chart<'a, M: 'a>(ctx: Ctx, values: Vec<i64>, labels: Vec<String>, height: f32) -> Element<'a, M> {
    let p = ctx.p;
    let max = values.iter().copied().max().unwrap_or(0).max(1);
    let chart_h = (height - 44.0).max(20.0);
    let last = values.len().saturating_sub(1);
    let mut cols: Vec<Element<'a, M>> = Vec::new();
    for (i, v) in values.iter().enumerate() {
        let h = bar_height(*v, max, chart_h);
        let fill = if i == last { p.accent } else { Color { a: 0.55, ..p.accent } };
        let bar = container(Space::new(Length::Fill, h)).width(Length::Fill).style(move |_| container::Style {
            background: Some(Background::Color(fill)),
            border: Border { radius: 6.0.into(), ..Border::default() },
            ..Default::default()
        });
        let track = container(bar).width(26).height(chart_h).align_y(Vertical::Bottom).style(move |_| theme::card_flat(p));
        let value_txt: Element<'a, M> =
            if *v > 0 { label::<M>(ctx, v.to_string(), Txt::Caption).into() } else { Space::new(0.0, 14.0).into() };
        let name = labels.get(i).cloned().unwrap_or_default();
        let name_txt = shrink_text(ctx, &name, 11.0, Weight::Medium).color(if i == last { p.text } else { p.text_faint });
        cols.push(
            container(rcol![ctx; value_txt, track, name_txt].spacing(4).align_x(Horizontal::Center))
                .width(Length::Fill)
                .center_x(Length::Fill)
                .into(),
        );
    }
    h_row(ctx, cols).width(Length::Fill).height(height).into()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn bar_heights() {
        assert_eq!(bar_height(0, 10, 100.0), 0.0);
        assert_eq!(bar_height(10, 10, 100.0), 100.0);
        assert_eq!(bar_height(5, 10, 100.0), 50.0);
        assert_eq!(bar_height(1, 1000, 100.0), 4.0); // tiny values stay visible
    }

    #[test]
    fn ring_svg_has_track_and_arc_only_with_progress() {
        let t = Color::from_rgb(0.1, 0.1, 0.1);
        let a = Color::from_rgb(1.0, 0.0, 0.0);
        assert_eq!(ring_svg(100.0, 10.0, 0.0, t, a).matches("<circle").count(), 1);
        let s = ring_svg(100.0, 10.0, 0.5, t, a);
        assert_eq!(s.matches("<circle").count(), 2);
        assert!(s.contains("#FF0000") && s.contains("stroke-dasharray"));
        assert_eq!(ring_svg(100.0, 10.0, 7.0, t, a).matches("<circle").count(), 2);
        // clamped
    }
}
