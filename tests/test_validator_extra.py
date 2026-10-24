"""校验器补充测试：图片跳过、AI 待确认、非字符串值。"""
from __future__ import annotations

from pathlib import Path

from formora.core.models import FieldMapping, TemplateInfo
from formora.core.validator import validate_context, validate_mappings


class TestValidateMappingsExtra:
    def test_image_placeholder_skipped(self):
        """自动图表占位符在 skip 集合中时，未选图不应报错。"""
        mappings = [FieldMapping(template_field="图表", source_type="image", value="")]
        issues = validate_mappings(mappings, skip_image_placeholders={"图表"})
        assert not any(i.field == "图表" for i in issues)

    def test_needs_confirmation_warns(self):
        mappings = [FieldMapping(
            template_field="结论", source_type="constant",
            constant_value="x", needs_confirmation=True)]
        issues = validate_mappings(mappings)
        assert any(i.field == "结论" and "待确认" in i.message for i in issues)

    def test_existing_image_no_error(self, tmp_path):
        img = tmp_path / "a.png"
        img.write_bytes(b"fake")
        mappings = [FieldMapping(template_field="图", source_type="image", value=str(img))]
        assert validate_mappings(mappings) == []


class TestValidateContextExtra:
    def test_none_value_flags_core_field(self):
        t = TemplateInfo(path=Path("t.docx"), sections={"实验名称": "一、实验名称"})
        issues = validate_context({"实验名称": None}, t)
        assert any(i.field == "实验名称" and i.severity == "warning" for i in issues)

    def test_non_string_value_not_flagged(self):
        t = TemplateInfo(path=Path("t.docx"), sections={"实验名称": "一、实验名称"})
        issues = validate_context({"实验名称": 0}, t)
        assert not any(i.field == "实验名称" for i in issues)

    def test_image_placeholder_skipped(self):
            t = TemplateInfo(path=Path("t.docx"), placeholders=["图表", "姓名"])
            # "图表"是图片占位符被跳过；"姓名"是普通占位符且缺值，应报警
            issues = validate_context({}, t, image_placeholders={"图表"})
            fields = {i.field for i in issues}
            assert "图表" not in fields
            assert "姓名" in fields

    def test_no_sections_no_issues(self):
        t = TemplateInfo(path=Path("t.docx"), placeholders=["姓名"])
        assert validate_context({"姓名": "x"}, t) == []

