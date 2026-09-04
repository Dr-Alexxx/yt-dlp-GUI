from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

from .config import CONFIG_DIR

_CONVERTED = CONFIG_DIR / "cookies_converted.txt"


def _netscape_line(c: dict) -> str | None:
    name, value = c.get("name"), c.get("value")
    if not name or value is None:
        return None
    domain = str(c.get("domain") or "")
    if not domain:
        return None
    include_sub = "TRUE" if domain.startswith(".") else "FALSE"
    secure = "TRUE" if c.get("secure") else "FALSE"
    expiry = int(c.get("expirationDate") or c.get("expiry") or 2147483647)
    line = "\t".join([domain, include_sub, str(c.get("path") or "/"),
                      secure, str(expiry), name, str(value)])
    return f"#HttpOnly_{line}" if c.get("httpOnly") else line


def _convert(cookies, url: str) -> str:
    lines = ["# Netscape HTTP Cookie File",
             "# Converted from JSON by yt-dlp 下载器", ""]
    if isinstance(cookies, dict):
        host = urlparse(url).hostname or ""
        domain = f".{host}" if host else ""
        for name, value in cookies.items():
            lines.append("\t".join([domain, "TRUE", "/", "FALSE",
                                    "2147483647", str(name), str(value)]))
    elif isinstance(cookies, list):
        for c in cookies:
            if isinstance(c, dict):
                line = _netscape_line(c)
                if line:
                    lines.append(line)
    else:
        raise ValueError("不支持的 Cookie JSON 结构")
    if len(lines) <= 3:
        raise ValueError("Cookie JSON 中没有可用的条目（需要 name/value/domain）")
    return "\n".join(lines) + "\n"


def resolve_cookie_file(path: str, fmt: str, url: str = "") -> str:
    if not path:
        return path
    if fmt != "json":
        return path
    try:
        data = json.loads(Path(path).read_text("utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise ValueError(f"Cookie JSON 文件读取失败：{e}") from e
    _CONVERTED.parent.mkdir(parents=True, exist_ok=True)
    _CONVERTED.write_text(_convert(data, url), "utf-8")
    return str(_CONVERTED)
