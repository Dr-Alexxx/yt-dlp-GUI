import time

from backend.config import Config, DEFAULTS
from backend.downloader import DownloadManager
from backend.models import TaskStatus
from fakes import FakeYDL


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
