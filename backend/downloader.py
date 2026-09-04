from __future__ import annotations

import json
import os
import queue
import threading
import time
from pathlib import Path

import yt_dlp

from .config import TASKS_FILE
from .cookies import resolve_cookie_file
from .ffmpeg_mgr import find_ffmpeg
from .errors import humanize_error, is_cookie_db_error
from .models import Task, TaskStatus


class DownloadManager:
    ACTIVE = {TaskStatus.QUEUED, TaskStatus.PROBING,
              TaskStatus.WAITING, TaskStatus.DOWNLOADING}

    def __init__(self, config, push_event, ydl_factory=None,
                 max_workers=None, tasks_file: Path = TASKS_FILE):
        self.config = config
        self._push = push_event
        self._ydl_factory = ydl_factory or (lambda opts: yt_dlp.YoutubeDL(opts))
        self.tasks_file = Path(tasks_file)
        self.tasks: dict[str, Task] = {}
        self.order: list[str] = []
        self._q: queue.Queue[str] = queue.Queue()
        self._cancel: dict[str, threading.Event] = {}
        self._choice: dict[str, threading.Event] = {}
        self._selection: dict[str, list[int]] = {}
        self._retried: set[str] = set()
        self._cookie_fallback: set[str] = set()
        self._last_notify: dict[str, float] = {}
        self._lock = threading.Lock()
        self._persist_lock = threading.Lock()
        self._load_history()
        n = max_workers if max_workers is not None else int(config.get("max_concurrent"))
        for _ in range(max(1, n)):
            threading.Thread(target=self._worker, daemon=True).start()

    def add_task(self, url: str, options: dict | None = None) -> str:
        task = Task(url=url, options=dict(options or {}))
        with self._lock:
            self.tasks[task.id] = task
            self.order.append(task.id)
        self._cancel[task.id] = threading.Event()
        self._choice[task.id] = threading.Event()
        self._q.put(task.id)
        self._notify(task)
        return task.id

    def get_task_list(self) -> list[dict]:
        with self._lock:
            return [self.tasks[i].to_dict() for i in self.order]

    def has_active(self) -> bool:
        with self._lock:
            return any(t.status in self.ACTIVE for t in self.tasks.values())

    def pause_task(self, task_id: str):
        self._cancel[task_id].set()

    def resume_task(self, task_id: str):
        task = self.tasks[task_id]
        if task.status is not TaskStatus.CANCELLED:
            return
        self._cancel[task_id].clear()
        self._reset(task)
        self._q.put(task_id)

    def cancel_task(self, task_id: str):
        self._cancel[task_id].set()

    def retry_task(self, task_id: str):
        task = self.tasks[task_id]
        if task.status not in (TaskStatus.ERROR, TaskStatus.CANCELLED):
            return
        self._cancel[task_id].clear()
        self._retried.discard(task_id)
        task.error = ""
        self._reset(task)
        self._q.put(task_id)

    def submit_playlist_selection(self, task_id: str, entries: list[int]):
        self._selection[task_id] = list(entries or [])
        self._choice[task_id].set()

    def _worker(self):
        while True:
            try:
                task_id = self._q.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                self._process(self.tasks[task_id])
            except Exception:
                pass

    def _process(self, task: Task):
        if self._cancel[task.id].is_set():
            self._mark_cancelled(task)
            return
        task.transition(TaskStatus.PROBING)
        self._notify(task)
        try:
            info = self._probe(task)
        except yt_dlp.utils.DownloadCancelled:
            self._mark_cancelled(task)
            return
        except Exception as e:
            self._fail(task, str(e))
            return
        try:
            if not self._resolve_playlist(task, info):
                return
            task.transition(TaskStatus.DOWNLOADING)
            self._notify(task)
            ydl = self._ydl_factory(self._build_options(task))
            ydl.download([task.url])
            task.transition(TaskStatus.DONE)
            self._notify(task)
        except yt_dlp.utils.DownloadCancelled:
            self._mark_cancelled(task)
        except Exception as e:
            self._fail(task, str(e))

    def _probe(self, task: Task):
        opts = self._base_options(task)
        opts["skip_download"] = True
        ydl = self._ydl_factory(opts)
        info = ydl.extract_info(task.url, download=False)
        if self._cancel[task.id].is_set():
            raise yt_dlp.utils.DownloadCancelled()
        if info:
            task.title = info.get("title") or task.url
        self._notify(task)
        return info

    def _resolve_playlist(self, task: Task, info: dict) -> bool:
        if info.get("_type") != "playlist":
            return True
        sel = task.options.get("playlist_selection") or self._selection.get(task.id)
        if sel:
            self._selection[task.id] = sel
            return True
        entries = info.get("entries") or []
        self._push({"type": "need_playlist", "task_id": task.id,
                    "title": info.get("title"),
                    "entries": [{"index": e.get("playlist_index"),
                                 "title": e.get("title"),
                                 "duration": e.get("duration")} for e in entries]})
        task.transition(TaskStatus.WAITING)
        self._notify(task)
        while not self._choice[task.id].wait(0.2):
            if self._cancel[task.id].is_set():
                raise yt_dlp.utils.DownloadCancelled()
        return True

    def _base_options(self, task: Task | None = None) -> dict:
        opts = {
            "outtmpl": str(Path(self.config.get("download_dir")) /
                           "%(title)s [%(id)s].%(ext)s"),
            "retries": 3,
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
        }
        cookie_file = self.config.get("cookie_file")
        cookies_browser = self.config.get("cookies_browser")
        if task is not None and task.id in self._cookie_fallback:
            pass
        elif cookie_file:
            opts["cookiefile"] = resolve_cookie_file(
                cookie_file,
                self.config.get("cookie_file_format") or "netscape",
                task.url if task is not None else "")
        elif cookies_browser:
            opts["cookiesfrombrowser"] = (cookies_browser,)
        langs = self.config.get("subtitle_langs")
        if langs:
            opts["writesubtitles"] = True
            opts["subtitleslangs"] = [s.strip() for s in langs.split(",") if s.strip()]
        ff = find_ffmpeg(self.config)
        if ff:
            opts["ffmpeg_location"] = str(Path(ff).parent)
        return opts

    def _build_options(self, task: Task) -> dict:
        opts = self._base_options(task)
        opts["format"] = task.options.get("format") or "bestvideo*+bestaudio/best"
        if task.options.get("audio_only"):
            opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]
        sel = self._selection.get(task.id)
        if sel:
            opts["playlist_items"] = ",".join(str(i) for i in sorted(sel))
        opts["progress_hooks"] = [lambda d: self._hook(task, d)]
        return opts

    def _hook(self, task: Task, d: dict):
        if self._cancel[task.id].is_set():
            raise yt_dlp.utils.DownloadCancelled()
        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            done = d.get("downloaded_bytes", 0)
            task.percent = round(done / total * 100, 1) if total else 0.0
            speed = d.get("speed")
            task.speed = f"{speed / 1048576:.1f}MB/s" if speed else ""
            eta = d.get("eta")
            task.eta = f"{eta // 60:02d}:{eta % 60:02d}" if eta else ""
            now = time.monotonic()
            if now - self._last_notify.get(task.id, 0) > 0.3:
                self._last_notify[task.id] = now
                self._notify(task)
        elif d.get("status") == "finished":
            task.percent = 100.0
            if d.get("filename"):
                task.filepath = d["filename"]
            self._notify(task)

    def _fail(self, task: Task, msg: str):
        if (is_cookie_db_error(msg) and task.id not in self._cookie_fallback
                and (self.config.get("cookie_file")
                     or self.config.get("cookies_browser"))):
            self._cookie_fallback.add(task.id)
            self._push({"type": "cookie_fallback"})
            task.error = "浏览器 Cookie 读取失败，本次已自动改用无 Cookie 模式重试"
            self._reset(task)
            self._q.put(task.id)
            return
        if task.id not in self._retried:
            self._retried.add(task.id)
            self._reset(task)
            self._q.put(task.id)
            return
        task.error = humanize_error(msg)[:400]
        task.transition(TaskStatus.ERROR)
        self._notify(task)

    def _reset(self, task: Task):
        task.percent = 0.0
        task.speed = ""
        task.eta = ""
        task.transition(TaskStatus.QUEUED)
        self._notify(task)

    def _mark_cancelled(self, task: Task):
        task.transition(TaskStatus.CANCELLED)
        self._notify(task)

    def _notify(self, task: Task):
        self._push({"type": "task_update", "task": task.to_dict()})
        self._persist()

    def _persist(self):
        with self._lock:
            data = {"order": list(self.order),
                    "tasks": [self.tasks[i].to_dict() for i in self.order]}
        tmp = self.tasks_file.with_suffix(".json.tmp")
        try:
            with self._persist_lock:
                self.tasks_file.parent.mkdir(parents=True, exist_ok=True)
                tmp.write_text(json.dumps(data, ensure_ascii=False), "utf-8")
                os.replace(tmp, self.tasks_file)
        except OSError:
            pass

    def _load_history(self):
        if not self.tasks_file.exists():
            return
        try:
            data = json.loads(self.tasks_file.read_text("utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        for d in data.get("tasks", []):
            t = Task(url=d["url"], options=d.get("options") or {})
            t.id = d["id"]
            t.title = d.get("title", "")
            t.filepath = d.get("filepath", "")
            try:
                t.status = TaskStatus(d.get("status", "cancelled"))
            except ValueError:
                t.status = TaskStatus.CANCELLED
            if t.status is not TaskStatus.DONE:
                t.status = TaskStatus.CANCELLED
            with self._lock:
                self.tasks[t.id] = t
                self.order.append(t.id)
            self._cancel[t.id] = threading.Event()
            self._choice[t.id] = threading.Event()
