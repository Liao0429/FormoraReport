"""AI 客户端离线测试：不发起真实网络请求，用 monkeypatch 模拟 HTTP 层。"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from formora.ai import client as ai_client
from formora.ai.cache import AICache
from formora.core.errors import ExternalDependencyError
from formora.services.config import Config


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
    def test_not_configured_without_key_or_url(self, tmp_path):
        cfg = Config(tmp_path / "config.json")
        # 默认 ai.enabled=True（开关默认开），但缺少密钥与 API 地址时仍视为未配置
        assert cfg.get("ai")["enabled"] is True
        assert not ai_client.is_configured(cfg)

    def test_configured_when_enabled_key_and_url(self, tmp_path, monkeypatch):
        cfg = Config(tmp_path / "config.json")
        cfg.set(
            "ai", {"enabled": True, "base_url": "https://example.com/v1", "model": "m"}
        )
        monkeypatch.setattr(cfg, "get_ai_api_key", lambda: "k")
        assert ai_client.is_configured(cfg)

    def test_not_configured_when_disabled(self, tmp_path, monkeypatch):
        cfg = Config(tmp_path / "config.json")
        cfg.set(
            "ai", {"enabled": False, "base_url": "https://example.com/v1", "model": "m"}
        )
        monkeypatch.setattr(cfg, "get_ai_api_key", lambda: "k")
        assert not ai_client.is_configured(cfg)


class TestPostChat:
    def test_builds_v1_url_and_payload(self, monkeypatch):
        captured: dict = {}
        _install_fake_urlopen(monkeypatch, b'{"ok":true}', captured)
        body = ai_client._post_chat(
            "https://example.com/v1",
            "model-x",
            "secret",
            [{"role": "user", "content": "hi"}],
            json_mode=True,
        )
        assert captured["url"] == "https://example.com/v1/chat/completions"
        assert captured["payload"]["model"] == "model-x"
        assert captured["payload"]["temperature"] == 0.2
        assert captured["payload"]["response_format"] == {"type": "json_object"}
        assert captured["headers"]["Authorization"] == "Bearer secret"
        assert body == {"ok": True}

    def test_appends_v1_when_missing(self, monkeypatch):
        captured: dict = {}
        _install_fake_urlopen(monkeypatch, b"{}", captured)
        ai_client._post_chat(
            "https://example.com", "m", "k", [{"role": "user", "content": "x"}]
        )
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
        cfg.set(
            "ai", {"enabled": True, "base_url": "https://example.com/v1", "model": "m"}
        )
        monkeypatch.setattr(cfg, "get_ai_api_key", lambda: "k")

        content = json.dumps(
            {
                "fields": [
                    {
                        "field": "实验名称",
                        "value": "测试实验",
                        "source": "素材.txt",
                        "needs_confirmation": False,
                    }
                ],
            }
        )
        _install_fake_urlopen(
            monkeypatch,
            json.dumps(
                {
                    "choices": [{"message": {"content": content}}],
                }
            ).encode("utf-8"),
        )

        fields = ai_client.extract_fields(cfg, "素材内容", ["实验名称"])
        assert fields[0]["field"] == "实验名称"
        assert fields[0]["value"] == "测试实验"
        assert fields[0]["source"] == "素材.txt"
        assert fields[0]["needs_confirmation"] is False


class TestReviewReport:
    def test_parses_issues_from_response(self, tmp_path, monkeypatch):
        cfg = Config(tmp_path / "config.json")
        cfg.set(
            "ai", {"enabled": True, "base_url": "https://example.com/v1", "model": "m"}
        )
        monkeypatch.setattr(cfg, "get_ai_api_key", lambda: "k")

        content = json.dumps(
            {"issues": [{"field": "实验结论", "issue": "为空", "severity": "error"}]}
        )
        _install_fake_urlopen(
            monkeypatch,
            json.dumps(
                {
                    "choices": [{"message": {"content": content}}],
                }
            ).encode("utf-8"),
        )

        issues = ai_client.review_report(cfg, "报告文本")
        assert issues[0]["field"] == "实验结论"
        assert issues[0]["severity"] == "error"

class TestPrivacySwitch:
    """隐私开关：ai.enabled=False 时，即使已配置完整也绝不上传数据。"""

    @staticmethod
    def _disabled_cfg(tmp_path, monkeypatch) -> Config:
        cfg = Config(tmp_path / "config.json")
        cfg.set(
            "ai",
            {"enabled": False, "base_url": "https://example.com/v1", "model": "m"},
        )
        monkeypatch.setattr(cfg, "get_ai_api_key", lambda: "k")
        return cfg

    @staticmethod
    def _forbid_network(monkeypatch):
        def _forbid(req, timeout=60):
            raise AssertionError("隐私开关关闭时不应发起网络请求")

        monkeypatch.setattr("urllib.request.urlopen", _forbid)

    def test_extract_fields_raises_without_network(self, tmp_path, monkeypatch):
        cfg = self._disabled_cfg(tmp_path, monkeypatch)
        self._forbid_network(monkeypatch)
        with pytest.raises(ExternalDependencyError, match="关闭"):
            ai_client.extract_fields(cfg, "素材", ["实验名称"])

    def test_review_report_raises_without_network(self, tmp_path, monkeypatch):
        cfg = self._disabled_cfg(tmp_path, monkeypatch)
        self._forbid_network(monkeypatch)
        with pytest.raises(ExternalDependencyError, match="关闭"):
            ai_client.review_report(cfg, "报告文本")

    def test_chat_json_raises_when_disabled(self, tmp_path, monkeypatch):
        cfg = self._disabled_cfg(tmp_path, monkeypatch)
        self._forbid_network(monkeypatch)
        with pytest.raises(ExternalDependencyError, match="关闭"):
            ai_client._chat_json(cfg, [{"role": "user", "content": "x"}])

class TestCacheIntegration:
    """AI 成本缓存：命中 / 未命中 / 关闭 / 不串用户与字段。"""

    @staticmethod
    def _configured_cfg(cfg_path, monkeypatch, **ai_overrides) -> Config:
        cfg = Config(cfg_path)
        ai = {
            "enabled": True,
            "base_url": "https://example.com/v1",
            "model": "m",
            **ai_overrides,
        }
        cfg.set("ai", ai)
        monkeypatch.setattr(cfg, "get_ai_api_key", lambda: "k")
        return cfg

    @staticmethod
    def _counting_urlopen(monkeypatch):
        """安装计数 fake urlopen，返回固定可解析 JSON。"""
        calls = {"n": 0}

        def fake_urlopen(req, timeout=60):
            calls["n"] += 1
            return _FakeResp(
                json.dumps(
                    {"choices": [{"message": {"content": json.dumps({"fields": []})}}]}
                ).encode("utf-8")
            )

        monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
        return calls

    def test_cache_hit_returns_same_result_and_single_api_call(
        self, tmp_path, monkeypatch
    ):
        cfg = self._configured_cfg(tmp_path / "config.json", monkeypatch)
        calls = self._counting_urlopen(monkeypatch)
        fields1 = ai_client.extract_fields(cfg, "素材", ["实验名称"])
        fields2 = ai_client.extract_fields(cfg, "素材", ["实验名称"])
        assert fields1 == fields2
        assert calls["n"] == 1  # 第二次命中缓存，不再发请求

    def test_cache_miss_on_different_messages(self, tmp_path, monkeypatch):
        cfg = self._configured_cfg(tmp_path / "config.json", monkeypatch)
        calls = self._counting_urlopen(monkeypatch)
        ai_client.extract_fields(cfg, "素材A", ["实验名称"])
        ai_client.extract_fields(cfg, "素材B", ["实验名称"])
        assert calls["n"] == 2  # 消息不同 => 键不同 => 两次都未命中

    def test_cache_disabled_via_config(self, tmp_path, monkeypatch):
        cfg = self._configured_cfg(
            tmp_path / "config.json", monkeypatch, cache_enabled=False
        )
        calls = self._counting_urlopen(monkeypatch)
        ai_client.extract_fields(cfg, "素材", ["实验名称"])
        ai_client.extract_fields(cfg, "素材", ["实验名称"])
        assert calls["n"] == 2  # 配置关闭缓存 => 每次都发请求

    def test_cache_disabled_via_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv("FORMORA_AI_CACHE_ENABLED", "0")
        cfg = self._configured_cfg(tmp_path / "config.json", monkeypatch)
        calls = self._counting_urlopen(monkeypatch)
        ai_client.extract_fields(cfg, "素材", ["实验名称"])
        ai_client.extract_fields(cfg, "素材", ["实验名称"])
        assert calls["n"] == 2  # 环境变量关闭缓存

    def test_cache_does_not_mix_users(self, tmp_path, monkeypatch):
        cfg_a = self._configured_cfg(tmp_path / "config.json", monkeypatch)
        cfg_b = self._configured_cfg(
            tmp_path / "b" / "config.json", monkeypatch
        )
        cfg_b.set("user", {"id": "user-b"})
        calls = self._counting_urlopen(monkeypatch)
        ai_client.extract_fields(cfg_a, "素材", ["实验名称"])
        ai_client.extract_fields(cfg_b, "素材", ["实验名称"])
        assert calls["n"] == 2  # 不同用户命名空间 => 不串缓存

    def test_cache_does_not_mix_scopes(self, tmp_path, monkeypatch):
        cfg = self._configured_cfg(tmp_path / "config.json", monkeypatch)
        calls = self._counting_urlopen(monkeypatch)
        ai_client._chat_json(
            cfg, [{"role": "user", "content": "x"}], cache_scope="scope-a"
        )
        ai_client._chat_json(
            cfg, [{"role": "user", "content": "x"}], cache_scope="scope-b"
        )
        assert calls["n"] == 2  # 不同业务场景 => 键不同

    def test_temperature_affects_cache_key(self, tmp_path, monkeypatch):
        cfg = self._configured_cfg(tmp_path / "config.json", monkeypatch)
        calls = self._counting_urlopen(monkeypatch)
        ai_client._chat_json(
            cfg, [{"role": "user", "content": "x"}], temperature=0.1
        )
        ai_client._chat_json(
            cfg, [{"role": "user", "content": "x"}], temperature=0.9
        )
        assert calls["n"] == 2  # temperature 不同 => 键不同




class TestTryExtractFields:
    """try_extract_fields：失败不抛异常，返回 (None, 错误信息)，便于回退规则映射。"""

    @staticmethod
    def _configured_cfg(tmp_path, monkeypatch) -> Config:
        cfg = Config(tmp_path / "config.json")
        cfg.set(
            "ai", {"enabled": True, "base_url": "https://example.com/v1", "model": "m"}
        )
        monkeypatch.setattr(cfg, "get_ai_api_key", lambda: "k")
        return cfg

    def test_returns_fields_on_success(self, tmp_path, monkeypatch):
        cfg = self._configured_cfg(tmp_path, monkeypatch)
        content = json.dumps(
            {
                "fields": [
                    {
                        "field": "实验名称",
                        "value": "测试实验",
                        "source": "素材.txt",
                        "needs_confirmation": False,
                    }
                ]
            }
        )
        _install_fake_urlopen(
            monkeypatch,
            json.dumps(
                {"choices": [{"message": {"content": content}}]}
            ).encode("utf-8"),
        )
        fields, err = ai_client.try_extract_fields(cfg, "素材内容", ["实验名称"])
        assert err is None
        assert fields[0]["field"] == "实验名称"
        assert fields[0]["value"] == "测试实验"

    def test_returns_error_on_network_failure(self, tmp_path, monkeypatch):
        cfg = self._configured_cfg(tmp_path, monkeypatch)

        def boom(req, timeout=60):
            raise OSError("网络不可用")

        monkeypatch.setattr("urllib.request.urlopen", boom)
        fields, err = ai_client.try_extract_fields(cfg, "素材", ["实验名称"])
        assert fields is None
        assert err is not None
        assert "网络不可用" in err

    def test_returns_error_when_not_configured(self, tmp_path):
        cfg = Config(tmp_path / "config.json")
        fields, err = ai_client.try_extract_fields(cfg, "素材", ["实验名称"])
        assert fields is None
        assert err is not None

    def test_returns_error_on_invalid_response(self, tmp_path, monkeypatch):
        cfg = self._configured_cfg(tmp_path, monkeypatch)
        monkeypatch.setattr(ai_client, "_chat_json", lambda *a, **k: 42)
        fields, err = ai_client.try_extract_fields(cfg, "素材", ["实验名称"])
        assert fields is None
        assert err is not None
