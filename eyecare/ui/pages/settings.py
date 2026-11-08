"""Settings: theme, language, autostart, animations, updates and about."""
from __future__ import annotations

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QVBoxLayout, QWidget

from eyecare import APP_NAME, __version__
from eyecare.core import hotkeys as hk
from eyecare.core.i18n import tr
from eyecare.updates import State

from ..widgets import (
    AnimatedButton, Dropdown, ProgressBar, Segmented, SettingRow, ShortcutEdit, Toggle,
    secondary_button,
)
from .base import Page

THEMES = ["dark", "light", "system"]
LANGS = ["en", "fa"]
AUTHOR_URL = "https://github.com/imhamiddev"


class SettingsPage(Page):
    def __init__(self, engine):
        super().__init__(engine, "nav.settings")
        self.theme = Segmented([tr("set.dark"), tr("set.light"), tr("set.system")])
        self.lang = Dropdown(["English", "فارسی"])
        self.autostart = Toggle()
        self.animations = Toggle()
        self.card(
            SettingRow(tr("set.theme"), "", self.theme),
            SettingRow(tr("set.language"), "", self.lang),
            SettingRow(tr("set.autostart"), tr("set.autostart_desc"), self.autostart),
            SettingRow(tr("set.animations"), tr("set.animations_desc"), self.animations),
        )

        self.section(tr("set.updates"))
        self.auto_update = Toggle()
        self.update_btn = secondary_button(tr("upd.btn_check"), "refresh")
        self.update_row = SettingRow(tr("upd.version").replace("{v}", __version__), "", self.update_btn)
        self.progress = ProgressBar()
        self.progress_box = QWidget()
        pl = QVBoxLayout(self.progress_box)
        pl.setContentsMargins(0, 0, 0, 14)
        pl.addWidget(self.progress)
        self.progress_box.setVisible(False)
        self.card(
            SettingRow(tr("set.auto_update"), tr("set.auto_update_desc"), self.auto_update),
            self.update_row,
            self.progress_box,
        )

        self.section(tr("set.hotkeys"))
        self.hk_on = Toggle()
        self.hk_edits: dict[str, ShortcutEdit] = {}
        self.hk_rows: dict[str, SettingRow] = {}
        self._hk_errors: dict[str, str] = {}
        rows = [SettingRow(tr("set.hotkeys"), tr("set.hotkeys_desc"), self.hk_on)]
        for action in hk.ACTIONS:
            edit = ShortcutEdit(hk.DEFAULTS[action])
            edit.committed.connect(lambda combo, a=action: self._hotkey_edited(a, combo))
            row = SettingRow(tr(f"hk.{action}"), "", edit)
            self.hk_edits[action], self.hk_rows[action] = edit, row
            rows.append(row)
        self.card(*rows)

        self.section(tr("set.about"))
        self.author_btn = AnimatedButton(tr("set.made_by"), "external-link", "ghost", align="start")
        self.author_btn.setToolTip(tr("set.open_github"))
        self.author_btn.clicked.connect(self.open_author)
        about = QWidget()
        al = QVBoxLayout(about)
        al.setContentsMargins(0, 8, 0, 8)
        al.setAlignment(Qt.AlignmentFlag.AlignLeading)
        al.addWidget(self.author_btn, 0, Qt.AlignmentFlag.AlignLeading)
        self.card(SettingRow(APP_NAME, f"v{__version__}", None), about)
        self.finish()

        self.theme.changed.connect(self._save)
        self.lang.currentIndexChanged.connect(self._save)
        self.autostart.toggled.connect(self._save)
        self.animations.toggled.connect(self._save)
        self.auto_update.toggled.connect(self._save)
        self.hk_on.toggled.connect(self._save)
        self.update_btn.clicked.connect(self._on_update_clicked)
        engine.updates.changed.connect(self._refresh_update)
        self.load()
        self._refresh_update()

    # -- about ------------------------------------------------------------
    def open_author(self) -> None:
        QDesktopServices.openUrl(QUrl(AUTHOR_URL))

    # -- updates ----------------------------------------------------------
    def _on_update_clicked(self) -> None:
        um = self.engine.updates
        if um.state == State.AVAILABLE:
            if um.can_install:
                um.download()
            elif um.info:
                QDesktopServices.openUrl(QUrl(um.info.page))
        elif um.state == State.READY:
            um.install()
        else:
            um.check()

    def _refresh_update(self) -> None:
        um = self.engine.updates
        v = um.info.version if um.info else ""
        btn, st = self.update_btn, um.state
        enabled, kind, icon, text = True, "secondary", "refresh", tr("upd.btn_check")
        if st == State.IDLE:
            desc = tr("upd.idle")
        elif st == State.CHECKING:
            desc, enabled, text = tr("upd.checking"), False, tr("upd.btn_checking")
        elif st == State.UP_TO_DATE:
            desc = tr("upd.up_to_date")
        elif st == State.AVAILABLE:
            if um.can_install:
                desc = tr("upd.available").replace("{v}", v)
                kind, icon, text = "primary", "download", tr("upd.btn_download")
            else:
                desc = tr("upd.manual_only").replace("{v}", v)
                icon, text = "external-link", tr("upd.btn_open")
        elif st == State.DOWNLOADING:
            pct = str(int(um.progress * 100))
            desc, enabled, kind, icon = tr("upd.downloading").replace("{p}", pct), False, "primary", "download"
            text = tr("upd.btn_downloading")
        elif st == State.READY:
            desc = tr("upd.ready").replace("{v}", v)
            kind, icon, text = "primary", "power", tr("upd.btn_install")
        else:  # ERROR
            desc, text = tr("upd.error"), tr("upd.btn_retry")
        self.update_row.set_texts(tr("upd.version").replace("{v}", __version__), desc)
        btn.kind, btn.icon_name = kind, icon
        btn.setText(text)
        btn.setEnabled(enabled)
        btn.updateGeometry()
        btn.update()
        downloading = st == State.DOWNLOADING
        self.progress_box.setVisible(downloading or st == State.READY)
        self.progress.set_value(um.progress if downloading else (1.0 if st == State.READY else 0.0))

    # -- settings ---------------------------------------------------------
    def load(self) -> None:
        g = self.engine.settings.general
        self._loading = True
        self.theme.set_index(THEMES.index(g.theme) if g.theme in THEMES else 0, emit=False)
        self.lang.setCurrentIndex(LANGS.index(g.language) if g.language in LANGS else 0)
        self.autostart.setChecked(g.autostart)
        self.animations.setChecked(g.animations)
        self.auto_update.setChecked(g.auto_update)
        h = self.engine.settings.hotkeys
        self.hk_on.setChecked(h.enabled)
        for action, edit in self.hk_edits.items():
            edit.set_combo(getattr(h, action))
            edit.setEnabled(h.enabled)
        self._loading = False
        self._hotkey_status()

    def _save(self, *_args) -> None:
        if self._loading:
            return
        g = self.engine.settings.general
        g.theme = THEMES[self.theme.index()]
        g.language = LANGS[self.lang.currentIndex()]
        g.autostart = self.autostart.isChecked()
        g.animations = self.animations.isChecked()
        g.auto_update = self.auto_update.isChecked()
        self.engine.settings.hotkeys.enabled = self.hk_on.isChecked()
        for edit in self.hk_edits.values():
            edit.setEnabled(self.hk_on.isChecked())
        self.engine.commit_settings()

    # -- shortcuts --------------------------------------------------------
    def _hotkey_edited(self, action: str, combo: str) -> None:
        h = self.engine.settings.hotkeys
        message = ""
        try:
            canonical = hk.normalize(combo)
        except ValueError:
            canonical, message = "", tr("hk.invalid")
        if canonical:
            clash = any(a != action and hk.normalize(getattr(h, a)) == canonical for a in hk.ACTIONS)
            if clash:
                canonical, message = "", tr("hk.duplicate")
        if not canonical:  # reject: restore the previous shortcut and explain why
            self.hk_edits[action].set_combo(getattr(h, action))
            self._hk_errors[action] = message
            self._hotkey_status()
            return
        self._hk_errors.pop(action, None)
        setattr(h, action, canonical)
        self.hk_edits[action].set_combo(canonical)
        self.engine.commit_settings()
        self._hotkey_status()

    def _hotkey_status(self) -> None:
        failed = self.engine.hotkey_failures
        for action, row in self.hk_rows.items():
            note = self._hk_errors.get(action) or (tr("hk.in_use") if action in failed else "")
            row.set_texts(tr(f"hk.{action}"), note)

    def refresh(self) -> None:
        self._hotkey_status()
