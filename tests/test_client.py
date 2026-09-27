import io
import json
from urllib.error import HTTPError

import pytest
from wiki_interest.client import Client, ResearchError, validate_url

URL = "https://www.wikidata.org/w/api.php?action=test"


class FakeOpener:
    def __init__(self, events):
        self.events = list(events)
        self.calls = 0

    def open(self, request, timeout):
        self.calls += 1
        event = self.events.pop(0)
        if isinstance(event, Exception):
            raise event
        return io.BytesIO(event)


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr("wiki_interest.client.time.sleep", lambda _: None)


def test_offline_reuses_verified_source_without_http(tmp_path):
    live = Client(tmp_path)
    live._opener = FakeOpener([b'{"items": []}'])
    assert live.get(URL) == {"items": []}
    offline = Client(tmp_path, offline=True)
    offline._opener = FakeOpener([])
    assert offline.get(URL) == {"items": []}
    assert offline.hits == 1
    assert offline.requests == 0


def test_corrupt_cache_is_not_accepted_offline(tmp_path):
    live = Client(tmp_path)
    live._opener = FakeOpener([b'{"items": []}'])
    live.get(URL)
    path = next(tmp_path.glob("*.json"))
    data = json.loads(path.read_text())
    data["data"] = {"items": [42]}
    path.write_text(json.dumps(data))
    with pytest.raises(ResearchError, match="Offline"):
        Client(tmp_path, offline=True).get(URL)


def test_rate_limit_is_retried(tmp_path):
    client = Client(tmp_path)
    client._opener = FakeOpener(
        [HTTPError(URL, 429, "rate", {"Retry-After": "0"}, None), b'{"items": []}']
    )
    assert client.get(URL) == {"items": []}
    assert client.requests == 2


def test_exhausted_network_fails_without_fabricating_data(tmp_path):
    client = Client(tmp_path)
    client._opener = FakeOpener([TimeoutError()] * 4)
    with pytest.raises(ResearchError, match="4 attempts"):
        client.get(URL)
    assert list(tmp_path.glob("*.json")) == []


def test_permanent_forbidden_is_not_retried(tmp_path):
    client = Client(tmp_path)
    client._opener = FakeOpener([HTTPError(URL, 403, "forbidden", {}, None)])
    with pytest.raises(ResearchError, match="403"):
        client.get(URL)
    assert client.requests == 1


def test_long_retry_after_stops_instead_of_retrying_early(tmp_path):
    client = Client(tmp_path)
    client._opener = FakeOpener([HTTPError(URL, 429, "rate", {"Retry-After": "300"}, None)])
    with pytest.raises(ResearchError, match="retry later"):
        client.get(URL)


@pytest.mark.parametrize(
    "url",
    [
        "http://www.wikidata.org/x",
        "https://evil.test/x",
        "https://en.wikipedia.org.evil.test/x",
        "https://user:pass@en.wikipedia.org/x",
        "https://en.wikipedia.org:444/x",
        "https://127.0.0.1/x",
    ],
)
def test_untrusted_network_targets_rejected(url):
    with pytest.raises(ResearchError):
        validate_url(url)


def test_malformed_json_is_not_cached(tmp_path):
    client = Client(tmp_path)
    client._opener = FakeOpener([b"not json"])
    with pytest.raises(ResearchError, match="JSON"):
        client.get(URL)
    assert list(tmp_path.glob("*.json")) == []
