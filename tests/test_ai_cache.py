"""AICache 单元测试：缓存键敏感性、命中率统计、损坏降级、持久化。

不发起真实网络请求；全部使用临时目录隔离缓存文件。
"""

import json
import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import formora.ai.cache as cache_mod
from formora.ai.cache import AICache, default_cache_path, make_cache_key


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class _FakeTime:
    """可手动拨动的假时钟，用于 TTL / 淘汰顺序的确定性测试。"""

    def __init__(self, now: float = 1_000_000.0):
        self.now = now

    def time(self) -> float:
        return self.now


# --------------------------------------------------------------------------- #
# make_cache_key：缓存键必须包含所有影响结果的参数
# --------------------------------------------------------------------------- #
class TestMakeCacheKey:
    def test_deterministic(self):
        msgs = [{"role": "user", "content": "你好"}]
        assert make_cache_key("m", msgs, 0.2, True) == make_cache_key(
            "m", msgs, 0.2, True
        )

    def test_model_affects_key(self):
        msgs = [{"role": "user", "content": "x"}]
        assert make_cache_key("model-a", msgs) != make_cache_key("model-b", msgs)

    def test_temperature_affects_key(self):
        msgs = [{"role": "user", "content": "x"}]
        assert make_cache_key("m", msgs, 0.2) != make_cache_key("m", msgs, 0.8)

    def test_messages_affect_key(self):
        a = [{"role": "user", "content": "a"}]
        b = [{"role": "user", "content": "b"}]
        assert make_cache_key("m", a) != make_cache_key("m", b)

    def test_json_mode_affects_key(self):
        msgs = [{"role": "user", "content": "x"}]
        assert make_cache_key("m", msgs, json_mode=True) != make_cache_key(
            "m", msgs, json_mode=False
        )

    def test_extra_affects_key(self):
        msgs = [{"role": "user", "content": "x"}]
        assert make_cache_key("m", msgs, extra={"max_tokens": 10}) != make_cache_key(
            "m", msgs, extra={"max_tokens": 20}
        )


# --------------------------------------------------------------------------- #
# 基本读写
# --------------------------------------------------------------------------- #
class TestBasic:
    def test_miss_returns_none(self, tmp_path):
        cache = AICache(tmp_path / "cache.json")
        assert cache.get("nope") is None

    def test_set_then_get(self, tmp_path):
        cache = AICache(tmp_path / "cache.json")
        key = make_cache_key("m", [{"role": "user", "content": "hi"}])
        result = {"fields": [{"field": "f", "value": "v"}]}
        assert cache.get(key) is None
        cache.set(key, result)
        assert cache.get(key) == result

    def test_set_none_rejected(self, tmp_path):
        cache = AICache(tmp_path / "cache.json")
        with pytest.raises(ValueError):
            cache.set("k", None)

    def test_get_or_set_calls_producer_once(self, tmp_path):
        cache = AICache(tmp_path / "cache.json")
        calls: list[int] = []

        def producer():
            calls.append(1)
            return {"v": len(calls)}

        assert cache.get_or_set("k", producer) == {"v": 1}
        assert cache.get_or_set("k", producer) == {"v": 1}
        assert len(calls) == 1

    def test_clear_removes_entries(self, tmp_path):
        cache = AICache(tmp_path / "cache.json")
        cache.set("k", {"v": 1})
        cache.clear()
        assert cache.get("k") is None
        assert cache.stats()["size"] == 0

    def test_no_tmp_file_left_after_write(self, tmp_path):
        p = tmp_path / "cache.json"
        cache = AICache(p)
        cache.set("k", 1)
        assert p.exists()
        assert not p.with_name(p.name + ".tmp").exists()


# --------------------------------------------------------------------------- #
# 命中率统计（内存 + 持久化）
# --------------------------------------------------------------------------- #
class TestStats:
    def test_hit_miss_counts(self, tmp_path):
        cache = AICache(tmp_path / "cache.json")
        assert cache.stats() == {"hits": 0, "misses": 0, "total": 0, "size": 0}
        cache.get("a")  # miss
        cache.get("b")  # miss
        cache.set("a", {"x": 1})
        cache.get("a")  # hit
        s = cache.stats()
        assert s == {"hits": 1, "misses": 2, "total": 3, "size": 1}

    def test_stats_and_entries_persist_across_reload(self, tmp_path):
        p = tmp_path / "cache.json"
        cache = AICache(p)
        cache.get("miss1")
        cache.set("hit1", {"x": 1})
        cache.get("hit1")  # hit
        cache.persist_stats()

        cache2 = AICache(p)
        assert cache2.stats()["hits"] == 1
        assert cache2.stats()["misses"] == 1
        assert cache2.get("hit1") == {"x": 1}  # 条目也持久化了
        assert cache2.stats()["hits"] == 2

    def test_reset_stats_keeps_entries(self, tmp_path):
        cache = AICache(tmp_path / "cache.json")
        cache.get("x")
        cache.set("x", 1)
        cache.get("x")
        cache.reset_stats()
        s = cache.stats()
        assert s["hits"] == 0
        assert s["misses"] == 0
        assert cache.get("x") == 1  # 条目仍在


# --------------------------------------------------------------------------- #
# 损坏降级：读失败一律当作未命中并重建
# --------------------------------------------------------------------------- #
class TestCorruption:
    def test_garbage_file_treated_as_miss(self, tmp_path):
        p = tmp_path / "cache.json"
        _write(p, "{{{ not json !!!")
        cache = AICache(p)
        assert cache.get("any") is None
        assert cache.stats()["misses"] == 1

    def test_truncated_json_treated_as_miss(self, tmp_path):
        p = tmp_path / "cache.json"
        _write(p, '{"version": 1, "entries": {"k": {"result": {"a": 1}, "c')
        cache = AICache(p)
        assert cache.get("k") is None

    def test_empty_file_treated_as_miss(self, tmp_path):
        p = tmp_path / "cache.json"
        _write(p, "")
        cache = AICache(p)
        assert cache.get("k") is None

    def test_rebuilds_valid_file_after_corruption(self, tmp_path):
        p = tmp_path / "cache.json"
        _write(p, "not json")
        cache = AICache(p)
        cache.set("k", {"ok": True})
        assert cache.get("k") == {"ok": True}
        data = json.loads(p.read_text(encoding="utf-8"))
        assert data["version"] == 1
        assert data["entries"]["k"]["result"] == {"ok": True}

    def test_wrong_version_rebuilt(self, tmp_path):
        p = tmp_path / "cache.json"
        _write(p, json.dumps({"version": 999, "entries": {}}))
        cache = AICache(p)
        assert cache.get("x") is None

    def test_bad_shape_entries_ignored(self, tmp_path):
        p = tmp_path / "cache.json"
        _write(
            p,
            json.dumps(
                {
                    "version": 1,
                    "stats": {"hits": 5, "misses": 2},
                    "entries": {
                        "good": {"result": {"ok": 1}, "created_at": 1.0},
                        "bad": "not-a-dict",
                        "no-result": {"created_at": 1.0},
                    },
                }
            ),
        )
        cache = AICache(p)
        assert cache.get("good") == {"ok": 1}  # 合法条目可用
        assert cache.get("bad") is None       # 脏条目被清洗，按未命中计
        assert cache.get("no-result") is None
        assert cache.stats()["hits"] == 6      # 载入 5 + 本次命中 1
        assert cache.stats()["misses"] == 4    # 载入 2 + 本次 miss 2


# --------------------------------------------------------------------------- #
# TTL 与容量限制
# --------------------------------------------------------------------------- #
class TestTTLAndLimits:
    def test_ttl_expiry_counts_as_miss(self, tmp_path, monkeypatch):
        ft = _FakeTime()
        monkeypatch.setattr(cache_mod, "time", ft)
        cache = AICache(tmp_path / "cache.json", ttl=10)
        cache.set("k", {"v": 1})
        assert cache.get("k") == {"v": 1}
        ft.now += 11
        assert cache.get("k") is None
        assert cache.stats() == {"hits": 1, "misses": 1, "total": 2, "size": 0}

    def test_max_entries_evicts_oldest(self, tmp_path, monkeypatch):
        ft = _FakeTime()
        monkeypatch.setattr(cache_mod, "time", ft)
        cache = AICache(tmp_path / "cache.json", max_entries=2)
        ft.now = 100.0
        cache.set("a", 1)
        ft.now = 200.0
        cache.set("b", 2)
        ft.now = 300.0
        cache.set("c", 3)
        assert cache.get("a") is None  # 最旧被淘汰
        assert cache.get("b") == 2
        assert cache.get("c") == 3


# --------------------------------------------------------------------------- #
# 路径
# --------------------------------------------------------------------------- #
class TestPath:
    def test_default_cache_path_env(self, monkeypatch, tmp_path):
        p = tmp_path / "env_cache.json"
        monkeypatch.setenv("FORMORA_AI_CACHE_PATH", str(p))
        assert default_cache_path() == p

    def test_explicit_path_used(self, tmp_path):
        p = tmp_path / "sub" / "cache.json"
        cache = AICache(p)
        assert cache.path == p
        cache.set("k", 1)
        assert p.exists()

    def test_constructor_uses_env_default(self, monkeypatch, tmp_path):
        p = tmp_path / "env_cache.json"
        monkeypatch.setenv("FORMORA_AI_CACHE_PATH", str(p))
        cache = AICache()
        assert cache.path == p


# --------------------------------------------------------------------------- #
# contains / 键校验
# --------------------------------------------------------------------------- #
class TestContainsAndKeyValidation:
    def test_contains(self, tmp_path):
        cache = AICache(tmp_path / "cache.json")
        assert cache.contains("k") is False
        cache.set("k", {"v": 1})
        assert cache.contains("k") is True
        assert cache.contains("other") is False

    def test_validate_key_raises(self, tmp_path):
        cache = AICache(tmp_path / "cache.json")
        with pytest.raises(ValueError):
            cache.get("")
        with pytest.raises(ValueError):
            cache.get(None)
        with pytest.raises(ValueError):
            cache.set(123, {"v": 1})
        with pytest.raises(ValueError):
            cache.contains("")
        with pytest.raises(ValueError):
            cache.get_or_set("", lambda: 1)


# --------------------------------------------------------------------------- #
# clear(keep_stats)：是否保留命中率统计
# --------------------------------------------------------------------------- #
class TestClearKeepStats:
    def test_clear_keep_stats_false_resets_counts(self, tmp_path):
        cache = AICache(tmp_path / "cache.json")
        cache.get("m")          # miss
        cache.set("k", 1)
        cache.get("k")          # hit
        assert cache.stats()["hits"] == 1
        assert cache.stats()["misses"] == 1
        assert cache.stats()["size"] == 1
        cache.clear(keep_stats=False)
        s = cache.stats()
        assert s["hits"] == 0
        assert s["misses"] == 0
        assert s["size"] == 0

    def test_clear_keep_stats_true_preserves_counts(self, tmp_path):
        cache = AICache(tmp_path / "cache.json")
        cache.get("m")
        cache.set("k", 1)
        cache.get("k")
        cache.clear(keep_stats=True)
        s = cache.stats()
        assert s["hits"] == 1
        assert s["misses"] == 1
        assert s["size"] == 0


# --------------------------------------------------------------------------- #
# 加载边界：非 dict 根 / 缺 stats、entries / 统计值类型错误
# --------------------------------------------------------------------------- #
class TestLoadEdgeCases:
    def test_load_non_dict_root(self, tmp_path):
        p = tmp_path / "cache.json"
        _write(p, json.dumps(["not", "a", "dict"]))
        cache = AICache(p)
        assert cache.stats() == {"hits": 0, "misses": 0, "total": 0, "size": 0}
        assert cache.get("k") is None

    def test_load_missing_stats_entries(self, tmp_path):
        p = tmp_path / "cache.json"
        _write(p, json.dumps({"version": 1}))
        cache = AICache(p)
        assert cache.stats() == {"hits": 0, "misses": 0, "total": 0, "size": 0}
        assert cache.get("k") is None

    def test_stats_bad_type(self, tmp_path):
        p = tmp_path / "cache.json"
        _write(
            p,
            json.dumps(
                {
                    "version": 1,
                    "stats": {"hits": "x", "misses": "y"},
                    "entries": {"k": {"result": 1, "created_at": 1.0}},
                }
            ),
        )
        cache = AICache(p)
        assert cache.stats()["hits"] == 0
        assert cache.stats()["misses"] == 0
        assert cache.get("k") == 1  # 条目本身仍可用


# --------------------------------------------------------------------------- #
# 保存失败降级：磁盘错误不影响内存缓存
# --------------------------------------------------------------------------- #
class TestSaveFailure:
    def test_save_mkdir_failure(self, tmp_path, monkeypatch):
        cache = AICache(tmp_path / "cache.json")

        def boom(*args, **kwargs):
            raise OSError("disk full")

        monkeypatch.setattr(Path, "mkdir", boom)
        cache.set("k", {"v": 1})  # 不应抛异常
        assert cache.get("k") == {"v": 1}  # 内存仍可读