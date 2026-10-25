"""本地任务历史记录（JSONL 追加）。

记录每次生成任务：模板、数据源、映射、输出路径、状态、日志。
用户数据仅存本地，不入仓库。
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime
from pathlib import Path

from formora.core.models import ReportTask

logger = logging.getLogger("formora.history")
from formora.services.config import HISTORY_PATH

_lock = threading.Lock()
# 历史文件保留的最大条数：超过则轮转，避免无限膨胀（与日志轮转策略对齐）
MAX_HISTORY_ENTRIES = 2000


def _trim_history() -> None:
    """历史超长时只保留最近 MAX_HISTORY_ENTRIES 条，重写文件。"""
    try:
        lines = HISTORY_PATH.read_text(encoding="utf-8").splitlines()
        if len(lines) > MAX_HISTORY_ENTRIES:
            trimmed = lines[-MAX_HISTORY_ENTRIES:]
            HISTORY_PATH.write_text("\n".join(trimmed) + "\n", encoding="utf-8")
            logger.info("历史记录已轮转：保留最近 %d 条", MAX_HISTORY_ENTRIES)
    except OSError:
        pass


def _data_source_str(ds) -> str | None:
    """兼容 DataSource 对象或 Path/str。"""
    if ds is None:
        return None
    if hasattr(ds, "path"):
        return str(ds.path)
    return str(ds)


def _json_safe(value):
    """把 Path 等非 JSON 原生类型转成可序列化值，避免落盘失败。"""
    if isinstance(value, Path):
        return str(value)
    return value


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
        # 完整映射：供「最近任务」点击恢复时还原映射，继续编辑/生成
        "mappings": [
            {
                "template_field": m.template_field,
                "source_type": m.source_type,
                "source_column": m.source_column,
                "constant_value": m.constant_value,
                "value": _json_safe(m.value),
                "required": m.required,
                "source": m.source,
                "needs_confirmation": m.needs_confirmation,
            }
            for m in task.mappings
        ],
        # AI 来源追踪：仅记录含依据或需确认的字段，便于事后核对
        "ai_sources": [
            {
                "field": m.template_field,
                "source": m.source,
                "needs_confirmation": m.needs_confirmation,
            }
            for m in task.mappings
            if m.source or m.needs_confirmation
        ],
    }
    with _lock:
        HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(HISTORY_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        # 文件过大时轮转（约 5MB 以上），避免长期使用无限膨胀
        try:
            if HISTORY_PATH.stat().st_size > 5 * 1024 * 1024:
                _trim_history()
        except OSError:
            pass


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
                logger.warning("历史记录第 %d 行无法解析，已跳过", len(entries) + 1)
                continue
    return entries[-limit:][::-1]  # 最新在前


def get_task(task_id: str) -> dict | None:
    """按 id 读取单条历史记录（供界面恢复任务使用）；不存在返回 None。"""
    if not task_id:
        return None
    if not HISTORY_PATH.exists():
        return None
    with _lock:
        for line in HISTORY_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except Exception:
                continue
            if entry.get("id") == task_id:
                return entry
    return None


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
