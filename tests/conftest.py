import pytest

import backend.downloader as dl_mod
from fakes import FakeYDL, FAIL_URLS, GATES


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    FakeYDL.instances.clear()
    FAIL_URLS.clear()
    GATES.clear()
    monkeypatch.setattr(dl_mod, "find_ffmpeg", lambda cfg: None)
    yield
