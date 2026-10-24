"""AI 客户端离线测试：不发起真实网络请求，用 monkeypatch 模拟 HTTP 层。"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from formora.ai import client as ai_client
from formora.core.errors import ExternalDependencyError
from formora.services.config import Config


class _FakeResp:
    def __init__(self, payload: bytes):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self._payload


def _install_fake_urlopen(monkeypatch, payload: bytes, captured: dict | None = None):
    def fake_urlopen(req, timeout=60):
        if captured is not None:
            captured["url"] = req.full_url
            captured["payload"] = json.loads(req.data.decode("utf-8"))
            captured["headers"] = dict(req.headers)
            captured["timeout"] = timeout
        return _FakeResp(payload)
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)


class TestIsConfigured:
    def test_not_configured_by_default(self, tmp_path):
        cfg = Config(tmp_path / "config.json")
        assert not ai_client.is_configured(cfg)

    def test_configured_when_enabled_key_and_url(self, tmp_path, monkeypatch):
        cfg = Config(tmp_path / "config.json")
        cfg.set("ai", {"enabled": True, "base_url": "https://example.com/v1", "model": "m"})
        monkeypatch.setattr(cfg, "get_ai_api_key", lambda: "k")
        assert ai_client.is_configured(cfg)


class TestPostChat:
    def test_builds_v1_url_and_payload(self, monkeypatch):
        captured: dict = {}
        _install_fake_urlopen(monkeypatch, b'{"ok":true}', captured)
        body = ai_client._post_chat(
            "https://example.com/v1", "model-x", "secret",
            [{"role": "user", "content": "hi"}], json_mode=True,
        )
        assert captured["url"] == "https://example.com/v1/chat/completions"
        assert captured["payload"]["model"] == "model-x"
        assert captured["payload"]["temperature"] == 0.2
        assert captured["payload"]["response_format"] == {"type": "json_object"}
        assert captured["headers"]["Authorization"] == "Bearer secret"
        assert body == {"ok": True}

    def test_appends_v1_when_missing(self, monkeypatch):
        captured: dict = {}
        _install_fake_urlopen(monkeypatch, b'{}', captured)
        ai_client._post_chat("https://example.com", "m", "k", [{"role": "user", "content": "x"}])
        assert captured["url"] == "https://example.com/v1/chat/completions"

    def test_wraps_network_errors(self, monkeypatch):
        def boom(req, timeout=60):
            raise OSError("网络不可用")
        monkeypatch.setattr("urllib.request.urlopen", boom)
        with pytest.raises(ExternalDependencyError):
            ai_client._post_chat("https://example.com", "m", "k", [])


class TestTestConnection:
    def test_requires_config(self):
        with pytest.raises(ExternalDependencyError):
            ai_client.test_connection("", "", "")

    def test_returns_model_response(self, monkeypatch):
        _install_fake_urlopen(
            monkeypatch,
            b'{"choices":[{"message":{"content":"pong"}}]}',
        )
        result = ai_client.test_connection("https://example.com/v1", "m", "k")
        assert result == "pong"


class TestExtractFields:
    def test_raises_when_not_configured(self, tmp_path):
        cfg = Config(tmp_path / "config.json")
        with pytest.raises(ExternalDependencyError):
            ai_client.extract_fields(cfg, "素材", ["实验名称"])

    def test_parses_fields_from_response(self, tmp_path, monkeypatch):
        cfg = Config(tmp_path / "config.json")
        cfg.set("ai", {"enabled": True, "base_url": "https://example.com/v1", "model": "m"})
        monkeypatch.setattr(cfg, "get_ai_api_key", lambda: "k")

        content = json.dumps({
            "fields": [{
                "field": "实验名称",
                "value": "测试实验",
                "source": "素材.txt",
                "needs_confirmation": False,
            }],
        })
        _install_fake_urlopen(monkeypatch, json.dumps({
            "choices": [{"message": {"content": content}}],
        }).encode("utf-8"))

        fields = ai_client.extract_fields(cfg, "素材内容", ["实验名称"])
        assert fields[0]["field"] == "实验名称"
        assert fields[0]["value"] == "测试实验"
        assert fields[0]["source"] == "素材.txt"
        assert fields[0]["needs_confirmation"] is False


class TestReviewReport:
    def test_parses_issues_from_response(self, tmp_path, monkeypatch):
        cfg = Config(tmp_path / "config.json")
        cfg.set("ai", {"enabled": True, "base_url": "https://example.com/v1", "model": "m"})
        monkeypatch.setattr(cfg, "get_ai_api_key", lambda: "k")

        content = json.dumps({"issues": [{"field": "实验结论", "issue": "为空", "severity": "error"}]})
        _install_fake_urlopen(monkeypatch, json.dumps({
            "choices": [{"message": {"content": content}}],
        }).encode("utf-8"))

        issues = ai_client.review_report(cfg, "报告文本")
        assert issues[0]["field"] == "实验结论"
        assert issues[0]["severity"] == "error"