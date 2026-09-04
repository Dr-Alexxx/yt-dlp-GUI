import threading
import time

from backend.config import Config, DEFAULTS
from backend.downloader import DownloadManager
from backend.models import TaskStatus
from fakes import COOKIE_FAIL_URLS, FAIL_URLS, GATES, FakeYDL


def wait_until(cond, timeout=3.0):
    end = time.time() + timeout
    while time.time() < end:
        if cond():
            return True
        time.sleep(0.02)
    return False


def make_manager(tmp_path, events):
    cfg = Config(path=tmp_path / "config.json",
                 defaults={**DEFAULTS, "max_concurrent": 1})
    return DownloadManager(cfg, events.append, ydl_factory=FakeYDL,
                           tasks_file=tmp_path / "tasks.json", max_workers=1)


def test_download_completes(tmp_path):
    events = []
    m = make_manager(tmp_path, events)
    tid = m.add_task("https://example.com/v1")
    assert wait_until(lambda: m.tasks[tid].status is TaskStatus.DONE)
    t = m.tasks[tid]
    assert t.percent == 100.0
    assert t.filepath == "out.mp4"
    assert t.title == "测试视频"
    assert any(e["type"] == "task_update" for e in events)


def test_progress_events_pushed(tmp_path):
    events = []
    m = make_manager(tmp_path, events)
    tid = m.add_task("https://example.com/v1")
    assert wait_until(lambda: m.tasks[tid].status is TaskStatus.DONE)
    percents = [e["task"]["percent"] for e in events
                if e["type"] == "task_update" and e["task"]["id"] == tid]
    assert 50.0 in percents
    assert 100.0 in percents


def test_get_task_list_order(tmp_path):
    m = make_manager(tmp_path, [])
    id1 = m.add_task("https://example.com/v1")
    id2 = m.add_task("https://example.com/v2")
    assert wait_until(lambda: all(
        m.tasks[i].status in (TaskStatus.DONE, TaskStatus.ERROR)
        for i in (id1, id2)))
    tasks = m.get_task_list()
    assert [t["id"] for t in tasks] == [id1, id2]


def test_has_active(tmp_path):
    m = make_manager(tmp_path, [])
    tid = m.add_task("https://example.com/v1")
    assert wait_until(lambda: m.tasks[tid].status is TaskStatus.DONE)
    assert m.has_active() is False


def test_persistence_reload(tmp_path):
    m = make_manager(tmp_path, [])
    tid = m.add_task("https://example.com/v1")
    assert wait_until(lambda: m.tasks[tid].status is TaskStatus.DONE)
    m2 = DownloadManager(m.config, lambda e: None, ydl_factory=FakeYDL,
                         tasks_file=tmp_path / "tasks.json", max_workers=1)
    titles = [t["title"] for t in m2.get_task_list()]
    assert "测试视频" in titles


def test_pause_during_download(tmp_path):
    gate = threading.Event()
    GATES["https://example.com/v1"] = gate
    m = make_manager(tmp_path, [])
    tid = m.add_task("https://example.com/v1")
    assert wait_until(lambda: m.tasks[tid].status is TaskStatus.DOWNLOADING)
    m.pause_task(tid)
    gate.set()
    assert wait_until(lambda: m.tasks[tid].status is TaskStatus.CANCELLED)


def test_resume_after_pause(tmp_path):
    gate = threading.Event()
    GATES["https://example.com/v1"] = gate
    m = make_manager(tmp_path, [])
    tid = m.add_task("https://example.com/v1")
    assert wait_until(lambda: m.tasks[tid].status is TaskStatus.DOWNLOADING)
    m.pause_task(tid)
    gate.set()
    assert wait_until(lambda: m.tasks[tid].status is TaskStatus.CANCELLED)
    m.resume_task(tid)
    assert wait_until(lambda: m.tasks[tid].status is TaskStatus.DONE)


def test_cancel_queued_task(tmp_path):
    gate = threading.Event()
    GATES["https://example.com/v1"] = gate
    m = make_manager(tmp_path, [])
    tid = m.add_task("https://example.com/v1")
    m.cancel_task(tid)
    gate.set()
    assert wait_until(lambda: m.tasks[tid].status is TaskStatus.CANCELLED)


def test_auto_retry_on_transient_error(tmp_path):
    FAIL_URLS.add("https://example.com/v1")
    m = make_manager(tmp_path, [])
    tid = m.add_task("https://example.com/v1")
    assert wait_until(lambda: m.tasks[tid].status is TaskStatus.DONE)


def test_manual_retry_after_error(tmp_path):
    FAIL_URLS.add("https://example.com/v1")
    FAIL_URLS.add("https://example.com/v1")
    m = make_manager(tmp_path, [])
    tid = m.add_task("https://example.com/v1")
    assert wait_until(lambda: m.tasks[tid].status is TaskStatus.ERROR)
    assert m.tasks[tid].error
    FAIL_URLS.add("https://example.com/v1")
    FAIL_URLS.add("https://example.com/v1")
    m.retry_task(tid)
    assert wait_until(lambda: m.tasks[tid].status is TaskStatus.ERROR)
    assert m.tasks[tid].error


def test_playlist_waiting_and_selection(tmp_path):
    m = make_manager(tmp_path, [])
    tid = m.add_task("https://example.com/playlist")
    assert wait_until(lambda: m.tasks[tid].status is TaskStatus.WAITING)
    m.submit_playlist_selection(tid, [2])
    assert wait_until(lambda: m.tasks[tid].status is TaskStatus.DONE)
    dl_opts = [i.opts for i in FakeYDL.instances if "progress_hooks" in i.opts]
    assert dl_opts[-1]["playlist_items"] == "2"


def test_playlist_cancel_while_waiting(tmp_path):
    m = make_manager(tmp_path, [])
    tid = m.add_task("https://example.com/playlist")
    assert wait_until(lambda: m.tasks[tid].status is TaskStatus.WAITING)
    m.cancel_task(tid)
    assert wait_until(lambda: m.tasks[tid].status is TaskStatus.CANCELLED)


def test_cookie_lock_falls_back_to_no_cookie(tmp_path):
    COOKIE_FAIL_URLS.add("https://example.com/v1")
    events = []
    cfg = Config(path=tmp_path / "config.json",
                 defaults={**DEFAULTS, "max_concurrent": 1,
                           "cookies_browser": "edge"})
    m = DownloadManager(cfg, events.append, ydl_factory=FakeYDL,
                        tasks_file=tmp_path / "tasks.json", max_workers=1)
    tid = m.add_task("https://example.com/v1")
    assert wait_until(lambda: m.tasks[tid].status is TaskStatus.DONE)
    assert any(e["type"] == "cookie_fallback" for e in events)
    dl_opts = [i.opts for i in FakeYDL.instances if "progress_hooks" in i.opts]
    assert "cookiesfrombrowser" in dl_opts[0]
    assert "cookiesfrombrowser" not in dl_opts[-1]
