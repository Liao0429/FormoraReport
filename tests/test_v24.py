"""2.4 新增逻辑测试：数值格式化、图表类型选择等。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from formora.core import mapper
from formora.core.models import FieldMapping


class TestValueFormatting:
    def test_float_integer(self):
        """85.0 应显示为 85。"""
        assert mapper._format_value(85.0) == "85"

    def test_float_decimal(self):
        assert mapper._format_value(12.34) == "12.34"

    def test_int(self):
        assert mapper._format_value(42) == "42"

    def test_scientific_small(self):
        """1e-05 应转为普通小数。"""
        val = mapper._format_value(1e-05)
        assert val == "0.00001"

    def test_percent_string(self):
        assert mapper._format_value("85%") == "85%"

    def test_none(self):
        assert mapper._format_value(None) == ""

    def test_string(self):
        assert mapper._format_value("样本A") == "样本A"

    def test_date(self):
        import datetime
        assert mapper._format_value(datetime.date(2026, 10, 25)) == "2026-10-25"
        assert mapper._format_value(datetime.datetime(2026, 10, 25, 8, 30)) == "2026-10-25"

    def test_resolve_values_formats_column(self):
        mappings = [FieldMapping(template_field="数值", source_type="column", source_column="数值")]
        ctx = mapper.resolve_values(mappings, row={"数值": 85.0})
        assert ctx["数值"] == "85"


class TestMultiLineChart:
    def test_generate_multi_line(self, tmp_path):
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
        from formora.core import chart
        out = tmp_path / "multi.png"
        chart.generate_multi_line_chart(
            ["A", "B", "C"],
            {"通道A": [1.0, 2.0, 3.0], "通道B": [2.0, 1.5, 2.5]},
            out, title="多通道", x_label="样本", y_label="数值")
        assert out.exists() and out.stat().st_size > 0

    def test_multi_line_length_mismatch(self, tmp_path):
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
        import pytest

        from formora.core import chart
        from formora.core.errors import DocumentFormatError
        with pytest.raises(DocumentFormatError):
            chart.generate_multi_line_chart(
                ["A", "B"], {"通道A": [1.0]}, tmp_path / "bad.png")


class TestTemplateDeepCompat:
    def test_dollar_and_bracket_placeholders_detected(self):
        """${字段} 与 【字段】 应被检测为占位符。"""
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
        from formora.core.template_parser import _find_placeholders
        found = _find_placeholders("${姓名} 和 【学号】 和 {{班级}}")
        assert "姓名" in found
        assert "学号" in found
        assert "班级" in found


class TestDataRowsFormatted:
    def test_data_rows_none_becomes_empty(self, tmp_path):
        """表格循环中 None 不应渲染为字面量 "None"。"""
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
        from types import SimpleNamespace

        from formora.core import template_parser
        from formora.core.models import ReportTask
        from formora.services import report_service
        from formora.services.config import Config

        cfg = Config(tmp_path / "config.json")
        cfg.set("output_dir", str(tmp_path / "out"))
        template = template_parser.parse_template(Path(__file__).resolve().parent.parent / "tests" / "samples" / "实验报告模板.docx")
        # 构造含 None 的数据
        from formora.core.models import DataSource
        data = DataSource(path=Path("d.csv"), kind="csv", columns=["项目", "数值"],
                          rows=[{"项目": "A", "数值": None}, {"项目": "B", "数值": 2.0}])
        task = ReportTask(name="格式化", template_path=Path("t.docx"))
        state = SimpleNamespace(config=cfg, template=template, data=data, mappings=[], task=task)
        ctx = report_service.resolve_context(state, row=data.rows[0])
        assert ctx["data_rows"][0]["数值"] == ""  # None -> 空串
        assert ctx["data_rows"][0]["项目"] == "A"

    def test_data_rows_formats_float(self):
        """表格循环中 85.0 应显示为 85。"""
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
        import tempfile
        from types import SimpleNamespace

        from formora.core import template_parser
        from formora.core.models import DataSource, ReportTask
        from formora.services import report_service
        from formora.services.config import Config

        with tempfile.TemporaryDirectory() as td:
            cfg = Config(Path(td) / "config.json")
            cfg.set("output_dir", str(Path(td) / "out"))
            template = template_parser.parse_template(Path(__file__).resolve().parent.parent / "tests" / "samples" / "实验报告模板.docx")
            data = DataSource(path=Path("d.csv"), kind="csv", columns=["项目", "数值"],
                              rows=[{"项目": "A", "数值": 85.0}])
            task = ReportTask(name="格式化", template_path=Path("t.docx"))
            state = SimpleNamespace(config=cfg, template=template, data=data, mappings=[], task=task)
            ctx = report_service.resolve_context(state, row=data.rows[0])
            assert ctx["data_rows"][0]["数值"] == "85"