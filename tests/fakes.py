from collections import Counter
from pathlib import Path

import yt_dlp

class _CountingFailURLs(Counter):
    def add(self, url):
        self[url] += 1


FAIL_URLS = _CountingFailURLs()
COOKIE_FAIL_URLS = set()
FRESH_FAIL_URLS = _CountingFailURLs()
GATES = {}


class FakeYDL:
    instances = []

    def __init__(self, opts):
        self.opts = opts
        FakeYDL.instances.append(self)

    def extract_info(self, url, download=False):
        if "playlist" in url:
            return {"_type": "playlist", "title": "测试播放列表", "entries": [
                {"playlist_index": 1, "title": "v1", "duration": 10},
                {"playlist_index": 2, "title": "v2", "duration": 20},
            ]}
        return {"_type": "video", "title": "测试视频", "formats": []}

    def download(self, urls):
        url = urls[0]
        if url in COOKIE_FAIL_URLS:
            COOKIE_FAIL_URLS.discard(url)
            raise yt_dlp.utils.DownloadError(
                "Could not copy Chrome cookie database. See "
                "https://github.com/yt-dlp/yt-dlp/issues/7271 for more info")
        if FRESH_FAIL_URLS[url] > 0:
            FRESH_FAIL_URLS[url] -= 1
            raise yt_dlp.utils.DownloadError(
                "Fresh cookies (not necessarily logged in) are needed")
        if FAIL_URLS[url] > 0:
            FAIL_URLS[url] -= 1
            raise yt_dlp.utils.DownloadError("HTTP Error 403")
        gate = GATES.get(url)
        for hook in self.opts.get("progress_hooks", []):
            hook({"status": "downloading", "downloaded_bytes": 50,
                  "total_bytes": 100, "speed": 1048576, "eta": 5})
            if gate is not None:
                gate.wait(timeout=5)
            hook({"status": "finished", "filename": "out.mp4"})


class FakePlayYDL:
    instances = []
    fail_urls = set()

    def __init__(self, opts):
        self.opts = opts
        FakePlayYDL.instances.append(self)

    def extract_info(self, url, download=True):
        if url in FakePlayYDL.fail_urls:
            raise yt_dlp.utils.DownloadError(
                "Fresh cookies (not necessarily logged in) are needed")
        hooks = self.opts.get("progress_hooks", [])
        for h in hooks:
            h({"status": "downloading", "downloaded_bytes": 50,
               "total_bytes": 100})
        out = Path(self.opts["outtmpl"])
        out.parent.mkdir(parents=True, exist_ok=True)
        fp = out.parent / "video.mp4"
        fp.write_bytes(b"0123456789" * 10)
        for h in hooks:
            h({"status": "finished"})
        return {"requested_downloads": [{"filepath": str(fp)}],
                "title": "测试视频"}
