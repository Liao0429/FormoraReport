"""配置管理补充测试：默认值深拷贝、原子写、DPAPI 平台限制。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from formora.core.errors import UserError
from formora.services import config as config_module
from formora.services.config import DEFAULTS, Config, ensure_dirs


class TestDefaultsIsolation:
    def test_mutating_config_does_not_mutate_defaults(self, tmp_path):
        c = Config(tmp_path / "config.json")
        c.get("ai")["enabled"] = False
        assert DEFAULTS["ai"]["enabled"] is True

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


# ---- 覆盖率补充：损坏配置备份/回退、set/get、DPAPI 解密、非 Windows 路径 ----

def test_load_corrupt_json_backs_up(tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text("{not valid json", encoding="utf-8")
    c = Config(cfg_path)
    assert c.data == DEFAULTS
    assert (tmp_path / "config.json.bak").exists()
    assert not cfg_path.exists()


def test_load_non_dict_backs_up(tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text("[1, 2]", encoding="utf-8")
    c = Config(cfg_path)
    assert c.data == DEFAULTS
    assert (tmp_path / "config.json.bak").exists()
    assert not cfg_path.exists()


def test_load_backup_oserror(tmp_path, monkeypatch):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text("{broken json", encoding="utf-8")

    def _raising_replace(self, target):
        raise OSError("simulated replace failure")

    monkeypatch.setattr(Path, "replace", _raising_replace)
    c = Config(cfg_path)  # 不应抛异常
    assert c.data == DEFAULTS
    assert cfg_path.exists()


def test_set_method(tmp_path):
    c = Config(tmp_path / "config.json")
    c.set("theme", "dark")
    assert c.get("theme") == "dark"
    c.set("custom", {"nested": [1, 2]})
    assert c.get("custom") == {"nested": [1, 2]}
    assert c.get("missing") is None
    assert c.get("missing", "fallback") == "fallback"


@pytest.mark.skipif(sys.platform != "win32", reason="DPAPI 仅 Windows 支持")
def test_dpapi_decrypt_success(tmp_path, monkeypatch):
    import base64
    import ctypes
    import ctypes.wintypes

    class FakeBlob(ctypes.Structure):
        _fields_ = [
            ("cbData", ctypes.wintypes.DWORD),
            ("pbData", ctypes.POINTER(ctypes.c_char)),
        ]

    plaintext = "sk-还原后的明文密钥"
    enc = base64.b64encode(b"encrypted-bytes").decode("ascii")
    keepalive = []

    def fake_unprotect(*args):
        out_ptr = args[6]
        out = ctypes.cast(out_ptr, ctypes.POINTER(FakeBlob)).contents
        buf = ctypes.create_string_buffer(plaintext.encode("utf-8"))
        keepalive.append(buf)
        out.pbData = ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))
        out.cbData = len(plaintext.encode("utf-8"))
        return True

    monkeypatch.setattr(ctypes.windll.crypt32, "CryptUnprotectData", fake_unprotect)
    monkeypatch.setattr(ctypes.windll.kernel32, "LocalFree", lambda _ptr: 0)

    c = Config(tmp_path / "config.json")
    c.data["ai"]["api_key_enc"] = enc
    assert c.get_ai_api_key() == plaintext


def test_non_windows_paths(monkeypatch, tmp_path):
    import importlib

    import formora.services

    original = config_module
    try:
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
        sys.modules.pop("formora.services.config", None)
        reloaded = importlib.import_module("formora.services.config")
        assert reloaded._IS_WINDOWS is False
        assert reloaded.APP_DIR == tmp_path / "xdg" / "FormoraReport"
        assert reloaded.CONFIG_PATH == reloaded.APP_DIR / "config.json"
        assert reloaded.LOG_DIR == reloaded.APP_DIR / "logs"
    finally:
        sys.modules["formora.services.config"] = original
        formora.services.config = original
