//! The iced application: windows, navigation, messages and the 1-second heartbeat.

use std::sync::Arc;
use std::time::Duration;

use crate::engine::EngineEvent;
use iced::alignment::Vertical;
use iced::widget::{button, container, image, scrollable, Space};
use iced::{window, Element, Length, Point, Size, Subscription, Task, Theme};

use crate::common::i18n;
use crate::engine::Engine;
use crate::platform;

use super::actions::{self, Setting};
use super::overlay::{self, ToastKind};
use super::pages;
use super::pages::exercises::Run;
use super::theme::{self, Btn, Palette};
use super::tray::{Tray, TrayCommand};
use super::widgets::*;
use crate::platform::hotkeys::{self as hk, HotkeyService};
use crate::updates::{auto_check_due, GithubBackend, UpdateManager};

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
    /// Text typed into an `HH:MM` box.
    TimeDraft(actions::StrKey, String),
    StartExercise(&'static str),
    NextExerciseStep,
    StopExercise,
    CheckUpdates,
    DownloadUpdate,
    InstallUpdate,
    OpenReleasePage,
    PlaySample,
    OpenAuthor,
    /// Poll the tray icon for clicks (~7 times a second).
    TrayPoll,
    SetQuiet(Option<f64>),
    SkipBreak,
    ToastStartBreak,
    ToastSnooze,
    ToastDrank,
    ToastShowStretch,
    DismissToast,
    Quit,
}

pub struct App {
    pub engine: Engine,
    pub page: Page,
    pub main_window: Option<window::Id>,
    pub system_dark: bool,
    /// Half-typed time fields (invalid text stays here until it parses).
    pub drafts: std::collections::HashMap<String, String>,
    pub hk_errors: std::collections::HashMap<usize, String>,
    pub exercise: Option<Run>,
    pub updates: UpdateManager,
    pub tray: Option<Tray>,
    /// Break screens (one window per monitor).
    pub break_windows: Vec<window::Id>,
    /// The reminder toast currently on screen: (window, what, seconds shown).
    pub toast: Option<(window::Id, ToastKind, u32)>,
    pub hotkeys: Option<HotkeyService>,
    /// The settings the registered shortcuts were built from (to detect changes).
    hotkey_plan: Vec<hk::Binding>,
    /// Shortcuts another program already owns.
    pub hk_conflicts: std::collections::HashSet<usize>,
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
        let mut app = App {
            engine,
            page: Page::Home,
            main_window: None,
            system_dark: true,
            drafts: Default::default(),
            hk_errors: Default::default(),
            exercise: None,
            updates: UpdateManager::new(Arc::new(GithubBackend), crate::VERSION),
            tray: None,
            break_windows: Vec::new(),
            toast: None,
            hotkeys: None,
            hotkey_plan: Vec::new(),
            hk_conflicts: Default::default(),
        };
        app.engine.start();
        i18n::set_language(&app.engine.settings.general.language);
        app.tray = Tray::new(&app.engine.settings.general.language);
        app.reload_hotkeys();
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
        if self.ctx().p.dark {
            Theme::Dark
        } else {
            Theme::Light
        }
    }

    pub fn update(&mut self, message: Message) -> Task<Message> {
        match message {
            Message::Tick => {
                self.engine.on_tick();
                let mut tasks = vec![self.handle_events()];
                tasks.push(self.age_toast());
                if let Some(run) = &mut self.exercise {
                    if !run.tick(1.0) {
                        self.exercise = None;
                    }
                }
                self.updates.poll();
                self.maybe_auto_check();
                let (lang, paused, night) =
                    (self.engine.settings.general.language.clone(), self.engine.paused, self.engine.settings.night_light.enabled);
                if let Some(tray) = &mut self.tray {
                    tray.sync(&lang, paused, night);
                }
                return Task::batch(tasks);
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
                self.break_windows.retain(|w| *w != id);
                if self.toast.map(|t| t.0) == Some(id) {
                    self.toast = None;
                }
            }
            Message::SkipBreak => {
                self.engine.skip_break();
                return self.handle_events();
            }
            Message::ToastStartBreak => {
                let close = self.close_toast();
                self.engine.start_break();
                return Task::batch([close, self.handle_events()]);
            }
            Message::ToastSnooze => {
                self.engine.snooze();
                return self.close_toast();
            }
            Message::ToastDrank => {
                self.engine.record_water();
                return self.close_toast();
            }
            Message::ToastShowStretch => {
                self.page = Page::Exercises;
                self.exercise = Run::start("neck");
                return Task::batch([self.close_toast(), self.open_main()]);
            }
            Message::DismissToast => return self.close_toast(),
            Message::TakeBreak => {
                self.engine.start_break();
                return self.handle_events();
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
                self.reload_hotkeys();
            }
            Message::TimeDraft(key, text) => {
                let id = format!("{key:?}");
                match actions::apply(&mut self.engine, &Setting::Str(key, text.clone())) {
                    Ok(()) => {
                        self.drafts.remove(&id);
                        if let actions::StrKey::Hotkey(i) = key {
                            self.hk_errors.remove(&i);
                        }
                    }
                    Err(rejected) => {
                        self.drafts.insert(id, text);
                        if let (actions::StrKey::Hotkey(i), actions::Rejected::BadShortcut(msg)) = (key, rejected) {
                            self.hk_errors.insert(i, msg);
                        }
                    }
                }
            }
            Message::StartExercise(id) => self.exercise = Run::start(id),
            Message::NextExerciseStep => {
                if let Some(run) = &mut self.exercise {
                    if !run.advance() {
                        self.exercise = None;
                    }
                }
            }
            Message::StopExercise => self.exercise = None,
            Message::CheckUpdates => self.start_check(),
            Message::DownloadUpdate => self.updates.download(),
            Message::InstallUpdate => {
                if self.updates.install().is_ok() {
                    self.engine.shutdown();
                    return iced::exit();
                }
            }
            Message::OpenReleasePage => {
                let page = self
                    .updates
                    .release
                    .as_ref()
                    .map(|r| r.page.clone())
                    .unwrap_or_else(|| crate::common::updater::RELEASE_PAGE.to_string());
                platform::open_url(&page);
            }
            Message::PlaySample => {
                self.engine.play_sound("start", false, true);
            }
            Message::OpenAuthor => {
                platform::open_url("https://github.com/imhamiddev");
            }
            Message::TrayPoll => {
                let commands = self.tray.as_ref().map(|t| t.poll()).unwrap_or_default();
                let mut messages: Vec<Message> = commands.into_iter().map(command_message).collect();
                if let Some(service) = &self.hotkeys {
                    messages.extend(service.poll().into_iter().filter_map(hotkey_message));
                }
                let tasks: Vec<Task<Message>> = messages.into_iter().map(|m| self.update(m)).collect();
                return Task::batch(tasks);
            }
            Message::SetQuiet(minutes) => match minutes {
                Some(m) if m <= 0.0 => self.engine.set_quiet(Some(0.0)),
                other => self.engine.set_quiet(other),
            },
            Message::Quit => {
                self.engine.shutdown();
                return iced::exit();
            }
        }
        Task::none()
    }

    /// (Re-)register global shortcuts if the configured ones changed.
    fn reload_hotkeys(&mut self) {
        let plan = hk::plan(&self.engine.settings.hotkeys);
        if plan == self.hotkey_plan && self.hotkeys.is_some() {
            return;
        }
        self.hotkeys = None; // drop the old registration first
        self.hotkey_plan = plan.clone();
        if plan.is_empty() {
            self.hk_conflicts.clear();
            return;
        }
        let (service, failed) = HotkeyService::start(&plan);
        self.hk_conflicts = failed.into_iter().collect();
        self.engine.hotkey_failures = self.hk_conflicts.iter().map(|i| hk::action_name(*i).to_string()).collect();
        self.hotkeys = Some(service);
    }

    fn start_check(&mut self) {
        self.updates.check();
        self.engine.settings.general.last_update_check = now_epoch();
        self.engine.save_quietly();
    }

    fn maybe_auto_check(&mut self) {
        let g = &self.engine.settings.general;
        if !self.updates.is_busy()
            && self.updates.state == crate::updates::UpdateState::Idle
            && auto_check_due(g.auto_update, g.last_update_check, now_epoch())
        {
            self.start_check();
        }
    }

    /// React to what the engine reported: open/close break screens and toasts, play chimes.
    fn handle_events(&mut self) -> Task<Message> {
        let mut tasks: Vec<Task<Message>> = Vec::new();
        for event in self.engine.drain_events() {
            match event {
                EngineEvent::PromptRequested => {
                    self.engine.play_sound("notify", true, false);
                    tasks.push(self.show_toast(ToastKind::Rule));
                }
                EngineEvent::BreakStarted(_) => {
                    tasks.push(self.close_toast());
                    self.engine.play_sound("start", false, false);
                    tasks.push(self.open_break_windows());
                }
                EngineEvent::BreakFinished(completed) => {
                    if completed {
                        self.engine.play_sound("end", false, false);
                    }
                    tasks.push(self.close_break_windows());
                }
                EngineEvent::NaturalBreak => tasks.push(self.close_toast()),
                EngineEvent::BlinkRequested => {
                    self.engine.record_blink_shown();
                    self.engine.play_sound("notify", true, false);
                    tasks.push(self.show_toast(ToastKind::Blink));
                }
                EngineEvent::WaterRequested => {
                    self.engine.play_sound("notify", true, false);
                    tasks.push(self.show_toast(ToastKind::Water));
                }
                EngineEvent::PostureRequested => {
                    self.engine.play_sound("notify", true, false);
                    tasks.push(self.show_toast(ToastKind::Posture));
                }
                _ => {}
            }
        }
        // The engine may have dropped the prompt itself (snooze/timeout/disabled).
        if matches!(self.toast, Some((_, ToastKind::Rule, _))) && self.engine.rule.phase != crate::features::rule202020::Phase::Prompt {
            tasks.push(self.close_toast());
        }
        Task::batch(tasks)
    }

    fn open_break_windows(&mut self) -> Task<Message> {
        if !self.break_windows.is_empty() {
            return Task::none();
        }
        let monitors = if self.engine.monitors.is_empty() { self.engine.platform().list_monitors() } else { self.engine.monitors.clone() };
        let mut tasks = Vec::new();
        for m in monitors {
            let settings = window::Settings {
                size: Size::new(m.width as f32, m.height as f32),
                position: window::Position::Specific(Point::new(m.x as f32, m.y as f32)),
                decorations: false,
                resizable: false,
                level: window::Level::AlwaysOnTop,
                ..Default::default()
            };
            let (id, open) = window::open(settings);
            self.break_windows.push(id);
            tasks.push(open.map(Message::WindowOpened));
        }
        Task::batch(tasks)
    }

    fn close_break_windows(&mut self) -> Task<Message> {
        Task::batch(self.break_windows.drain(..).map(window::close::<Message>).collect::<Vec<_>>())
    }

    fn show_toast(&mut self, kind: ToastKind) -> Task<Message> {
        if self.engine.rule.phase == crate::features::rule202020::Phase::Break || !self.break_windows.is_empty() {
            return Task::none(); // never interrupt a break
        }
        if matches!(self.toast, Some((_, ToastKind::Rule, _))) && kind != ToastKind::Rule {
            return Task::none(); // the 20-20-20 prompt wins
        }
        let close = self.close_toast();
        let primary = self.engine.monitors.iter().find(|m| m.primary).cloned().or_else(|| self.engine.monitors.first().cloned());
        let (w, h) = (400.0_f32, 190.0_f32);
        let position = primary
            .map(|m| Point::new(m.x as f32 + m.width as f32 - w - 24.0, m.y as f32 + m.height as f32 - h - 72.0))
            .unwrap_or(Point::new(100.0, 100.0));
        let settings = window::Settings {
            size: Size::new(w, h),
            position: window::Position::Specific(position),
            decorations: false,
            resizable: false,
            level: window::Level::AlwaysOnTop,
            ..Default::default()
        };
        let (id, open) = window::open(settings);
        self.toast = Some((id, kind, 0));
        Task::batch([close, open.map(Message::WindowOpened)])
    }

    fn close_toast(&mut self) -> Task<Message> {
        match self.toast.take() {
            Some((id, _, _)) => window::close(id),
            None => Task::none(),
        }
    }

    /// Close timed toasts once their time is up.
    fn age_toast(&mut self) -> Task<Message> {
        if let Some((_, kind, shown)) = &mut self.toast {
            *shown += 1;
            if kind.lifetime_seconds().is_some_and(|max| *shown >= max) {
                return self.close_toast();
            }
        }
        Task::none()
    }

    pub fn subscription(&self) -> Subscription<Message> {
        let mut subs =
            vec![iced::time::every(Duration::from_secs(1)).map(|_| Message::Tick), window::close_events().map(Message::WindowClosed)];
        if self.tray.is_some() || self.hotkeys.is_some() {
            subs.push(iced::time::every(Duration::from_millis(150)).map(|_| Message::TrayPoll));
        }
        if self.engine.is_animating() {
            subs.push(iced::time::every(Duration::from_millis(16)).map(|_| Message::Frame));
        }
        Subscription::batch(subs)
    }

    pub fn view(&self, id: window::Id) -> Element<'_, Message> {
        let ctx = self.ctx();
        if self.break_windows.contains(&id) {
            return overlay::break_view(ctx, &self.engine);
        }
        if let Some((toast_id, kind, _)) = self.toast {
            if toast_id == id {
                let version = self.updates.release.as_ref().map(|r| r.version.as_str()).unwrap_or("");
                return overlay::toast_view(ctx, kind, version);
            }
        }
        let p = ctx.p;
        let body: Element<'_, Message> = match self.page {
            Page::Home => pages::home::view(ctx, &self.engine),
            Page::Stats => pages::stats::view(ctx, &self.engine),
            Page::Care => pages::care::view(ctx, &self.engine),
            Page::Display => pages::display::view(ctx, &self.engine, &self.drafts),
            Page::Exercises => pages::exercises::view(ctx, self.exercise.as_ref()),
            Page::Settings => pages::settings::view(ctx, &self.engine, &self.updates, &self.drafts, &self.hk_errors, &self.hk_conflicts),
        };
        let heading: Element<'_, Message> = rcol![ctx;
            label::<Message>(ctx, ctx.t(if self.page == Page::Home { "app" } else { self.page.nav_key() }), Txt::H1),
            if self.page == Page::Home { label::<Message>(ctx, ctx.t("tagline"), Txt::Muted) } else { label::<Message>(ctx, "", Txt::Muted) },
        ]
        .spacing(6)
        .into();
        let page =
            scrollable(container(rcol![ctx; heading, Space::new(0.0, 8.0), body].spacing(16)).padding([32.0, 36.0]).width(Length::Fill))
                .height(Length::Fill);
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
        let mut nav = rcol![ctx; brand, Space::new(0.0, 14.0)].spacing(4);
        for page in Page::ALL {
            let active = self.page == page;
            let fg = if active { p.text } else { p.text_muted };
            let content = h_row(
                ctx,
                vec![
                    icon(page.icon(), 18.0, if active { p.accent } else { fg }),
                    label::<Message>(ctx, ctx.t(page.nav_key()), Txt::Body).color(fg).into(),
                ],
            )
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
        let col = rcol![ctx; nav, Space::new(0.0, Length::Fill), quick].padding([22.0, 16.0]);
        container(col).width(theme::SIDEBAR_W).height(Length::Fill).style(move |_| theme::sidebar(p)).into()
    }
}

/// The app message for a pressed global shortcut (index into the hotkey actions).
pub fn hotkey_message(index: usize) -> Option<Message> {
    match crate::common::hotkeys::ACTIONS.get(index).copied()? {
        "night_light" => Some(Message::ToggleNight(true)),
        "break_now" => Some(Message::TakeBreak),
        "pause" => Some(Message::TogglePause),
        "quiet" => Some(Message::ToggleQuiet),
        _ => None,
    }
}

/// The app message for a tray menu command.
pub fn command_message(cmd: TrayCommand) -> Message {
    match cmd {
        TrayCommand::Open => Message::OpenMain,
        TrayCommand::Break => Message::TakeBreak,
        TrayCommand::TogglePause => Message::TogglePause,
        TrayCommand::ToggleNight => Message::ToggleNight(true),
        TrayCommand::Quiet(m) => Message::SetQuiet(m),
        TrayCommand::Quit => Message::Quit,
    }
}

fn now_epoch() -> f64 {
    std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map(|d| d.as_secs_f64()).unwrap_or(0.0)
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn shortcuts_map_to_the_right_messages() {
        assert!(matches!(hotkey_message(0), Some(Message::ToggleNight(_))));
        assert!(matches!(hotkey_message(1), Some(Message::TakeBreak)));
        assert!(matches!(hotkey_message(2), Some(Message::TogglePause)));
        assert!(matches!(hotkey_message(3), Some(Message::ToggleQuiet)));
        assert!(hotkey_message(4).is_none());
    }

    #[test]
    fn tray_commands_map_to_messages() {
        assert!(matches!(command_message(TrayCommand::Open), Message::OpenMain));
        assert!(matches!(command_message(TrayCommand::Quiet(Some(30.0))), Message::SetQuiet(Some(m)) if m == 30.0));
        assert!(matches!(command_message(TrayCommand::Quit), Message::Quit));
    }
}
