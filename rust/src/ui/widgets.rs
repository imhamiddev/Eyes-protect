//! Reusable building blocks (cards, setting rows, toggles, ring, bar chart...).

use std::collections::HashMap;
use std::sync::OnceLock;

use iced::alignment::{Horizontal, Vertical};
use iced::font::{Family, Weight};
use iced::mouse;
use iced::widget::canvas::{self, Canvas, Frame, Geometry, Path, Stroke};
use iced::widget::{button, column, container, row, slider, svg, text, toggler, Space};
use iced::{Background, Border, Color, Element, Font, Length, Padding, Pixels, Point, Rectangle, Renderer, Size, Theme};

use super::icon_data::ICONS;
use super::theme::{self, Btn, Palette};

/// Per-frame rendering context: palette + language direction.
#[derive(Debug, Clone, Copy)]
pub struct Ctx {
    pub p: Palette,
    pub fa: bool,
}

impl Ctx {
    pub fn lang(&self) -> &'static str {
        if self.fa { "fa" } else { "en" }
    }

    /// Translate `key` into the UI language.
    pub fn t(&self, key: &str) -> String {
        crate::common::i18n::tr_in(self.lang(), key)
    }

    pub fn font(&self, weight: Weight) -> Font {
        Font { family: Family::Name(if self.fa { "Vazirmatn" } else { "Inter" }), weight, ..Font::DEFAULT }
    }
}

// -- text ---------------------------------------------------------------------------------
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
    text(content).size(size).color(color).font(ctx.font(weight))
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
        Some(h) => svg(h.clone())
            .width(size)
            .height(size)
            .style(move |_: &Theme, _| svg::Style { color: Some(color) })
            .into(),
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
    column![Space::new(0.0, 6.0), label::<M>(ctx, title.to_string(), Txt::Caption)].into()
}

/// Label (+ optional description) on one side, a control on the other.
pub fn setting_row<'a, M: Clone + 'a>(ctx: Ctx, title: &str, desc: &str, control: Element<'a, M>) -> Element<'a, M> {
    let mut text_col = column![label::<M>(ctx, title.to_string(), Txt::Body)].spacing(3);
    if !desc.is_empty() {
        text_col = text_col.push(label::<M>(ctx, desc.to_string(), Txt::Caption));
    }
    let r = h_row(
        ctx,
        vec![
            container(text_col).width(Length::Fill).into(),
            container(control).align_y(Vertical::Center).into(),
        ],
    )
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
    let b = button(content).padding(Padding::from([0.0, 18.0])).height(theme::BUTTON_H).style(move |_, st| theme::button_style(p, kind, st));
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
    items.push(text(text_.to_string()).size(theme::F_BODY).font(ctx.font(weight)).into());
    let content = h_row(ctx, items).spacing(8).align_y(Vertical::Center);
    styled_button(ctx, container(content).center_y(Length::Fill), kind, Some(msg))
}

/// Slider with a value read-out: `[----o----] 40`.
pub fn slider_row<'a, M: Clone + 'a>(ctx: Ctx, range: std::ops::RangeInclusive<i32>, value: i32, suffix: &str, msg: impl Fn(i32) -> M + 'a) -> Element<'a, M> {
    let p = ctx.p;
    let s = slider(range, value, msg).width(220).style(move |_: &Theme, status| {
        let hovered = matches!(status, slider::Status::Hovered | slider::Status::Dragged);
        slider::Style {
            rail: slider::Rail { backgrounds: (Background::Color(p.accent), Background::Color(p.surface_raised)), width: 6.0, border: Border { radius: 3.0.into(), ..Border::default() } },
            handle: slider::Handle {
                shape: slider::HandleShape::Circle { radius: 9.0 },
                background: Background::Color(if hovered { p.accent } else { p.text }),
                border_width: 3.0,
                border_color: p.surface,
            },
        }
    });
    let readout = container(label::<M>(ctx, format!("{value}{suffix}"), Txt::Muted)).width(52).align_x(if ctx.fa { Horizontal::Left } else { Horizontal::Right });
    h_row(ctx, vec![s.into(), readout.into()]).spacing(12).align_y(Vertical::Center).into()
}

/// Number stepper: `[-] 20 [+]`.
pub fn stepper<'a, M: Clone + 'a>(ctx: Ctx, value: i64, min: i64, max: i64, step: i64, msg: impl Fn(i64) -> M + Clone + 'a) -> Element<'a, M> {
    let p = ctx.p;
    let small = move |name: &str, target: i64, enabled: bool, m: M| {
        let b = button(container(icon(name, 16.0, if enabled { p.text } else { p.text_faint })).center(Length::Fill))
            .width(theme::CONTROL_H)
            .height(theme::CONTROL_H)
            .style(move |_, st| theme::button_style(p, Btn::Secondary, st));
        let _ = target;
        if enabled { b.on_press(m) } else { b }
    };
    let dec = (value - step).max(min);
    let inc = (value + step).min(max);
    let value_box = container(label::<M>(ctx, value.to_string(), Txt::Body)).width(56).center_x(Length::Fill).center_y(theme::CONTROL_H).style(move |_| theme::card_flat(p));
    row![
        small("minus", dec, value > min, msg(dec)),
        value_box,
        small("plus", inc, value < max, msg(inc)),
    ]
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
        let b = button(container(text(caption.clone()).size(theme::F_BODY).font(ctx.font(Weight::Medium))).center_y(Length::Fill))
            .padding(Padding::from([0.0, 14.0]))
            .height(theme::CONTROL_H - 6.0)
            .style(move |_, st| {
                let hovered = matches!(st, button::Status::Hovered);
                button::Style {
                    background: Some(Background::Color(if on { p.accent } else if hovered { p.surface_hover } else { Color::TRANSPARENT })),
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
    let head = h_row(ctx, vec![icon(icon_name, 18.0, p.accent), label::<M>(ctx, caption.to_string(), Txt::Muted).into()]).spacing(8).align_y(Vertical::Center);
    card_padded(ctx, Padding::from([18.0, 22.0]), column![head, label::<M>(ctx, value, Txt::H1)].spacing(10))
}

// -- ring ---------------------------------------------------------------------------------------
pub struct Ring {
    pub progress: f32,
    pub text: String,
    pub p: Palette,
    pub font: Font,
    pub thickness: f32,
}

impl<M> canvas::Program<M> for Ring {
    type State = ();

    fn draw(&self, _s: &(), renderer: &Renderer, _t: &Theme, bounds: Rectangle, _c: mouse::Cursor) -> Vec<Geometry> {
        let mut frame = Frame::new(renderer, bounds.size());
        let center = frame.center();
        let radius = bounds.width.min(bounds.height) / 2.0 - self.thickness;
        let track = Path::circle(center, radius);
        frame.stroke(&track, Stroke::default().with_width(self.thickness).with_color(self.p.surface_raised));
        let progress = self.progress.clamp(0.0, 1.0);
        if progress > 0.0 {
            let start = -std::f32::consts::FRAC_PI_2;
            let arc = Path::new(|b| {
                b.arc(canvas::path::Arc {
                    center,
                    radius,
                    start_angle: iced::Radians(start),
                    end_angle: iced::Radians(start + progress * std::f32::consts::TAU * 0.99999),
                });
            });
            frame.stroke(&arc, Stroke::default().with_width(self.thickness).with_color(self.p.accent).with_line_cap(canvas::LineCap::Round));
        }
        frame.fill_text(canvas::Text {
            content: self.text.clone(),
            position: center,
            color: self.p.text,
            size: Pixels(46.0),
            font: self.font,
            horizontal_alignment: Horizontal::Center,
            vertical_alignment: Vertical::Center,
            ..Default::default()
        });
        vec![frame.into_geometry()]
    }
}

pub fn ring<'a, M: 'a>(ctx: Ctx, size: f32, progress: f32, text: String) -> Element<'a, M> {
    Canvas::new(Ring { progress, text, p: ctx.p, font: ctx.font(Weight::Semibold), thickness: 11.0 }).width(size).height(size).into()
}

// -- bar chart ----------------------------------------------------------------------------------
pub struct BarChart {
    pub values: Vec<i64>,
    pub labels: Vec<String>,
    pub p: Palette,
    pub font: Font,
}

impl<M> canvas::Program<M> for BarChart {
    type State = ();

    fn draw(&self, _s: &(), renderer: &Renderer, _t: &Theme, bounds: Rectangle, _c: mouse::Cursor) -> Vec<Geometry> {
        let mut frame = Frame::new(renderer, bounds.size());
        let n = self.values.len().max(1) as f32;
        let label_h = 22.0;
        let top = 18.0;
        let chart_h = (bounds.height - label_h - top).max(10.0);
        let slot = bounds.width / n;
        let bar_w = (slot * 0.5).min(34.0);
        let max = self.values.iter().copied().max().unwrap_or(0).max(1) as f32;
        for (i, v) in self.values.iter().enumerate() {
            let x = slot * i as f32 + (slot - bar_w) / 2.0;
            let h = (chart_h * (*v as f32 / max)).max(if *v > 0 { 4.0 } else { 0.0 });
            let last = i + 1 == self.values.len();
            // track
            frame.fill(&Path::rounded_rectangle(Point::new(x, top), Size::new(bar_w, chart_h), 6.0.into()), self.p.surface_raised);
            if h > 0.0 {
                let color = if last { self.p.accent } else { Color { a: 0.55, ..self.p.accent } };
                frame.fill(&Path::rounded_rectangle(Point::new(x, top + chart_h - h), Size::new(bar_w, h), 6.0.into()), color);
                frame.fill_text(canvas::Text {
                    content: v.to_string(),
                    position: Point::new(x + bar_w / 2.0, top + chart_h - h - 4.0),
                    color: self.p.text_muted,
                    size: Pixels(11.0),
                    font: self.font,
                    horizontal_alignment: Horizontal::Center,
                    vertical_alignment: Vertical::Bottom,
                    ..Default::default()
                });
            }
            if let Some(l) = self.labels.get(i) {
                frame.fill_text(canvas::Text {
                    content: l.clone(),
                    position: Point::new(x + bar_w / 2.0, bounds.height - label_h / 2.0),
                    color: if last { self.p.text } else { self.p.text_faint },
                    size: Pixels(11.0),
                    font: self.font,
                    horizontal_alignment: Horizontal::Center,
                    vertical_alignment: Vertical::Center,
                    ..Default::default()
                });
            }
        }
        vec![frame.into_geometry()]
    }
}

pub fn bar_chart<'a, M: 'a>(ctx: Ctx, values: Vec<i64>, labels: Vec<String>, height: f32) -> Element<'a, M> {
    Canvas::new(BarChart { values, labels, p: ctx.p, font: ctx.font(Weight::Medium) }).width(Length::Fill).height(height).into()
}
