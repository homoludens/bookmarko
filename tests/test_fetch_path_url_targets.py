import socket
from types import SimpleNamespace

import pytest

from flaskmarks.core.marks_import_thread import fetch_url_metadata
from flaskmarks.core.url_fetch_validation import URLTargetValidationError
from flaskmarks.core import url_fetch_validation


def _addrinfo_for(ip_text):
    return [
        (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (ip_text, 80))
    ]


@pytest.mark.parametrize(
    ("resolved_ip", "reason"),
    [
        ("127.0.0.1", "loopback"),
        ("10.0.0.7", "private"),
        ("169.254.1.10", "link-local"),
    ],
)
def test_fetch_path_blocks_non_public_targets_before_network(
    monkeypatch, resolved_ip, reason
):
    def fake_getaddrinfo(_host, _port, proto=None):
        assert proto == socket.IPPROTO_TCP
        return _addrinfo_for(resolved_ip)

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("Network fetch should not run for blocked targets")

    monkeypatch.setattr(url_fetch_validation.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr("flaskmarks.core.marks_import_thread.requests.head", fail_if_called)

    with pytest.raises(URLTargetValidationError) as exc_info:
        fetch_url_metadata("http://blocked-target.example/path")

    assert resolved_ip in str(exc_info.value)
    assert reason in str(exc_info.value)


def test_fetch_path_allows_public_target_and_continues_fetch(monkeypatch):
    called = {"head": 0}

    def fake_getaddrinfo(_host, _port, proto=None):
        assert proto == socket.IPPROTO_TCP
        return _addrinfo_for("93.184.216.34")

    class FakeHeadResponse:
        headers = {"content-type": "text/html; charset=utf-8"}

        def __enter__(self):
            return self

        def __exit__(self, _exc_type, _exc, _tb):
            return False

    def fake_head(_url, timeout):
        called["head"] += 1
        assert timeout == 4
        return FakeHeadResponse()

    class FakeArticle:
        def __init__(self, _url):
            self.html = None
            self.summary = "Example summary"
            self.keywords = []
            self.is_parsed = False

        def download(self):
            return None

        def parse(self):
            return None

        def nlp(self):
            return None

    monkeypatch.setattr(url_fetch_validation.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr("flaskmarks.core.marks_import_thread.requests.head", fake_head)
    monkeypatch.setattr(
        "flaskmarks.core.marks_import_thread.tldextract.extract",
        lambda _url: SimpleNamespace(domain="example"),
    )
    monkeypatch.setattr("flaskmarks.core.marks_import_thread.check_url_video", lambda _url: False)
    monkeypatch.setattr("flaskmarks.core.marks_import_thread.Article", FakeArticle)

    url = "https://public-target.example/path"
    metadata = fetch_url_metadata(url)

    assert called["head"] == 1
    assert metadata is not None
    assert metadata["url"] == url
    assert metadata["title"] == url
