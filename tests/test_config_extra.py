"""配置管理补充测试：默认值深拷贝、原子写、DPAPI 平台限制。"""
from __future__ import annotations

import pytest

from formora.core.errors import UserError
from formora.services import config as config_module
from formora.services.config import DEFAULTS, Config, ensure_dirs


class TestDefaultsIsolation:
    def test_mutating_config_does_not_mutate_defaults(self, tmp_path):
        c = Config(tmp_path / "config.json")
        c.get("ai")["enabled"] = True
        assert DEFAULTS["ai"]["enabled"] is False

    def test_defaults_are_deep_copied(self, tmp_path):
        c1 = Config(tmp_path / "config.json")
        c2 = Config(tmp_path / "config2.json")
        c1.get("ai")["model"] = "gpt-other"
        assert c2.get("ai")["model"] == "gpt-4o-mini"


class TestAtomicSave:
    def test_save_writes_file_and_cleans_tmp(self, tmp_path):
        c = Config(tmp_path / "config.json")
        c.set("theme", "dark")
        c.save()
        assert (tmp_path / "config.json").exists()
        assert not (tmp_path / "config.json.tmp").exists()

    def test_save_roundtrip(self, tmp_path):
        c = Config(tmp_path / "config.json")
        c.set("theme", "dark")
        c.save()
        c2 = Config(tmp_path / "config.json")
        assert c2.get("theme") == "dark"


class TestDpapiPlatformGuard:
    def test_encrypt_raises_on_non_windows(self, monkeypatch):
        monkeypatch.setattr(config_module, "_IS_WINDOWS", False)
        with pytest.raises(UserError):
            config_module._dpapi_encrypt("secret")

    def test_decrypt_raises_on_non_windows(self, monkeypatch):
        monkeypatch.setattr(config_module, "_IS_WINDOWS", False)
        with pytest.raises(UserError):
            config_module._dpapi_decrypt("c2VjcmV0")

    def test_get_key_empty_when_no_enc(self, tmp_path):
        c = Config(tmp_path / "config.json")
        assert c.get_ai_api_key() == ""


class TestEnsureDirs:
    def test_creates_dirs(self, tmp_path, monkeypatch):
        app_dir = tmp_path / "app"
        log_dir = tmp_path / "logs"
        monkeypatch.setattr(config_module, "APP_DIR", app_dir)
        monkeypatch.setattr(config_module, "LOG_DIR", log_dir)
        ensure_dirs()
        assert app_dir.exists()
        assert log_dir.exists()
