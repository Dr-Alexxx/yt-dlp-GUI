import io
import zipfile
from pathlib import Path

import backend.ffmpeg_mgr as fm
from backend.config import Config, DEFAULTS


def make_cfg(tmp_path):
    return Config(path=tmp_path / "config.json",
                  defaults={**DEFAULTS, "ffmpeg_path": ""})


def test_detect_user_config_first(tmp_path, monkeypatch):
    exe = tmp_path / "custom" / "ffmpeg.exe"
    exe.parent.mkdir()
    exe.write_bytes(b"x")
    cfg = make_cfg(tmp_path)
    cfg.data["ffmpeg_path"] = str(exe)
    monkeypatch.setattr(fm, "BIN_DIR", tmp_path / "bin")
    assert fm.find_ffmpeg(cfg) == str(exe)


def test_detect_local_bin(tmp_path, monkeypatch):
    cfg = make_cfg(tmp_path)
    monkeypatch.setattr(fm, "BIN_DIR", tmp_path / "bin")
    (tmp_path / "bin").mkdir()
    (tmp_path / "bin" / "ffmpeg.exe").write_bytes(b"x")
    assert fm.find_ffmpeg(cfg) == str(tmp_path / "bin" / "ffmpeg.exe")


def test_detect_path_fallback(tmp_path, monkeypatch):
    cfg = make_cfg(tmp_path)
    monkeypatch.setattr(fm, "BIN_DIR", tmp_path / "bin")
    monkeypatch.setattr(fm.shutil, "which", lambda name: "C:/ffmpeg/ffmpeg.exe")
    assert fm.find_ffmpeg(cfg) == "C:/ffmpeg/ffmpeg.exe"


def test_detect_none(tmp_path, monkeypatch):
    cfg = make_cfg(tmp_path)
    monkeypatch.setattr(fm, "BIN_DIR", tmp_path / "nonexistent")
    monkeypatch.setattr(fm.shutil, "which", lambda name: None)
    assert fm.find_ffmpeg(cfg) is None


def test_download_extracts_and_saves(tmp_path, monkeypatch):
    cfg = make_cfg(tmp_path)
    monkeypatch.setattr(fm, "BIN_DIR", tmp_path / "bin")
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w") as z:
        z.writestr("ffmpeg-master/bin/ffmpeg.exe", b"ffmpeg-bytes")
        z.writestr("ffmpeg-master/bin/ffprobe.exe", b"ffprobe-bytes")
        z.writestr("ffmpeg-master/bin/other.txt", b"junk")

    def fake_urlretrieve(url, path, reporthook=None):
        Path(path).write_bytes(zbuf.getvalue())
        if reporthook:
            reporthook(1, len(zbuf.getvalue()), len(zbuf.getvalue()))

    monkeypatch.setattr(fm.urllib.request, "urlretrieve", fake_urlretrieve)
    percents = []
    out = fm.download_ffmpeg(cfg, percents.append)
    assert out == str(tmp_path / "bin" / "ffmpeg.exe")
    assert (tmp_path / "bin" / "ffmpeg.exe").read_bytes() == b"ffmpeg-bytes"
    assert (tmp_path / "bin" / "ffprobe.exe").read_bytes() == b"ffprobe-bytes"
    assert not (tmp_path / "bin" / "ffmpeg.zip").exists()
    assert 100.0 in percents
    assert cfg.get("ffmpeg_path") == out

def test_bin_dir_frozen_next_to_exe(monkeypatch, tmp_path):
    import sys
    exe = tmp_path / "app" / "yt-dlp下载器.exe"
    exe.parent.mkdir()
    exe.write_bytes(b"x")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe))
    assert fm._bin_dir() == tmp_path / "app" / "bin"


def test_bin_dir_source_layout(monkeypatch):
    import sys
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    assert fm._bin_dir() == fm.BIN_DIR
