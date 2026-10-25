"""历史记录补充测试：数据源字符串化、时间格式、对象落盘。"""

from __future__ import annotations

import json
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


class TestGetTask:
    def test_get_task_returns_entry(self, tmp_path, monkeypatch):
        hist_path = tmp_path / "history.jsonl"
        monkeypatch.setattr(history, "HISTORY_PATH", hist_path)
        hist_path.write_text(
            json.dumps({"id": "abc", "name": "t1"}, ensure_ascii=False) + "\n"
            + json.dumps({"id": "def", "name": "t2"}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        entry = history.get_task("def")
        assert entry is not None
        assert entry["id"] == "def"
        assert entry["name"] == "t2"

    def test_get_task_missing_returns_none(self, tmp_path, monkeypatch):
        hist_path = tmp_path / "history.jsonl"
        monkeypatch.setattr(history, "HISTORY_PATH", hist_path)
        hist_path.write_text(
            json.dumps({"id": "abc", "name": "t1"}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        assert history.get_task("nope") is None

    def test_get_task_empty_id(self, tmp_path, monkeypatch):
        hist_path = tmp_path / "history.jsonl"
        monkeypatch.setattr(history, "HISTORY_PATH", hist_path)
        hist_path.write_text(
            json.dumps({"id": "abc", "name": "t1"}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        assert history.get_task("") is None

    def test_get_task_no_file(self, tmp_path, monkeypatch):
        hist_path = tmp_path / "history.jsonl"
        monkeypatch.setattr(history, "HISTORY_PATH", hist_path)
        assert history.get_task("abc") is None


class TestTrimHistory:
    def test_trim_history_rotates(self, tmp_path, monkeypatch):
        hist_path = tmp_path / "history.jsonl"
        monkeypatch.setattr(history, "HISTORY_PATH", hist_path)
        lines = [f"line-{i}" for i in range(2001)]
        hist_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        history._trim_history()
        result = hist_path.read_text(encoding="utf-8").splitlines()
        assert len(result) == history.MAX_HISTORY_ENTRIES == 2000
        assert result[0] == "line-1"
        assert result[-1] == "line-2000"

    def test_record_task_rotates_on_large_file(self, tmp_path, monkeypatch):
        hist_path = tmp_path / "history.jsonl"
        monkeypatch.setattr(history, "HISTORY_PATH", hist_path)
        # 预写 3000 行、每行约 2KB：文件超过 5MB 且行数超过上限，触发轮转
        pad = "x" * 2000
        pre_lines = [
            json.dumps({"id": f"pre-{i}", "pad": pad}, ensure_ascii=False)
            for i in range(3000)
        ]
        hist_path.write_text("\n".join(pre_lines) + "\n", encoding="utf-8")
        assert hist_path.stat().st_size > 5 * 1024 * 1024
        task = ReportTask(name="t", template_path=Path("t.docx"))
        history.record_task(task)
        result = hist_path.read_text(encoding="utf-8").splitlines()
        assert len(result) == history.MAX_HISTORY_ENTRIES
        assert json.loads(result[-1])["id"] == task.id


class TestLoadHistory:
    def test_load_history_skips_blank_lines(self, tmp_path, monkeypatch):
        hist_path = tmp_path / "history.jsonl"
        monkeypatch.setattr(history, "HISTORY_PATH", hist_path)
        hist_path.write_text(
            json.dumps({"id": "1", "name": "good"}, ensure_ascii=False) + "\n"
            + "\n"
            + "this is not json\n"
            + "\n"
            + json.dumps({"id": "2", "name": "good2"}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        entries = history.load_history()
        assert [e["id"] for e in entries] == ["2", "1"]


class TestJsonSafe:
    def test_json_safe_path(self):
        assert history._json_safe(Path("a")) == "a"
        assert history._json_safe("a") == "a"
