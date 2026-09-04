from __future__ import annotations

_PATTERNS = [
    ("Could not copy Chrome cookie database",
     "浏览器 Cookie 读取失败：对应浏览器正在运行，Cookie 数据库被锁。"
     "请关闭该浏览器后重试，或改用 cookies.txt 文件（设置页「Cookie 文件路径」）。"),
    ("HTTP Error 412",
     "被网站风控拦截（HTTP 412）：通常与浏览器导出的 Cookie 请求特征有关。"
     "建议改用无 Cookie 模式，或用 GetCookie 等工具导出 cookies.txt 填入设置页。"),
]


def humanize_error(raw: str) -> str:
    if not raw:
        return raw
    for pattern, hint in _PATTERNS:
        if pattern in raw:
            return f"{hint}\n原始错误：{raw}"
    return raw


def is_cookie_db_error(raw: str) -> bool:
    return bool(raw) and "Could not copy Chrome cookie database" in raw
