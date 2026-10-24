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
                ["A", "B"], {"s1": [1.0]}, tmp_path / "x.png")
