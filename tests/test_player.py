import threading
import time
import tempfile
from pathlib import Path

import urllib.request

import backend.player as pl
from backend.player import PlayerSession
from backend.config import Config, DEFAULTS
from fakes import FakePlayYDL


def _serve(directory: Path):
    handler = pl._make_handler(directory)
    server = pl.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def _get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def test_range_206_and_full_200(tmp_path):
    f = tmp_path / "video.mp4"
    f.write_bytes(b"0123456789" * 10)  # 100 bytes
    server = _serve(tmp_path)
    try:
        base = f"http://127.0.0.1:{server.server_address[1]}/video.mp4"
        status, headers, body = _get(base)
        assert status == 200 and len(body) == 100
        assert headers.get("Accept-Ranges") == "bytes"
        status, headers, body = _get(base, {"Range": "bytes=10-19"})
        assert status == 206
        assert headers.get("Content-Range") == "bytes 10-19/100"
        assert body == b"0123456789"
    finally:
        server.shutdown()


def test_range_suffix_and_416(tmp_path):
    f = tmp_path / "video.mp4"
    f.write_bytes(b"0123456789" * 10)
    server = _serve(tmp_path)
    try:
        base = f"http://127.0.0.1:{server.server_address[1]}/video.mp4"
        status, headers, body = _get(base, {"Range": "bytes=-5"})
        assert status == 206 and body == b"56789"
        assert headers.get("Content-Range") == "bytes 95-99/100"
        status, _, _ = _get(base, {"Range": "bytes=500-600"})
        assert status == 416
    finally:
        server.shutdown()


def test_path_traversal_404(tmp_path):
    f = tmp_path / "video.mp4"
    f.write_bytes(b"x")
    secret = tmp_path.parent / "secret.txt"
    secret.write_text("s")
    server = _serve(tmp_path)
    try:
        base = f"http://127.0.0.1:{server.server_address[1]}/..%2fsecret.txt"
        status, _, _ = _get(base)
        assert status == 404
        status, _, _ = _get(f"http://127.0.0.1:{server.server_address[1]}/nope.mp4")
        assert status == 404
    finally:
        server.shutdown()


def wait_until(cond, timeout=5.0):
    end = time.time() + timeout
    while time.time() < end:
        if cond():
            return True
        time.sleep(0.02)
    return False


def make_session(events, fail=False):
    if fail:
        FakePlayYDL.fail_urls.add("https://example.com/v1")
    cfg = Config(path=Path(tempfile.gettempdir()) / "unused-cfg.json",
                 defaults={**DEFAULTS})
    s = PlayerSession("sess1", Path(tempfile.gettempdir()) / "play-test-sess1",
                      events.append, ydl_factory=FakePlayYDL)
    return s, cfg


def test_session_lifecycle(tmp_path):
    events = []
    s, cfg = make_session(events)
    s.start("https://example.com/v1", {}, cfg)
    assert wait_until(lambda: any(e["type"] == "play_ready" for e in events))
    assert (s.dir / "video.mp4").exists()
    assert s.port and s.filename == "video.mp4"
    s.stop()
    assert wait_until(lambda: not s.dir.exists())
    assert not any(e["type"] == "play_error" for e in events)


def test_session_progress_events(tmp_path):
    events = []
    s, cfg = make_session(events)
    s.start("https://example.com/v1", {}, cfg)
    assert wait_until(lambda: any(e["type"] == "play_ready" for e in events))
    progress = [e["percent"] for e in events if e["type"] == "play_progress"]
    assert 50.0 in progress and 100.0 in progress
    s.stop()


def test_session_error_humanized(tmp_path):
    events = []
    s, cfg = make_session(events, fail=True)
    s.start("https://example.com/v1", {}, cfg)
    assert wait_until(lambda: any(e["type"] == "play_error" for e in events))
    err = [e for e in events if e["type"] == "play_error"][0]["error"]
    assert "风控" in err
    s.stop()
