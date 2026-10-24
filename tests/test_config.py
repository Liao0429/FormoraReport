"""配置与 DPAPI 密钥加解密测试。"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from formora.services.config import Config


def test_config_defaults_and_roundtrip():
    tmp = Path(tempfile.mkdtemp()) / "config.json"
    c = Config(tmp)
    assert c.get("theme") == "light"
    c.set_ai_api_key("sk-test-secret-123")
    saved = tmp.read_text(encoding="utf-8")
    # 密文不应包含明文
    assert "sk-test-secret-123" not in saved
    assert c.get_ai_api_key() == "sk-test-secret-123"


def test_config_ai_settings():
    tmp = Path(tempfile.mkdtemp()) / "config.json"
    c = Config(tmp)
    c.set("ai", {"enabled": True, "base_url": "https://example.com/v1", "model": "m"})
    c.save()
    c2 = Config(tmp)
    assert c2.get("ai")["base_url"] == "https://example.com/v1"
    assert c2.get("ai")["model"] == "m"


def test_empty_key_returns_empty():
    tmp = Path(tempfile.mkdtemp()) / "config.json"
    c = Config(tmp)
    c.set_ai_api_key("")
    assert c.get_ai_api_key() == ""