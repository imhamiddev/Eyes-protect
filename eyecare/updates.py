"""Qt update manager: background checks, downloads and hand-off to the installer."""
from __future__ import annotations

import tempfile
import threading
import time
from enum import Enum
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal

from eyecare import __version__
from eyecare.core import updater

CHECK_EVERY_SECONDS = 6 * 3600
FIRST_CHECK_DELAY_MS = 25_000


class State(Enum):
    IDLE = "idle"
    CHECKING = "checking"
    UP_TO_DATE = "up_to_date"
    AVAILABLE = "available"
    DOWNLOADING = "downloading"
    READY = "ready"
    ERROR = "error"


class UpdateManager(QObject):
    changed = Signal()
    update_ready = Signal(object)    # ReleaseInfo, downloaded by the automatic flow
    quit_requested = Signal()
    # worker-thread -> main-thread hand-offs
    _checked = Signal(object, str, bool)
    _progress = Signal(float)
    _downloaded = Signal(object, str)

    def __init__(self, engine, version: str = __version__, fetch=updater.fetch_latest,
                 download=updater.download, launch=updater.launch_installer,
                 can_install=updater.can_self_update, work_dir: Path | None = None):
        super().__init__()
        self.engine = engine
        self.version = version
        self._fetch, self._download, self._launch = fetch, download, launch
        self._can_install = can_install
        self._work_dir = work_dir or Path(tempfile.gettempdir()) / "EyeCare-update"
        self.state = State.IDLE
        self.info: updater.ReleaseInfo | None = None
        self.progress = 0.0
        self.error = ""
        self.installer: Path | None = None
        self._auto_flow = False
        self._cancel = threading.Event()
        self._checked.connect(self._on_checked)
        self._progress.connect(self._on_progress)
        self._downloaded.connect(self._on_downloaded)
        self._timer = QTimer(self)
        self._timer.setInterval(30 * 60 * 1000)
        self._timer.timeout.connect(self._auto_tick)

    # -- scheduling -------------------------------------------------------
    def start_background(self) -> None:
        self._timer.start()
        QTimer.singleShot(FIRST_CHECK_DELAY_MS, self._auto_tick)

    def _auto_tick(self) -> None:
        g = self.engine.settings.general
        busy = self.state in (State.CHECKING, State.DOWNLOADING, State.READY)
        if g.auto_update and not busy and time.time() - g.last_update_check >= CHECK_EVERY_SECONDS:
            self.check(auto=True)

    @property
    def can_install(self) -> bool:
        return bool(self._can_install())

    # -- check ------------------------------------------------------------
    def check(self, auto: bool = False) -> None:
        if self.state in (State.CHECKING, State.DOWNLOADING):
            return
        self._auto_flow = auto
        self.error = ""
        self._set(State.CHECKING)
        threading.Thread(target=self._check_worker, args=(auto,), daemon=True).start()

    def _check_worker(self, auto: bool) -> None:
        try:
            info = self._fetch()
            self._checked.emit(info, "", auto)
        except Exception as exc:  # noqa: BLE001 - report any failure to the UI
            self._checked.emit(None, str(exc) or "error", auto)

    def _on_checked(self, info, error: str, auto: bool) -> None:
        if error:
            self.error = error
            self._set(State.ERROR)
            return
        self.engine.settings.general.last_update_check = time.time()
        self.engine.save_quietly()
        if info is not None and updater.is_newer(info.version, self.version):
            self.info = info
            self._set(State.AVAILABLE)
            if auto and self.can_install:
                self.download()
        else:
            self.info = None
            self._set(State.UP_TO_DATE)

    # -- download ---------------------------------------------------------
    def download(self) -> None:
        if self.state not in (State.AVAILABLE, State.ERROR) or self.info is None:
            return
        self.progress = 0.0
        self._cancel.clear()
        self._set(State.DOWNLOADING)
        dest = self._work_dir / f"EyeCare-Setup-{self.info.version}.exe"
        threading.Thread(target=self._download_worker, args=(self.info, dest), daemon=True).start()

    def _download_worker(self, info, dest: Path) -> None:
        try:
            path = self._download(info, dest, self._progress.emit, self._cancel.is_set)
            self._downloaded.emit(info, str(path))
        except Exception as exc:  # noqa: BLE001
            self._downloaded.emit(None, str(exc) or "error")

    def _on_progress(self, value: float) -> None:
        self.progress = value
        self.changed.emit()

    def _on_downloaded(self, info, payload: str) -> None:
        if info is None:
            self.error = payload
            self._set(State.ERROR)
            return
        self.installer = Path(payload)
        self._set(State.READY)
        if self._auto_flow:
            self.update_ready.emit(info)

    # -- install ----------------------------------------------------------
    def install(self) -> bool:
        """Launch the silent installer and ask the app to quit. Returns success."""
        if self.state != State.READY or not self.installer or not self.installer.exists():
            return False
        try:
            self._launch(self.installer)
        except Exception as exc:  # noqa: BLE001
            self.error = str(exc)
            self._set(State.ERROR)
            return False
        self.quit_requested.emit()
        return True

    def cancel(self) -> None:
        self._cancel.set()

    def _set(self, state: State) -> None:
        self.state = state
        self.changed.emit()
