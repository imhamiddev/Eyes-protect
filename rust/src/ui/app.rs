//! The iced application: windows, navigation, messages and the 1-second heartbeat.

use std::sync::Arc;
use std::time::Duration;

use iced::alignment::Vertical;
use iced::widget::{button, column, container, image, scrollable, Space};
use iced::{window, Element, Length, Size, Subscription, Task, Theme};

use crate::common::i18n;
use crate::engine::Engine;
use crate::platform;

use super::actions::{self, Setting};
use super::pages;
use super::theme::{self, Btn, Palette};
use super::widgets::*;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Page {
    Home,
    Stats,
    Care,
    Display,
    Exercises,
    Settings,
}

impl Page {
    pub const ALL: [Page; 6] = [Page::Home, Page::Stats, Page::Care, Page::Display, Page::Exercises, Page::Settings];

    pub fn nav_key(self) -> &'static str {
        match self {
            Page::Home => "nav.home",
            Page::Stats => "nav.stats",
            Page::Care => "nav.care",
            Page::Display => "nav.display",
            Page::Exercises => "nav.exercises",
            Page::Settings => "nav.settings",
        }
    }

    pub fn icon(self) -> &'static str {
        match self {
            Page::Home => "dashboard",
            Page::Stats => "chart",
            Page::Care => "eye",
            Page::Display => "moon",
            Page::Exercises => "activity",
            Page::Settings => "sliders",
        }
    }
}

#[derive(Debug, Clone)]
pub enum Message {
    /// One-second heartbeat.
    Tick,
    /// ~60 fps while the display fade runs.
    Frame,
    Nav(Page),
    OpenMain,
    WindowOpened(window::Id),
    WindowClosed(window::Id),
    TakeBreak,
    TogglePause,
    ToggleQuiet,
    ToggleNight(bool),
    Set(Setting),
    Quit,
}

pub struct App {
    pub engine: Engine,
    pub page: Page,
    pub main_window: Option<window::Id>,
    pub system_dark: bool,
}

const FONTS: [&[u8]; 6] = [
    include_bytes!("../../assets/Inter-Regular.ttf"),
    include_bytes!("../../assets/Inter-Medium.ttf"),
    include_bytes!("../../assets/Inter-SemiBold.ttf"),
    include_bytes!("../../assets/Vazirmatn-Regular.ttf"),
    include_bytes!("../../assets/Vazirmatn-Medium.ttf"),
    include_bytes!("../../assets/Vazirmatn-SemiBold.ttf"),
];
const LOGO: &[u8] = include_bytes!("../../assets/logo.png");

fn main_window_settings() -> window::Settings {
    window::Settings { size: Size::new(980.0, 660.0), min_size: Some(Size::new(820.0, 560.0)), ..Default::default() }
}

impl App {
    pub fn new(engine: Engine, background: bool) -> (Self, Task<Message>) {
        let mut app = App { engine, page: Page::Home, main_window: None, system_dark: true };
        app.engine.start();
        i18n::set_language(&app.engine.settings.general.language);
        let task = if background { Task::none() } else { app.open_main() };
        (app, task)
    }

    fn open_main(&mut self) -> Task<Message> {
        if let Some(id) = self.main_window {
            return window::gain_focus(id);
        }
        let (id, open) = window::open(main_window_settings());
        self.main_window = Some(id);
        open.map(Message::WindowOpened)
    }

    pub fn ctx(&self) -> Ctx {
        let g = &self.engine.settings.general;
        Ctx { p: theme::palette(&g.theme, self.system_dark), fa: g.language == "fa" }
    }

    pub fn title(&self, _id: window::Id) -> String {
        crate::APP_NAME.to_string()
    }

    pub fn theme(&self, _id: window::Id) -> Theme {
        if self.ctx().p.dark { Theme::Dark } else { Theme::Light }
    }

    pub fn update(&mut self, message: Message) -> Task<Message> {
        match message {
            Message::Tick => {
                self.engine.on_tick();
                self.handle_events();
            }
            Message::Frame => {
                self.engine.advance_tween(16.0);
            }
            Message::Nav(page) => self.page = page,
            Message::OpenMain => return self.open_main(),
            Message::WindowOpened(_) => {}
            Message::WindowClosed(id) => {
                if self.main_window == Some(id) {
                    self.main_window = None;
                }
            }
            Message::TakeBreak => {
                self.engine.start_break();
                self.handle_events();
            }
            Message::TogglePause => {
                let paused = !self.engine.paused;
                self.engine.set_paused(paused);
            }
            Message::ToggleQuiet => {
                self.engine.toggle_quiet(60.0);
            }
            Message::ToggleNight(_) => {
                self.engine.toggle_night_light();
            }
            Message::Set(change) => {
                if matches!(&change, Setting::Str(actions::StrKey::Language, _)) {
                    // applied below, then the global language follows the setting
                }
                let _ = actions::apply(&mut self.engine, &change);
                i18n::set_language(&self.engine.settings.general.language);
            }
            Message::Quit => {
                self.engine.shutdown();
                return iced::exit();
            }
        }
        Task::none()
    }

    /// React to what the engine reported (toasts, break screens... are added by later modules).
    fn handle_events(&mut self) {
        let _ = self.engine.drain_events();
    }

    pub fn subscription(&self) -> Subscription<Message> {
        let mut subs = vec![
            iced::time::every(Duration::from_secs(1)).map(|_| Message::Tick),
            window::close_events().map(Message::WindowClosed),
        ];
        if self.engine.is_animating() {
            subs.push(iced::time::every(Duration::from_millis(16)).map(|_| Message::Frame));
        }
        Subscription::batch(subs)
    }

    pub fn view(&self, _id: window::Id) -> Element<'_, Message> {
        let ctx = self.ctx();
        let p = ctx.p;
        let body: Element<'_, Message> = match self.page {
            Page::Home => pages::home::view(ctx, &self.engine),
            _ => label::<Message>(ctx, ctx.t(self.page.nav_key()), Txt::H2).into(),
        };
        let heading: Element<'_, Message> = column![
            label::<Message>(ctx, ctx.t(if self.page == Page::Home { "app" } else { self.page.nav_key() }), Txt::H1),
            if self.page == Page::Home { label::<Message>(ctx, ctx.t("tagline"), Txt::Muted) } else { label::<Message>(ctx, "", Txt::Muted) },
        ]
        .spacing(6)
        .into();
        let page = scrollable(container(column![heading, Space::new(0.0, 8.0), body].spacing(16)).padding([32.0, 36.0]).width(Length::Fill)).height(Length::Fill);
        let layout = h_row(ctx, vec![self.sidebar(ctx), container(page).width(Length::Fill).height(Length::Fill).into()]);
        container(layout).width(Length::Fill).height(Length::Fill).style(move |_| theme::root(p)).into()
    }

    fn sidebar(&self, ctx: Ctx) -> Element<'_, Message> {
        let p: Palette = ctx.p;
        let brand = h_row(
            ctx,
            vec![
                image(image::Handle::from_bytes(LOGO)).width(34).height(34).into(),
                label::<Message>(ctx, ctx.t("app"), Txt::Title).into(),
            ],
        )
        .spacing(10)
        .align_y(Vertical::Center);
        let mut nav = column![brand, Space::new(0.0, 14.0)].spacing(4);
        for page in Page::ALL {
            let active = self.page == page;
            let fg = if active { p.text } else { p.text_muted };
            let content = h_row(ctx, vec![icon(page.icon(), 18.0, if active { p.accent } else { fg }), label::<Message>(ctx, ctx.t(page.nav_key()), Txt::Body).color(fg).into()])
                .spacing(12)
                .align_y(Vertical::Center);
            nav = nav.push(
                button(container(content).center_y(Length::Fill))
                    .width(Length::Fill)
                    .height(40)
                    .padding([0.0, 14.0])
                    .style(move |_, st| theme::button_style(p, Btn::Nav { active }, st))
                    .on_press(Message::Nav(page)),
            );
        }
        let quick = container(
            h_row(
                ctx,
                vec![
                    container(label::<Message>(ctx, ctx.t("display.night"), Txt::Muted)).width(Length::Fill).into(),
                    toggle(ctx, self.engine.settings.night_light.enabled, Message::ToggleNight),
                ],
            )
            .align_y(Vertical::Center),
        )
        .padding([10.0, 14.0])
        .style(move |_| theme::card_flat(p));
        let col = column![nav, Space::new(0.0, Length::Fill), quick].padding([22.0, 16.0]);
        container(col).width(theme::SIDEBAR_W).height(Length::Fill).style(move |_| theme::sidebar(p)).into()
    }
}

/// Start the application (blocks until the user quits).
pub fn run(background: bool) -> iced::Result {
    let engine = Engine::load(platform::system());
    let mut state = Some(App::new(engine, background));
    let mut daemon = iced::daemon(App::title, App::update, App::view)
        .subscription(App::subscription)
        .theme(App::theme)
        .default_font(iced::Font::with_name("Inter"));
    for font in FONTS {
        daemon = daemon.font(font);
    }
    daemon.run_with(move || state.take().expect("run_with is called once"))
}

#[allow(dead_code)]
fn _assert_send(_: Arc<dyn platform::Platform>) {}
