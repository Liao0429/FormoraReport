"""服务层单元与集成测试：日志分类、历史记录、报告服务。"""

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from formora.core import data_reader, mapper, template_parser
from formora.core.errors import (
    DocumentFormatError,
    ExternalDependencyError,
    UserError,
)
from formora.core.models import DataSource, ReportTask
from formora.services import history, logging_setup
from formora.services.config import Config
from formora.services.report_service import (
    auto_chart,
    generate_single,
    is_image_field,
    materials_text,
)

SAMPLES = Path(__file__).resolve().parent.parent / "tests" / "samples"
TEMPLATE = SAMPLES / "实验报告模板.docx"
DATA = SAMPLES / "实验数据.csv"


class TestCategoryOf:
    def test_user(self):
        assert logging_setup.category_of(UserError("x")) == "user"

    def test_format(self):
        assert logging_setup.category_of(DocumentFormatError("x")) == "format"

    def test_dependency(self):
        assert logging_setup.category_of(ExternalDependencyError("x")) == "dependency"

    def test_unknown_is_bug(self):
        assert logging_setup.category_of(RuntimeError("x")) == "bug"


class TestHistory:
    def test_record_and_load_roundtrip(self, tmp_path, monkeypatch):
        hist_path = tmp_path / "history.jsonl"
        monkeypatch.setattr(history, "HISTORY_PATH", hist_path)

        task = ReportTask(name="历史任务", template_path=Path("t.docx"))
        task.log("success", "system", "报告已生成")
        history.record_task(task)

        entries = history.load_history()
        assert len(entries) == 1
        assert entries[0]["name"] == "历史任务"
        assert entries[0]["status"] == "draft"
        assert entries[0]["logs"][0]["message"] == "报告已生成"

    def test_load_empty_when_no_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(history, "HISTORY_PATH", tmp_path / "missing.jsonl")
        assert history.load_history() == []

    def test_load_skips_bad_lines(self, tmp_path, monkeypatch):
        hist_path = tmp_path / "history.jsonl"
        hist_path.write_text('{"good":1}\nnot-json\n{"good":2}\n', encoding="utf-8")
        monkeypatch.setattr(history, "HISTORY_PATH", hist_path)
        entries = history.load_history()
        assert len(entries) == 2


class TestReportService:
    def test_is_image_field(self):
        assert is_image_field("截图")
        assert is_image_field("实验结果图")
        assert is_image_field("chart")
        assert is_image_field("数据图")
        assert not is_image_field("姓名")
        assert not is_image_field("")

    def test_materials_text_tabular(self):
        data = DataSource(
            path=Path("d.csv"),
            kind="csv",
            columns=["项目", "数值"],
            rows=[{"项目": "样本A", "数值": 12.5}, {"项目": "样本B", "数值": 18.2}],
        )
        state = SimpleNamespace(data=data)
        text = materials_text(state)
        assert "项目=样本A" in text
        assert "数值=12.5" in text

    def test_materials_text_none(self):
        assert materials_text(SimpleNamespace(data=None)) == ""

    def test_materials_text_text_source(self):
        data = DataSource(path=Path("t.txt"), kind="txt", text="纯文本素材")
        state = SimpleNamespace(data=data)
        assert "纯文本素材" in materials_text(state)

    def test_auto_chart_returns_png(self, tmp_path):
        cfg = Config(tmp_path / "config.json")
        cfg.set("output_dir", str(tmp_path / "out"))
        data = DataSource(
            path=DATA,
            kind="csv",
            columns=["项目", "数值"],
            rows=[{"项目": "A", "数值": 1.0}, {"项目": "B", "数值": 2.0}],
        )
        state = SimpleNamespace(
            data=data,
            config=cfg,
            task=ReportTask(name="自动图表", template_path=TEMPLATE),
        )
        img = auto_chart(state)
        assert img
        assert Path(img).exists()

    def test_auto_chart_none_for_text(self, tmp_path):
        cfg = Config(tmp_path / "config.json")
        cfg.set("output_dir", str(tmp_path / "out"))
        state = SimpleNamespace(
            data=DataSource(path=Path("t.txt"), kind="txt", text="文字"),
            config=cfg,
            task=ReportTask(name="x", template_path=TEMPLATE),
        )
        assert auto_chart(state) is None


def _make_state(tmp_path):
    """构造带真实样例的完整任务状态（输出与历史都隔离在临时目录）。"""
    cfg = Config(tmp_path / "config.json")
    cfg.set("output_dir", str(tmp_path / "out"))

    template = template_parser.parse_template(TEMPLATE)
    data = data_reader.read_data(DATA)
    mappings = mapper.auto_map(template, data)
    constants = {
        "实验名称": "集成测试实验",
        "实验目的": "验证服务层全流程",
        "实验环境": "本机",
        "实验步骤": "1. 映射；2. 生成",
        "实验结果": "成功",
        "问题分析": "无",
        "实验结论": "结论",
    }
    for m in mappings:
        if m.source_type == "constant" and m.template_field in constants:
            m.constant_value = constants[m.template_field]

    task = ReportTask(name="服务层集成", template_path=TEMPLATE)
    return SimpleNamespace(
        config=cfg,
        template=template,
        data=data,
        mappings=mappings,
        task=task,
    )


class TestGenerateSingleIntegration:
    def test_generate_single_creates_docx_and_history(self, tmp_path, monkeypatch):
        hist_path = tmp_path / "history.jsonl"
        monkeypatch.setattr(history, "HISTORY_PATH", hist_path)

        state = _make_state(tmp_path)
        out = generate_single(state)

        assert out.exists()
        from docx import Document

        texts = " ".join(p.text for p in Document(str(out)).paragraphs)
        assert "集成测试实验" in texts

        # 任务状态更新且历史已落盘
        assert state.task.status == "done"
        entries = history.load_history()
        assert len(entries) == 1
        assert entries[0]["output_path"] == str(out)
