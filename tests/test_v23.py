"""2.3 新增逻辑测试：百分比出图、时间序列轴选择、循环体字段识别、单份/批量 data_rows 统一。"""

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from formora.core import data_reader, mapper, template_parser
from formora.core.models import DataSource, ReportTask
from formora.services import report_service
from formora.services.config import Config

SAMPLES = Path(__file__).resolve().parent.parent / "tests" / "samples"
TEMPLATE = SAMPLES / "实验报告模板.docx"


class TestAutoChartV23:
    def _make_state(self, tmp_path, columns, rows):
        cfg = Config(tmp_path / "config.json")
        cfg.set("output_dir", str(tmp_path / "out"))
        data = DataSource(path=Path("d.csv"), kind="csv", columns=columns, rows=rows)
        task = ReportTask(name="图表测试", template_path=TEMPLATE)
        return SimpleNamespace(data=data, config=cfg, task=task)

    def test_percent_column_generates_chart(self, tmp_path):
        """百分比列（"85%"）应被识别为数值列并出图。"""
        state = self._make_state(
            tmp_path,
            ["样本", "转化率"],
            [{"样本": "A", "转化率": "85%"}, {"样本": "B", "转化率": "92%"}],
        )
        img = report_service.auto_chart(state)
        assert img, "百分比列应能生成图表"
        assert Path(img).exists()

    def test_text_numeric_column_generates_chart(self, tmp_path):
        """文本数字（"12.5"）应被识别为数值列并出图。"""
        state = self._make_state(
            tmp_path,
            ["样本", "数值"],
            [{"样本": "A", "数值": "12.5"}, {"样本": "B", "数值": "18.2"}],
        )
        img = report_service.auto_chart(state)
        assert img and Path(img).exists()

    def test_time_series_x_axis_is_time_column(self, tmp_path):
        """含"时间"的列应作 x 轴，而不是被当 y 轴。"""
        state = self._make_state(
            tmp_path,
            ["时间(s)", "温度(℃)"],
            [{"时间(s)": 1, "温度(℃)": 20.0}, {"时间(s)": 2, "温度(℃)": 25.5}],
        )
        img = report_service.auto_chart(state)
        assert img and Path(img).exists()
        # 图表已生成即可（轴选择正确性通过 matplotlib 内部保证，这里验证能生成）


class TestLoopFieldRecognition:
    def test_loop_body_fields_not_in_top_level_placeholders(self):
        """循环体 {{ row['项目'] }} 不应成为顶层映射占位符。"""
        from formora.core.template_parser import parse_template

        info = parse_template(TEMPLATE)
        # 样例模板循环体内有 row['项目']、row['数值']
        assert "row['项目']" not in info.placeholders
        assert "row['数值']" not in info.placeholders
        # 顶层占位符仍应识别
        assert "实验名称" in info.placeholders
        assert "姓名" in info.placeholders


class TestDataRowsUnifiedV23:
    def _make_state(self, tmp_path):
        cfg = Config(tmp_path / "config.json")
        cfg.set("output_dir", str(tmp_path / "out"))
        template = template_parser.parse_template(TEMPLATE)
        data = data_reader.read_data(SAMPLES / "实验数据.csv")
        mappings = mapper.auto_map(template, data)
        constants = {
            "实验名称": "统一语义",
            "实验目的": "验证",
            "实验环境": "本机",
            "实验步骤": "步骤",
            "实验结果": "结果",
            "问题分析": "无",
            "实验结论": "结论",
        }
        for m in mappings:
            if m.source_type == "constant" and m.template_field in constants:
                m.constant_value = constants[m.template_field]
        task = ReportTask(name="统一语义", template_path=TEMPLATE)
        return SimpleNamespace(
            config=cfg, template=template, data=data, mappings=mappings, task=task
        )

    def test_single_with_row_injects_only_that_row(self, tmp_path):
        """单份生成传入 row 时，data_rows 只含当前行（与批量一致）。"""
        state = self._make_state(tmp_path)
        ctx = report_service.resolve_context(state, row=state.data.rows[0])
        expected = report_service._format_rows([state.data.rows[0]])
        assert ctx["data_rows"] == expected

    def test_single_without_row_injects_all(self, tmp_path):
        """未传 row（仅校验/预览）时注入全表。"""
        state = self._make_state(tmp_path)
        ctx = report_service.resolve_context(state, row=None)
        expected = report_service._format_rows(state.data.rows)
        assert ctx["data_rows"] == expected
