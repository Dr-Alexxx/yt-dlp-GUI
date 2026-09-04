from __future__ import annotations

import json
import os
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("APPDATA") or Path.home()) / "yt-dlp-gui"
CONFIG_FILE = CONFIG_DIR / "config.json"
TASKS_FILE = CONFIG_DIR / "tasks.json"

DEFAULTS = {
    "download_dir": str(Path.home() / "Downloads"),
    "cookie_file": "",
    "cookies_browser": "",
    "ffmpeg_path": "",
    "max_concurrent": 2,
    "subtitle_langs": "",
}


class Config:
    def __init__(self, path: Path = CONFIG_FILE, defaults: dict | None = None):
        self.path = path
        self.data = dict(defaults if defaults is not None else DEFAULTS)
        self.load()

    def load(self) -> None:
        if self.path.exists():
            try:
                self.data.update(json.loads(self.path.read_text("utf-8")))
            except (json.JSONDecodeError, OSError):
                pass

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2), "utf-8")

    def get(self, key: str):
        return self.data.get(key, DEFAULTS.get(key))

    def set(self, key: str, value) -> None:
        self.data[key] = value
        self.save()
