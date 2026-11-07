import hashlib
import http.server
import threading
from pathlib import Path

import pytest

from eyecare.core import updater as u


def release(tag="v0.3.0", digest=None, assets=None, **extra):
    asset = {"name": u.ASSET_NAME, "size": 5, "digest": digest,
             "browser_download_url": f"https://github.com/{u.REPO}/releases/download/{tag}/{u.ASSET_NAME}"}
    return {"tag_name": tag, "body": "notes", "html_url": "https://github.com/x/y",
            "assets": [asset] if assets is None else assets, **extra}


def test_parse_version_and_compare():
    assert u.parse_version("v1.2.3") == (1, 2, 3)
    assert u.parse_version("1.2.0") == (1, 2)
    assert u.parse_version("2.0.0-beta.1") == (2,)
    with pytest.raises(ValueError):
        u.parse_version("latest")
    assert u.is_newer("v0.10.0", "0.9.9")
    assert u.is_newer("0.3.0", "0.2.0")
    assert not u.is_newer("0.2.0", "0.2.0")
    assert not u.is_newer("0.2", "0.2.0")
    assert not u.is_newer("junk", "0.2.0")


def test_release_parsing():
    info = u.release_from_json(release(digest="sha256:ABCD"))
    assert info.version == "0.3.0" and info.sha256 == "abcd" and info.size == 5


def test_release_rejects_drafts_prereleases_and_missing_asset():
    assert u.release_from_json(release(draft=True)) is None
    assert u.release_from_json(release(prerelease=True)) is None
    assert u.release_from_json(release(assets=[])) is None
    assert u.release_from_json(release(assets=[{"name": "other.zip"}])) is None
    assert u.release_from_json("nonsense") is None


def test_release_rejects_untrusted_asset_host():
    data = release()
    data["assets"][0]["browser_download_url"] = "https://evil.example.com/EyeCare-Setup.exe"
    assert u.release_from_json(data) is None
    data["assets"][0]["browser_download_url"] = "http://github.com/EyeCare-Setup.exe"
    assert u.release_from_json(data) is None


class _Handler(http.server.BaseHTTPRequestHandler):
    payload = b"hello"

    def do_GET(self):  # noqa: N802
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "https://evil.example.com/x")
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Length", str(len(self.payload)))
        self.end_headers()
        self.wfile.write(self.payload)

    def log_message(self, *a):
        pass


@pytest.fixture
def server():
    srv = http.server.HTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


def _info(url, payload=b"hello", sha="auto", size=None):
    digest = hashlib.sha256(payload).hexdigest() if sha == "auto" else sha
    return u.ReleaseInfo("0.3.0", "v0.3.0", "", url, len(payload) if size is None else size, digest, "p")


KW = dict(allowed={"127.0.0.1"}, allow_insecure=True)


def test_download_verifies_and_reports_progress(server, tmp_path):
    seen = []
    out = u.download(_info(server + "/f"), tmp_path / "s.exe", seen.append, **KW)
    assert out.read_bytes() == b"hello" and seen[-1] == 1.0
    assert not list(tmp_path.glob("*.part"))


def test_download_rejects_bad_checksum(server, tmp_path):
    with pytest.raises(u.UpdateError, match="checksum"):
        u.download(_info(server + "/f", sha="0" * 64), tmp_path / "s.exe", **KW)
    assert not (tmp_path / "s.exe").exists() and not list(tmp_path.glob("*.part"))


def test_download_rejects_wrong_size(server, tmp_path):
    with pytest.raises(u.UpdateError, match="size"):
        u.download(_info(server + "/f", size=99), tmp_path / "s.exe", **KW)


def test_download_blocks_untrusted_redirect(server, tmp_path):
    with pytest.raises(u.UpdateError):
        u.download(_info(server + "/redirect"), tmp_path / "s.exe", **KW)


def test_download_blocks_untrusted_start_url(tmp_path):
    with pytest.raises(u.UpdateError, match="untrusted"):
        u.download(_info("https://evil.example.com/a.exe"), tmp_path / "s.exe")


def test_download_can_be_cancelled(server, tmp_path):
    with pytest.raises(u.Cancelled):
        u.download(_info(server + "/f"), tmp_path / "s.exe", cancelled=lambda: True, **KW)
    assert not list(tmp_path.glob("*.part"))


def test_fetch_latest_rejects_untrusted_url():
    with pytest.raises(u.UpdateError):
        u.fetch_latest(url="https://evil.example.com/latest")


def test_installer_command_shape():
    cmd = u.installer_command(Path("C:/Temp/EyeCare-Setup.exe"))
    assert "/VERYSILENT" in cmd and "/CLOSEAPPLICATIONS" in cmd and cmd.startswith("ping")


def test_self_update_only_when_frozen_windows():
    assert u.can_self_update() is False
