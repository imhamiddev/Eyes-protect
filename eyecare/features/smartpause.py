"""Decide whether reminders should stay quiet because the user is busy (pure logic)."""
from __future__ import annotations

from eyecare.core.config import SmartPause

# SHQueryUserNotificationState values
QUNS_BUSY = 2                 # full-screen app (or presentation settings applied)
QUNS_D3D_FULL_SCREEN = 3      # a game / exclusive full-screen
QUNS_PRESENTATION = 4         # presentation mode
QUNS_QUIET_TIME = 6           # Focus assist
QUNS_APP = 7                  # full-screen Store app
FULLSCREEN_STATES = frozenset({QUNS_BUSY, QUNS_D3D_FULL_SCREEN, QUNS_PRESENTATION, QUNS_APP})

MEETING_APPS = frozenset({
    "zoom.exe", "teams.exe", "ms-teams.exe", "webex.exe", "ciscocollabhost.exe", "atmgr.exe",
    "skype.exe", "lync.exe", "bluejeans.exe", "gotomeeting.exe", "slack.exe",
})
MEETING_WORDS = ("meeting", "call", "webinar", "huddle", "conference")
BROWSER_MEETING_TITLES = ("google meet", "zoom meeting", "meet - ", "microsoft teams meeting")


def is_meeting(exe: str, title: str) -> bool:
    t = title.lower()
    if any(k in t for k in BROWSER_MEETING_TITLES) or t.startswith("meet -"):
        return True
    return exe.lower() in MEETING_APPS and any(w in t for w in MEETING_WORDS)


def classify(cfg: SmartPause, notification_state: int | None,
             foreground: tuple[int, str, str] | None, own_pid: int | None = None) -> str | None:
    """Return 'fullscreen' | 'meeting' | 'focus' | None.

    Our own full-screen break screen must not count as a busy app."""
    if not cfg.enabled:
        return None
    pid, exe, title = foreground if foreground else (None, "", "")
    ours = own_pid is not None and pid == own_pid
    if cfg.meetings and not ours and is_meeting(exe, title):
        return "meeting"
    if cfg.fullscreen and not ours and notification_state in FULLSCREEN_STATES:
        return "fullscreen"
    if cfg.focus_assist and notification_state == QUNS_QUIET_TIME:
        return "focus"
    return None


class Debouncer:
    """Enter a busy state only after it persisted for ``enter_after`` polls; leave at once."""

    def __init__(self, enter_after: int = 2):
        self.enter_after = max(1, enter_after)
        self.reason: str | None = None
        self._candidate: str | None = None
        self._count = 0

    def update(self, observed: str | None) -> str | None:
        if observed is None:
            self.reason, self._candidate, self._count = None, None, 0
            return None
        if observed == self.reason:
            return self.reason
        if observed == self._candidate:
            self._count += 1
        else:
            self._candidate, self._count = observed, 1
        if self._count >= self.enter_after:
            self.reason = observed
        return self.reason
