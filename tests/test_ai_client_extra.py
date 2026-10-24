"""AI 客户端补充测试：base_url 校验（SSRF 防护）、异常结构。"""
from __future__ import annotations

import pytest

from formora.ai import client as ai_client
from formora.core.errors import ExternalDependencyError
from formora.services.config import Config


class TestValidateBaseUrl:
    def test_empty(self):
        with pytest.raises(ExternalDependencyError):
            ai_client._validate_base_url("")

    def test_missing_scheme(self):
        with pytest.raises(ExternalDependencyError):
            ai_client._validate_base_url("api.example.com/v1")

    def test_http_non_loopback_blocked(self):
        with pytest.raises(ExternalDependencyError):
            ai_client._validate_base_url("http://example.com/v1")

    def test_loopback_http_allowed(self):
        assert ai_client._validate_base_url("http://localhost:8080/v1") == "http://localhost:8080/v1"
        assert ai_client._validate_base_url("http://127.0.0.1:11434/v1") == "http://127.0.0.1:11434/v1"

    def test_private_ranges_blocked(self):
        for url in (
            "https://10.0.0.1/v1",
            "https://192.168.1.1/v1",
            "https://172.16.0.1/v1",
            "https://169.254.169.254/v1",
            "https://100.64.0.1/v1",
        ):
            with pytest.raises(ExternalDependencyError):
                ai_client._validate_base_url(url)

    def test_bare_ip_blocked(self):
        with pytest.raises(ExternalDependencyError):
            ai_client._validate_base_url("https://1.2.3.4/v1")

    def test_valid_https_normalized(self):
        assert ai_client._validate_base_url("https://api.example.com/v1/") == "https://api.example.com/v1"

    def test_malformed(self):
        with pytest.raises(ExternalDependencyError):
            ai_client._validate_base_url("https://")


class TestIsConfiguredExtra:
    def test_enabled_but_no_key(self, tmp_path):
        cfg = Config(tmp_path / "config.json")
        cfg.set("ai", {"enabled": True, "base_url": "https://example.com/v1", "model": "m"})
        assert not ai_client.is_configured(cfg)

    def test_key_but_not_enabled(self, tmp_path, monkeypatch):
        cfg = Config(tmp_path / "config.json")
        cfg.set("ai", {"enabled": False, "base_url": "https://example.com/v1", "model": "m"})
        monkeypatch.setattr(cfg, "get_ai_api_key", lambda: "k")
        assert not ai_client.is_configured(cfg)


class TestExtractFieldsExtra:
    def test_non_dict_result_raises(self, tmp_path, monkeypatch):
        cfg = Config(tmp_path / "config.json")
        cfg.set("ai", {"enabled": True, "base_url": "https://example.com/v1", "model": "m"})
        monkeypatch.setattr(cfg, "get_ai_api_key", lambda: "k")
        monkeypatch.setattr(ai_client, "_chat_json", lambda *a, **k: ["not-a-dict"])
        with pytest.raises(ExternalDependencyError):
            ai_client.extract_fields(cfg, "素材", ["实验名称"])

    def test_returns_fields_list(self, tmp_path, monkeypatch):
        cfg = Config(tmp_path / "config.json")
        cfg.set("ai", {"enabled": True, "base_url": "https://example.com/v1", "model": "m"})
        monkeypatch.setattr(cfg, "get_ai_api_key", lambda: "k")
        monkeypatch.setattr(ai_client, "_chat_json",
                            lambda *a, **k: {"fields": [{"field": "实验名称", "value": "x"}]})
        fields = ai_client.extract_fields(cfg, "素材", ["实验名称"])
        assert fields[0]["field"] == "实验名称"


class TestReviewReportExtra:
    def test_non_dict_result_raises(self, tmp_path, monkeypatch):
        cfg = Config(tmp_path / "config.json")
        cfg.set("ai", {"enabled": True, "base_url": "https://example.com/v1", "model": "m"})
        monkeypatch.setattr(cfg, "get_ai_api_key", lambda: "k")
        monkeypatch.setattr(ai_client, "_chat_json", lambda *a, **k: 42)
        with pytest.raises(ExternalDependencyError):
            ai_client.review_report(cfg, "报告文本")

    def test_returns_issues_list(self, tmp_path, monkeypatch):
        cfg = Config(tmp_path / "config.json")
        cfg.set("ai", {"enabled": True, "base_url": "https://example.com/v1", "model": "m"})
        monkeypatch.setattr(cfg, "get_ai_api_key", lambda: "k")
        monkeypatch.setattr(ai_client, "_chat_json",
                            lambda *a, **k: {"issues": [{"field": "结论", "issue": "为空"}]})
        issues = ai_client.review_report(cfg, "报告文本")
        assert issues[0]["field"] == "结论"


class TestSystemPrompt:
    def test_contains_anti_hallucination_rules(self):
        assert "不得编造" in ai_client.SYSTEM_PROMPT
        assert "needs_confirmation" in ai_client.SYSTEM_PROMPT
        assert "待补充" in ai_client.SYSTEM_PROMPT
