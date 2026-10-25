"""配置与 DPAPI 密钥加解密测试。"""

import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from formora.services.config import Config


@pytest.mark.skipif(sys.platform != "win32", reason="DPAPI 加密仅 Windows 支持")
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


def test_ai_enabled_default_true():
    """数据隐私开关：ai.enabled 默认开启，关闭后由设置页写入 False。"""
    tmp = Path(tempfile.mkdtemp()) / "config.json"
    c = Config(tmp)
    assert c.get("ai")["enabled"] is True


def test_config_chart_defaults():
    """图表样式配置默认值：颜色/尺寸/DPI/网格/字号。"""
    tmp = Path(tempfile.mkdtemp()) / "config.json"
    c = Config(tmp)
    chart_cfg = c.get("chart")
    assert chart_cfg["colors"] == ["#1f77b4", "#ff7f0e"]
    assert chart_cfg["figsize"] == [6, 4]
    assert chart_cfg["dpi"] == 150
    assert chart_cfg["grid"] is True
    assert chart_cfg["font_size"] == 10


def test_config_chart_roundtrip_and_partial_merge():
    """保存部分 chart 配置后，缺失字段仍回退默认值。"""
    tmp = Path(tempfile.mkdtemp()) / "config.json"
    c = Config(tmp)
    c.set("chart", {"dpi": 100, "grid": False})
    c.save()
    c2 = Config(tmp)
    chart_cfg = c2.get("chart")
    assert chart_cfg["dpi"] == 100
    assert chart_cfg["grid"] is False
    # 未保存的字段保持默认
    assert chart_cfg["colors"] == ["#1f77b4", "#ff7f0e"]
    assert chart_cfg["figsize"] == [6, 4]
    assert chart_cfg["font_size"] == 10
