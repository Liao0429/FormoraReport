"""报告生成器补充测试：目录创建、解析缓存、依赖缺失、图片包装。"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from formora.core import generator
from formora.core.errors import DocumentFormatError, ExternalDependencyError
from formora.core.models import TemplateInfo


def _make_mini_png(path: Path) -> Path:
    from PIL import Image
    img = Image.new("RGB", (4, 4), "#4a90d9")
    img.save(str(path))
    return path


class TestOutputDirs:
    def test_creates_nested_parent(self, tmp_path):
        """输出目录不存在时应自动创建。"""
        from docx import Document
        tpl = tmp_path / "tpl.docx"
        doc = Document()
        doc.add_paragraph("{{实验名称}}")
        doc.save(str(tpl))
        out = tmp_path / "deep" / "nested" / "out.docx"
        generator.generate_report(tpl, {"实验名称": "x"}, out)
        assert out.exists()

    def test_reuses_template_info(self, tmp_path, monkeypatch):
        """传入 template_info 时不应重复解析模板。"""
        from docx import Document
        tpl = tmp_path / "tpl.docx"
        doc = Document()
        doc.add_paragraph("{{实验名称}}")
        doc.save(str(tpl))
        info = TemplateInfo(path=tpl, placeholders=["实验名称"])

        import formora.core.generator as gen
        monkeypatch.setattr(gen, "parse_template", lambda *a, **k: pytest.fail("不应重新解析"))
        out = generator.generate_report(tpl, {"实验名称": "x"}, tmp_path / "out.docx", template_info=info)
        assert out.exists()


class TestDependencyErrors:
    def test_docxtpl_missing_raises(self, tmp_path, monkeypatch):
        from docx import Document
        tpl = tmp_path / "tpl.docx"
        doc = Document()
        doc.add_paragraph("{{实验名称}}")
        doc.save(str(tpl))
        info = TemplateInfo(path=tpl, placeholders=["实验名称"])
        monkeypatch.setitem(sys.modules, "docxtpl", None)
        with pytest.raises(ExternalDependencyError):
            generator.generate_report(tpl, {"实验名称": "x"}, tmp_path / "out.docx", template_info=info)

    def test_no_placeholders_raises(self, tmp_path):
        from docx import Document
        tpl = tmp_path / "tpl.docx"
        doc = Document()
        doc.add_paragraph("没有任何占位符")
        doc.save(str(tpl))
        info = TemplateInfo(path=tpl, placeholders=[], loop_blocks=[])
        with pytest.raises(DocumentFormatError):
            generator.generate_report(tpl, {}, tmp_path / "out.docx", template_info=info)


class TestRenderImage:
    def test_missing_image_raises(self, tmp_path):
        from docx import Document
        tpl = tmp_path / "tpl.docx"
        doc = Document()
        doc.add_paragraph("{{chart}}")
        doc.save(str(tpl))
        from docxtpl import DocxTemplate
        t = DocxTemplate(str(tpl))
        with pytest.raises(ExternalDependencyError):
            generator._render_image(t, "chart", str(tmp_path / "不存在.png"))

    def test_existing_image_returns_inline_image(self, tmp_path):
        from docx import Document
        tpl = tmp_path / "tpl.docx"
        doc = Document()
        doc.add_paragraph("{{chart}}")
        doc.save(str(tpl))
        png = _make_mini_png(tmp_path / "img.png")
        from docxtpl import DocxTemplate
        t = DocxTemplate(str(tpl))
        obj = generator._render_image(t, "chart", str(png))
        # InlineImage 对象应有 _width 等属性（docxtpl 内部实现）
        assert obj is not None
