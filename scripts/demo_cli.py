#!/usr/bin/env python3
"""无 AI 模式核心链路演示（headless CLI）：
导入模板 → 读取数据 → 字段映射 → 预览值 → 生成图表 → 生成 DOCX → 校验 → 验证输出可打开。

用法：
  cd <项目目录>
  source .venv/Scripts/activate
  python scripts/demo_cli.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from formora.core import chart, data_reader, generator, mapper, template_parser, validator
from formora.core.errors import FormoraError

SAMPLES = Path(__file__).resolve().parent.parent / "tests" / "samples"
OUT = Path(__file__).resolve().parent.parent / "tests" / "output"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    template_path = SAMPLES / "实验报告模板.docx"
    data_path = SAMPLES / "实验数据.csv"

    print("=" * 60)
    print("1) 解析模板")
    info = template_parser.parse_template(template_path)
    print(f"   占位符: {info.placeholders}")
    print(f"   循环块: {info.loop_blocks}")
    print(f"   检测到章节: {list(info.sections.keys())}")
    print(f"   表格数: {len(info.tables)}")

    print("2) 读取数据")
    ds = data_reader.read_data(data_path)
    print(f"   类型={ds.kind} 摘要={ds.summary} 列={ds.columns}")

    print("3) 自动字段映射")
    mappings = mapper.auto_map(info, ds)
    for m in mappings:
        print(f"   {m.template_field} -> {m.source_type}:{m.source_column or m.constant_value!r}")

    # 为文本型核心字段填入示例内容（真实使用中由用户提供/ AI 生成）
    constants = {
        "实验名称": "基于 Python 的数据排序与查找实验",
        "实验目的": "掌握常见排序与查找算法的原理与实现，理解时间复杂度的差异。",
        "实验环境": "Windows 10，Python 3.12，PyCharm",
        "实验步骤": "1. 编写冒泡排序；2. 编写二分查找；3. 用样本数据测试并记录耗时。",
        "实验结果": "三种排序算法在 1000 个随机数上运行，冒泡排序耗时最长，快速排序最快。",
        "问题分析": "冒泡排序时间复杂度 O(n²)，在数据量增大时性能明显下降。",
        "实验结论": "本次实验验证了不同排序算法的性能差异，理解了算法选择的重要性。",
    }
    for m in mappings:
        if m.source_type == "constant" and m.template_field in constants:
            m.constant_value = constants[m.template_field]

    print("4) 生成图表")
    row = ds.rows[0] if ds.rows else {}
    # 用全部数据行生成折线图
    xs = [str(r["项目"]) for r in ds.rows]
    ys = [float(r["数值"]) for r in ds.rows]
    chart_png = OUT / "实验数据图表.png"
    chart.generate_line_chart(xs, ys, chart_png, title="实验数据折线图", x_label="样本", y_label="数值")
    print(f"   图表已生成: {chart_png}")

    print("5) 解析上下文并生成 DOCX")
    context = mapper.resolve_values(mappings, row=row)
    # 加入循环块数据
    context["data_rows"] = ds.rows
    context["chart"] = None  # 占位，实际用 image_vars 注入 InlineImage

    output = generator.generate_report(
        template_path, context, OUT / "实验报告_输出.docx",
        image_vars={"chart": str(chart_png)},
    )
    print(f"   输出: {output}")

    print("6) 校验")
    issues = validator.validate_context(context, info, image_placeholders={"chart"})
    for iss in issues:
        print(f"   [{iss.severity}] {iss.field}: {iss.message}")

    print("7) 验证输出可打开")
    from docx import Document
    doc = Document(str(output))
    texts = [p.text for p in doc.paragraphs if p.text.strip()]
    print(f"   段落数={len(texts)}")
    for t in texts[:12]:
        print(f"   | {t[:60]}")
    print("\n✅ 无 AI 核心链路跑通。")


if __name__ == "__main__":
    try:
        main()
    except FormoraError as e:
        print(f"\n❌ {e}")
        sys.exit(1)