import yt_dlp

FAIL_URLS = set()
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
        if url in FAIL_URLS:
            FAIL_URLS.discard(url)
            raise yt_dlp.utils.DownloadError("HTTP Error 403")
        gate = GATES.get(url)
        for hook in self.opts.get("progress_hooks", []):
            hook({"status": "downloading", "downloaded_bytes": 50,
                  "total_bytes": 100, "speed": 1048576, "eta": 5})
            if gate is not None:
                gate.wait(timeout=5)
            hook({"status": "finished", "filename": "out.mp4"})
