"""Update logic: find the newest GitHub release, download it safely, run the installer.

Network access uses only the standard library. Downloads are restricted to HTTPS
GitHub hosts (including every redirect hop) and verified against the SHA-256 digest
that GitHub publishes for each release asset.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

REPO = "imhamiddev/Eyes-protect"
API_LATEST = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASE_PAGE = f"https://github.com/{REPO}/releases/latest"
ASSET_NAME = "EyeCare-Setup.exe"
ALLOWED_HOSTS = frozenset({
    "api.github.com", "github.com", "objects.githubusercontent.com",
    "release-assets.githubusercontent.com",
})
MAX_DOWNLOAD_BYTES = 300 * 1024 * 1024
USER_AGENT = "EyeCare-updater"


class UpdateError(Exception):
    pass


class Cancelled(UpdateError):
    pass


@dataclass(frozen=True)
class ReleaseInfo:
    version: str
    tag: str
    notes: str
    url: str
    size: int
    sha256: str | None
    page: str


# -- versions ---------------------------------------------------------------
def parse_version(text: str) -> tuple[int, ...]:
    """'v1.2.3' / '1.2' / '1.2.3-beta' -> (1, 2, 3). Raises ValueError if no digits."""
    core = text.strip().lstrip("vV").split("-")[0].split("+")[0]
    parts = re.findall(r"\d+", core)
    if not parts:
        raise ValueError(f"not a version: {text!r}")
    nums = [int(p) for p in parts]
    while len(nums) > 1 and nums[-1] == 0:
        nums.pop()
    return tuple(nums)


def is_newer(remote: str, local: str) -> bool:
    try:
        return parse_version(remote) > parse_version(local)
    except ValueError:
        return False


# -- release lookup -----------------------------------------------------------
def release_from_json(data: dict) -> ReleaseInfo | None:
    """Extract the installer asset from a GitHub release payload (None if absent)."""
    if not isinstance(data, dict) or data.get("draft") or data.get("prerelease"):
        return None
    tag = str(data.get("tag_name") or "")
    for asset in data.get("assets") or []:
        if asset.get("name") == ASSET_NAME:
            digest = str(asset.get("digest") or "")
            sha = digest.split(":", 1)[1].lower() if digest.startswith("sha256:") else None
            url = str(asset.get("browser_download_url") or "")
            if not _host_ok(url, ALLOWED_HOSTS):
                return None
            return ReleaseInfo(
                version=tag.lstrip("vV"), tag=tag, notes=str(data.get("body") or ""),
                url=url, size=int(asset.get("size") or 0), sha256=sha,
                page=str(data.get("html_url") or RELEASE_PAGE),
            )
    return None


def _host_ok(url: str, allowed, allow_insecure: bool = False) -> bool:
    parts = urlparse(url)
    if parts.scheme != "https" and not (allow_insecure and parts.scheme == "http"):
        return False
    return (parts.hostname or "").lower() in allowed


class _SafeRedirects(urllib.request.HTTPRedirectHandler):
    def __init__(self, allowed, allow_insecure: bool = False):
        super().__init__()
        self.allowed, self.allow_insecure = allowed, allow_insecure

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not _host_ok(newurl, self.allowed, self.allow_insecure):
            raise UpdateError(f"blocked redirect to {urlparse(newurl).hostname}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _opener(allowed=ALLOWED_HOSTS, allow_insecure: bool = False):
    return urllib.request.build_opener(_SafeRedirects(allowed, allow_insecure))


def fetch_latest(timeout: float = 12.0, url: str = API_LATEST, allowed=ALLOWED_HOSTS,
                 allow_insecure: bool = False) -> ReleaseInfo | None:
    """Newest published release with an installer, or None if there isn't one."""
    if not _host_ok(url, allowed, allow_insecure):
        raise UpdateError("untrusted update URL")
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json", "User-Agent": USER_AGENT})
    try:
        with _opener(allowed, allow_insecure).open(req, timeout=timeout) as resp:
            return release_from_json(json.loads(resp.read(2_000_000).decode("utf-8")))
    except UpdateError:
        raise
    except Exception as exc:  # network down, rate limit, bad JSON...
        raise UpdateError(str(exc)) from exc


# -- download -----------------------------------------------------------------
def download(info: ReleaseInfo, dest: Path, on_progress: Callable[[float], None] | None = None,
             cancelled: Callable[[], bool] | None = None, timeout: float = 20.0,
             allowed=ALLOWED_HOSTS, allow_insecure: bool = False) -> Path:
    """Download the installer to ``dest`` and verify size + SHA-256. Returns the path."""
    if not _host_ok(info.url, allowed, allow_insecure):
        raise UpdateError("untrusted download URL")
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(info.url, headers={"User-Agent": USER_AGENT})
    sha = hashlib.sha256()
    done = 0
    try:
        with _opener(allowed, allow_insecure).open(req, timeout=timeout) as resp, open(part, "wb") as out:
            total = int(resp.headers.get("Content-Length") or info.size or 0)
            if total > MAX_DOWNLOAD_BYTES:
                raise UpdateError("download is unexpectedly large")
            while True:
                if cancelled and cancelled():
                    raise Cancelled("cancelled")
                chunk = resp.read(256 * 1024)
                if not chunk:
                    break
                done += len(chunk)
                if done > MAX_DOWNLOAD_BYTES:
                    raise UpdateError("download is unexpectedly large")
                out.write(chunk)
                sha.update(chunk)
                if on_progress and total:
                    on_progress(min(1.0, done / total))
        if info.size and done != info.size:
            raise UpdateError("downloaded file has the wrong size")
        if info.sha256 and sha.hexdigest().lower() != info.sha256.lower():
            raise UpdateError("checksum mismatch - the download was discarded")
        part.replace(dest)
        if on_progress:
            on_progress(1.0)
        return dest
    except UpdateError:
        part.unlink(missing_ok=True)
        raise
    except Exception as exc:
        part.unlink(missing_ok=True)
        raise UpdateError(str(exc)) from exc


# -- install ------------------------------------------------------------------
def can_self_update() -> bool:
    """Only the installed (frozen) Windows build can replace itself."""
    return sys.platform == "win32" and bool(getattr(sys, "frozen", False))


def installer_command(installer: Path) -> str:
    """Shell line that waits briefly for this process to exit, then runs the silent installer."""
    return (f'ping -n 4 127.0.0.1 >nul & start "" "{installer}" '
            f'/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS')


def launch_installer(installer: Path) -> None:
    """Start the installer detached; the caller must quit the app right after."""
    if sys.platform != "win32":
        raise UpdateError("installing updates is only supported on Windows")
    flags = 0x08000000 | 0x00000008  # CREATE_NO_WINDOW | DETACHED_PROCESS
    subprocess.Popen(f"cmd /c {installer_command(installer)}", shell=True, creationflags=flags,
                     close_fds=True)
