#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量生成 100 份报告基准（对比优化前后用）。

用法: ./.venv/Scripts/python.exe scripts/benchmark_batch.py
输出: 总耗时 ms / 平均 ms 每份 / 成功份数。不写入任何报告文件。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from formora.core import mapper, template_parser
from formora.core.models import DataSource, ReportTask
from formora.services.config import Config
from formora.services.report_service import generate_batch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLES = PROJECT_ROOT / "tests" / "samples"
TEMPLATE = SAMPLES / "实验报告模板.docx"

N_ROWS = 100


def build_state(out_dir: Path) -> SimpleNamespace:
    cfg = Config(PROJECT_ROOT / "tests" / "output" / "bench_config.json")
    cfg.set("output_dir", str(out_dir))
    template = template_parser.parse_template(TEMPLATE)
    # 直接构造 100 行表格数据，绕开 data_reader（基准只关心生成环节）
    names = ["样本A", "样本B", "样本C", "样本D"]
    rows = [{"项目": names[i % len(names)], "数值": 12.5 + i} for i in range(N_ROWS)]
    data = DataSource(
        path=SAMPLES / "实验数据.csv",
        kind="csv",
        columns=["项目", "数值"],
        rows=rows,
        summary=f"{N_ROWS} 行 × 2 列",
        row_count=N_ROWS,
    )
    mappings = mapper.auto_map(template, data)
    constants = {
        "实验名称": "批量基准实验",
        "实验目的": "验证批量性能",
        "实验环境": "本机",
        "实验步骤": "1. 映射；2. 生成",
        "实验结果": "成功",
        "问题分析": "无",
        "实验结论": "结论",
    }
    for m in mappings:
        if m.source_type == "constant" and m.template_field in constants:
            m.constant_value = constants[m.template_field]
    task = ReportTask(name="批量基准", template_path=TEMPLATE)
    return SimpleNamespace(
        config=cfg,
        template=template,
        data=data,
        mappings=mappings,
        task=task,
        last_batch_dir=None,
    )


def main() -> None:
    # 基准测试不应写入真实任务历史
    import formora.services.report_service as rs

    rs.record_task = lambda task: None

    out_dir = PROJECT_ROOT / "tests" / "output" / "bench_batch"
    state = build_state(out_dir)
    print(f"模板: {TEMPLATE.name} | 数据行数: {len(state.data.rows)}")
    t0 = time.perf_counter()
    results, errors = generate_batch(state, auto_chart=False)
    dt = (time.perf_counter() - t0) * 1000
    print(f"成功: {len(results)} | 失败: {len(errors)}")
    print(f"总耗时: {dt:.1f} ms | 平均: {dt / N_ROWS:.2f} ms/份")
    if errors:
        print("前 3 个错误:")
        for e in errors[:3]:
            print(" -", e)


if __name__ == "__main__":
    main()