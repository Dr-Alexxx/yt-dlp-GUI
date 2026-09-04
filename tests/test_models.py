from backend.models import Task, TaskStatus


def test_initial_status_queued():
    t = Task(url="https://example.com/v")
    assert t.status is TaskStatus.QUEUED
    assert t.id


def test_valid_transition():
    t = Task(url="u")
    assert t.transition(TaskStatus.PROBING) is True
    assert t.status is TaskStatus.PROBING


def test_invalid_transition():
    t = Task(url="u")
    assert t.transition(TaskStatus.DONE) is False
    assert t.status is TaskStatus.QUEUED


def test_retry_transitions():
    t = Task(url="u")
    t.transition(TaskStatus.PROBING)
    t.transition(TaskStatus.DOWNLOADING)
    t.transition(TaskStatus.ERROR)
    assert t.transition(TaskStatus.QUEUED) is True
    t.transition(TaskStatus.DOWNLOADING)
    t.transition(TaskStatus.CANCELLED)
    assert t.transition(TaskStatus.QUEUED) is True


def test_done_is_terminal():
    t = Task(url="u")
    t.transition(TaskStatus.PROBING)
    t.transition(TaskStatus.DOWNLOADING)
    t.transition(TaskStatus.DONE)
    assert t.transition(TaskStatus.QUEUED) is False


def test_to_dict_roundtrip():
    t = Task(url="https://example.com/v", options={"format": "18"})
    t.transition(TaskStatus.PROBING)
    d = t.to_dict()
    assert d["url"] == "https://example.com/v"
    assert d["options"] == {"format": "18"}
    assert d["status"] == "probing"
    assert TaskStatus(d["status"]) is TaskStatus.PROBING
