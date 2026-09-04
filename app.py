from __future__ import annotations

import ctypes
import json
import sys
from pathlib import Path

import webview

from backend.api import JsApi
from backend.config import Config
from backend.downloader import DownloadManager

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist" / "index.html"


def make_push(window):
    def push(event):
        try:
            window.evaluate_js(
                "window.__pushEvent(" +
                json.dumps(event, ensure_ascii=False) + ")")
        except Exception:
            pass
    return push


def main():
    dev = "--dev" in sys.argv
    url = "http://localhost:5173" if dev else str(DIST)
    window = webview.create_window("yt-dlp 下载器", url,
                                   width=1100, height=750)
    push = make_push(window)
    config = Config()
    manager = DownloadManager(config, push)
    api = JsApi(manager, config, push)

    def on_closing():
        if not manager.has_active():
            return True
        MB_YESNO, MB_ICONQUESTION, MB_TOPMOST = 0x4, 0x20, 0x40000
        IDYES = 6
        r = ctypes.windll.user32.MessageBoxW(
            0, "有任务进行中，确定退出？", "yt-dlp 下载器",
            MB_YESNO | MB_ICONQUESTION | MB_TOPMOST)
        return r == IDYES

    window.events.closing += on_closing
    webview.start(debug=dev)


if __name__ == "__main__":
    main()
