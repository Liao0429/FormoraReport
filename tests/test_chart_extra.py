"""图表生成补充测试：空数据、多系列、长度不一致。"""

from __future__ import annotations

import pytest

from formora.core import chart
from formora.core.errors import DocumentFormatError


class TestLineChartExtra:
    def test_empty_y_raises(self, tmp_path):
        with pytest.raises(DocumentFormatError):
            chart.generate_line_chart(["A"], [], tmp_path / "x.png")

    def test_length_mismatch_raises(self, tmp_path):
        with pytest.raises(DocumentFormatError):
            chart.generate_line_chart(["A", "B"], [1.0], tmp_path / "x.png")


class TestBarChartExtra:
    def test_empty_raises(self, tmp_path):
        with pytest.raises(DocumentFormatError):
            chart.generate_bar_chart([], [], tmp_path / "x.png")

    def test_mismatch_raises(self, tmp_path):
        with pytest.raises(DocumentFormatError):
            chart.generate_bar_chart(["A"], [1.0, 2.0], tmp_path / "x.png")


class TestMultiLineExtra:
    def test_empty_series_raises(self, tmp_path):
        with pytest.raises(DocumentFormatError):
            chart.generate_multi_line_chart(["A"], {}, tmp_path / "x.png")

    def test_empty_x_raises(self, tmp_path):
        with pytest.raises(DocumentFormatError):
            chart.generate_multi_line_chart([], {"s": []}, tmp_path / "x.png")

    def test_series_length_mismatch_raises(self, tmp_path):
        with pytest.raises(DocumentFormatError):
            chart.generate_multi_line_chart(
                ["A", "B"], {"s1": [1.0]}, tmp_path / "x.png"
            )

class TestChartStyleConfig:
    """图表样式可配置化：无配置保持现行为，配置后样式生效。"""

    def test_resolve_style_defaults_without_config(self):
        style = chart._resolve_style({})
        assert style["figsize"] == (6.4, 4.0)
        assert style["dpi"] == 150
        assert style["grid"] is True
        assert style["font_size"] == 10
        assert style["colors"] == [
            "#4a90d9",
            "#e67e22",
            "#27ae60",
            "#e74c3c",
            "#8e44ad",
            "#16a085",
        ]

    def test_resolve_style_applies_config(self):
        style = chart._resolve_style(
            {
                "colors": ["#1f77b4", "#ff7f0e"],
                "figsize": [6, 4],
                "dpi": 200,
                "grid": False,
                "font_size": 12,
            }
        )
        assert style["colors"] == ["#1f77b4", "#ff7f0e"]
        assert style["figsize"] == (6.0, 4.0)
        assert style["dpi"] == 200
        assert style["grid"] is False
        assert style["font_size"] == 12

    def test_line_chart_figsize_dpi_applied(self, tmp_path):
        import matplotlib.pyplot as plt

        img = chart.generate_line_chart(
            [1, 2, 3],
            [3.0, 1.0, 2.0],
            tmp_path / "line.png",
            config={"chart": {"figsize": [8, 5], "dpi": 100, "grid": False}},
        )
        data = plt.imread(str(img))
        # 8(in) * 100(dpi) = 800 x 500 像素
        assert data.shape[:2] == (500, 800)

    def test_bar_chart_color_applied(self, tmp_path):
        import matplotlib.pyplot as plt

        img = chart.generate_bar_chart(
            ["A", "B"],
            [1.0, 2.0],
            tmp_path / "bar.png",
            config={"chart": {"colors": ["#e74c3c"]}},
        )
        data = plt.imread(str(img))
        # 柱体应包含配置的红色像素
        red = (
            (data[:, :, 0] > 0.8)
            & (data[:, :, 1] < 0.4)
            & (data[:, :, 2] < 0.4)
        )
        assert red.any()

    def test_multi_line_chart_colors_applied(self, tmp_path):
        import matplotlib.pyplot as plt

        img = chart.generate_multi_line_chart(
            [1, 2, 3],
            {"s1": [1.0, 2.0, 3.0], "s2": [3.0, 2.0, 1.0]},
            tmp_path / "multi.png",
            config={"chart": {"colors": ["#1f77b4", "#ff7f0e"]}},
        )
        data = plt.imread(str(img))
        blue = (
            (data[:, :, 2] > 0.6)
            & (data[:, :, 0] < 0.4)
            & (data[:, :, 1] < 0.6)
        )
        orange = (
            (data[:, :, 0] > 0.9)
            & (data[:, :, 1] > 0.4)
            & (data[:, :, 1] < 0.7)
            & (data[:, :, 2] < 0.2)
        )
        assert blue.any() and orange.any()

    def test_global_config_injection(self, tmp_path):
        import matplotlib.pyplot as plt

        chart.set_chart_config({"chart": {"figsize": [6, 4], "dpi": 100, "grid": False}})
        try:
            img = chart.generate_line_chart(
                [1, 2, 3], [1.0, 2.0, 3.0], tmp_path / "global.png"
            )
            data = plt.imread(str(img))
            assert data.shape[:2] == (400, 600)
        finally:
            chart.set_chart_config(None)
