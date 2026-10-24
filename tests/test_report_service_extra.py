"""报告服务补充测试：字段判定、文件名清洗、上下文构造、批量导出。"""

from __future__ import annotations

from pathlib import Path

import pytest

from formora.core.errors import FormoraError
from formora.core.models import DataSource, FieldMapping
from formora.services import report_service
from formora.services.report_service import (
    _auto_chart_enabled,
    _drop_uncovered_image_fields,
    _format_rows,
    _output_dir,
    batch_export_pdf,
    generate_batch,
    generate_single,
    image_placeholders,
    is_chart_field,
    is_image_field,
    sanitize_filename,
)


class TestFieldPredicates:
    def test_is_chart_field(self):
        assert is_chart_field("图表")
        assert is_chart_field("实验结果图")
        assert is_chart_field("曲线图")
        assert not is_chart_field("姓名")
        assert not is_chart_field("")
        assert not is_chart_field("地图")  # 排除词

    def test_is_image_field_excludes(self):
        assert is_image_field("截图")
        assert not is_image_field("地图")
        assert not is_image_field("图纸")
        assert not is_image_field("图标")


class TestSanitizeFilename:
    def test_removes_illegal_chars(self):
        assert sanitize_filename("任务:名*称?") == "任务名称"

    def test_strips_edges(self):
        assert sanitize_filename("  任务  ") == "任务"

    def test_strips_dots(self):
        assert sanitize_filename("任务..") == "任务"

    def test_empty_falls_back(self):
        assert sanitize_filename("") == "未命名"
        assert sanitize_filename("   ") == "未命名"
        assert sanitize_filename(None) == "未命名"

    def test_keeps_chinese(self):
        assert sanitize_filename("批量生成_第1行") == "批量生成_第1行"


class TestFormatRows:
    def test_none_to_empty(self):
        rows = [{"项目": "A", "数值": None}]
        assert _format_rows(rows) == [{"项目": "A", "数值": ""}]

    def test_float_integer(self):
        assert _format_rows([{"数值": 85.0}]) == [{"数值": "85"}]

    def test_datetime_to_date(self):
        import datetime

        rows = [{"日期": datetime.datetime(2026, 10, 25, 8, 0)}]
        assert _format_rows(rows) == [{"日期": "2026-10-25"}]


class TestOutputDir:
    def test_empty_config_falls_back_to_default(self, tmp_path, monkeypatch):
        from formora.services import config as config_module

        default = tmp_path / "Documents" / "FormoraReport"
        monkeypatch.setattr(config_module, "OUTPUT_DEFAULT_DIR", default)

        from formora.services.config import Config

        cfg = Config(tmp_path / "config.json")
        cfg.set("output_dir", "")

        class FakeTask:
            name = "x"

        state = type("State", (), {"config": cfg, "task": FakeTask()})()
        out = _output_dir(state)
        assert out == default
        assert out.exists()

    def test_custom_output_dir(self, tmp_path):
        from formora.services.config import Config

        cfg = Config(tmp_path / "config.json")
        custom = tmp_path / "custom"
        cfg.set("output_dir", str(custom))
        state = type("State", (), {"config": cfg})()
        assert _output_dir(state) == custom
        assert custom.exists()


class TestAutoChartEnabled:
    def test_explicit_overrides_config(self):
        state = type("State", (), {"config": {"auto_chart": False}})()
        assert _auto_chart_enabled(state, explicit=True) is True
        assert _auto_chart_enabled(state, explicit=False) is False

    def test_default_true(self):
        state = type("State", (), {"config": {}})()
        assert _auto_chart_enabled(state) is True

    def test_config_false(self):
        state = type("State", (), {"config": {"auto_chart": False}})()
        assert _auto_chart_enabled(state) is False


class TestImagePlaceholders:
    def test_includes_auto_chart_placeholders(self):
        mappings = [
            FieldMapping(
                template_field="姓名", source_type="column", source_column="姓名"
            ),
            FieldMapping(template_field="图表", source_type="image", value=""),
            FieldMapping(
                template_field="曲线图", source_type="column", source_column="数值"
            ),
        ]
        state = type("State", (), {"mappings": mappings})()
        s = image_placeholders(state, auto_chart_enabled=True)
        assert "图表" in s
        assert "曲线图" in s
        assert "姓名" not in s

    def test_without_auto_chart_only_explicit_images(self):
        mappings = [
            FieldMapping(template_field="图表", source_type="image", value=""),
            FieldMapping(
                template_field="姓名", source_type="column", source_column="姓名"
            ),
        ]
        state = type("State", (), {"mappings": mappings})()
        s = image_placeholders(state, auto_chart_enabled=False)
        assert s == {"图表"}


class TestDropUncoveredImageFields:
    def test_removes_uncovered_none(self):
        mappings = [FieldMapping(template_field="图", source_type="image", value="")]
        ctx = {"图": None, "姓名": "x"}
        _drop_uncovered_image_fields(ctx, mappings, image_vars={})
        assert "图" not in ctx
        assert "姓名" in ctx

    def test_keeps_covered(self):
        mappings = [
            FieldMapping(template_field="图", source_type="image", value="a.png")
        ]
        ctx = {"图": None}
        _drop_uncovered_image_fields(ctx, mappings, image_vars={"图": "a.png"})
        assert "图" in ctx


class TestResolveContext:
    def test_no_data_rows_for_non_tabular(self, make_config):
        cfg = make_config()
        state = type(
            "State",
            (),
            {
                "config": cfg,
                "data": DataSource(path=Path("t.txt"), kind="txt", text="文字"),
                "mappings": [
                    FieldMapping(
                        template_field="结论",
                        source_type="constant",
                        constant_value="c",
                    )
                ],
            },
        )()
        ctx = report_service.resolve_context(state)
        assert ctx["结论"] == "c"
        assert "data_rows" not in ctx


class TestGenerateErrors:
    def test_generate_single_without_template(self, make_config):
        cfg = make_config()
        state = type("State", (), {"config": cfg, "template": None})()
        with pytest.raises(FormoraError):
            generate_single(state)

    def test_generate_batch_with_text_data(self, make_config):
        cfg = make_config()
        state = type(
            "State",
            (),
            {
                "config": cfg,
                "template": object(),
                "data": DataSource(path=Path("t.txt"), kind="txt", text="文字"),
            },
        )()
        with pytest.raises(FormoraError):
            generate_batch(state)

    def test_generate_batch_without_template(self, make_config):
        cfg = make_config()
        state = type("State", (), {"config": cfg, "template": None})()
        with pytest.raises(FormoraError):
            generate_batch(state)


class TestBatchExportPdf:
    def test_all_success(self, tmp_path, monkeypatch):
        from formora.core import pdf_exporter

        monkeypatch.setattr(
            pdf_exporter,
            "export_pdf",
            lambda docx, out: Path(out).write_bytes(b"pdf") or Path(out),
        )
        docx1 = tmp_path / "a.docx"
        docx2 = tmp_path / "b.docx"
        docx1.write_bytes(b"x")
        docx2.write_bytes(b"x")
        ok, failed = batch_export_pdf([str(docx1), str(docx2)])
        assert ok == 2
        assert failed == []
        assert (tmp_path / "a.pdf").exists()

    def test_partial_failure(self, tmp_path, monkeypatch):
        from formora.core import pdf_exporter
        from formora.core.errors import ExternalDependencyError

        def fake_export(docx, out):
            if "bad" in docx:
                raise ExternalDependencyError("无转换器")
            Path(out).write_bytes(b"pdf")
            return Path(out)

        monkeypatch.setattr(pdf_exporter, "export_pdf", fake_export)
        good = tmp_path / "good.docx"
        bad = tmp_path / "bad.docx"
        good.write_bytes(b"x")
        bad.write_bytes(b"x")
        ok, failed = batch_export_pdf([str(good), str(bad)])
        assert ok == 1
        assert len(failed) == 1
        assert "bad" in failed[0]
