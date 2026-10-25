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




_AI_MAPPING_CODE = r"""
import json
import os
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["FORMORA_AI_CACHE_ENABLED"] = "0"  # 禁用 AI 结果缓存，保证测试确定性
sys.path.insert(0, os.path.join(os.environ["FORMORA_ROOT"], "src"))

from PySide6.QtWidgets import QApplication, QMessageBox

from formora.core import data_reader, mapper, template_parser
from formora.services.config import Config
from formora.ui.app_state import AppState
from formora.ui.pages.mapping_page import MappingPage

# 非阻塞：替换所有模态对话框，避免测试卡在弹窗
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.critical = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)

SAMPLES = Path(os.environ["FORMORA_ROOT"]) / "tests" / "samples"


class _FakeResp:
    def __init__(self, payload: bytes):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self._payload


def _wait_thread(page, app, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline and page._ai_thread is not None and page._ai_thread.isRunning():
        app.processEvents()
        time.sleep(0.05)
    app.processEvents()
    assert page._ai_thread is not None and not page._ai_thread.isRunning(), "AI 线程未在超时前结束"


# ---------- 状态准备 ----------
cfg = Config(Path(tempfile.mkdtemp()) / "config.json")
cfg.set("ai", {"enabled": True, "base_url": "https://example.com/v1", "model": "m"})
cfg.set("privacy", {"upload_warning_shown": True})
cfg.get_ai_api_key = lambda: "k"  # 实例属性覆盖方法，避免 DPAPI

template = template_parser.parse_template(SAMPLES / "实验报告模板.docx")
data = data_reader.read_data(SAMPLES / "实验数据.csv")
state = AppState(config=cfg)
state.new_task("AI映射测试")
state.task.template_path = SAMPLES / "实验报告模板.docx"
state.task.data_source = data
state.template = template
state.data = data
state.mappings = mapper.auto_map(template, data)

app = QApplication([])
page = MappingPage(state, lambda *a: None)
page.refresh()


def _row_of(field: str) -> int:
    for r in range(page.table.rowCount()):
        if page.table.item(r, 0).text() == field:
            return r
    raise AssertionError(f"未找到字段 {field}")


# ---------- 模拟用户手动填写「实验名称」 ----------
row = _row_of("实验名称")
edit = page._value_edit(row)
edit.setText("用户手填")
page._value_changed(row)
assert "实验名称" in page._user_fields, "手动填写后应记录用户字段"
assert state.mappings[row].constant_value == "用户手填"

# ---------- 阶段一：AI 网络失败 -> 自动回退规则映射，不覆盖用户手填 ----------
def boom(req, timeout=60):
    raise OSError("模拟网络不可用")


urllib.request.urlopen = boom
page._ai_assist()
_wait_thread(page, app)
assert state.mappings[row].constant_value == "用户手填", "AI 失败后用户手填应保留"
rule = {m.template_field: m for m in mapper.auto_map(template, data)}
for m in state.mappings:
    if m.template_field in page._user_fields or m.source_type == "image":
        continue
    rm = rule[m.template_field]
    assert m.source_type == rm.source_type, f"{m.template_field} 应回退为规则映射"
    assert m.source_column == rm.source_column, f"{m.template_field} 数据列应回退"
assert "回退" in page.issues_text.toPlainText(), "应提示已回退规则映射"
print("PHASE1_AI_FAILURE_FALLBACK_OK")

# ---------- 阶段二：AI 成功 -> 也不覆盖用户手填，只填充未手动修改字段 ----------
def fake_urlopen(req, timeout=60):
    template_fields = [
        m.template_field for m in state.mappings if m.source_type != "image"
    ]
    content = json.dumps(
        {
            "fields": [
                {
                    "field": f,
                    "value": f"AI-{f}",
                    "source": "实验数据.csv",
                    "needs_confirmation": False,
                }
                for f in template_fields
            ]
        }
    )
    body = json.dumps({"choices": [{"message": {"content": content}}]})
    return _FakeResp(body.encode("utf-8"))


urllib.request.urlopen = fake_urlopen
page._ai_assist()
_wait_thread(page, app)
assert state.mappings[row].constant_value == "用户手填", "AI 成功也不应覆盖用户手填"
by = {m.template_field: m for m in state.mappings}
assert by["实验目的"].source_type == "constant"
assert by["实验目的"].constant_value == "AI-实验目的", "AI 应填充未手动修改的字段"
assert "已保留" in page.issues_text.toPlainText(), "应提示已保留用户手动填写的字段"
print("PHASE2_AI_SUCCESS_PRESERVE_MANUAL_OK")
print("AI_MAPPING_UI_OK")
"""


@pytest.mark.skipif(sys.platform != "win32", reason="UI 测试针对 Windows")
def test_ui_ai_mapping_preserve_manual_and_fallback():
    """AI 映射 UI：失败自动回退规则映射；成功/失败均不覆盖用户手动填写。"""
    import os

    env = {
        **os.environ,
        "QT_QPA_PLATFORM": "offscreen",
        "PYTHONIOENCODING": "utf-8",
        "FORMORA_ROOT": str(SCRIPT.parent.parent),
    }
    result = subprocess.run(
        [sys.executable, "-c", _AI_MAPPING_CODE],
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )
    assert result.returncode == 0, (
        f"AI 映射 UI 测试失败:\n{result.stdout}\n{result.stderr}"
    )
    assert "AI_MAPPING_UI_OK" in result.stdout
