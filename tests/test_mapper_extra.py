"""字段映射补充测试：归一化、别名、无数据/无占位符边界。"""

from __future__ import annotations

from pathlib import Path

from formora.core import mapper
from formora.core.models import DataSource, FieldMapping, TemplateInfo


class TestNormalize:
    def test_strips_whitespace_and_symbols(self):
        assert mapper._normalize("学生 姓名") == "学生姓名"
        assert mapper._normalize("student_id") == "studentid"
        assert mapper._normalize("学号（ID）") == "学号id"
        assert mapper._normalize("实验 名称 (一)") == "实验名称一"

    def test_empty(self):
        assert mapper._normalize("") == ""
        assert mapper._normalize(None) == ""


class TestAutoMapEdge:
    def test_no_data_all_constant(self):
        t = TemplateInfo(path=Path("t.docx"), placeholders=["姓名", "学号"])
        mappings = mapper.auto_map(t, None)
        assert all(m.source_type == "constant" for m in mappings)
        assert len(mappings) == 2

    def test_no_placeholders(self):
        t = TemplateInfo(path=Path("t.docx"), placeholders=[])
        ds = DataSource(path=Path("d.csv"), kind="csv", columns=["姓名"])
        assert mapper.auto_map(t, ds) == []

    def test_non_tabular_data_all_constant(self):
        t = TemplateInfo(path=Path("t.docx"), placeholders=["姓名"])
        ds = DataSource(path=Path("d.txt"), kind="txt", text="文字")
        mappings = mapper.auto_map(t, ds)
        assert all(m.source_type == "constant" for m in mappings)

    def test_contain_match_fallback(self):
        """占位符「编号」应包含匹配到列「实验编号」。"""
        t = TemplateInfo(path=Path("t.docx"), placeholders=["编号"])
        ds = DataSource(path=Path("d.csv"), kind="csv", columns=["实验编号"])
        mappings = mapper.auto_map(t, ds)
        assert mappings[0].source_type == "column"
        assert mappings[0].source_column == "实验编号"


class TestResolveValuesEdge:
    def test_text_source(self):
        mappings = [
            FieldMapping(template_field="结论", source_type="text", value="文本值")
        ]
        ctx = mapper.resolve_values(mappings)
        assert ctx["结论"] == "文本值"

    def test_chart_source(self):
        mappings = [
            FieldMapping(template_field="图", source_type="chart", value="a.png")
        ]
        ctx = mapper.resolve_values(mappings)
        assert ctx["图"] == "a.png"

    def test_row_none_columns_empty(self):
        mappings = [
            FieldMapping(
                template_field="姓名", source_type="column", source_column="姓名"
            )
        ]
        ctx = mapper.resolve_values(mappings, row=None)
        assert ctx["姓名"] == ""

    def test_constant_empty_becomes_empty_string(self):
        mappings = [
            FieldMapping(
                template_field="备注", source_type="constant", constant_value=None
            )
        ]
        ctx = mapper.resolve_values(mappings)
        assert ctx["备注"] == ""
