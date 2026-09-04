from __future__ import annotations

import threading

import yt_dlp

from .ffmpeg_mgr import download_ffmpeg, find_ffmpeg

CONFIG_KEYS = {"download_dir", "cookie_file", "cookies_browser",
               "ffmpeg_path", "max_concurrent", "subtitle_langs"}


def _valid_url(url: str) -> bool:
    return bool(url) and url.lower().startswith(("http://", "https://"))


class JsApi:
    def __init__(self, manager, config, push_event):
        self.manager = manager
        self.config = config
        self._push = push_event

    def add_task(self, url, options=None):
        url = (url or "").strip() if isinstance(url, str) else ""
        if not _valid_url(url):
            return {"ok": False, "error": "无效的 URL"}
        return {"ok": True, "task_id": self.manager.add_task(url, options)}

    def add_batch(self, urls, options=None):
        ids, errors = [], []
        for line in (urls or "").splitlines():
            line = line.strip()
            if not line:
                continue
            r = self.add_task(line, options)
            if r["ok"]:
                ids.append(r["task_id"])
            else:
                errors.append(r["error"])
        return {"ok": True, "task_ids": ids, "errors": errors}

    def get_task_list(self):
        return {"ok": True, "tasks": self.manager.get_task_list()}

    def pause_task(self, task_id):
        if task_id not in self.manager.tasks:
            return {"ok": False, "error": "任务不存在"}
        self.manager.pause_task(task_id)
        return {"ok": True}

    def resume_task(self, task_id):
        if task_id not in self.manager.tasks:
            return {"ok": False, "error": "任务不存在"}
        self.manager.resume_task(task_id)
        return {"ok": True}

    def cancel_task(self, task_id):
        if task_id not in self.manager.tasks:
            return {"ok": False, "error": "任务不存在"}
        self.manager.cancel_task(task_id)
        return {"ok": True}

    def retry_task(self, task_id):
        if task_id not in self.manager.tasks:
            return {"ok": False, "error": "任务不存在"}
        self.manager.retry_task(task_id)
        return {"ok": True}

    def submit_playlist_selection(self, task_id, entries):
        if task_id not in self.manager.tasks:
            return {"ok": False, "error": "任务不存在"}
        self.manager.submit_playlist_selection(task_id, entries)
        return {"ok": True}

    def probe_url(self, url):
        url = (url or "").strip() if isinstance(url, str) else ""
        if not _valid_url(url):
            return {"ok": False, "error": "无效的 URL"}
        opts = {"quiet": True, "no_warnings": True,
                "skip_download": True, "noplaylist": True}
        try:
            info = yt_dlp.YoutubeDL(opts).extract_info(url, download=False)
        except Exception as e:
            return {"ok": False, "error": str(e)}
        formats = [{"format_id": f.get("format_id"), "ext": f.get("ext"),
                    "resolution": f.get("resolution") or f.get("format_note"),
                    "filesize": f.get("filesize") or f.get("filesize_approx"),
                    "vcodec": f.get("vcodec"), "acodec": f.get("acodec")}
                   for f in (info.get("formats") or [])]
        return {"ok": True, "info": {"title": info.get("title"),
                                     "duration": info.get("duration"),
                                     "formats": formats}}

    def get_config(self):
        return {"ok": True, "config": self.config.data}

    def save_config(self, patch):
        for key, value in (patch or {}).items():
            if key in CONFIG_KEYS:
                self.config.set(key, value)
        return {"ok": True}

    def check_ffmpeg(self):
        return {"ok": True, "path": find_ffmpeg(self.config)}

    def download_ffmpeg(self):
        def work():
            def cb(percent):
                self._push({"type": "ffmpeg_progress", "percent": percent})
            try:
                path = download_ffmpeg(self.config, cb)
                self._push({"type": "ffmpeg_progress",
                            "percent": 100.0, "path": path})
            except Exception as e:
                self._push({"type": "ffmpeg_progress",
                            "percent": -1, "error": str(e)})
        threading.Thread(target=work, daemon=True).start()
        return {"ok": True}
