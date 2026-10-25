"""UI 冒烟测试（通过子进程运行，隔离 Qt 全局状态）。"""

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.ui

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "ui_smoke_test.py"


@pytest.mark.skipif(sys.platform != "win32", reason="UI 测试针对 Windows")
def test_ui_smoke():
    import os

    env = {**os.environ, "QT_QPA_PLATFORM": "offscreen", "PYTHONIOENCODING": "utf-8"}
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        check=False,
        capture_output=True,
        text=True,
        timeout=180,
        env=env,
    )
    assert result.returncode == 0, f"UI 冒烟测试失败:\n{result.stdout}\n{result.stderr}"
_PRIVACY_SWITCH_CODE = r"""
import os
import sys
import tempfile
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.join(os.environ["FORMORA_ROOT"], "src"))

from PySide6.QtWidgets import QApplication

from formora.services.config import Config
from formora.ui.app_state import AppState
from formora.ui.pages.settings_page import SettingsPage

cfg = Config(Path(tempfile.mkdtemp()) / "config.json")
app = QApplication([])
page = SettingsPage(AppState(config=cfg), lambda *a: None)
assert page.ai_enabled.isChecked(), "「启用 AI 辅助」开关应默认开启"
assert page.ai_base.isEnabled(), "开启时 AI 配置项应可用"
page.ai_enabled.setChecked(False)
assert not page.ai_enabled.isChecked()
assert not page.ai_base.isEnabled(), "关闭后 AI 配置项应禁用"
assert not page.ai_model.isEnabled()
assert not page.ai_key.isEnabled()
assert not page.ai_temp.isEnabled()
assert not page.test_btn.isEnabled(), "关闭后「测试连接」按钮应禁用"
print("SETTINGS_PRIVACY_SWITCH_OK")
"""


@pytest.mark.skipif(sys.platform != "win32", reason="UI 测试针对 Windows")
def test_ui_settings_privacy_switch():
    import os

    env = {
        **os.environ,
        "QT_QPA_PLATFORM": "offscreen",
        "PYTHONIOENCODING": "utf-8",
        "FORMORA_ROOT": str(SCRIPT.parent.parent),
    }
    result = subprocess.run(
        [sys.executable, "-c", _PRIVACY_SWITCH_CODE],
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )
    assert result.returncode == 0, (
        f"设置页隐私开关测试失败:\n{result.stdout}\n{result.stderr}"
    )
    assert "SETTINGS_PRIVACY_SWITCH_OK" in result.stdout

