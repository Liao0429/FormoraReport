"""AI 客户端补充测试：base_url 校验（SSRF 防护）、异常结构。"""

from __future__ import annotations

import io
import json
import urllib.error

import pytest

from formora.ai import client as ai_client
from formora.ai.cache import AICache
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
        assert (
            ai_client._validate_base_url("http://localhost:8080/v1")
            == "http://localhost:8080/v1"
        )
        assert (
            ai_client._validate_base_url("http://127.0.0.1:11434/v1")
            == "http://127.0.0.1:11434/v1"
        )

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
        assert (
            ai_client._validate_base_url("https://api.example.com/v1/")
            == "https://api.example.com/v1"
        )

    def test_malformed(self):
        with pytest.raises(ExternalDependencyError):
            ai_client._validate_base_url("https://")


class TestIsConfiguredExtra:
    def test_enabled_but_no_key(self, tmp_path):
        cfg = Config(tmp_path / "config.json")
        cfg.set(
            "ai", {"enabled": True, "base_url": "https://example.com/v1", "model": "m"}
        )
        assert not ai_client.is_configured(cfg)

    def test_key_but_not_enabled(self, tmp_path, monkeypatch):
        cfg = Config(tmp_path / "config.json")
        cfg.set(
            "ai", {"enabled": False, "base_url": "https://example.com/v1", "model": "m"}
        )
        monkeypatch.setattr(cfg, "get_ai_api_key", lambda: "k")
        assert not ai_client.is_configured(cfg)


class TestExtractFieldsExtra:
    def test_non_dict_result_raises(self, tmp_path, monkeypatch):
        cfg = Config(tmp_path / "config.json")
        cfg.set(
            "ai", {"enabled": True, "base_url": "https://example.com/v1", "model": "m"}
        )
        monkeypatch.setattr(cfg, "get_ai_api_key", lambda: "k")
        monkeypatch.setattr(ai_client, "_chat_json", lambda *a, **k: ["not-a-dict"])
        with pytest.raises(ExternalDependencyError):
            ai_client.extract_fields(cfg, "素材", ["实验名称"])

    def test_returns_fields_list(self, tmp_path, monkeypatch):
        cfg = Config(tmp_path / "config.json")
        cfg.set(
            "ai", {"enabled": True, "base_url": "https://example.com/v1", "model": "m"}
        )
        monkeypatch.setattr(cfg, "get_ai_api_key", lambda: "k")
        monkeypatch.setattr(
            ai_client,
            "_chat_json",
            lambda *a, **k: {"fields": [{"field": "实验名称", "value": "x"}]},
        )
        fields = ai_client.extract_fields(cfg, "素材", ["实验名称"])
        assert fields[0]["field"] == "实验名称"


class TestReviewReportExtra:
    def test_non_dict_result_raises(self, tmp_path, monkeypatch):
        cfg = Config(tmp_path / "config.json")
        cfg.set(
            "ai", {"enabled": True, "base_url": "https://example.com/v1", "model": "m"}
        )
        monkeypatch.setattr(cfg, "get_ai_api_key", lambda: "k")
        monkeypatch.setattr(ai_client, "_chat_json", lambda *a, **k: 42)
        with pytest.raises(ExternalDependencyError):
            ai_client.review_report(cfg, "报告文本")

    def test_returns_issues_list(self, tmp_path, monkeypatch):
        cfg = Config(tmp_path / "config.json")
        cfg.set(
            "ai", {"enabled": True, "base_url": "https://example.com/v1", "model": "m"}
        )
        monkeypatch.setattr(cfg, "get_ai_api_key", lambda: "k")
        monkeypatch.setattr(
            ai_client,
            "_chat_json",
            lambda *a, **k: {"issues": [{"field": "结论", "issue": "为空"}]},
        )
        issues = ai_client.review_report(cfg, "报告文本")
        assert issues[0]["field"] == "结论"


class TestSystemPrompt:
    def test_contains_anti_hallucination_rules(self):
        assert "不得编造" in ai_client.SYSTEM_PROMPT
        assert "needs_confirmation" in ai_client.SYSTEM_PROMPT
        assert "待补充" in ai_client.SYSTEM_PROMPT


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path, monkeypatch):
    """每个测试使用独立缓存文件，避免污染真实缓存与测试间相互影响。"""
    monkeypatch.setattr(ai_client, "_CACHE", AICache(tmp_path / "ai_cache.json"))


class _FakeResp:
    def __init__(self, payload: bytes):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self._payload


def _install_fake_urlopen(monkeypatch, payload: bytes):
    def fake_urlopen(req, timeout=60):
        return _FakeResp(payload)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)


class TestPostChatExtra:
    def test_post_chat_http_error_status(self, monkeypatch):
        """HTTP 500 响应（body 可解析为 JSON）也被包装成 ExternalDependencyError。"""
        body = json.dumps(
            {"error": {"message": "server exploded", "type": "server_error"}}
        ).encode("utf-8")

        def fake_urlopen(req, timeout=60):
            raise urllib.error.HTTPError(
                req.full_url, 500, "Internal Server Error", {}, io.BytesIO(body)
            )

        monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
        with pytest.raises(ExternalDependencyError) as excinfo:
            ai_client._post_chat("https://example.com", "m", "k", [])
        assert "AI 请求失败" in str(excinfo.value)
        assert "500" in str(excinfo.value)


class TestParseModelJsonExtra:
    def test_parse_model_json_none_raises(self):
        with pytest.raises(ValueError):
            ai_client._parse_model_json(None)

    def test_parse_model_json_markdown_fence(self):
        # 以 ```json 围栏开头、无前后缀
        assert ai_client._parse_model_json('```json\n{"a": 1}\n```') == {"a": 1}
        # 围栏带前缀与后缀文本
        result = ai_client._parse_model_json(
            '以下是抽取结果：\n```json\n{"fields": [{"field": "实验名称", "value": "测试实验"}]}\n```\n如有疑问请告知。'
        )
        assert result == {"fields": [{"field": "实验名称", "value": "测试实验"}]}
        # 无围栏、带前后缀文本时提取首个 JSON 数组
        assert ai_client._parse_model_json("结果如下 [1, 2, 3] 完毕") == [1, 2, 3]


class TestProduceJsonExtra:
    def test_produce_unparseable_json_raises(self, tmp_path, monkeypatch):
        cfg = Config(tmp_path / "config.json")
        cfg.set(
            "ai", {"enabled": True, "base_url": "https://example.com/v1", "model": "m"}
        )
        monkeypatch.setattr(cfg, "get_ai_api_key", lambda: "k")
        _install_fake_urlopen(
            monkeypatch,
            json.dumps({"choices": [{"message": {"content": "不是JSON"}}]}).encode(
                "utf-8"
            ),
        )
        with pytest.raises(ExternalDependencyError, match="无法解析为 JSON"):
            ai_client.extract_fields(cfg, "素材", ["实验名称"])

    def test_reasoning_content_fallback(self, tmp_path, monkeypatch):
        cfg = Config(tmp_path / "config.json")
        cfg.set(
            "ai", {"enabled": True, "base_url": "https://example.com/v1", "model": "m"}
        )
        monkeypatch.setattr(cfg, "get_ai_api_key", lambda: "k")
        reasoning = json.dumps(
            {"fields": [{"field": "实验名称", "value": "推理得出的结论"}]}
        )
        _install_fake_urlopen(
            monkeypatch,
            json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": None,
                                "reasoning_content": reasoning,
                            }
                        }
                    ]
                }
            ).encode("utf-8"),
        )
        fields = ai_client.extract_fields(cfg, "素材", ["实验名称"])
        assert fields[0]["field"] == "实验名称"
        assert fields[0]["value"] == "推理得出的结论"
