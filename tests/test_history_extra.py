"""历史记录补充测试：数据源字符串化、时间格式、对象落盘。"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from formora.core.models import DataSource, ReportTask
from formora.services import history


class TestDataSourceStr:
    def test_none(self):
        assert history._data_source_str(None) is None

    def test_path(self):
        assert history._data_source_str(Path("a.csv")) == "a.csv"

    def test_str(self):
        assert history._data_source_str("b.csv") == "b.csv"

    def test_datasource_object(self):
        ds = DataSource(path=Path("c.csv"), kind="csv")
        assert history._data_source_str(ds) == "c.csv"


class TestNowStr:
    def test_format(self):
        s = history.now_str()
        assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$", s)

    def test_parses_as_datetime(self):
        s = history.now_str()
        dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
        assert dt.year >= 2020


class TestRecordWithDataSourceObject:
    def test_record_writes_path(self, tmp_path, monkeypatch):
        hist_path = tmp_path / "history.jsonl"
        monkeypatch.setattr(history, "HISTORY_PATH", hist_path)
        ds = DataSource(path=Path("数据.csv"), kind="csv")
        task = ReportTask(name="t", template_path=Path("t.docx"), data_source=ds)
        history.record_task(task)
        entries = history.load_history()
        assert entries[0]["data_source"] == "数据.csv"

    def test_record_with_none_source(self, tmp_path, monkeypatch):
        hist_path = tmp_path / "history.jsonl"
        monkeypatch.setattr(history, "HISTORY_PATH", hist_path)
        task = ReportTask(name="t", template_path=Path("t.docx"))
        history.record_task(task)
        entries = history.load_history()
        assert entries[0]["data_source"] is None
