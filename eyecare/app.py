"""Application controller: wires the engine to windows, toasts, tray and theme."""
from __future__ import annotations

import random
import sys

from PySide6.QtCore import QLockFile, Qt, QTimer
from PySide6.QtWidgets import QApplication

from eyecare import APP_NAME
from eyecare.core import i18n, winapi
from eyecare.core.config import config_dir
from eyecare.core import hotkeys as hk
from eyecare.engine import Engine
from eyecare.hotkeys import HotkeyManager
from eyecare.features.rule202020 import Phase
from eyecare.ui import brand, fonts, motion
from eyecare.core.exercises import STRETCHES
from eyecare.ui.break_overlay import BreakOverlay
from eyecare.ui.pages.exercises import ExerciseRunner
from eyecare.ui.main_window import MainWindow
from eyecare.ui.theme import theme
from eyecare.ui.toast import ToastManager
from eyecare.ui.tray import Tray

PROMPT_TOAST_MS = 30_000
BLINK_TOAST_MS = 4_000
WATER_TOAST_MS = 15_000


class EyeCareApp:
    def __init__(self, qt_app: QApplication, engine: Engine | None = None):
        self.qt = qt_app
        self.engine = engine or Engine()
        self.toasts = ToastManager()
        self.overlay = BreakOverlay()
        self.window: MainWindow | None = None
        self.tray: Tray | None = None
        self._prompt_toast = None
        self._mini_toast = None
        self._stretch = None
        self.hotkeys = HotkeyManager()
        self._hotkey_cfg: tuple | None = None
        self._applied: tuple[str, str] | None = None

        motion.set_enabled(self.engine.settings.general.animations)
        self.apply_appearance()
        self.window = MainWindow(self.engine)
        self.tray = Tray(self.engine)
        self.tray.open_requested.connect(self.show_window)
        self.tray.quit_requested.connect(self.quit)

        e = self.engine
        e.prompt_requested.connect(self.on_prompt)
        e.break_started.connect(self.on_break_started)
        e.break_tick.connect(self.on_break_tick)
        e.break_finished.connect(self.on_break_finished)
        e.blink_requested.connect(self.on_blink)
        e.posture_requested.connect(self.on_posture)
        e.water_requested.connect(self.on_water)
        e.natural_break.connect(self.on_natural_break)
        e.settings_changed.connect(self.on_settings_changed)
        e.state_changed.connect(self._drop_stale_prompt)
        e.updates.update_ready.connect(self.on_update_ready)
        e.updates.quit_requested.connect(self.quit)
        self.overlay.skipped.connect(e.skip_break)
        self.hotkeys.triggered.connect(self.on_hotkey)
        e.settings_changed.connect(self.sync_hotkeys)

        self._theme_watch = QTimer()
        self._theme_watch.setInterval(5000)
        self._theme_watch.timeout.connect(self._follow_system_theme)
        self._theme_watch.start()

    # -- appearance -------------------------------------------------------
    def _palette_name(self) -> str:
        choice = self.engine.settings.general.theme
        if choice == "system":
            return "light" if winapi.system_uses_light_theme() else "dark"
        return choice if choice in ("dark", "light") else "dark"

    def apply_appearance(self) -> bool:
        """Apply theme + language. Returns True when the language changed."""
        lang = self.engine.settings.general.language
        language_changed = bool(self._applied) and self._applied[1] != lang
        i18n.set_language(lang)
        self.qt.setLayoutDirection(Qt.LayoutDirection.RightToLeft if i18n.is_rtl()
                                   else Qt.LayoutDirection.LeftToRight)
        theme.apply(self._palette_name(), lang)
        self.qt.setStyleSheet(theme.qss())
        self._applied = (self._palette_name(), lang)
        return language_changed

    def on_settings_changed(self) -> None:
        motion.set_enabled(self.engine.settings.general.animations)
        if self._applied != (self._palette_name(), self.engine.settings.general.language):
            if self.apply_appearance() and self.window:
                self.window.rebuild()
                if self.tray:
                    self.tray.retranslate()

    def _follow_system_theme(self) -> None:
        if self.engine.settings.general.theme == "system" and self._applied \
                and self._applied[0] != self._palette_name():
            self.apply_appearance()

    # -- windows ----------------------------------------------------------
    def show_window(self) -> None:
        if not self.window:
            return
        self.window.show()
        self.window.setWindowState(self.window.windowState() & ~Qt.WindowState.WindowMinimized)
        self.window.raise_()
        self.window.activateWindow()

    def start(self, background: bool) -> None:
        self.sync_hotkeys()
        self.engine.start()
        if self.tray:
            self.tray.show()
        if not background:
            self.show_window()

    def quit(self) -> None:
        if self.window:
            self.window.quitting = True
        self.overlay.end()
        self.toasts.clear()
        self.hotkeys.shutdown()
        if self.tray:
            self.tray.hide()
        self.engine.shutdown()
        self.qt.quit()

    # -- reminders ----------------------------------------------------------
    def on_prompt(self) -> None:
        if not self.engine.settings.rule202020.enabled:
            self.engine.snooze()
            return
        self.engine.play_sound("notify", reminder=True)
        self._prompt_toast = self.toasts.show(
            "eye", i18n.tr("toast.rule_title"), i18n.tr("toast.rule_body"),
            [(i18n.tr("toast.start"), self.engine.start_break, True),
             (i18n.tr("toast.snooze"), self.engine.snooze, False)],
            timeout_ms=PROMPT_TOAST_MS)

    def _drop_stale_prompt(self) -> None:
        if self._prompt_toast is not None and self.engine.rule.phase != Phase.PROMPT:
            self._prompt_toast.dismiss()
            self._prompt_toast = None

    def on_break_started(self, seconds: int) -> None:
        s = self.engine.settings
        self.engine.play_sound("start")
        if self._prompt_toast is not None:
            self._prompt_toast.dismiss()
            self._prompt_toast = None
        if s.rule202020.use_break_lock:
            self.overlay.begin(seconds, s.break_lock.skippable, s.break_lock.skip_after_seconds,
                               s.break_lock.show_exercise)
        else:
            self._mini_toast = self.toasts.show(
                "timer", i18n.tr("break.title"), self._mini_text(seconds),
                [(i18n.tr("break.skip"), self.engine.skip_break, False)])

    @staticmethod
    def _mini_text(seconds: int) -> str:
        return f"{i18n.tr('break.hint')}  ·  {seconds}"

    def on_break_tick(self, seconds_left: int) -> None:
        if self.overlay.active:
            self.overlay.update_left(seconds_left)
        elif self._mini_toast is not None:
            self._mini_toast.set_body(self._mini_text(seconds_left))

    def on_break_finished(self, completed: bool) -> None:
        self.overlay.end()
        if self._mini_toast is not None:
            self._mini_toast.dismiss()
            self._mini_toast = None
        if completed:
            self.engine.play_sound("end")
            self.toasts.show("check", i18n.tr("break.done"), "", [], timeout_ms=3000)

    def on_blink(self) -> None:
        self.engine.record_blink_shown()
        self.engine.play_sound("notify", reminder=True)
        self.toasts.show("eye", i18n.tr("toast.blink_title"), i18n.tr("toast.blink_body"),
                         [], timeout_ms=BLINK_TOAST_MS)

    def on_posture(self) -> None:
        self.engine.play_sound("notify", reminder=True)
        self.toasts.show(
            "person", i18n.tr("toast.posture_title"), i18n.tr("toast.posture_body"),
            [(i18n.tr("toast.posture_start"), self.start_stretch, True),
             (i18n.tr("toast.dismiss"), lambda: None, False)],
            timeout_ms=20_000)

    def start_stretch(self, exercise=None) -> ExerciseRunner:
        self._stretch = ExerciseRunner(exercise or random.choice(STRETCHES), None, self.engine)
        self._stretch.show()
        self._stretch.raise_()
        self._stretch.activateWindow()
        return self._stretch

    def on_water(self) -> None:
        self.engine.play_sound("notify", reminder=True)
        self.toasts.show("droplet", i18n.tr("toast.water_title"), i18n.tr("toast.water_body"),
                         [(i18n.tr("toast.drank"), self.engine.record_water, True)],
                         timeout_ms=WATER_TOAST_MS)

    def on_update_ready(self, info) -> None:
        self.toasts.show(
            "download", i18n.tr("upd.toast_title"),
            i18n.tr("upd.toast_body").replace("{v}", info.version),
            [(i18n.tr("upd.toast_install"), self.engine.updates.install, True),
             (i18n.tr("upd.toast_later"), lambda: None, False)])

    # -- global shortcuts ---------------------------------------------------
    def sync_hotkeys(self) -> None:
        h = self.engine.settings.hotkeys
        cfg = (h.enabled, h.night_light, h.break_now, h.pause, h.quiet)
        if cfg == self._hotkey_cfg:
            return
        self._hotkey_cfg = cfg
        mapping = {a: getattr(h, a) for a in hk.ACTIONS}
        self.engine.hotkey_failures = set(self.hotkeys.register(h.enabled, mapping))
        self.engine.state_changed.emit()

    def on_hotkey(self, action: str) -> None:
        e = self.engine
        if action == "night_light":
            on = e.toggle_night_light()
            self._hotkey_toast("moon", i18n.tr("tray.night"), i18n.tr("hk.on" if on else "hk.off"))
        elif action == "break_now":
            e.start_break()
        elif action == "pause":
            e.set_paused(not e.paused)
            self._hotkey_toast("pause" if e.paused else "play", i18n.tr("app"),
                               i18n.tr("hk.paused" if e.paused else "hk.resumed"))
        elif action == "quiet":
            on = e.toggle_quiet(60)
            self._hotkey_toast("bell", i18n.tr("app"), i18n.tr("hk.quiet_on" if on else "hk.quiet_off"))

    def _hotkey_toast(self, icon: str, title: str, body: str) -> None:
        self.toasts.show(icon, title, body, [], timeout_ms=1800)

    def on_natural_break(self) -> None:
        self.toasts.show("check", i18n.tr("break.done"), "", [], timeout_ms=2500)


def run(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    background = "--background" in argv
    qt = QApplication([a for a in argv if a != "--background"])
    qt.setApplicationName(APP_NAME)
    qt.setQuitOnLastWindowClosed(False)
    qt.setWindowIcon(brand.app_icon())

    lock = QLockFile(str(config_dir() / "eyecare.lock"))
    lock.setStaleLockTime(0)
    if not lock.tryLock(100):
        return 0  # already running

    winapi.create_single_instance_mutex()
    fonts.load_fonts()
    app = EyeCareApp(qt)
    app.start(background=background)
    code = qt.exec()
    lock.unlock()
    return code
