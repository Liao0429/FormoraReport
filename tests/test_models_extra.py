"""核心数据模型补充测试：默认值、属性、边界行为。"""

from __future__ import annotations

from pathlib import Path

from formora.core.models import (
    DataSource,
    FieldMapping,
    ReportTask,
    TaskLog,
    TemplateInfo,
    ValidationIssue,
)


class TestTaskLog:
    def test_fields(self):
        log = TaskLog(level="info", category="system", message="开始")
        assert log.level == "info"
        assert log.category == "system"
        assert log.message == "开始"


class TestValidationIssue:
    def test_fields(self):
        issue = ValidationIssue(severity="error", field="姓名", message="缺失")
        assert issue.severity == "error"
        assert issue.field == "姓名"
        assert issue.message == "缺失"


class TestFieldMappingDefaults:
    def test_default_source_type_is_column(self):
        m = FieldMapping(template_field="姓名")
        assert m.source_type == "column"
        assert m.source_column is None
        assert m.constant_value is None
        assert m.value is None
        assert m.required is False

    def test_resolved_value_text(self):
        m = FieldMapping(template_field="结论", source_type="text", value="自由文本")
        assert m.resolved_value() == "自由文本"

    def test_resolved_value_other(self):
        m = FieldMapping(template_field="图表", source_type="chart", value="chart.png")
        assert m.resolved_value() == "chart.png"


class TestDataSourceDefaults:
    def test_defaults(self):
        ds = DataSource(path=Path("a.csv"), kind="csv")
        assert ds.columns == []
        assert ds.rows == []
        assert ds.text == ""
        assert ds.summary == ""


class TestTemplateInfo:
    def test_missing_core_fields_with_conclusion_alias(self):
        """sections 只有「结论」时，'结论' 不算缺失，但 '实验结论' 仍缺失。"""
        t = TemplateInfo(path=Path("x.docx"), sections={"结论": "九、结论"})
        missing = t.missing_core_fields
        assert "结论" not in missing
        assert "实验结论" in missing

    def test_missing_core_fields_all_present(self):
        t = TemplateInfo(
            path=Path("x.docx"),
            sections={
                "实验名称": "一、实验名称",
                "实验目的": "二、实验目的",
                "实验环境": "三、实验环境",
                "实验步骤": "四、实验步骤",
                "实验数据": "五、实验数据",
                "实验结果": "六、实验结果",
                "问题分析": "七、问题分析",
                "实验结论": "八、实验结论",
            },
        )
        # 模板缺"结论"章节（CORE_FIELDS 含"结论"）
        assert t.missing_core_fields == ["结论"]


class TestReportTask:
    def test_default_status_and_output(self):
        task = ReportTask(name="t", template_path=Path("t.docx"))
        assert task.status == "draft"
        assert task.output_path is None
        assert task.logs == []

    def test_log_appends_multiple(self):
        task = ReportTask(name="t", template_path=Path("t.docx"))
        task.log("info", "system", "a")
        task.log("error", "bug", "b")
        assert [l.message for l in task.logs] == ["a", "b"]

    def test_ids_unique(self):
        ids = {
            ReportTask(name="a", template_path=Path("t.docx")).id for _ in range(100)
        }
        assert len(ids) == 100
