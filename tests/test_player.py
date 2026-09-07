import threading
from pathlib import Path

import urllib.request

import backend.player as pl


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
