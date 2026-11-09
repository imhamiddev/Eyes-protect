//! Update logic: find the newest GitHub release, download it safely, run the installer.
//!
//! Downloads are restricted to HTTPS GitHub hosts (including every redirect hop) and verified
//! against the SHA-256 digest that GitHub publishes for each release asset.

use serde_json::Value;
use sha2::{Digest, Sha256};
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::time::Duration;
use url::Url;

use super::changelog::extract_bullets;

pub const REPO: &str = "imhamiddev/Eyes-protect";
pub const API_LATEST: &str = "https://api.github.com/repos/imhamiddev/Eyes-protect/releases/latest";
pub const RELEASE_PAGE: &str = "https://github.com/imhamiddev/Eyes-protect/releases/latest";
pub const ASSET_NAME: &str = "EyeCare-Setup.exe";
pub const MAX_DOWNLOAD_BYTES: u64 = 300 * 1024 * 1024;
pub const USER_AGENT: &str = "EyeCare-updater";
const MAX_REDIRECTS: usize = 5;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum UpdateError {
    Failed(String),
    Cancelled,
}

impl UpdateError {
    pub fn msg(text: impl Into<String>) -> Self {
        UpdateError::Failed(text.into())
    }
}

impl std::fmt::Display for UpdateError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            UpdateError::Failed(m) => f.write_str(m),
            UpdateError::Cancelled => f.write_str("cancelled"),
        }
    }
}
impl std::error::Error for UpdateError {}

/// Which hosts we are willing to talk to.
#[derive(Debug, Clone)]
pub struct Policy {
    pub allowed: Vec<String>,
    pub allow_insecure: bool,
}

impl Policy {
    /// HTTPS GitHub hosts only (the production policy).
    pub fn github() -> Self {
        Self {
            allowed: ["api.github.com", "github.com", "objects.githubusercontent.com", "release-assets.githubusercontent.com"]
                .into_iter()
                .map(String::from)
                .collect(),
            allow_insecure: false,
        }
    }

    /// Plain-HTTP access to specific hosts (tests talk to 127.0.0.1).
    pub fn insecure_for(hosts: &[&str]) -> Self {
        Self { allowed: hosts.iter().map(|h| h.to_string()).collect(), allow_insecure: true }
    }

    pub fn host_ok(&self, url: &str) -> bool {
        let Ok(parsed) = Url::parse(url) else { return false };
        let scheme_ok = parsed.scheme() == "https" || (self.allow_insecure && parsed.scheme() == "http");
        scheme_ok && parsed.host_str().is_some_and(|h| self.allowed.iter().any(|a| a.eq_ignore_ascii_case(h)))
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ReleaseInfo {
    pub version: String,
    pub tag: String,
    pub notes: String,
    pub url: String,
    pub size: u64,
    pub sha256: Option<String>,
    pub page: String,
}

// -- versions ---------------------------------------------------------------
/// `"v1.2.3"` / `"1.2"` / `"1.2.3-beta"` -> `[1, 2, 3]`; trailing zeros are dropped.
pub fn parse_version(text: &str) -> Result<Vec<u64>, UpdateError> {
    let core = text.trim().trim_start_matches(['v', 'V']);
    let core = core.split('-').next().unwrap_or("");
    let core = core.split('+').next().unwrap_or("");
    let mut nums: Vec<u64> = Vec::new();
    let mut digits = String::new();
    for ch in core.chars().chain(std::iter::once(' ')) {
        if ch.is_ascii_digit() {
            digits.push(ch);
        } else if !digits.is_empty() {
            nums.push(digits.parse().map_err(|_| UpdateError::msg(format!("not a version: {text:?}")))?);
            digits.clear();
        }
    }
    if nums.is_empty() {
        return Err(UpdateError::msg(format!("not a version: {text:?}")));
    }
    while nums.len() > 1 && nums.last() == Some(&0) {
        nums.pop();
    }
    Ok(nums)
}

pub fn is_newer(remote: &str, local: &str) -> bool {
    match (parse_version(remote), parse_version(local)) {
        (Ok(r), Ok(l)) => r > l,
        _ => false,
    }
}

// -- release lookup -----------------------------------------------------------
/// Extract the installer asset from a GitHub release payload (`None` if absent).
pub fn release_from_json(data: &Value) -> Option<ReleaseInfo> {
    let obj = data.as_object()?;
    let flag = |k: &str| obj.get(k).and_then(Value::as_bool).unwrap_or(false);
    if flag("draft") || flag("prerelease") {
        return None;
    }
    let text = |v: Option<&Value>| v.and_then(Value::as_str).unwrap_or("").to_string();
    let tag = text(obj.get("tag_name"));
    for asset in obj.get("assets").and_then(Value::as_array).into_iter().flatten() {
        if asset.get("name").and_then(Value::as_str) != Some(ASSET_NAME) {
            continue;
        }
        let digest = text(asset.get("digest"));
        let sha = digest.strip_prefix("sha256:").map(str::to_lowercase);
        let url = text(asset.get("browser_download_url"));
        if !Policy::github().host_ok(&url) {
            return None;
        }
        let page = text(obj.get("html_url"));
        return Some(ReleaseInfo {
            version: tag.trim_start_matches(['v', 'V']).to_string(),
            tag,
            notes: text(obj.get("body")),
            url,
            size: asset.get("size").and_then(Value::as_u64).unwrap_or(0),
            sha256: sha,
            page: if page.is_empty() { RELEASE_PAGE.to_string() } else { page },
        });
    }
    None
}

/// GET `url`, following redirects by hand so that every hop is checked against `policy`.
fn http_get(url: &str, policy: &Policy, timeout: Duration, accept: Option<&str>) -> Result<ureq::Response, UpdateError> {
    let agent = ureq::AgentBuilder::new().redirects(0).timeout(timeout).build();
    let mut current = url.to_string();
    for _ in 0..=MAX_REDIRECTS {
        if !policy.host_ok(&current) {
            let host = Url::parse(&current).ok().and_then(|u| u.host_str().map(String::from)).unwrap_or_default();
            return Err(UpdateError::msg(format!("blocked redirect to {host}")));
        }
        let mut req = agent.get(&current).set("User-Agent", USER_AGENT);
        if let Some(a) = accept {
            req = req.set("Accept", a);
        }
        let resp = req.call().map_err(|e| UpdateError::msg(e.to_string()))?;
        if matches!(resp.status(), 301 | 302 | 303 | 307 | 308) {
            let location = resp.header("Location").ok_or_else(|| UpdateError::msg("redirect without a location"))?;
            let base = Url::parse(&current).map_err(|e| UpdateError::msg(e.to_string()))?;
            current = base.join(location).map_err(|e| UpdateError::msg(e.to_string()))?.to_string();
            continue;
        }
        return Ok(resp);
    }
    Err(UpdateError::msg("too many redirects"))
}

/// Newest published release with an installer, or `None` if there isn't one.
pub fn fetch_latest(timeout: Duration, url: &str, policy: &Policy) -> Result<Option<ReleaseInfo>, UpdateError> {
    if !policy.host_ok(url) {
        return Err(UpdateError::msg("untrusted update URL"));
    }
    let resp = http_get(url, policy, timeout, Some("application/vnd.github+json"))?;
    let mut body = String::new();
    resp.into_reader().take(2_000_000).read_to_string(&mut body).map_err(|e| UpdateError::msg(e.to_string()))?;
    let json: Value = serde_json::from_str(&body).map_err(|e| UpdateError::msg(e.to_string()))?;
    Ok(release_from_json(&json))
}

/// [`fetch_latest`] against the real GitHub API.
pub fn fetch_latest_release() -> Result<Option<ReleaseInfo>, UpdateError> {
    fetch_latest(Duration::from_secs(12), API_LATEST, &Policy::github())
}

// -- download -----------------------------------------------------------------
fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

fn part_path(dest: &Path) -> PathBuf {
    let mut name = dest.file_name().map(|n| n.to_os_string()).unwrap_or_default();
    name.push(".part");
    dest.with_file_name(name)
}

/// Download the installer to `dest` and verify size + SHA-256. Returns the path.
pub fn download(
    info: &ReleaseInfo,
    dest: &Path,
    on_progress: &mut dyn FnMut(f64),
    cancelled: &dyn Fn() -> bool,
    timeout: Duration,
    policy: &Policy,
) -> Result<PathBuf, UpdateError> {
    if !policy.host_ok(&info.url) {
        return Err(UpdateError::msg("untrusted download URL"));
    }
    if let Some(parent) = dest.parent() {
        std::fs::create_dir_all(parent).map_err(|e| UpdateError::msg(e.to_string()))?;
    }
    let part = part_path(dest);
    let result = download_to(info, dest, &part, on_progress, cancelled, timeout, policy);
    if result.is_err() {
        let _ = std::fs::remove_file(&part);
    }
    result
}

fn download_to(
    info: &ReleaseInfo,
    dest: &Path,
    part: &Path,
    on_progress: &mut dyn FnMut(f64),
    cancelled: &dyn Fn() -> bool,
    timeout: Duration,
    policy: &Policy,
) -> Result<PathBuf, UpdateError> {
    let io = |e: std::io::Error| UpdateError::msg(e.to_string());
    let resp = http_get(&info.url, policy, timeout, None)?;
    let total: u64 = resp.header("Content-Length").and_then(|v| v.parse().ok()).unwrap_or(info.size);
    if total > MAX_DOWNLOAD_BYTES {
        return Err(UpdateError::msg("download is unexpectedly large"));
    }
    let mut reader = resp.into_reader();
    let mut out = std::fs::File::create(part).map_err(io)?;
    let mut sha = Sha256::new();
    let (mut done, mut buf) = (0u64, vec![0u8; 256 * 1024]);
    loop {
        if cancelled() {
            return Err(UpdateError::Cancelled);
        }
        let n = reader.read(&mut buf).map_err(io)?;
        if n == 0 {
            break;
        }
        done += n as u64;
        if done > MAX_DOWNLOAD_BYTES {
            return Err(UpdateError::msg("download is unexpectedly large"));
        }
        out.write_all(&buf[..n]).map_err(io)?;
        sha.update(&buf[..n]);
        if total > 0 {
            on_progress((done as f64 / total as f64).min(1.0));
        }
    }
    drop(out);
    if info.size > 0 && done != info.size {
        return Err(UpdateError::msg("downloaded file has the wrong size"));
    }
    if let Some(expected) = &info.sha256 {
        if !hex(&sha.finalize()).eq_ignore_ascii_case(expected) {
            return Err(UpdateError::msg("checksum mismatch - the download was discarded"));
        }
    }
    std::fs::rename(part, dest).map_err(io)?;
    on_progress(1.0);
    Ok(dest.to_path_buf())
}

// -- install ------------------------------------------------------------------
/// Only an installed (release) Windows build can replace itself.
pub fn can_self_update() -> bool {
    cfg!(windows) && !cfg!(debug_assertions)
}

/// Shell line that waits briefly for this process to exit, then runs the silent installer.
pub fn installer_command(installer: &Path) -> String {
    format!(
        "ping -n 4 127.0.0.1 >nul & start \"\" \"{}\" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS",
        installer.display()
    )
}

/// Start the installer detached; the caller must quit the app right after.
#[cfg(windows)]
pub fn launch_installer(installer: &Path) -> Result<(), UpdateError> {
    use std::os::windows::process::CommandExt;
    const CREATE_NO_WINDOW: u32 = 0x0800_0000;
    const DETACHED_PROCESS: u32 = 0x0000_0008;
    std::process::Command::new("cmd")
        .raw_arg(format!("/c {}", installer_command(installer)))
        .creation_flags(CREATE_NO_WINDOW | DETACHED_PROCESS)
        .spawn()
        .map(|_| ())
        .map_err(|e| UpdateError::msg(e.to_string()))
}

#[cfg(not(windows))]
pub fn launch_installer(_installer: &Path) -> Result<(), UpdateError> {
    Err(UpdateError::msg("installing updates is only supported on Windows"))
}

/// Short plain-text bullet list from a release body (markdown stripped).
pub fn summarize_notes(notes: &str, language: &str, limit: usize) -> Vec<String> {
    extract_bullets(notes, language, limit, 140)
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    use std::io::{BufRead, BufReader};
    use std::net::TcpListener;

    fn release(tag: &str, digest: Value, assets: Option<Value>, extra: Value) -> Value {
        let asset = json!({"name": ASSET_NAME, "size": 5, "digest": digest,
            "browser_download_url": format!("https://github.com/{REPO}/releases/download/{tag}/{ASSET_NAME}")});
        let mut v = json!({"tag_name": tag, "body": "notes", "html_url": "https://github.com/x/y",
            "assets": assets.unwrap_or_else(|| json!([asset]))});
        if let (Some(o), Some(e)) = (v.as_object_mut(), extra.as_object()) {
            o.extend(e.clone());
        }
        v
    }

    #[test]
    fn parse_version_and_compare() {
        assert_eq!(parse_version("v1.2.3").unwrap(), [1, 2, 3]);
        assert_eq!(parse_version("1.2.0").unwrap(), [1, 2]);
        assert_eq!(parse_version("2.0.0-beta.1").unwrap(), [2]);
        assert!(parse_version("latest").is_err());
        assert!(is_newer("v0.10.0", "0.9.9"));
        assert!(is_newer("0.3.0", "0.2.0"));
        assert!(!is_newer("0.2.0", "0.2.0"));
        assert!(!is_newer("0.2", "0.2.0"));
        assert!(!is_newer("junk", "0.2.0"));
    }

    #[test]
    fn release_parsing() {
        let info = release_from_json(&release("v0.3.0", json!("sha256:ABCD"), None, json!({}))).unwrap();
        assert_eq!((info.version.as_str(), info.sha256.as_deref(), info.size), ("0.3.0", Some("abcd"), 5));
    }

    #[test]
    fn release_rejects_drafts_prereleases_and_missing_asset() {
        assert!(release_from_json(&release("v0.3.0", json!(null), None, json!({"draft": true}))).is_none());
        assert!(release_from_json(&release("v0.3.0", json!(null), None, json!({"prerelease": true}))).is_none());
        assert!(release_from_json(&release("v0.3.0", json!(null), Some(json!([])), json!({}))).is_none());
        assert!(release_from_json(&release("v0.3.0", json!(null), Some(json!([{"name": "other.zip"}])), json!({}))).is_none());
        assert!(release_from_json(&json!("nonsense")).is_none());
    }

    #[test]
    fn release_rejects_untrusted_asset_host() {
        for bad in ["https://evil.example.com/EyeCare-Setup.exe", "http://github.com/EyeCare-Setup.exe"] {
            let mut data = release("v0.3.0", json!(null), None, json!({}));
            data["assets"][0]["browser_download_url"] = json!(bad);
            assert!(release_from_json(&data).is_none(), "{bad}");
        }
    }

    /// Tiny HTTP server: `/redirect` bounces to an untrusted host, everything else is 200 "hello".
    fn server() -> String {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let port = listener.local_addr().unwrap().port();
        std::thread::spawn(move || {
            for stream in listener.incoming().flatten() {
                let mut stream = stream;
                let mut line = String::new();
                let mut reader = BufReader::new(stream.try_clone().unwrap());
                let _ = reader.read_line(&mut line);
                loop {
                    let mut h = String::new();
                    if reader.read_line(&mut h).unwrap_or(0) <= 2 {
                        break;
                    }
                }
                let reply = if line.contains("/redirect") {
                    "HTTP/1.1 302 Found\r\nLocation: https://evil.example.com/x\r\nContent-Length: 0\r\nConnection: close\r\n\r\n".to_string()
                } else {
                    "HTTP/1.1 200 OK\r\nContent-Length: 5\r\nConnection: close\r\n\r\nhello".to_string()
                };
                let _ = stream.write_all(reply.as_bytes());
            }
        });
        format!("http://127.0.0.1:{port}")
    }

    fn info(url: &str, sha: Option<String>, size: u64) -> ReleaseInfo {
        ReleaseInfo { version: "0.3.0".into(), tag: "v0.3.0".into(), notes: String::new(), url: url.into(), size, sha256: sha, page: "p".into() }
    }
    fn hello_sha() -> String {
        hex(&Sha256::digest(b"hello"))
    }
    fn local() -> Policy {
        Policy::insecure_for(&["127.0.0.1"])
    }
    fn parts_in(dir: &Path) -> usize {
        std::fs::read_dir(dir).unwrap().flatten().filter(|e| e.file_name().to_string_lossy().ends_with(".part")).count()
    }

    #[test]
    fn download_verifies_and_reports_progress() {
        let (base, dir) = (server(), tempfile::tempdir().unwrap());
        let mut seen = Vec::new();
        let out = download(&info(&format!("{base}/f"), Some(hello_sha()), 5), &dir.path().join("s.exe"), &mut |p| seen.push(p), &|| false, Duration::from_secs(5), &local()).unwrap();
        assert_eq!(std::fs::read(out).unwrap(), b"hello");
        assert_eq!(*seen.last().unwrap(), 1.0);
        assert_eq!(parts_in(dir.path()), 0);
    }

    #[test]
    fn download_rejects_bad_checksum() {
        let (base, dir) = (server(), tempfile::tempdir().unwrap());
        let err = download(&info(&format!("{base}/f"), Some("0".repeat(64)), 5), &dir.path().join("s.exe"), &mut |_| {}, &|| false, Duration::from_secs(5), &local()).unwrap_err();
        assert!(err.to_string().contains("checksum"), "{err}");
        assert!(!dir.path().join("s.exe").exists());
        assert_eq!(parts_in(dir.path()), 0);
    }

    #[test]
    fn download_rejects_wrong_size() {
        let (base, dir) = (server(), tempfile::tempdir().unwrap());
        let err = download(&info(&format!("{base}/f"), Some(hello_sha()), 99), &dir.path().join("s.exe"), &mut |_| {}, &|| false, Duration::from_secs(5), &local()).unwrap_err();
        assert!(err.to_string().contains("size"), "{err}");
    }

    #[test]
    fn download_blocks_untrusted_redirect() {
        let (base, dir) = (server(), tempfile::tempdir().unwrap());
        let err = download(&info(&format!("{base}/redirect"), Some(hello_sha()), 5), &dir.path().join("s.exe"), &mut |_| {}, &|| false, Duration::from_secs(5), &local()).unwrap_err();
        assert!(err.to_string().contains("blocked redirect"), "{err}");
    }

    #[test]
    fn download_blocks_untrusted_start_url() {
        let dir = tempfile::tempdir().unwrap();
        let err = download(&info("https://evil.example.com/a.exe", None, 0), &dir.path().join("s.exe"), &mut |_| {}, &|| false, Duration::from_secs(5), &Policy::github()).unwrap_err();
        assert!(err.to_string().contains("untrusted"), "{err}");
    }

    #[test]
    fn download_can_be_cancelled() {
        let (base, dir) = (server(), tempfile::tempdir().unwrap());
        let err = download(&info(&format!("{base}/f"), Some(hello_sha()), 5), &dir.path().join("s.exe"), &mut |_| {}, &|| true, Duration::from_secs(5), &local()).unwrap_err();
        assert_eq!(err, UpdateError::Cancelled);
        assert_eq!(parts_in(dir.path()), 0);
    }

    #[test]
    fn fetch_latest_rejects_untrusted_url() {
        assert!(fetch_latest(Duration::from_secs(1), "https://evil.example.com/latest", &Policy::github()).is_err());
    }

    #[test]
    fn fetch_latest_parses_a_release_from_a_local_server() {
        // Serve a release JSON whose asset points at github.com, then parse it back.
        let body = release("v0.9.0", json!("sha256:ab"), None, json!({})).to_string();
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let port = listener.local_addr().unwrap().port();
        std::thread::spawn(move || {
            if let Some(Ok(mut s)) = listener.incoming().next() {
                let mut reader = BufReader::new(s.try_clone().unwrap());
                loop {
                    let mut h = String::new();
                    if reader.read_line(&mut h).unwrap_or(0) <= 2 {
                        break;
                    }
                }
                let reply = format!("HTTP/1.1 200 OK\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}", body.len(), body);
                let _ = s.write_all(reply.as_bytes());
            }
        });
        let url = format!("http://127.0.0.1:{port}/latest");
        let found = fetch_latest(Duration::from_secs(5), &url, &local()).unwrap().unwrap();
        assert_eq!((found.version.as_str(), found.sha256.as_deref()), ("0.9.0", Some("ab")));
    }

    #[test]
    fn installer_command_shape() {
        let cmd = installer_command(Path::new("C:/Temp/EyeCare-Setup.exe"));
        assert!(cmd.contains("/VERYSILENT") && cmd.contains("/CLOSEAPPLICATIONS") && cmd.starts_with("ping"));
    }

    #[test]
    fn self_update_only_in_release_windows_builds() {
        assert!(!can_self_update());
    }

    #[test]
    fn release_notes_are_summarized_like_the_changelog() {
        assert_eq!(summarize_notes("- a\n- b\n- c", "en", 2), ["a", "b"]);
    }
}
