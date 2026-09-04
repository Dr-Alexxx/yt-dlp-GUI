from __future__ import annotations

import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
BIN_DIR = APP_DIR / "bin"
FFMPEG_URL = ("https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/"
              "ffmpeg-master-latest-win64-gpl.zip")


def _bin_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "bin"
    return BIN_DIR


def find_ffmpeg(config) -> str | None:
    configured = config.get("ffmpeg_path")
    if configured and Path(configured).exists():
        return configured
    local = _bin_dir() / "ffmpeg.exe"
    if local.exists():
        return str(local)
    return shutil.which("ffmpeg")


def download_ffmpeg(config, progress_cb=None) -> str:
    bin_dir = _bin_dir()
    bin_dir.mkdir(parents=True, exist_ok=True)
    zip_path = bin_dir / "ffmpeg.zip"

    def report(count, block, total):
        if total and progress_cb:
            progress_cb(round(min(count * block / total * 100, 100.0), 1))

    urllib.request.urlretrieve(FFMPEG_URL, zip_path, reporthook=report)
    with zipfile.ZipFile(zip_path) as z:
        for name in z.namelist():
            base = Path(name).name
            if base in ("ffmpeg.exe", "ffprobe.exe"):
                (bin_dir / base).write_bytes(z.read(name))
    zip_path.unlink()
    config.set("ffmpeg_path", str(bin_dir / "ffmpeg.exe"))
    return str(bin_dir / "ffmpeg.exe")
