from __future__ import annotations

import re
import shutil
import tempfile
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

import yt_dlp

from .config import Config
from .errors import humanize_error
from .ffmpeg_mgr import find_ffmpeg


def _make_handler(directory: Path):
    class _Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            name = Path(unquote(urlparse(self.path).path)).name
            target = directory / name
            if not target.is_file():
                self.send_error(404)
                return
            size = target.stat().st_size
            start, end = 0, size - 1
            status = 200
            rng = self.headers.get("Range")
            if rng:
                m = re.match(r"bytes=(\d*)-(\d*)$", rng.strip())
                if m and (m.group(1) or m.group(2)):
                    if m.group(1):
                        start = int(m.group(1))
                        if m.group(2):
                            end = min(int(m.group(2)), size - 1)
                    else:
                        start = max(size - int(m.group(2)), 0)
                    status = 206
            if start > end or start >= size:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.end_headers()
                return
            self.send_response(status)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(end - start + 1))
            if status == 206:
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.end_headers()
            with open(target, "rb") as fh:
                fh.seek(start)
                remaining = end - start + 1
                while remaining > 0:
                    chunk = fh.read(min(65536, remaining))
                    if not chunk:
                        break
                    try:
                        self.wfile.write(chunk)
                    except (BrokenPipeError, ConnectionAbortedError):
                        return
                    remaining -= len(chunk)

    return _Handler


class PlayerSession:
    def __init__(self, session_id: str, work_dir: Path, push_event,
                 ydl_factory=None):
        self.id = session_id
        self.dir = work_dir
        self._push = push_event
        self._ydl_factory = ydl_factory or (lambda opts: yt_dlp.YoutubeDL(opts))
        self._cancel = threading.Event()
        self._thread: threading.Thread | None = None
        self.server = None
        self.port: int | None = None
        self.filename: str | None = None
        self.progress = 0.0
        self._last_notify = 0.0

    def start(self, url: str, options: dict, config: Config):
        self._thread = threading.Thread(
            target=self._run, args=(url, options, config), daemon=True)
        self._thread.start()

    def _hook(self, d: dict):
        if self._cancel.is_set():
            raise yt_dlp.utils.DownloadCancelled()
        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            done = d.get("downloaded_bytes", 0)
            self.progress = round(done / total * 100, 1) if total else 0.0
            now = time.monotonic()
            if now - self._last_notify > 0.3:
                self._last_notify = now
                self._push({"type": "play_progress", "session_id": self.id,
                            "percent": self.progress})
        elif d.get("status") == "finished":
            self._push({"type": "play_progress", "session_id": self.id,
                        "percent": 100.0})

    def _build_options(self, url: str, options: dict, config: Config) -> dict:
        opts = {
            "outtmpl": str(self.dir / "%(title).40s [%(id)s].%(ext)s"),
            "format": "bestvideo*+bestaudio/best",
            "retries": 3,
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
        }
        cookie_file = config.get("cookie_file")
        if cookie_file:
            from .cookies import resolve_cookie_file
            opts["cookiefile"] = resolve_cookie_file(
                cookie_file, config.get("cookie_file_format") or "netscape", url)
        elif config.get("cookies_browser"):
            opts["cookiesfrombrowser"] = (config.get("cookies_browser"),)
        if options.get("custom_ua") and options.get("ua_string"):
            opts["http_headers"] = {"User-Agent": options["ua_string"]}
        ff = find_ffmpeg(config)
        if ff:
            opts["ffmpeg_location"] = str(Path(ff).parent)
        opts["progress_hooks"] = [self._hook]
        return opts

    def _run(self, url: str, options: dict, config: Config):
        try:
            opts = self._build_options(url, options, config)
            ydl = self._ydl_factory(opts)
            info = ydl.extract_info(url, download=True)
            if self._cancel.is_set():
                return
            filepath = (info.get("requested_downloads") or [{}])[0].get("filepath")
            if not filepath:
                raise ValueError("未能获取输出文件")
            self.filename = Path(filepath).name
            handler = _make_handler(self.dir)
            self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
            self.port = self.server.server_address[1]
            threading.Thread(target=self.server.serve_forever, daemon=True).start()
            self._push({"type": "play_ready", "session_id": self.id,
                        "port": self.port, "filename": self.filename})
        except yt_dlp.utils.DownloadCancelled:
            return
        except Exception as e:
            if self._cancel.is_set():
                return
            self._push({"type": "play_error", "session_id": self.id,
                        "error": humanize_error(str(e))[:400]})

    def stop(self):
        self._cancel.set()
        if self.server is not None:
            self.server.shutdown()
            self.server = None
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=5)
        shutil.rmtree(self.dir, ignore_errors=True)


class PlayerManager:
    def __init__(self, config: Config, push_event, ydl_factory=None):
        self.config = config
        self._push = push_event
        self._ydl_factory = ydl_factory
        self.play_root = Path(tempfile.gettempdir()) / "yt-dlp-gui-play"
        self.sessions: dict[str, PlayerSession] = {}
        self.cleanup_all()

    def cleanup_all(self):
        shutil.rmtree(self.play_root, ignore_errors=True)
        self.sessions.clear()

    def has_active(self) -> bool:
        return bool(self.sessions)

    def start_play(self, url: str, options: dict | None = None) -> dict:
        if not find_ffmpeg(self.config):
            return {"ok": False,
                    "error": "FFmpeg 未就绪，无法在线播放。请在主界面横幅中先下载 FFmpeg。"}
        if self.sessions:
            return {"ok": False, "error": "已有播放会话进行中，请先关闭当前播放"}
        sid = uuid.uuid4().hex[:12]
        session = PlayerSession(sid, self.play_root / sid, self._push,
                                ydl_factory=self._ydl_factory)
        self.sessions[sid] = session
        session.start(url, dict(options or {}), self.config)
        return {"ok": True, "session_id": sid}

    def stop_play(self, session_id: str) -> dict:
        session = self.sessions.pop(session_id, None)
        if session is None:
            return {"ok": False, "error": "会话不存在"}
        session.stop()
        return {"ok": True}

    def shutdown(self):
        for sid in list(self.sessions):
            self.stop_play(sid)
