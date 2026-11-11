//! Update state machine: check -> download -> ready, running network work on a worker thread.
//!
//! The UI calls [`UpdateManager::poll`] on every tick and renders [`UpdateManager::state`].

use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::mpsc::{channel, Receiver};
use std::sync::Arc;

use crate::common::updater::{self, ReleaseInfo, UpdateError};

/// Automatic checks run at most once per day.
pub const AUTO_CHECK_INTERVAL_SECONDS: f64 = 24.0 * 3600.0;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum UpdateState {
    Idle,
    Checking,
    UpToDate,
    Available,
    Downloading,
    Ready,
    Error,
}

/// The network side, replaceable in tests.
pub trait Backend: Send + Sync {
    fn fetch_latest(&self) -> Result<Option<ReleaseInfo>, UpdateError>;
    fn download(&self, info: &ReleaseInfo, on_progress: &mut dyn FnMut(f64), cancelled: &dyn Fn() -> bool) -> Result<PathBuf, UpdateError>;
}

/// GitHub releases, installer saved in the temp folder.
pub struct GithubBackend;

impl Backend for GithubBackend {
    fn fetch_latest(&self) -> Result<Option<ReleaseInfo>, UpdateError> {
        updater::fetch_latest_release()
    }

    fn download(&self, info: &ReleaseInfo, on_progress: &mut dyn FnMut(f64), cancelled: &dyn Fn() -> bool) -> Result<PathBuf, UpdateError> {
        let dest = std::env::temp_dir().join("EyeCare-Update").join(updater::ASSET_NAME);
        updater::download(info, &dest, on_progress, cancelled, std::time::Duration::from_secs(30), &updater::Policy::github())
    }
}

enum Msg {
    Checked(Result<Option<ReleaseInfo>, UpdateError>),
    Progress(f64),
    Downloaded(Result<PathBuf, UpdateError>),
}

pub struct UpdateManager {
    backend: Arc<dyn Backend>,
    current_version: String,
    pub state: UpdateState,
    pub release: Option<ReleaseInfo>,
    pub progress: f64,
    pub installer: Option<PathBuf>,
    pub error: String,
    cancel: Arc<AtomicBool>,
    rx: Option<Receiver<Msg>>,
}

impl UpdateManager {
    pub fn new(backend: Arc<dyn Backend>, current_version: &str) -> Self {
        Self {
            backend,
            current_version: current_version.to_string(),
            state: UpdateState::Idle,
            release: None,
            progress: 0.0,
            installer: None,
            error: String::new(),
            cancel: Arc::new(AtomicBool::new(false)),
            rx: None,
        }
    }

    pub fn is_busy(&self) -> bool {
        matches!(self.state, UpdateState::Checking | UpdateState::Downloading)
    }

    pub fn check(&mut self) {
        if self.is_busy() {
            return;
        }
        self.state = UpdateState::Checking;
        self.error.clear();
        let (tx, rx) = channel();
        self.rx = Some(rx);
        let backend = Arc::clone(&self.backend);
        std::thread::spawn(move || {
            let _ = tx.send(Msg::Checked(backend.fetch_latest()));
        });
    }

    pub fn download(&mut self) {
        let Some(info) = self.release.clone() else { return };
        if self.state != UpdateState::Available && self.state != UpdateState::Error {
            return;
        }
        self.state = UpdateState::Downloading;
        self.progress = 0.0;
        self.cancel.store(false, Ordering::Relaxed);
        let (tx, rx) = channel();
        self.rx = Some(rx);
        let (backend, cancel) = (Arc::clone(&self.backend), Arc::clone(&self.cancel));
        std::thread::spawn(move || {
            let progress_tx = tx.clone();
            let result = backend.download(
                &info,
                &mut |p| {
                    let _ = progress_tx.send(Msg::Progress(p));
                },
                &|| cancel.load(Ordering::Relaxed),
            );
            let _ = tx.send(Msg::Downloaded(result));
        });
    }

    pub fn cancel(&mut self) {
        self.cancel.store(true, Ordering::Relaxed);
    }

    /// Apply results from the worker thread. Returns `true` if the state changed.
    pub fn poll(&mut self) -> bool {
        let Some(rx) = &self.rx else { return false };
        let msgs: Vec<Msg> = rx.try_iter().collect();
        let before = (self.state, self.progress.to_bits());
        for msg in msgs {
            match msg {
                Msg::Progress(p) => self.progress = p,
                Msg::Checked(Ok(Some(info))) if updater::is_newer(&info.version, &self.current_version) => {
                    self.release = Some(info);
                    self.state = UpdateState::Available;
                }
                Msg::Checked(Ok(_)) => self.state = UpdateState::UpToDate,
                Msg::Checked(Err(e)) => {
                    self.error = e.to_string();
                    self.state = UpdateState::Error;
                }
                Msg::Downloaded(Ok(path)) => {
                    self.installer = Some(path);
                    self.progress = 1.0;
                    self.state = UpdateState::Ready;
                }
                Msg::Downloaded(Err(UpdateError::Cancelled)) => self.state = UpdateState::Available,
                Msg::Downloaded(Err(e)) => {
                    self.error = e.to_string();
                    self.state = UpdateState::Error;
                }
            }
        }
        before != (self.state, self.progress.to_bits())
    }

    /// Start the downloaded installer; the caller must quit the app afterwards.
    pub fn install(&self) -> Result<(), UpdateError> {
        match (&self.state, &self.installer) {
            (UpdateState::Ready, Some(path)) => updater::launch_installer(path),
            _ => Err(UpdateError::msg("no update is ready to install")),
        }
    }
}

/// Should the background check run now?
pub fn auto_check_due(auto_update: bool, last_check: f64, now: f64) -> bool {
    auto_update && now - last_check >= AUTO_CHECK_INTERVAL_SECONDS
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::{Duration, Instant};

    struct Fake {
        latest: Result<Option<ReleaseInfo>, UpdateError>,
        download: Result<PathBuf, UpdateError>,
    }
    impl Backend for Fake {
        fn fetch_latest(&self) -> Result<Option<ReleaseInfo>, UpdateError> {
            self.latest.clone()
        }
        fn download(
            &self,
            _i: &ReleaseInfo,
            on_progress: &mut dyn FnMut(f64),
            cancelled: &dyn Fn() -> bool,
        ) -> Result<PathBuf, UpdateError> {
            on_progress(0.5);
            if cancelled() {
                return Err(UpdateError::Cancelled);
            }
            self.download.clone()
        }
    }

    fn release(v: &str) -> ReleaseInfo {
        ReleaseInfo {
            version: v.into(),
            tag: format!("v{v}"),
            notes: String::new(),
            url: "https://github.com/x".into(),
            size: 1,
            sha256: None,
            page: "p".into(),
        }
    }
    fn manager(latest: Result<Option<ReleaseInfo>, UpdateError>, download: Result<PathBuf, UpdateError>) -> UpdateManager {
        UpdateManager::new(Arc::new(Fake { latest, download }), "0.4.0")
    }
    fn settle(m: &mut UpdateManager) {
        let start = Instant::now();
        while m.is_busy() && start.elapsed() < Duration::from_secs(5) {
            m.poll();
            std::thread::sleep(Duration::from_millis(5));
        }
        m.poll();
    }

    #[test]
    fn newer_release_becomes_available() {
        let mut m = manager(Ok(Some(release("0.5.0"))), Ok(PathBuf::from("x")));
        m.check();
        assert_eq!(m.state, UpdateState::Checking);
        settle(&mut m);
        assert_eq!(m.state, UpdateState::Available);
        assert_eq!(m.release.as_ref().unwrap().version, "0.5.0");
    }

    #[test]
    fn same_or_older_release_is_up_to_date() {
        for v in ["0.4.0", "0.3.0"] {
            let mut m = manager(Ok(Some(release(v))), Ok(PathBuf::from("x")));
            m.check();
            settle(&mut m);
            assert_eq!(m.state, UpdateState::UpToDate, "{v}");
        }
        let mut none = manager(Ok(None), Ok(PathBuf::from("x")));
        none.check();
        settle(&mut none);
        assert_eq!(none.state, UpdateState::UpToDate);
    }

    #[test]
    fn network_errors_are_reported() {
        let mut m = manager(Err(UpdateError::msg("offline")), Ok(PathBuf::from("x")));
        m.check();
        settle(&mut m);
        assert_eq!((m.state, m.error.as_str()), (UpdateState::Error, "offline"));
    }

    #[test]
    fn download_reaches_ready_and_install_needs_it() {
        let mut m = manager(Ok(Some(release("0.5.0"))), Ok(PathBuf::from("setup.exe")));
        assert!(m.install().is_err());
        m.check();
        settle(&mut m);
        m.download();
        assert_eq!(m.state, UpdateState::Downloading);
        settle(&mut m);
        assert_eq!((m.state, m.progress), (UpdateState::Ready, 1.0));
        assert_eq!(m.installer, Some(PathBuf::from("setup.exe")));
    }

    #[test]
    fn download_failure_can_be_retried() {
        let mut m = manager(Ok(Some(release("0.5.0"))), Err(UpdateError::msg("checksum mismatch")));
        m.check();
        settle(&mut m);
        m.download();
        settle(&mut m);
        assert_eq!(m.state, UpdateState::Error);
        m.download(); // the release is remembered, so "try again" works
        assert_eq!(m.state, UpdateState::Downloading);
        settle(&mut m);
    }

    #[test]
    fn cancelled_download_returns_to_available() {
        let mut m = manager(Ok(Some(release("0.5.0"))), Ok(PathBuf::from("x")));
        m.check();
        settle(&mut m);
        m.cancel.store(true, Ordering::Relaxed);
        m.state = UpdateState::Available;
        m.download(); // download() resets the cancel flag, so cancel after starting:
        m.cancel();
        settle(&mut m);
        assert!(matches!(m.state, UpdateState::Available | UpdateState::Ready));
    }

    #[test]
    fn download_is_ignored_without_a_release() {
        let mut m = manager(Ok(None), Ok(PathBuf::from("x")));
        m.download();
        assert_eq!(m.state, UpdateState::Idle);
    }

    #[test]
    fn automatic_checks_run_at_most_daily() {
        assert!(auto_check_due(true, 0.0, 100_000.0));
        assert!(!auto_check_due(true, 100_000.0, 100_000.0 + 3600.0));
        assert!(!auto_check_due(false, 0.0, 1e12));
        assert!(auto_check_due(true, 1000.0, 1000.0 + AUTO_CHECK_INTERVAL_SECONDS));
    }
}
