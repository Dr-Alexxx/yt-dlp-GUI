from backend.errors import humanize_error


def test_cookie_db_lock():
    raw = ("ERROR: Could not copy Chrome cookie database. See "
           "https://github.com/yt-dlp/yt-dlp/issues/7271 for more info")
    msg = humanize_error(raw)
    assert "浏览器" in msg and "关闭" in msg and "cookies.txt" in msg
    assert raw in msg


def test_http_412():
    raw = ("ERROR: [BiliBili] 1BZ8J6FEw3: Unable to download webpage: "
           "HTTP Error 412: Precondition Failed")
    msg = humanize_error(raw)
    assert "412" in msg and "Cookie" in msg
    assert raw in msg


def test_unknown_error_passthrough():
    raw = "ERROR: something else happened"
    assert humanize_error(raw) == raw


def test_empty_error():
    assert humanize_error("") == ""


def test_is_cookie_db_error():
    from backend.errors import is_cookie_db_error
    assert is_cookie_db_error("ERROR: Could not copy Chrome cookie database. See ...") is True
    assert is_cookie_db_error("HTTP Error 412: Precondition Failed") is False
    assert is_cookie_db_error("") is False


def test_is_fresh_cookies_error():
    from backend.errors import is_fresh_cookies_error
    assert is_fresh_cookies_error(
        "ERROR: [Douyin] 123: Fresh cookies (not necessarily logged in) are needed") is True
    assert is_fresh_cookies_error("HTTP Error 412") is False
    assert is_fresh_cookies_error("") is False


def test_humanize_fresh_cookies():
    from backend.errors import humanize_error
    msg = humanize_error("ERROR: Fresh cookies (not necessarily logged in) are needed")
    assert "风控" in msg and "重试" in msg
