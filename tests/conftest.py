import pytest

import backend.downloader as dl_mod
from fakes import FakeYDL, FakePlayYDL, FAIL_URLS, GATES, COOKIE_FAIL_URLS, FRESH_FAIL_URLS


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    FakeYDL.instances.clear()
    FakePlayYDL.instances.clear()
    FakePlayYDL.fail_urls.clear()
    FAIL_URLS.clear()
    GATES.clear()
    COOKIE_FAIL_URLS.clear()
    FRESH_FAIL_URLS.clear()
    monkeypatch.setattr(dl_mod, "find_ffmpeg", lambda cfg: None)
    yield
