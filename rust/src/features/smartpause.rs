//! Decide whether reminders should stay quiet because the user is busy (pure logic).

use crate::common::config::SmartPause;

// SHQueryUserNotificationState values
pub const QUNS_BUSY: i32 = 2; // full-screen app (or presentation settings applied)
pub const QUNS_D3D_FULL_SCREEN: i32 = 3; // a game / exclusive full-screen
pub const QUNS_PRESENTATION: i32 = 4; // presentation mode
pub const QUNS_QUIET_TIME: i32 = 6; // Focus assist
pub const QUNS_APP: i32 = 7; // full-screen Store app
pub const FULLSCREEN_STATES: [i32; 4] = [QUNS_BUSY, QUNS_D3D_FULL_SCREEN, QUNS_PRESENTATION, QUNS_APP];

pub const MEETING_APPS: [&str; 11] = [
    "zoom.exe", "teams.exe", "ms-teams.exe", "webex.exe", "ciscocollabhost.exe", "atmgr.exe",
    "skype.exe", "lync.exe", "bluejeans.exe", "gotomeeting.exe", "slack.exe",
];
pub const MEETING_WORDS: [&str; 5] = ["meeting", "call", "webinar", "huddle", "conference"];
pub const BROWSER_MEETING_TITLES: [&str; 4] = ["google meet", "zoom meeting", "meet - ", "microsoft teams meeting"];

/// Why reminders are being held back.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Reason {
    Fullscreen,
    Meeting,
    Focus,
}

impl Reason {
    pub fn as_str(self) -> &'static str {
        match self {
            Reason::Fullscreen => "fullscreen",
            Reason::Meeting => "meeting",
            Reason::Focus => "focus",
        }
    }
}

/// The window that currently has the focus.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Foreground {
    pub pid: u32,
    pub exe: String,
    pub title: String,
}

pub fn is_meeting(exe: &str, title: &str) -> bool {
    let t = title.to_lowercase();
    if BROWSER_MEETING_TITLES.iter().any(|k| t.contains(k)) || t.starts_with("meet -") {
        return true;
    }
    MEETING_APPS.contains(&exe.to_lowercase().as_str()) && MEETING_WORDS.iter().any(|w| t.contains(w))
}

/// Classify what (if anything) should keep reminders quiet.
///
/// Our own full-screen break screen must not count as a busy app.
pub fn classify(
    cfg: &SmartPause,
    notification_state: Option<i32>,
    foreground: Option<&Foreground>,
    own_pid: Option<u32>,
) -> Option<Reason> {
    if !cfg.enabled {
        return None;
    }
    let (pid, exe, title) = match foreground {
        Some(f) => (Some(f.pid), f.exe.as_str(), f.title.as_str()),
        None => (None, "", ""),
    };
    let ours = own_pid.is_some() && pid == own_pid;
    if cfg.meetings && !ours && is_meeting(exe, title) {
        return Some(Reason::Meeting);
    }
    if cfg.fullscreen && !ours && notification_state.is_some_and(|s| FULLSCREEN_STATES.contains(&s)) {
        return Some(Reason::Fullscreen);
    }
    if cfg.focus_assist && notification_state == Some(QUNS_QUIET_TIME) {
        return Some(Reason::Focus);
    }
    None
}

/// Enter a busy state only after it persisted for `enter_after` polls; leave at once.
#[derive(Debug, Clone)]
pub struct Debouncer {
    enter_after: u32,
    pub reason: Option<Reason>,
    candidate: Option<Reason>,
    count: u32,
}

impl Debouncer {
    pub fn new(enter_after: u32) -> Self {
        Self { enter_after: enter_after.max(1), reason: None, candidate: None, count: 0 }
    }

    pub fn update(&mut self, observed: Option<Reason>) -> Option<Reason> {
        let Some(observed) = observed else {
            self.reason = None;
            self.candidate = None;
            self.count = 0;
            return None;
        };
        if Some(observed) == self.reason {
            return self.reason;
        }
        if Some(observed) == self.candidate {
            self.count += 1;
        } else {
            self.candidate = Some(observed);
            self.count = 1;
        }
        if self.count >= self.enter_after {
            self.reason = Some(observed);
        }
        self.reason
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn fg(pid: u32, exe: &str, title: &str) -> Foreground {
        Foreground { pid, exe: exe.into(), title: title.into() }
    }
    fn on() -> SmartPause {
        SmartPause::default()
    }

    #[test]
    fn nothing_busy_by_default() {
        let chrome = fg(100, "chrome.exe", "Docs - Chrome");
        assert_eq!(classify(&on(), Some(5), Some(&chrome), None), None);
        assert_eq!(classify(&on(), None, None, None), None);
    }

    #[test]
    fn fullscreen_states() {
        let chrome = fg(100, "chrome.exe", "Docs - Chrome");
        for state in [2, 3, 4, 7] {
            assert_eq!(classify(&on(), Some(state), Some(&chrome), None), Some(Reason::Fullscreen));
        }
    }

    #[test]
    fn focus_assist() {
        let chrome = fg(100, "chrome.exe", "Docs - Chrome");
        assert_eq!(classify(&on(), Some(6), Some(&chrome), None), Some(Reason::Focus));
        let cfg = SmartPause { focus_assist: false, ..on() };
        assert_eq!(classify(&cfg, Some(6), Some(&chrome), None), None);
    }

    #[test]
    fn master_switch_and_sub_switches() {
        let chrome = fg(100, "chrome.exe", "Docs - Chrome");
        assert_eq!(classify(&SmartPause { enabled: false, ..on() }, Some(2), Some(&chrome), None), None);
        assert_eq!(classify(&SmartPause { fullscreen: false, ..on() }, Some(2), Some(&chrome), None), None);
        let meet = fg(1, "zoom.exe", "Zoom Meeting");
        assert_eq!(classify(&SmartPause { meetings: false, ..on() }, Some(5), Some(&meet), None), None);
    }

    #[test]
    fn meetings_detected() {
        for (exe, title) in [
            ("zoom.exe", "Zoom Meeting"),
            ("ms-teams.exe", "Weekly sync | Meeting | Microsoft Teams"),
            ("chrome.exe", "Meet - abc-defg-hij - Google Chrome"),
            ("msedge.exe", "Google Meet"),
            ("webex.exe", "Team call"),
        ] {
            assert_eq!(classify(&on(), Some(5), Some(&fg(1, exe, title)), None), Some(Reason::Meeting), "{exe} {title}");
        }
    }

    #[test]
    fn non_meetings_ignored() {
        for (exe, title) in [
            ("teams.exe", "Chat | Anna | Microsoft Teams"),
            ("chrome.exe", "How to hold a meeting - Wikipedia"),
            ("notepad.exe", "meeting notes.txt"),
            ("zoom.exe", "Zoom"),
        ] {
            assert_eq!(classify(&on(), Some(5), Some(&fg(1, exe, title)), None), None, "{exe} {title}");
        }
    }

    #[test]
    fn own_break_screen_is_not_busy() {
        let ours = fg(4242, "eyecare.exe", "Eye Care");
        assert_eq!(classify(&on(), Some(2), Some(&ours), Some(4242)), None);
        assert_eq!(classify(&on(), Some(2), Some(&ours), Some(1)), Some(Reason::Fullscreen));
        let ours_blank = fg(4242, "eyecare.exe", "");
        assert_eq!(classify(&on(), Some(6), Some(&ours_blank), Some(4242)), Some(Reason::Focus));
    }

    #[test]
    fn debouncer_enters_slowly_and_leaves_fast() {
        let mut d = Debouncer::new(2);
        assert_eq!(d.update(Some(Reason::Fullscreen)), None);
        assert_eq!(d.update(Some(Reason::Fullscreen)), Some(Reason::Fullscreen));
        assert_eq!(d.update(Some(Reason::Fullscreen)), Some(Reason::Fullscreen));
        assert_eq!(d.update(None), None);
        assert_eq!(d.update(Some(Reason::Meeting)), None);
    }

    #[test]
    fn debouncer_resets_candidate_on_change() {
        let mut d = Debouncer::new(2);
        d.update(Some(Reason::Fullscreen));
        assert_eq!(d.update(Some(Reason::Meeting)), None);
        assert_eq!(d.update(Some(Reason::Meeting)), Some(Reason::Meeting));
    }

    #[test]
    fn reasons_have_stable_names() {
        assert_eq!(Reason::Fullscreen.as_str(), "fullscreen");
        assert_eq!(Reason::Meeting.as_str(), "meeting");
        assert_eq!(Reason::Focus.as_str(), "focus");
    }
}
