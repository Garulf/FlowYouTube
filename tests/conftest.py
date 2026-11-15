import pytest

import youtube

VIDEOS = [
    {
        "id": "dQw4w9WgXcQ",
        "title": "Sourdough for beginners",
        "channel": "Bread Club",
        "duration": "12:04",
        "publish_time": "2 years ago",
        "url_suffix": "/watch?v=dQw4w9WgXcQ&pp=ygUJc291cmRvdWdo",
    },
    {
        "id": "a1b2c3d4e5f",
        "title": "Shaping a boule",
        "channel": "Bread Club",
        "duration": "8:31",
        "publish_time": "5 months ago",
        "url_suffix": "/watch?v=a1b2c3d4e5f&list=RDa1b2c3d4e5f&start_radio=1",
    },
]


class FakeSearch:
    calls = []
    videos = VIDEOS
    error = None

    def __init__(self, query, max_results=None, language=None, region=None):
        FakeSearch.calls.append((query, max_results, language, region))
        if FakeSearch.error:
            raise FakeSearch.error

    def to_dict(self):
        return [dict(video) for video in FakeSearch.videos]


@pytest.fixture
def settings():
    launcher = youtube.plugin.launcher
    launcher._settings = {}
    yield launcher._settings
    launcher._settings = {}


@pytest.fixture
def search(monkeypatch, settings):
    FakeSearch.calls = []
    FakeSearch.videos = VIDEOS
    FakeSearch.error = None
    youtube._cache.clear()
    monkeypatch.setattr(youtube, "YoutubeSearch", FakeSearch)
    yield FakeSearch
    youtube._cache.clear()
