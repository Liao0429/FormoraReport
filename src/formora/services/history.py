"""本地任务历史记录（JSONL 追加）。

记录每次生成任务：模板、数据源、映射、输出路径、状态、日志。
用户数据仅存本地，不入仓库。
"""
from __future__ import annotations

import json
import threading
from datetime import datetime

from formora.core.models import ReportTask
from formora.services.config import HISTORY_PATH

_lock = threading.Lock()


def _data_source_str(ds) -> str | None:
    """兼容 DataSource 对象或 Path/str。"""
    if ds is None:
        return None
    if hasattr(ds, "path"):
        return str(ds.path)
    return str(ds)


def record_task(task: ReportTask):
    entry = {
        "id": task.id,
        "name": task.name,
        "template_path": str(task.template_path),
        "data_source": _data_source_str(task.data_source),
        "status": task.status,
        "output_path": str(task.output_path) if task.output_path else None,
        "created_at": task.created_at,
        "logs": [
            {"level": l.level, "category": l.category, "message": l.message}
            for l in task.logs
        ],
        # AI 来源追踪：仅记录含依据或需确认的字段，便于事后核对
        "ai_sources": [
            {"field": m.template_field, "source": m.source, "needs_confirmation": m.needs_confirmation}
            for m in task.mappings
            if m.source or m.needs_confirmation
        ],
    }
    with _lock:
        HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(HISTORY_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_history(limit: int = 50) -> list[dict]:
    if not HISTORY_PATH.exists():
        return []
    with _lock:
        entries = []
        for line in HISTORY_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except Exception:
                continue
    return entries[-limit:][::-1]  # 最新在前


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")