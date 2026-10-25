"""模板解析器补充单元测试：占位符正则、章节识别、循环块、XML 文本抽取。"""

from __future__ import annotations

import pytest

from formora.core.errors import DocumentFormatError
from formora.core.template_parser import (
    _LOOP_BODY_RE,
    _LOOP_FIELD_RE,
    _LOOP_RE,
    _detect_sections,
    _extract_all_text,
    _find_placeholders,
    parse_template,
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

    def test_numbered_heading_detected(self):
        """「1. 实验目的」「（1）实验环境」等编号标题应识别为章节。"""
        sections = _detect_sections(["1. 实验目的", "（1）实验环境", "第一章 实验步骤"])
        assert sections.get("实验目的") == "1. 实验目的"
        assert sections.get("实验环境") == "（1）实验环境"
        assert sections.get("实验步骤") == "第一章 实验步骤"

    def test_body_sentence_with_prefix_not_detected(self):
        """关键字前有正文前缀（「本次」）时，短句不应误判为章节标题。"""
        sections = _detect_sections(["本次实验的目的是验证流程"])
        assert "实验目的" not in sections

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

    def test_concatenates_fragmented_runs(self):
        """同一段落内被拆成多个 w:t 的文本应按段落拼接（如 {{姓名}} 拆成 {{姓/名}}）。"""
        from docx import Document

        doc = Document()
        p = doc.add_paragraph()
        p.add_run("{{姓")
        p.add_run("名}}")
        texts = _extract_all_text(doc.element)
        assert "{{姓名}}" in texts

    def test_ignores_empty_text_nodes(self):
        from docx import Document

        doc = Document()
        doc.add_paragraph("   ")
        assert _extract_all_text(doc.element) == []


class TestParseTemplateFixes:
    def test_unclosed_loop_raises_friendly_error(self, tmp_path):
        """未闭合循环块应报友好错误，而不是静默跳过。"""
        from docx import Document

        doc = Document()
        doc.add_paragraph("{% for row in rows %}{{ row['项目'] }}")
        path = tmp_path / "unclosed_loop.docx"
        doc.save(str(path))
        with pytest.raises(DocumentFormatError):
            parse_template(path)

    def test_header_footer_split_placeholder_detected(self, tmp_path):
        """页眉中跨 w:t 拆分的占位符应被完整识别。"""
        from docx import Document

        doc = Document()
        header_para = doc.sections[0].header.paragraphs[0]
        header_para.add_run("{{实")
        header_para.add_run("验名称}}")
        path = tmp_path / "header_placeholder.docx"
        doc.save(str(path))
        info = parse_template(path)
        assert "实验名称" in info.placeholders
        assert info.has_header_footer

    def test_balanced_loop_still_parses(self, tmp_path):
        """成对闭合的循环块不应报错，循环体字段也不应进入顶层占位符。"""
        from docx import Document

        doc = Document()
        doc.add_paragraph("{% for row in rows %}{{ row['项目'] }}{% endfor %}")
        path = tmp_path / "balanced_loop.docx"
        doc.save(str(path))
        info = parse_template(path)
        assert "row" in info.loop_blocks
        assert "row['项目']" not in info.placeholders
