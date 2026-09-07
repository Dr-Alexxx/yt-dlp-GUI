from __future__ import annotations

import threading

import webview
import yt_dlp

from .errors import humanize_error
from .ffmpeg_mgr import download_ffmpeg, find_ffmpeg

CONFIG_KEYS = {"download_dir", "cookie_file", "cookie_file_format",
               "cookies_browser", "ffmpeg_path", "max_concurrent"}


def _valid_url(url: str) -> bool:
    return bool(url) and url.lower().startswith(("http://", "https://"))


class JsApi:
    def __init__(self, manager, config, push_event,
                 dialog_holder=None, player_manager=None):
        self.manager = manager
        self.config = config
        self._push = push_event
        self._holder = dialog_holder
        self.player = player_manager
        self._ffmpeg_dl_lock = threading.Lock()

    def _pick(self, dialog_type, file_types=None):
        window = getattr(self._holder, "window", None) if self._holder else None
        if window is None:
            return {"ok": False, "error": "窗口未就绪"}
        try:
            result = window.create_file_dialog(dialog_type, allow_multiple=False,
                                               file_types=file_types or ())
        except Exception as e:
            return {"ok": False, "error": f"打开文件对话框失败：{e}"}
        if not result:
            return {"ok": True, "path": ""}
        return {"ok": True, "path": result[0]}

    def pick_cookie_file(self):
        return self._pick(webview.OPEN_DIALOG,
                          ("Cookie 文件 (*.txt;*.json)",))

    def pick_download_dir(self):
        return self._pick(webview.FOLDER_DIALOG)

    def start_play(self, url, options=None):
        url = (url or "").strip() if isinstance(url, str) else ""
        if not _valid_url(url):
            return {"ok": False, "error": "无效的 URL"}
        if self.player is None:
            return {"ok": False, "error": "播放模块未就绪"}
        return self.player.start_play(url, options)

    def stop_play(self, session_id):
        if self.player is None:
            return {"ok": False, "error": "播放模块未就绪"}
        return self.player.stop_play(session_id)

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

    def probe_url(self, url, ua=None):
        url = (url or "").strip() if isinstance(url, str) else ""
        if not _valid_url(url):
            return {"ok": False, "error": "无效的 URL"}
        opts = {"quiet": True, "no_warnings": True,
                "skip_download": True, "noplaylist": True}
        if ua:
            opts["http_headers"] = {"User-Agent": ua}
        try:
            info = yt_dlp.YoutubeDL(opts).extract_info(url, download=False)
        except Exception as e:
            return {"ok": False, "error": humanize_error(str(e))}
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
            if not self._ffmpeg_dl_lock.acquire(blocking=False):
                self._push({"type": "ffmpeg_progress",
                            "percent": -1, "error": "下载进行中"})
                return

            def cb(percent):
                self._push({"type": "ffmpeg_progress", "percent": percent})
            try:
                path = download_ffmpeg(self.config, cb)
                self._push({"type": "ffmpeg_progress",
                            "percent": 100.0, "path": path})
            except Exception as e:
                self._push({"type": "ffmpeg_progress",
                            "percent": -1, "error": str(e)})
            finally:
                self._ffmpeg_dl_lock.release()
        threading.Thread(target=work, daemon=True).start()
        return {"ok": True}
