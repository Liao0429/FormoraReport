"""UI 冒烟测试（通过子进程运行，隔离 Qt 全局状态）。"""
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "ui_smoke_test.py"


@pytest.mark.skipif(sys.platform != "win32", reason="UI 测试针对 Windows")
def test_ui_smoke():
    import os
    env = {**os.environ, "QT_QPA_PLATFORM": "offscreen", "PYTHONIOENCODING": "utf-8"}
    result = subprocess.run(
        [sys.executable, str(SCRIPT)], capture_output=True, text=True, timeout=180, env=env)
    assert result.returncode == 0, f"UI 冒烟测试失败:\n{result.stdout}\n{result.stderr}"