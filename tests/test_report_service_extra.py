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
    _versioned_output,
    auto_chart,
    batch_export_pdf,
    collect_image_vars,
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

    def test_progress_cb_reports_each_file(self, tmp_path, monkeypatch):
        from formora.core import pdf_exporter

        monkeypatch.setattr(
            pdf_exporter,
            "export_pdf",
            lambda docx, out: Path(out).write_bytes(b"pdf") or Path(out),
        )
        files = []
        for name in ("a", "b", "c"):
            p = tmp_path / f"{name}.docx"
            p.write_bytes(b"x")
            files.append(str(p))
        seen = []
        ok, failed = batch_export_pdf(
            files, progress_cb=lambda done, total: seen.append((done, total))
        )
        assert ok == 3
        assert failed == []
        assert seen == [(1, 3), (2, 3), (3, 3)]

    def test_should_cancel_stops_batch(self, tmp_path, monkeypatch):
        from formora.core import pdf_exporter
        from formora.core.errors import BatchExportCancelledError

        calls = []

        def fake_export(docx, out):
            calls.append(str(docx))
            Path(out).write_bytes(b"pdf")
            return Path(out)

        monkeypatch.setattr(pdf_exporter, "export_pdf", fake_export)
        files = []
        for name in ("a", "b", "c"):
            p = tmp_path / f"{name}.docx"
            p.write_bytes(b"x")
            files.append(str(p))
        with pytest.raises(BatchExportCancelledError):
            batch_export_pdf(files, should_cancel=lambda: len(calls) >= 1)
        assert len(calls) == 1  # 只转换了第一份就协作式取消


class TestAutoChartFailure:
    def test_auto_chart_failure_logs_and_returns_none(
        self, tmp_path, monkeypatch, caplog, make_config
    ):
        """图表生成异常时返回 None，并记录任务 warning 与 logger 警告。"""
        import logging

        from formora.core import chart
        from formora.core.models import DataSource, ReportTask

        cfg = make_config(output_dir=str(tmp_path / "out"))
        data = DataSource(
            path=Path("d.csv"),
            kind="csv",
            columns=["项目", "数值"],
            rows=[{"项目": "A", "数值": 1.0}, {"项目": "B", "数值": 2.0}],
        )
        task = ReportTask(name="图表失败", template_path=Path("t.docx"))
        state = type("State", (), {"config": cfg, "data": data, "task": task})()

        def boom(*args, **kwargs):
            raise RuntimeError("绘图引擎崩溃")

        monkeypatch.setattr(chart, "generate_line_chart", boom)
        with caplog.at_level(logging.WARNING, logger="formora"):
            img = auto_chart(state)
        assert img is None
        assert any(
            entry.level == "warning" and "自动图表生成失败" in entry.message
            for entry in task.logs
        )
        assert "自动图表生成失败" in caplog.text


class TestAutoChartNoNumericCols:
    def test_auto_chart_no_numeric_cols(self, tmp_path, monkeypatch, make_config):
        """数据列全为文本时自动图表返回 None。"""
        from formora.core.models import DataSource, ReportTask

        cfg = make_config(output_dir=str(tmp_path / "out"))
        data = DataSource(
            path=Path("d.csv"),
            kind="csv",
            columns=["项目", "备注"],
            rows=[
                {"项目": "A", "备注": "文本一"},
                {"项目": "B", "备注": "文本二"},
            ],
        )
        task = ReportTask(name="全文本", template_path=Path("t.docx"))
        state = type("State", (), {"config": cfg, "data": data, "task": task})()
        assert auto_chart(state) is None

    def test_auto_chart_none_and_percent_selects_numeric_cols(
        self, tmp_path, monkeypatch, make_config
    ):
        """含 None 与百分比字符串时，正确识别数值列并生成图表。"""
        from formora.core import chart
        from formora.core.models import DataSource, ReportTask

        cfg = make_config(output_dir=str(tmp_path / "out"))
        data = DataSource(
            path=Path("d.csv"),
            kind="csv",
            columns=["项目", "数值", "百分比"],
            rows=[
                {"项目": "A", "数值": None, "百分比": "85%"},
                {"项目": "B", "数值": "90.5", "百分比": "92%"},
            ],
        )
        task = ReportTask(name="百分比", template_path=Path("t.docx"))
        state = type("State", (), {"config": cfg, "data": data, "task": task})()
        captured: dict[str, str] = {}

        def fake_line_chart(
            x_values,
            y_values,
            output_png,
            title="",
            x_label="",
            y_label="",
            config=None,
        ):
            captured["x_label"] = x_label
            captured["y_label"] = y_label
            return Path(output_png)

        monkeypatch.setattr(chart, "generate_line_chart", fake_line_chart)
        img = auto_chart(state)
        assert img is not None
        # 百分比列被识别为数值列；None 不破坏数值检测；x 轴取首个非数值列
        assert captured["x_label"] == "项目"
        assert captured["y_label"] == "数值"


class TestAutoChartXAxisHint:
    def test_auto_chart_x_axis_hint(self, tmp_path, monkeypatch, make_config):
        """含「时间」列时，x 轴优先选择时间列。"""
        from formora.core import chart
        from formora.core.models import DataSource, ReportTask

        cfg = make_config(output_dir=str(tmp_path / "out"))
        data = DataSource(
            path=Path("d.csv"),
            kind="csv",
            columns=["时间", "温度", "压力"],
            rows=[
                {"时间": "0s", "温度": 1.0, "压力": 2.0},
                {"时间": "1s", "温度": 3.0, "压力": 4.0},
            ],
        )
        task = ReportTask(name="时间轴", template_path=Path("t.docx"))
        state = type("State", (), {"config": cfg, "data": data, "task": task})()
        captured: dict[str, str] = {}

        def fake_line_chart(
            x_values,
            y_values,
            output_png,
            title="",
            x_label="",
            y_label="",
            config=None,
        ):
            captured["x_label"] = x_label
            return Path(output_png)

        monkeypatch.setattr(chart, "generate_line_chart", fake_line_chart)
        img = auto_chart(state)
        assert img is not None
        assert captured["x_label"] == "时间"

    def test_auto_chart_x_axis_no_hint_uses_first_non_numeric(
        self, tmp_path, monkeypatch, make_config
    ):
        """无时间/日期提示时，x 轴取首个非数值列。"""
        from formora.core import chart
        from formora.core.models import DataSource, ReportTask

        cfg = make_config(output_dir=str(tmp_path / "out"))
        data = DataSource(
            path=Path("d.csv"),
            kind="csv",
            columns=["样本", "温度"],
            rows=[{"样本": "A", "温度": 1.0}, {"样本": "B", "温度": 2.0}],
        )
        task = ReportTask(name="无提示", template_path=Path("t.docx"))
        state = type("State", (), {"config": cfg, "data": data, "task": task})()
        captured: dict[str, str] = {}

        def fake_line_chart(
            x_values,
            y_values,
            output_png,
            title="",
            x_label="",
            y_label="",
            config=None,
        ):
            captured["x_label"] = x_label
            return Path(output_png)

        monkeypatch.setattr(chart, "generate_line_chart", fake_line_chart)
        img = auto_chart(state)
        assert img is not None
        assert captured["x_label"] == "样本"


class TestCollectImageVars:
    def test_collect_image_vars_with_image_value(self):
        """source_type='image' 且 value 非空时，image_vars 包含该字段。"""
        from formora.core.models import FieldMapping

        mappings = [
            FieldMapping(template_field="截图", source_type="image", value="C:/x/a.png")
        ]
        state = type("State", (), {"mappings": mappings})()
        image_vars = collect_image_vars(state, auto_chart_enabled=False)
        assert image_vars == {"截图": "C:/x/a.png"}


class TestVersionedOutputSubdir:
    def test_versioned_output_subdir(self, tmp_path, make_config):
        """传 subdir 时创建子目录，且输出路径包含子目录。"""
        from formora.core.models import ReportTask

        cfg = make_config(output_dir=str(tmp_path / "out"))
        task = ReportTask(name="子目录", template_path=Path("t.docx"))
        state = type("State", (), {"config": cfg, "task": task})()
        out = _versioned_output(state, subdir="实验")
        assert out.parent == tmp_path / "out" / "实验"
        assert out.parent.exists()
        assert "实验" in out.parts
        assert out.name.startswith("子目录_输出_")
        assert out.name.endswith(".docx")


class TestGenerateBatchRowFailure:
    def test_generate_batch_row_failure_appends_error(
        self, tmp_path, monkeypatch, make_config
    ):
        """批量第 2 行生成失败时，errors 含「第2行失败」且成功结果数正确。"""
        from formora.core import generator
        from formora.core.models import DataSource, ReportTask

        cfg = make_config(output_dir=str(tmp_path / "out"))
        data = DataSource(
            path=Path("d.csv"),
            kind="csv",
            columns=["项目", "数值"],
            rows=[
                {"项目": "A", "数值": 1.0},
                {"项目": "B", "数值": 2.0},
                {"项目": "C", "数值": 3.0},
            ],
        )
        template = type("Template", (), {"path": Path("t.docx")})()
        task = ReportTask(name="批量失败", template_path=Path("t.docx"))
        state = type(
            "State",
            (),
            {
                "config": cfg,
                "template": template,
                "data": data,
                "mappings": [],
                "task": task,
            },
        )()
        calls = {"n": 0}

        def fake_generate(
            template_path, context, output_path, image_vars=None, template_info=None
        ):
            calls["n"] += 1
            if calls["n"] == 2:
                raise FormoraError("模拟生成失败")
            Path(output_path).write_bytes(b"docx")
            return Path(output_path)

        monkeypatch.setattr(generator, "generate_report", fake_generate)
        monkeypatch.setattr(report_service, "record_task", lambda task: None)
        results, errors = generate_batch(state, auto_chart=False)
        assert len(results) == 2
        assert errors == ["第2行失败: 模拟生成失败"]
