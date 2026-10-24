"""数据读取补充测试：编码回退、格式拒绝、全空行、列名清洗。"""

from __future__ import annotations

import pytest

from formora.core import data_reader
from formora.core.errors import DocumentFormatError


class TestEncodingFallback:
    def test_gbk_csv(self, tmp_path):
        """GBK 编码的 CSV 应能正确读取（utf-8 失败后回退 gbk）。"""
        p = tmp_path / "gbk.csv"
        p.write_bytes("项目,数值\n样本A,12.5\n".encode("gbk"))
        ds = data_reader.read_data(p)
        assert ds.kind == "csv"
        assert "样本A" in [r["项目"] for r in ds.rows]

    def test_utf8_bom_csv(self, tmp_path):
        p = tmp_path / "bom.csv"
        p.write_bytes("项目,数值\n样本A,1\n".encode("utf-8-sig"))
        ds = data_reader.read_data(p)
        assert ds.columns == ["项目", "数值"]

    def test_latin1_fallback(self, tmp_path):
        """既非 UTF-8 也非 GBK 的字节，最终应能用 latin-1 读出而不抛异常。"""
        p = tmp_path / "latin.txt"
        p.write_bytes(bytes([0xE9, 0xE8]) + b" text")  # é è 不是合法 utf-8/gbk 组合
        ds = data_reader.read_data(p)
        assert ds.kind == "txt"
        assert ds.text  # 非空即可


class TestFormatRejection:
    def test_xls_rejected(self, tmp_path):
        p = tmp_path / "old.xls"
        p.write_bytes(b"fake")
        with pytest.raises(DocumentFormatError):
            data_reader.read_data(p)

    def test_unknown_extension_rejected(self, tmp_path):
        p = tmp_path / "data.dat"
        p.write_bytes(b"x")
        with pytest.raises(DocumentFormatError):
            data_reader.read_data(p)

    def test_no_suffix_rejected(self, tmp_path):
        p = tmp_path / "README"
        p.write_bytes(b"x")
        with pytest.raises(DocumentFormatError):
            data_reader.read_data(p)

    def test_markdown_extension_mapped(self, tmp_path):
        p = tmp_path / "note.markdown"
        p.write_text("# 标题", encoding="utf-8")
        ds = data_reader.read_data(p)
        assert ds.kind == "md"


class TestTabularCleaning:
    def test_all_empty_rows_dropped(self, tmp_path):
        import pandas as pd

        p = tmp_path / "empty.xlsx"
        df = pd.DataFrame({"A": [1, None, 2], "B": ["x", None, "y"]})
        df.to_excel(p, index=False)
        ds = data_reader.read_data(p)
        assert len(ds.rows) == 2  # 全空行被 dropna(how="all") 去掉

    def test_columns_stripped(self, tmp_path):
        p = tmp_path / "strip.csv"
        p.write_text(" 项目 ,数值\nA,1\n", encoding="utf-8-sig")
        ds = data_reader.read_data(p)
        assert ds.columns == ["项目", "数值"]
