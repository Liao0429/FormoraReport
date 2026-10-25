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


class TestApplyAiSuggestions:
    """AI 建议落盘：用户手动填写的映射优先保留，不被 AI 覆盖。"""

    @staticmethod
    def _mapping(field: str, source_type: str = "constant", **kw) -> FieldMapping:
        return FieldMapping(template_field=field, source_type=source_type, **kw)

    def test_does_not_overwrite_user_manual_mapping(self):
        mappings = [
            FieldMapping(
                template_field="实验名称",
                source_type="constant",
                constant_value="用户手填",
                source="",
                needs_confirmation=False,
            )
        ]
        ai_result = [
            {
                "field": "实验名称",
                "value": "AI 内容",
                "source": "素材.txt",
                "needs_confirmation": False,
            }
        ]
        applied, confirmed, preserved = mapper.apply_ai_suggestions(
            mappings, ai_result, protected_fields={"实验名称"}
        )
        assert applied == 0
        assert confirmed == []
        assert preserved == ["实验名称"]
        assert mappings[0].constant_value == "用户手填"
        assert mappings[0].source == ""
        assert mappings[0].needs_confirmation is False

    def test_applies_to_unprotected_fields(self):
        mappings = [
            self._mapping("实验名称", constant_value=""),
            self._mapping("实验目的"),
        ]
        ai_result = [
            {
                "field": "实验名称",
                "value": "AI 名称",
                "source": "a.txt",
                "needs_confirmation": False,
            },
            {
                "field": "实验目的",
                "value": "待补充",
                "source": "",
                "needs_confirmation": True,
            },
        ]
        applied, confirmed, preserved = mapper.apply_ai_suggestions(mappings, ai_result)
        assert applied == 2
        assert confirmed == ["实验名称", "实验目的（待确认）"]
        assert preserved == []
        assert mappings[0].constant_value == "AI 名称"
        assert mappings[0].source == "a.txt"
        assert mappings[1].needs_confirmation is True

    def test_skips_image_fields(self):
        mappings = [self._mapping("图表", source_type="image")]
        applied, confirmed, preserved = mapper.apply_ai_suggestions(
            mappings,
            [{"field": "图表", "value": "x", "needs_confirmation": False}],
        )
        assert applied == 0
        assert confirmed == []
        assert preserved == []
        assert mappings[0].source_type == "image"

    def test_skips_unknown_fields(self):
        mappings = [self._mapping("姓名")]
        applied, _, _ = mapper.apply_ai_suggestions(
            mappings,
            [{"field": "不存在的字段", "value": "x", "needs_confirmation": False}],
        )
        assert applied == 0

    def test_empty_result(self):
        mappings = [self._mapping("姓名")]
        applied, confirmed, preserved = mapper.apply_ai_suggestions(mappings, [])
        assert (applied, confirmed, preserved) == (0, [], [])


class TestFallbackToRuleMapping:
    """AI 失败回退：自动恢复规则映射，且不覆盖用户手动填写。"""

    @staticmethod
    def _template() -> TemplateInfo:
        return TemplateInfo(path=Path("t.docx"), placeholders=["姓名", "学号", "结论"])

    @staticmethod
    def _data() -> DataSource:
        return DataSource(path=Path("d.csv"), kind="csv", columns=["姓名", "学号"])

    def test_restores_rule_mapping_for_unprotected_fields(self):
        t = self._template()
        ds = self._data()
        mappings = [
            FieldMapping(
                template_field="姓名",
                source_type="constant",
                constant_value="AI 内容",
                source="a.txt",
            ),
            FieldMapping(
                template_field="学号",
                source_type="constant",
                constant_value="AI 内容",
                source="a.txt",
            ),
            FieldMapping(
                template_field="结论",
                source_type="constant",
                constant_value="AI 内容",
                source="a.txt",
            ),
        ]
        restored, fields = mapper.fallback_to_rule_mapping(mappings, t, ds)
        assert restored == 3
        assert set(fields) == {"姓名", "学号", "结论"}
        by = {m.template_field: m for m in mappings}
        # 有列匹配 -> 回退为数据列映射
        assert by["姓名"].source_type == "column"
        assert by["姓名"].source_column == "姓名"
        assert by["姓名"].constant_value is None
        assert by["姓名"].source == ""
        assert by["姓名"].needs_confirmation is False
        assert by["学号"].source_type == "column"
        assert by["学号"].source_column == "学号"
        # 无列匹配 -> 回退为常量空值
        assert by["结论"].source_type == "constant"
        assert by["结论"].constant_value == ""
        assert by["结论"].source == ""

    def test_preserves_user_manual_mappings(self):
        t = self._template()
        ds = self._data()
        mappings = [
            FieldMapping(
                template_field="姓名",
                source_type="constant",
                constant_value="用户手填",
            )
        ]
        restored, fields = mapper.fallback_to_rule_mapping(
            mappings, t, ds, protected_fields={"姓名"}
        )
        assert restored == 0
        assert fields == []
        assert mappings[0].constant_value == "用户手填"

    def test_preserves_image_fields(self):
        t = self._template()
        ds = self._data()
        mappings = [
            FieldMapping(template_field="图表", source_type="image", value="x.png")
        ]
        restored, fields = mapper.fallback_to_rule_mapping(mappings, t, ds)
        assert restored == 0
        assert fields == []
        assert mappings[0].source_type == "image"

    def test_no_template_returns_zero(self):
        mappings = [FieldMapping(template_field="姓名")]
        restored, fields = mapper.fallback_to_rule_mapping(mappings, None, None)
        assert (restored, fields) == (0, [])
