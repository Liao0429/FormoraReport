"""模板解析器补充单元测试：占位符正则、章节识别、循环块、XML 文本抽取。"""

from __future__ import annotations

from formora.core.template_parser import (
    _LOOP_BODY_RE,
    _LOOP_FIELD_RE,
    _LOOP_RE,
    _detect_sections,
    _extract_all_text,
    _find_placeholders,
)


class TestFindPlaceholders:
    def test_empty(self):
        assert _find_placeholders("") == set()

    def test_three_syntaxes(self):
        found = _find_placeholders("{{姓名}} ${学号} 【班级】")
        assert found == {"姓名", "学号", "班级"}

    def test_internal_spaces_kept(self):
        assert _find_placeholders("{{ 学生 姓名 }}") == {"学生 姓名"}

    def test_multiline_not_matched(self):
        # 正则 `[^{}\n]` 排除换行，但 `\s*` 会吞掉占位符两侧的换行，
        # 因此 {{ 换行 姓名 换行 }} 中的"姓名"仍会被匹配
        assert _find_placeholders("{{\n姓名\n}}") == {"姓名"}

    def test_no_braces_inside_name(self):
        assert "a{b" not in _find_placeholders("{{a{b}}")
        assert "a}b" not in _find_placeholders("{{a}b}}")

    def test_dollar_empty_name(self):
        assert "${}" not in _find_placeholders("${}")


class TestLoopRegex:
    def test_loop_re_matches(self):
        m = _LOOP_RE.search("{% for row in data_rows %}")
        assert m is not None
        assert m.group(1) == "row"
        assert m.group(2) == "data_rows"

    def test_loop_field_re_bracket(self):
        assert _LOOP_FIELD_RE.search("{{ row['项目'] }}")
        assert _LOOP_FIELD_RE.search('{{ item["name"] }}')

    def test_loop_field_re_dot(self):
        assert _LOOP_FIELD_RE.search("{{ row.项目 }}")

    def test_loop_body_re_removes_block(self):
        text = "开头 {% for row in rows %}{{ row['a'] }}{% endfor %} 结尾"
        removed = _LOOP_BODY_RE.sub("", text)
        assert "row['a']" not in removed
        assert "开头" in removed and "结尾" in removed


class TestDetectSections:
    def test_heading_detected(self):
        sections = _detect_sections(["一、实验名称", "二、实验目的"])
        assert sections == {"实验名称": "一、实验名称", "实验目的": "二、实验目的"}

    def test_keyword_late_in_paragraph_not_detected(self):
        """「实验目的」出现在前 8 字符内且段落短，应识别为章节标题。"""
        sections = _detect_sections(["本次实验的目的是验证流程"])
        assert "实验目的" in sections

    def test_long_paragraph_not_detected(self):
        """标题段落过长（>50 字符）不视为章节标题。"""
        long_para = "实验名称：" + "很长的内容" * 10
        sections = _detect_sections([long_para])
        assert "实验名称" not in sections

    def test_first_occurrence_wins(self):
        sections = _detect_sections(["一、实验名称", "另一段", "1. 实验名称（重复）"])
        assert sections["实验名称"] == "一、实验名称"

    def test_synonyms(self):
        sections = _detect_sections(["题目：xxx", "总结"])
        assert sections.get("实验名称") == "题目：xxx"
        assert sections.get("实验结论") == "总结"


class TestExtractAllText:
    def test_extracts_paragraph_text(self):
        from docx import Document

        doc = Document()
        doc.add_paragraph("第一段")
        doc.add_paragraph("第二段")
        texts = _extract_all_text(doc.element)
        assert "第一段" in texts
        assert "第二段" in texts

    def test_extracts_table_cell_text(self):
        from docx import Document

        doc = Document()
        table = doc.add_table(rows=1, cols=1)
        table.cell(0, 0).text = "单元格内容"
        texts = _extract_all_text(doc.element)
        assert "单元格内容" in texts

    def test_ignores_empty_text_nodes(self):
        from docx import Document

        doc = Document()
        doc.add_paragraph("   ")
        assert _extract_all_text(doc.element) == []
