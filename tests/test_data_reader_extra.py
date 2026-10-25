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


class TestImportCompatibility:
    """数据导入兼容性回归（20 个 Agent 评审高危项）。"""

    def test_semicolon_separated_csv(self, tmp_path):
        """分号分隔的 CSV 应被自动嗅探，而非读成单列。"""
        p = tmp_path / "semi.csv"
        p.write_text("项目;数值\nA;1\nB;2\n", encoding="utf-8")
        ds = data_reader.read_data(p)
        assert ds.columns == ["项目", "数值"]
        assert len(ds.rows) == 2
        assert ds.rows[0]["项目"] == "A"
        assert ds.rows[0]["数值"] == 1

    def test_tab_separated_csv(self, tmp_path):
        """制表符分隔的 CSV 应被自动嗅探。"""
        p = tmp_path / "tab.tsv"
        p.write_text("项目\t数值\nA\t1\n", encoding="utf-8")
        ds = data_reader.read_data(p)
        assert ds.columns == ["项目", "数值"]
        assert len(ds.rows) == 1

    def test_duplicate_column_names_not_overwritten(self, tmp_path):
        """strip 后重复的列名应加序号，不静默覆盖丢数据。"""
        p = tmp_path / "dup.csv"
        p.write_text("项目, 项目 \nA,B\n", encoding="utf-8")
        ds = data_reader.read_data(p)
        # strip 后都是 "项目"，应产生 "项目" 和 "项目_2"
        assert "项目" in ds.columns
        assert "项目_2" in ds.columns
        # 两列数据都保留
        row = ds.rows[0]
        assert row["项目"] == "A"
        assert row["项目_2"] == "B"

    def test_timestamp_serializable(self, tmp_path):
        """Excel 日期列应转为 ISO 字符串（可 JSON 序列化）。"""
        import json
        import pandas as pd
        p = tmp_path / "dates.xlsx"
        df = pd.DataFrame({"时间": pd.to_datetime(["2026-01-01", "2026-01-02"])})
        df.to_excel(p, index=False)
        ds = data_reader.read_data(p)
        # 应可 JSON 序列化，且值为 ISO 字符串
        json.dumps(ds.rows)
        assert isinstance(ds.rows[0]["时间"], str)
        assert ds.rows[0]["时间"].startswith("2026")

    def test_empty_csv_friendly_error(self, tmp_path):
        """空 CSV 应报"文件内容为空"而非"文件损坏"。"""
        p = tmp_path / "empty.csv"
        p.write_text("", encoding="utf-8")
        with pytest.raises(DocumentFormatError) as ei:
            data_reader.read_data(p)
        assert "空" in str(ei.value) or "没有可读取" in str(ei.value)

class TestLargeCsvStreaming:
    """超大 CSV 流式读取：>20MB 预览模式、流式行数、单行读取。"""

    def _make_large_csv(self, tmp_path, target_bytes=21 * 1024 * 1024):
        """生成超过 20MB 的临时 CSV（重复行拼出），返回 (路径, 总行数)。"""
        p = tmp_path / "large.csv"
        header = "样本,数值,类别,备注\n"
        row = "样本X,12.5,类别A," + "长文本" * 40 + "\n"
        p.write_bytes(header.encode("utf-8"))
        total = 0
        with p.open("ab") as f:
            while f.tell() < target_bytes:
                f.write(row.encode("utf-8"))
                total += 1
        return p, total

    def test_large_csv_truncated_preview(self, tmp_path):
        p, total_rows = self._make_large_csv(tmp_path)
        ds = data_reader.read_data(p)
        assert ds.truncated is True
        assert ds.row_count == total_rows
        assert len(ds.rows) == 200  # 只载入前 200 行预览
        assert ds.columns == ["样本", "数值", "类别", "备注"]
        assert ds.encoding
        assert ds.sep == ","
        assert "预览" in ds.summary
        assert ds.rows[0]["样本"] == "样本X"
        assert ds.rows[0]["数值"] == "12.5"

    def test_iter_csv_rows_streams_all_rows(self, tmp_path):
        p, total_rows = self._make_large_csv(tmp_path)
        ds = data_reader.read_data(p)
        rows = list(
            data_reader.iter_csv_rows(p, encoding=ds.encoding, sep=ds.sep)
        )
        assert len(rows) == total_rows
        assert rows[0] == ds.rows[0]
        assert rows[-1]["样本"] == "样本X"

    def test_load_row(self, tmp_path):
        p, total_rows = self._make_large_csv(tmp_path)
        ds = data_reader.read_data(p)
        row0 = data_reader.load_row(
            p, encoding=ds.encoding, sep=ds.sep, row_index=0
        )
        assert row0 == ds.rows[0]
        mid = data_reader.load_row(
            p, encoding=ds.encoding, sep=ds.sep, row_index=total_rows // 2
        )
        assert mid["样本"] == "样本X"
        assert mid["数值"] == "12.5"

    def test_load_row_out_of_range(self, tmp_path):
        p, total_rows = self._make_large_csv(tmp_path)
        ds = data_reader.read_data(p)
        with pytest.raises(IndexError):
            data_reader.load_row(
                p, encoding=ds.encoding, sep=ds.sep, row_index=total_rows + 10
            )

    def test_small_csv_not_truncated(self, tmp_path):
        """小文件保持原全量读取行为，新增字段有默认值且不回退。"""
        p = tmp_path / "small.csv"
        p.write_text("项目,数值\nA,1\nB,2\n", encoding="utf-8")
        ds = data_reader.read_data(p)
        assert ds.truncated is False
        assert ds.row_count == len(ds.rows) == 2
        assert ds.encoding
        assert ds.sep == ","
