"""核心数据模型单元测试（无 IO、无依赖，可离线快速运行）。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from formora.core.models import DataSource, FieldMapping, ReportTask, TableInfo, TemplateInfo


class TestTemplateInfo:
    def test_missing_core_fields(self):
        t = TemplateInfo(
            path=Path("x.docx"),
            sections={"实验名称": "一、实验名称"},
        )
        missing = t.missing_core_fields
        assert "实验名称" not in missing
        assert "实验目的" in missing
        assert "实验结论" in missing

    def test_defaults(self):
        t = TemplateInfo(path=Path("x.docx"))
        assert t.placeholders == []
        assert t.loop_blocks == []
        assert t.sections == {}
        assert t.tables == []
        assert not t.has_images


class TestTableInfo:
    def test_fields(self):
        t = TableInfo(index=0, header=["a", "b"], row_count=2, col_count=2, sample=[["a", "b"]])
        assert t.header == ["a", "b"]
        assert t.row_count == 2
        assert t.col_count == 2


class TestDataSource:
    def test_is_tabular(self):
        assert DataSource(path=Path("a.csv"), kind="csv").is_tabular
        assert DataSource(path=Path("a.xlsx"), kind="xlsx").is_tabular
        assert not DataSource(path=Path("a.txt"), kind="txt").is_tabular
        assert not DataSource(path=Path("a.pdf"), kind="pdf").is_tabular


class TestFieldMapping:
    def test_resolved_value(self):
        m = FieldMapping(template_field="f", source_type="constant", constant_value="常量值")
        assert m.resolved_value() == "常量值"

        m2 = FieldMapping(template_field="f", source_type="column", source_column="c", value="列值")
        assert m2.resolved_value() == "列值"

    def test_ai_tracking_defaults(self):
        m = FieldMapping(template_field="f", source_type="constant", constant_value="x")
        assert m.source == ""
        assert not m.needs_confirmation


class TestReportTask:
    def test_log_appends(self):
        task = ReportTask(name="测试任务", template_path=Path("t.docx"))
        task.log("warning", "user", "字段缺失")
        assert len(task.logs) == 1
        assert task.logs[0].level == "warning"
        assert task.logs[0].category == "user"
        assert task.logs[0].message == "字段缺失"

    def test_id_generated(self):
        task = ReportTask(name="a", template_path=Path("t.docx"))
        assert len(task.id) == 12
        assert ReportTask(name="b", template_path=Path("t.docx")).id != task.id