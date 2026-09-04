import json

import pytest

from backend.cookies import resolve_cookie_file


def test_netscape_passthrough(tmp_path):
    f = tmp_path / "cookies.txt"
    f.write_text("# Netscape HTTP Cookie File\n", "utf-8")
    assert resolve_cookie_file(str(f), "netscape", "https://x.com/v") == str(f)


def test_json_array_conversion(tmp_path):
    f = tmp_path / "cookies.json"
    cookies = [{
        "domain": ".bilibili.com", "hostOnly": False, "httpOnly": True,
        "name": "SESSDATA", "path": "/", "secure": True,
        "expirationDate": 1800000000, "value": "abc-123",
    }]
    f.write_text(json.dumps(cookies), "utf-8")
    out = resolve_cookie_file(str(f), "json", "")
    text = out if "\n" in out else open(out, encoding="utf-8").read()
    with open(out, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    assert lines[0].startswith("# Netscape")
    line = [l for l in lines if "SESSDATA" in l][0]
    assert line.startswith("#HttpOnly_")
    parts = line.replace("#HttpOnly_", "").split("\t")
    assert parts[0] == ".bilibili.com"
    assert parts[1] == "TRUE"
    assert parts[2] == "/"
    assert parts[3] == "TRUE"
    assert parts[4] == "1800000000"
    assert parts[5] == "SESSDATA"
    assert parts[6] == "abc-123"


def test_json_dict_conversion_uses_url_host(tmp_path):
    f = tmp_path / "cookies.json"
    f.write_text(json.dumps({"SESSDATA": "abc", "bili_jct": "xyz"}), "utf-8")
    out = resolve_cookie_file(str(f), "json",
                              "https://www.bilibili.com/video/BV1xx")
    with open(out, encoding="utf-8") as fh:
        lines = [l for l in fh.read().splitlines() if l and not l.startswith("#")]
    assert len(lines) == 2
    parts = lines[0].split("\t")
    assert parts[0] == ".www.bilibili.com"
    assert parts[5] == "SESSDATA"


def test_invalid_json_raises_chinese_error(tmp_path):
    f = tmp_path / "cookies.json"
    f.write_text("not json{", "utf-8")
    with pytest.raises(ValueError, match="Cookie"):
        resolve_cookie_file(str(f), "json", "")


def test_unsupported_json_shape_raises(tmp_path):
    f = tmp_path / "cookies.json"
    f.write_text(json.dumps([1, 2, 3]), "utf-8")
    with pytest.raises(ValueError, match="Cookie"):
        resolve_cookie_file(str(f), "json", "")
