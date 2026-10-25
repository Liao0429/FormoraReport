#!/usr/bin/env python3
"""性能基准测试（无 UI，真实样例）。

测量：
- 模板解析耗时
- 数据读取耗时
- 单文档生成耗时（解析→映射→生成）
- 批量生成 N 份耗时
- 进程内存（psutil 优先，Windows 回退 ctypes，POSIX 回退 resource）
输出：reports/PERF_REPORT.md 数据源。
"""

from __future__ import annotations

import gc
import os
import platform
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from formora.core import chart, data_reader, generator, mapper, template_parser

SAMPLES: Path = Path(__file__).resolve().parent.parent / "tests" / "samples"
OUT: Path = Path(__file__).resolve().parent.parent / "tests" / "output"
TEMPLATE: Path = SAMPLES / "实验报告模板.docx"
DATA: Path = SAMPLES / "实验数据.csv"

try:
    import psutil

    _HAS_PSUTIL: bool = True
except Exception:  # pragma: no cover
    _HAS_PSUTIL = False


T = TypeVar("T")


def timed(fn: Callable[..., T], *args: Any) -> tuple[T, float]:
    """执行 fn(*args)，返回 (结果, 耗时毫秒)。

    计时前先 gc.collect()，减少 GC 噪音对耗时的干扰。
    """
    gc.collect()
    t0 = time.perf_counter()
    result = fn(*args)
    dt = (time.perf_counter() - t0) * 1000
    return result, dt


def current_memory_mb() -> str:
    """返回当前进程内存（MB）的显示文本。

    获取方式按平台选择：psutil 优先；Windows 回退 ctypes/psapi；
    POSIX 回退 resource（ru_maxrss，Linux 单位为 KB、macOS 为字节）；
    其余平台返回提示文本，保证脚本可移植。
    """
    if _HAS_PSUTIL:
        rss = psutil.Process().memory_info().rss
        return f"{rss / 1024 / 1024:.1f} MB"

    if sys.platform == "win32":
        import ctypes
        import ctypes.wintypes as wt

        class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("cb", wt.DWORD),
                ("PageFaultCount", wt.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", wt.DWORD),
                ("QuotaPagedPoolUsage", wt.DWORD),
                ("QuotaPeakNonPagedPoolUsage", wt.DWORD),
                ("QuotaNonPagedPoolUsage", wt.DWORD),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        counters = PROCESS_MEMORY_COUNTERS()
        ok = ctypes.windll.psapi.GetProcessMemoryInfo(
            ctypes.windll.kernel32.GetCurrentProcess(),
            ctypes.byref(counters),
            ctypes.sizeof(counters),
        )
        if ok:
            return f"{counters.WorkingSetSize / 1024 / 1024:.1f} MB"
        return "（获取失败）"

    if os.name == "posix":
        import resource

        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if sys.platform == "darwin":
            return f"{rss / 1024 / 1024:.1f} MB"
        return f"{rss / 1024:.1f} MB"

    return "（当前平台不支持）"


def main() -> None:
    """运行完整性能基准测试，并把结果写入 reports/PERF_REPORT.md。"""
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"样本: 模板={TEMPLATE.name}, 数据={DATA.name}")
    print(f"psutil 可用: {_HAS_PSUTIL}")

    # 1) 模板解析
    info, t_parse = timed(template_parser.parse_template, TEMPLATE)
    print(
        f"模板解析: {t_parse:.1f} ms | 占位符 {len(info.placeholders)} 个, 章节 {len(info.sections)} 个"
    )

    # 2) 数据读取
    ds, t_data = timed(data_reader.read_data, DATA)
    print(f"数据读取: {t_data:.1f} ms | {ds.summary}")
    if not ds.rows:
        raise SystemExit("样本数据为空，无法执行基准测试。")

    # 3) 单文档生成
    def gen_one() -> Path:
        """生成一份包含图表与常量字段的文档。"""
        mappings = mapper.auto_map(info, ds)
        constants = {
            f: f"基准测试内容 {f}"
            for f in [
                "实验名称",
                "实验目的",
                "实验环境",
                "实验步骤",
                "实验结果",
                "问题分析",
                "实验结论",
            ]
        }
        for m in mappings:
            if m.source_type == "constant" and m.template_field in constants:
                m.constant_value = constants[m.template_field]
        ctx = mapper.resolve_values(mappings, row=ds.rows[0] if ds.rows else None)
        ctx["data_rows"] = ds.rows
        img = OUT / "bench_chart.png"
        chart.generate_line_chart(
            [str(r["项目"]) for r in ds.rows], [float(r["数值"]) for r in ds.rows], img
        )
        return generator.generate_report(
            TEMPLATE, ctx, OUT / "bench_single.docx", image_vars={"chart": str(img)}
        )

    out1, t_single = timed(gen_one)
    print(f"单文档生成（含图表）: {t_single:.1f} ms -> {out1.name}")

    # 4) 批量生成 100 份
    def gen_batch(n: int = 100) -> int:
        """批量生成 n 份文档并返回 n。"""
        mappings = mapper.auto_map(info, ds)
        constants = {
            f: f"批量内容 {f}"
            for f in [
                "实验名称",
                "实验目的",
                "实验环境",
                "实验步骤",
                "实验结果",
                "问题分析",
                "实验结论",
            ]
        }
        for m in mappings:
            if m.source_type == "constant" and m.template_field in constants:
                m.constant_value = constants[m.template_field]
        ctx = mapper.resolve_values(mappings, row=ds.rows[0] if ds.rows else None)
        ctx["data_rows"] = ds.rows
        batch_dir = OUT / "bench_batch"
        batch_dir.mkdir(parents=True, exist_ok=True)
        for i in range(n):
            generator.generate_report(TEMPLATE, ctx, batch_dir / f"bench_{i}.docx")
        return n

    n: int = 100
    _, t_batch = timed(gen_batch, n)
    per_doc: float = t_batch / n
    print(f"批量生成 {n} 份: {t_batch:.1f} ms | 平均 {per_doc:.1f} ms/份")

    # 5) 内存
    mem: str = current_memory_mb()
    print(f"进程内存: {mem}")

    # 写入报告数据
    report = f"""# FormoraReport 性能基准报告

> 生成时间: {time.strftime("%Y-%m-%d %H:%M")}
> 方法: 真实样例（tests/samples），Python {platform.python_version()}，{platform.platform()}
> 说明: 未虚构数据，可在本机复现（python scripts/benchmark.py）

| 指标 | 结果 |
|------|------|
| 样本 | {TEMPLATE.name} + {DATA.name} |
| 模板解析 | {t_parse:.1f} ms |
| 数据读取 | {t_data:.1f} ms |
| 单文档生成（含图表） | {t_single:.1f} ms |
| 批量生成 {n} 份 | {t_batch:.1f} ms（平均 {per_doc:.1f} ms/份） |
| 进程内存 | {mem} |
"""
    report_path = Path(__file__).resolve().parent.parent / "reports" / "PERF_REPORT.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"\n报告已写入: {report_path}")


if __name__ == "__main__":
    main()
