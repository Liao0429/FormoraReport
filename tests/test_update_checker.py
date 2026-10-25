"""update_checker 单元测试：monkeypatch 模拟 GitHub API。

覆盖三种情况：有新版 / 无新版 / 网络失败，以及异常响应与异步入口。
"""

from __future__ import annotations

import asyncio
import json
import urllib.error

import pytest

from formora.services import update_checker

CURRENT = "2.15.0"
RELEASES_URL = "https://github.com/Liao0429/FormoraReport/releases/tag/v2.16.0"


class _FakeResponse:
    """模拟 urllib 响应对象（支持 with 语句与 read()）。"""

    def __init__(self, payload: dict):
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _install_fake(monkeypatch, payload: dict) -> None:
    def fake_urlopen(request, timeout=None):
        return _FakeResponse(payload)

    monkeypatch.setattr(update_checker, "urlopen", fake_urlopen)


@pytest.fixture(autouse=True)
def _current_version(monkeypatch):
    """固定当前版本，避免后续版本升级导致测试失效。"""
    monkeypatch.setattr(update_checker, "CURRENT_VERSION", CURRENT)


def test_new_version_available(monkeypatch):
    _install_fake(monkeypatch, {"tag_name": "v2.16.0", "html_url": RELEASES_URL})
    assert update_checker.check_for_update() == ("2.16.0", RELEASES_URL)


def test_no_new_version_same(monkeypatch):
    _install_fake(monkeypatch, {"tag_name": "v2.15.0", "html_url": RELEASES_URL})
    assert update_checker.check_for_update() is None


def test_no_new_version_older(monkeypatch):
    _install_fake(monkeypatch, {"tag_name": "v2.14.1", "html_url": RELEASES_URL})
    assert update_checker.check_for_update() is None


def test_network_failure(monkeypatch):
    def raise_error(request, timeout=None):
        raise urllib.error.URLError("network down")

    monkeypatch.setattr(update_checker, "urlopen", raise_error)
    assert update_checker.check_for_update() is None


def test_invalid_response(monkeypatch):
    """响应缺少 tag_name/html_url 时应静默返回 None。"""
    _install_fake(monkeypatch, {"foo": "bar"})
    assert update_checker.check_for_update() is None


def test_async_returns_result(monkeypatch):
    _install_fake(monkeypatch, {"tag_name": "v2.16.0", "html_url": RELEASES_URL})
    result = asyncio.run(update_checker.check_for_update_async())
    assert result == ("2.16.0", RELEASES_URL)
