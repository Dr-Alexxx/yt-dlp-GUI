from types import SimpleNamespace

from backend.api import JsApi


class FakeConfig:
    def __init__(self):
        self.data = {"max_concurrent": 2}

    def set(self, key, value):
        self.data[key] = value


class FakeManager:
    def __init__(self):
        self.calls = []
        self.tasks = {"t1": object()}

    def add_task(self, url, options=None):
        self.calls.append(("add", url, options))
        return "newid"

    def get_task_list(self):
        self.calls.append(("list",))
        return [{"id": "t1"}]

    def pause_task(self, task_id):
        self.calls.append(("pause", task_id))

    def resume_task(self, task_id):
        self.calls.append(("resume", task_id))

    def cancel_task(self, task_id):
        self.calls.append(("cancel", task_id))

    def retry_task(self, task_id):
        self.calls.append(("retry", task_id))

    def submit_playlist_selection(self, task_id, entries):
        self.calls.append(("playlist", task_id, entries))


def make_api():
    m, cfg = FakeManager(), FakeConfig()
    return JsApi(m, cfg, lambda e: None), m


def test_add_task_rejects_invalid_url():
    api, m = make_api()
    assert api.add_task("")["ok"] is False
    assert api.add_task("ftp://x")["ok"] is False
    assert api.add_task(None)["ok"] is False
    assert m.calls == []


def test_add_task_forwards_valid_url():
    api, m = make_api()
    r = api.add_task(" https://example.com/v ", {"format": "18"})
    assert r == {"ok": True, "task_id": "newid"}
    assert m.calls == [("add", "https://example.com/v", {"format": "18"})]


def test_add_batch_splits_lines():
    api, m = make_api()
    r = api.add_batch("https://a.com/1\n\nhttps://b.com/2\nbad")
    assert r["ok"] is True
    assert len(r["task_ids"]) == 2
    assert len(r["errors"]) == 1


def test_task_id_required():
    api, m = make_api()
    assert api.pause_task("nope")["ok"] is False
    assert api.cancel_task("nope")["ok"] is False
    assert api.retry_task("nope")["ok"] is False
    assert api.resume_task("nope")["ok"] is False
    assert api.submit_playlist_selection("nope", [1])["ok"] is False
    assert m.calls == []


def test_valid_task_calls_forwarded():
    api, m = make_api()
    assert api.pause_task("t1")["ok"] is True
    assert api.submit_playlist_selection("t1", [1, 3])["ok"] is True
    assert ("pause", "t1") in m.calls
    assert ("playlist", "t1", [1, 3]) in m.calls


def test_probe_url(monkeypatch):
    class FakeYDL:
        def __init__(self, opts):
            self.opts = opts

        def extract_info(self, url, download=False):
            return {"title": "T", "duration": 5, "formats": [
                {"format_id": "18", "ext": "mp4", "resolution": "360p",
                 "filesize": 1, "vcodec": "avc1", "acodec": "mp4a"}]}

    monkeypatch.setattr("backend.api.yt_dlp",
                        SimpleNamespace(YoutubeDL=lambda opts: FakeYDL(opts)))
    api, _ = make_api()
    r = api.probe_url("https://example.com/v")
    assert r["ok"] is True
    assert r["info"]["title"] == "T"
    assert r["info"]["formats"][0]["format_id"] == "18"
    assert api.probe_url("bad")["ok"] is False


def test_save_config_whitelist():
    api, _ = make_api()
    r = api.save_config({"ffmpeg_path": "C:/bin", "hacker_key": "x"})
    assert r["ok"] is True
    assert api.config.data == {"max_concurrent": 2, "ffmpeg_path": "C:/bin"}


def test_check_ffmpeg(monkeypatch):
    import backend.api as api_mod
    monkeypatch.setattr(api_mod, "find_ffmpeg", lambda cfg: "C:/bin/ffmpeg.exe")
    api, _ = make_api()
    assert api.check_ffmpeg() == {"ok": True, "path": "C:/bin/ffmpeg.exe"}


def test_file_pickers_guard_without_window():
    api, _ = make_api()
    assert api.pick_cookie_file()["ok"] is False
    assert api.pick_download_dir()["ok"] is False


def test_file_pickers_use_window_dialog(monkeypatch):
    import backend.api as api_mod

    calls = []

    class FakeWindow:
        def create_file_dialog(self, dialog_type, allow_multiple=False, file_types=()):
            calls.append((dialog_type, file_types))
            if dialog_type == "OPEN_DIALOG":
                return ("C:/cookies.txt",)
            return ("C:/Downloads",)

    api_obj, _ = make_api()
    api_obj._holder = type("H", (), {"window": FakeWindow()})()
    monkeypatch.setattr(api_mod.webview, "OPEN_DIALOG", "OPEN_DIALOG", raising=False)
    monkeypatch.setattr(api_mod.webview, "FOLDER_DIALOG", "FOLDER_DIALOG", raising=False)
    r1 = api_obj.pick_cookie_file()
    r2 = api_obj.pick_download_dir()
    assert r1 == {"ok": True, "path": "C:/cookies.txt"}
    assert r2 == {"ok": True, "path": "C:/Downloads"}
    assert calls[0][0] == "OPEN_DIALOG"
    assert calls[1][0] == "FOLDER_DIALOG"
    assert calls[1][1] == ()
