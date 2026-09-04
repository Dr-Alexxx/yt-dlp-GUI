import json

from backend.config import Config, DEFAULTS


def test_defaults_when_missing(tmp_path):
    cfg = Config(path=tmp_path / "config.json")
    assert cfg.get("max_concurrent") == DEFAULTS["max_concurrent"]
    assert cfg.get("download_dir") == DEFAULTS["download_dir"]


def test_set_persists_to_disk(tmp_path):
    p = tmp_path / "config.json"
    cfg = Config(path=p)
    cfg.set("subtitle_langs", "zh-CN,en")
    on_disk = json.loads(p.read_text("utf-8"))
    assert on_disk["subtitle_langs"] == "zh-CN,en"


def test_load_merges_over_defaults(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"max_concurrent": 3}), "utf-8")
    cfg = Config(path=p)
    assert cfg.get("max_concurrent") == 3
    assert cfg.get("download_dir") == DEFAULTS["download_dir"]


def test_defaults_copy_not_shared(tmp_path):
    cfg = Config(path=tmp_path / "a.json")
    cfg.data["max_concurrent"] = 99
    assert DEFAULTS["max_concurrent"] == 2
