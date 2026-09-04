from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum


class TaskStatus(str, Enum):
    QUEUED = "queued"
    PROBING = "probing"
    WAITING = "waiting"
    DOWNLOADING = "downloading"
    DONE = "done"
    ERROR = "error"
    CANCELLED = "cancelled"


ALLOWED: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.QUEUED: {TaskStatus.PROBING, TaskStatus.CANCELLED},
    TaskStatus.PROBING: {TaskStatus.WAITING, TaskStatus.DOWNLOADING, TaskStatus.ERROR, TaskStatus.CANCELLED},
    TaskStatus.WAITING: {TaskStatus.DOWNLOADING, TaskStatus.CANCELLED},
    TaskStatus.DOWNLOADING: {TaskStatus.DONE, TaskStatus.ERROR, TaskStatus.CANCELLED, TaskStatus.QUEUED},
    TaskStatus.ERROR: {TaskStatus.QUEUED},
    TaskStatus.CANCELLED: {TaskStatus.QUEUED},
    TaskStatus.DONE: set(),
}


@dataclass
class Task:
    url: str
    options: dict = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    status: TaskStatus = TaskStatus.QUEUED
    title: str = ""
    percent: float = 0.0
    speed: str = ""
    eta: str = ""
    error: str = ""
    filepath: str = ""

    def transition(self, new_status: TaskStatus) -> bool:
        if new_status in ALLOWED[self.status]:
            self.status = new_status
            return True
        return False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "url": self.url,
            "options": self.options,
            "status": self.status.value,
            "title": self.title,
            "percent": self.percent,
            "speed": self.speed,
            "eta": self.eta,
            "error": self.error,
            "filepath": self.filepath,
        }
