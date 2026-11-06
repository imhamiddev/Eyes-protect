"""Settings: theme, language, autostart and about."""
from __future__ import annotations

from eyecare import APP_NAME, __version__
from eyecare.core.i18n import tr

from ..widgets import Dropdown, Segmented, SettingRow, Toggle, label
from .base import Page

THEMES = ["dark", "light", "system"]
LANGS = ["en", "fa"]


class SettingsPage(Page):
    def __init__(self, engine):
        super().__init__(engine, "nav.settings")
        self.theme = Segmented([tr("set.dark"), tr("set.light"), tr("set.system")])
        self.lang = Dropdown(["English", "فارسی"])
        self.autostart = Toggle()
        self.card(
            SettingRow(tr("set.theme"), "", self.theme),
            SettingRow(tr("set.language"), "", self.lang),
            SettingRow(tr("set.autostart"), tr("set.autostart_desc"), self.autostart),
        )
        self.section(tr("set.about"))
        about = label(f"{APP_NAME} {__version__}", "Muted")
        self.card(SettingRow(APP_NAME, f"v{__version__}", None))
        del about
        self.finish()
        self.theme.changed.connect(self._save)
        self.lang.currentIndexChanged.connect(self._save)
        self.autostart.toggled.connect(self._save)
        self.load()

    def load(self) -> None:
        g = self.engine.settings.general
        self._loading = True
        self.theme.set_index(THEMES.index(g.theme) if g.theme in THEMES else 0, emit=False)
        self.lang.setCurrentIndex(LANGS.index(g.language) if g.language in LANGS else 0)
        self.autostart.setChecked(g.autostart)
        self._loading = False

    def _save(self, *_args) -> None:
        if self._loading:
            return
        g = self.engine.settings.general
        g.theme = THEMES[self.theme.index()]
        g.language = LANGS[self.lang.currentIndex()]
        g.autostart = self.autostart.isChecked()
        self.engine.commit_settings()
