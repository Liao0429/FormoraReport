"""AppState 测试：新建任务时状态复位。"""

from __future__ import annotations

from pathlib import Path

from formora.core.models import DataSource, TemplateInfo
from formora.services.config import Config
from formora.ui.app_state import AppState


def _make_state(tmp_path):
    cfg = Config(tmp_path / "config.json")
    return AppState(config=cfg)


class TestNewTask:
    def test_resets_all_fields(self, tmp_path):
        state = _make_state(tmp_path)
        # 先填充旧状态
        state.template = TemplateInfo(path=Path("t.docx"), placeholders=["x"])
        state.data = DataSource(path=Path("d.csv"), kind="csv", columns=["c"])
        state.mappings = []
        state.output_path = "old.docx"

        task = state.new_task(name="新任务")
        assert task.name == "新任务"
        assert state.template is None
        assert state.data is None
        assert state.mappings == []
        assert state.output_path is None
        assert state.task is task

    def test_keeps_config(self, tmp_path):
        state = _make_state(tmp_path)
        cfg = state.config
        state.new_task()
        assert state.config is cfg

    def test_created_at_set(self, tmp_path):
        state = _make_state(tmp_path)
        task = state.new_task()
        assert task.created_at  # 非空字符串
        assert len(task.created_at) >= 8

    def test_default_name(self, tmp_path):
        state = _make_state(tmp_path)
        task = state.new_task()
        assert task.name == "新任务"
