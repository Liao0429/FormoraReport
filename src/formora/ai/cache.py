"""AI 请求结果缓存（成本控制）。

缓存相同 AI 调用的结果，避免重复请求消耗 token / 费用。

设计要点：
- 缓存键对模型名、temperature、json_mode、messages 等影响输出的参数敏感，
  不同模型 / 参数之间不会串缓存。
- 命中率统计（hit / miss）同时保存在内存与缓存 JSON 文件的 ``stats`` 字段，
  进程重启后仍可保留。
- 缓存文件损坏、被截断或格式异常时优雅降级：当作未命中并重建空缓存，
  绝不因缓存问题让 AI 请求失败。
- 写入使用「临时文件 + os.replace」原子替换，避免崩溃留下半截 JSON。

用法（独立于 HTTP 客户端，便于集成）：:

    from formora.ai.cache import AICache, make_cache_key

    cache = AICache()                      # 默认 ~/.formora/ai_cache.json
    key = make_cache_key(model, messages, temperature=0.2, json_mode=True)
    result = cache.get(key)                # 未命中返回 None
    if result is None:
        result = call_ai(...)              # 真实请求
        cache.set(key, result)
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from pathlib import Path
from typing import Any

__all__ = ["AICache", "make_cache_key", "default_cache_path"]

_CACHE_VERSION = 1

_DATA_SCHEMA_VERSION = "version"
_DATA_STATS = "stats"
_DATA_ENTRIES = "entries"


def default_cache_path() -> Path:
    """返回默认缓存文件路径。

    优先使用环境变量 ``FORMORA_AI_CACHE_PATH``，否则为
    ``~/.formora/ai_cache.json``。
    """
    env = os.environ.get("FORMORA_AI_CACHE_PATH")
    if env:
        return Path(env)
    return Path.home() / ".formora" / "ai_cache.json"


def make_cache_key(
    model: str,
    messages: list[dict],
    temperature: float = 0.2,
    json_mode: bool = True,
    extra: dict | None = None,
) -> str:
    """生成对模型输出参数敏感的稳定缓存键。

    覆盖所有会影响结果的参数：模型名、消息内容、温度、json_mode
    （response_format）以及调用方额外参数（如 max_tokens）。不同参数组合
    得到不同键，从根上避免“不同模型串缓存”。
    """
    payload = {
        "v": _CACHE_VERSION,
        "model": model,
        "temperature": temperature,
        "json_mode": bool(json_mode),
        "messages": messages,
        "extra": extra or {},
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class AICache:
    """线程安全、文件持久化的 AI 响应缓存。

    参数：
        path: 缓存 JSON 文件路径；None 时用 :func:`default_cache_path`。
        ttl: 条目有效期（秒）；None 表示永不过期。
        max_entries: 最多缓存条目数，超出时淘汰最旧条目；None 不限制。
    """

    def __init__(
        self,
        path: str | Path | None = None,
        ttl: float | None = None,
        max_entries: int | None = None,
    ) -> None:
        self.path = Path(path) if path is not None else default_cache_path()
        self.ttl = ttl
        self.max_entries = max_entries
        self._lock = threading.RLock()
        self._data = self._load()

    # ------------------------------------------------------------------ #
    # 内部：读写磁盘
    # ------------------------------------------------------------------ #
    def _empty_data(self) -> dict[str, Any]:
        return {
            _DATA_SCHEMA_VERSION: _CACHE_VERSION,
            _DATA_STATS: {"hits": 0, "misses": 0},
            _DATA_ENTRIES: {},
        }

    def _load(self) -> dict[str, Any]:
        """读取缓存文件；任何异常（不存在/损坏/旧格式）都返回空缓存。"""
        empty = self._empty_data()
        try:
            with open(self.path, "r", encoding="utf-8", newline="") as fh:
                raw = json.load(fh)
        except (OSError, ValueError, UnicodeDecodeError):
            # 文件不存在、权限错误、JSON 损坏/截断：一律视为未命中并重建
            return empty
        if not isinstance(raw, dict):
            return empty
        if raw.get(_DATA_SCHEMA_VERSION) != _CACHE_VERSION:
            return empty
        stats = raw.get(_DATA_STATS)
        entries = raw.get(_DATA_ENTRIES)
        if not isinstance(stats, dict) or not isinstance(entries, dict):
            return empty
        try:
            hits = int(stats.get("hits", 0))
            misses = int(stats.get("misses", 0))
        except (TypeError, ValueError):
            hits = misses = 0
        # 逐条清洗：只保留结构合法的条目，防止脏数据在 get 时引发异常
        cleaned_entries: dict[str, Any] = {}
        for key, entry in entries.items():
            if not isinstance(key, str) or not isinstance(entry, dict):
                continue
            if "result" not in entry:
                continue
            try:
                created_at = float(entry.get("created_at", 0.0))
            except (TypeError, ValueError):
                created_at = 0.0
            cleaned_entries[key] = {
                "result": entry["result"],
                "created_at": created_at,
            }
        return {
            _DATA_SCHEMA_VERSION: _CACHE_VERSION,
            _DATA_STATS: {"hits": max(hits, 0), "misses": max(misses, 0)},
            _DATA_ENTRIES: cleaned_entries,
        }

    def _save(self) -> None:
        """原子写缓存文件：先写临时文件再 os.replace。失败不影响内存数据。"""
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            return
        tmp = self.path.with_name(self.path.name + ".tmp")
        try:
            with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
                json.dump(self._data, fh, ensure_ascii=False, indent=2, sort_keys=True)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, self.path)
        except OSError:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass

    # ------------------------------------------------------------------ #
    # 对外 API
    # ------------------------------------------------------------------ #
    def get(self, key: str) -> Any:
        """按缓存键取值；未命中（或已过期）返回 None 并计入 miss。"""
        self._validate_key(key)
        with self._lock:
            entries = self._data[_DATA_ENTRIES]
            entry = entries.get(key)
            now = time.time()
            if entry is None:
                self._data[_DATA_STATS]["misses"] += 1
                return None
            created_at = entry.get("created_at", 0)
            if self.ttl is not None and now - created_at > self.ttl:
                # 过期条目当作未命中：删除并重建
                del entries[key]
                self._data[_DATA_STATS]["misses"] += 1
                return None
            self._data[_DATA_STATS]["hits"] += 1
            return entry.get("result")

    def set(self, key: str, value: Any) -> None:
        """写入缓存。value 不能是 None（与未命中语义冲突）。"""
        self._validate_key(key)
        if value is None:
            raise ValueError("不允许缓存 None 值（None 表示未命中）")
        with self._lock:
            self._data[_DATA_ENTRIES][key] = {
                "result": value,
                "created_at": time.time(),
            }
            self._prune_locked()
            self._save()

    def get_or_set(self, key: str, producer) -> Any:
        """命中直接返回；未命中调用 producer() 生成结果并缓存。"""
        cached = self.get(key)
        if cached is not None:
            return cached
        value = producer()
        self.set(key, value)
        return value

    def stats(self) -> dict[str, int]:
        """返回命中率统计（内存值，实时准确）。"""
        with self._lock:
            hits = self._data[_DATA_STATS]["hits"]
            misses = self._data[_DATA_STATS]["misses"]
            return {
                "hits": hits,
                "misses": misses,
                "total": hits + misses,
                "size": len(self._data[_DATA_ENTRIES]),
            }

    def persist_stats(self) -> None:
        """把当前统计写回缓存文件（get 命中时不会即时落盘，可显式调用）。"""
        with self._lock:
            self._save()

    def reset_stats(self) -> None:
        """清零命中/未命中计数并落盘（保留缓存条目）。"""
        with self._lock:
            self._data[_DATA_STATS] = {"hits": 0, "misses": 0}
            self._save()

    def clear(self, keep_stats: bool = False) -> None:
        """清空缓存条目。默认保留统计；keep_stats=False 时一并清零并落盘。"""
        with self._lock:
            self._data[_DATA_ENTRIES] = {}
            if not keep_stats:
                self._data[_DATA_STATS] = {"hits": 0, "misses": 0}
            self._save()

    def contains(self, key: str) -> bool:
        """判断键是否存在（不考虑 TTL）。"""
        self._validate_key(key)
        with self._lock:
            return key in self._data[_DATA_ENTRIES]

    # ------------------------------------------------------------------ #
    # 内部辅助
    # ------------------------------------------------------------------ #
    @staticmethod
    def _validate_key(key: str) -> None:
        if not isinstance(key, str) or not key:
            raise ValueError("缓存键必须是非空字符串")

    def _prune_locked(self) -> None:
        """超出 max_entries 时淘汰最旧条目（调用方需持有锁）。"""
        if self.max_entries is None:
            return
        entries = self._data[_DATA_ENTRIES]
        while len(entries) > self.max_entries:
            oldest_key = min(entries, key=lambda k: entries[k].get("created_at", 0))
            del entries[oldest_key]