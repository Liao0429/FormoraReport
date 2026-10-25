#!/usr/bin/env python3
"""生成真实样例：通用/物理/化学实验报告模板（DOCX）+ 配套 CSV 数据。

用于 MVP 验证和自动化测试。生成到 tests/samples/。

样例内容完全确定：不依赖随机数、时间戳或当前工作目录，重复运行生成一致结果，
便于在 CI / 自动化测试中复现。
"""

from __future__ import annotations

import csv
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

SAMPLES = Path(__file__).resolve().parent.parent / "tests" / "samples"

# 通用样例 CSV 数据。数值以字符串书写，避免浮点序列化差异，保证字节级可复现。
_SAMPLE_ROWS: list[list[str]] = [
    ["项目", "数值"],
    ["样本A", "12.5"],
    ["样本B", "18.2"],
    ["样本C", "15.7"],
    ["样本D", "21.3"],
]

# 物理实验样例数据（单摆测重力加速度）
_PHYSICS_ROWS: list[list[str]] = [
    ["项目", "数值"],
    ["摆长L/cm", "25.0"],
    ["周期T1/s", "1.02"],
    ["周期T2/s", "1.05"],
    ["周期T3/s", "1.03"],
    ["周期T4/s", "1.04"],
    ["重力加速度g/(m/s²)", "9.79"],
]

# 化学实验样例数据（稀盐酸与大理石反应）
_CHEMISTRY_ROWS: list[list[str]] = [
    ["药品", "用量", "现象"],
    ["稀盐酸", "5 mL", "产生无色气泡，澄清石灰水变浑浊"],
    ["大理石", "2 g", "固体逐渐溶解，持续冒气泡"],
    ["澄清石灰水", "3 mL", "溶液由澄清变浑浊"],
    ["酚酞试液", "2 滴", "溶液变红"],
]


def _h(doc: Document, text: str) -> None:
    """添加一个加粗段落，作为章节标题。"""
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = True


def _add_info_table(doc: Document) -> None:
    """添加姓名/学号/班级/日期基本信息表。"""
    table = doc.add_table(rows=2, cols=4)
    table.style = "Table Grid"
    cells = [
        ("姓名", "{{姓名}}", "学号", "{{学号}}"),
        ("班级", "{{班级}}", "日期", "{{日期}}"),
    ]
    for ri, row in enumerate(cells):
        for ci, val in enumerate(row):
            table.cell(ri, ci).text = val


def _add_title(doc: Document, text: str) -> None:
    """添加居中加粗的大号标题。"""
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run(text)
    run.bold = True
    run.font.size = Pt(18)


def _save_docx(doc: Document, path: Path) -> None:
    """保存 DOCX，固定 zip 时间戳与条目顺序，保证重复运行字节级一致。

    python-docx 直接保存会在 zip 中写入当前时间戳，导致同一内容每次输出
    字节不同。这里先保存到内存，再以固定时间戳重写 zip，
    使样例文件可在 CI / 自动化测试中精确复现。
    """
    import io
    import zipfile

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    with zipfile.ZipFile(buf, "r") as zin:
        infos = zin.infolist()
        payload = {i.filename: zin.read(i.filename) for i in infos}
    with zipfile.ZipFile(str(path), "w", zipfile.ZIP_DEFLATED) as zout:
        for i in infos:
            zi = zipfile.ZipInfo(i.filename, date_time=(1980, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = i.external_attr
            zout.writestr(zi, payload[i.filename])


def make_template(path: Path) -> None:
    """生成含占位符/循环/图表位的 DOCX 实验报告模板。"""
    doc = Document()
    _add_title(doc, "实 验 报 告")

    _add_info_table(doc)

    doc.add_paragraph()
    _h(doc, "一、实验名称")
    doc.add_paragraph("{{实验名称}}")
    _h(doc, "二、实验目的")
    doc.add_paragraph("{{实验目的}}")
    _h(doc, "三、实验环境")
    doc.add_paragraph("{{实验环境}}")
    _h(doc, "四、实验步骤")
    doc.add_paragraph("{{实验步骤}}")
    _h(doc, "五、实验数据")
    doc.add_paragraph(
        "{% for row in data_rows %}{{ row['项目'] }}：{{ row['数值'] }}；{% endfor %}"
    )
    _h(doc, "六、实验结果图表")
    doc.add_paragraph("{{ chart }}")
    _h(doc, "七、实验结果")
    doc.add_paragraph("{{实验结果}}")
    _h(doc, "八、问题分析")
    doc.add_paragraph("{{问题分析}}")
    _h(doc, "九、实验结论")
    doc.add_paragraph("{{实验结论}}")

    _save_docx(doc, path)
    print(f"模板已生成: {path}")


def make_template_physics(path: Path) -> None:
    """生成物理实验报告模板（单摆测重力加速度）。

    含 {{姓名}}/{{学号}}/{{日期}}/{{chart}} 占位符、数据记录循环块，
    以及实验目的/原理/器材/步骤/误差分析/结论等章节。
    """
    doc = Document()
    _add_title(doc, "物 理 实 验 报 告")

    _add_info_table(doc)

    doc.add_paragraph()
    _h(doc, "一、实验目的")
    doc.add_paragraph("{{实验目的}}")
    _h(doc, "二、实验原理")
    doc.add_paragraph("{{实验原理}}")
    _h(doc, "三、实验器材")
    doc.add_paragraph("{{实验器材}}")
    _h(doc, "四、实验步骤")
    doc.add_paragraph("{{实验步骤}}")
    _h(doc, "五、数据记录表")
    doc.add_paragraph(
        "{% for row in data_rows %}{{ row['项目'] }} = {{ row['数值'] }}；{% endfor %}"
    )
    _h(doc, "六、误差分析")
    doc.add_paragraph("{{误差分析}}")
    _h(doc, "七、实验结果图表")
    doc.add_paragraph("{{chart}}")
    _h(doc, "八、实验结论")
    doc.add_paragraph("{{实验结论}}")

    _save_docx(doc, path)
    print(f"模板已生成: {path}")


def make_template_chemistry(path: Path) -> None:
    """生成化学实验报告模板。

    含图片占位符 {{装置图}}、现象记录循环块，
    以及实验名称/药品与仪器/操作步骤/数据分析/结论等章节。
    """
    doc = Document()
    _add_title(doc, "化 学 实 验 报 告")

    _add_info_table(doc)

    doc.add_paragraph()
    _h(doc, "一、实验名称")
    doc.add_paragraph("{{实验名称}}")
    _h(doc, "二、实验目的")
    doc.add_paragraph("{{实验目的}}")
    _h(doc, "三、实验原理")
    doc.add_paragraph("{{实验原理}}")
    _h(doc, "四、药品与仪器")
    doc.add_paragraph("{{药品与仪器}}")
    _h(doc, "五、操作步骤")
    doc.add_paragraph("{{操作步骤}}")
    _h(doc, "六、装置图")
    doc.add_paragraph("{{装置图}}")
    _h(doc, "七、现象记录")
    doc.add_paragraph(
        "{% for row in data_rows %}"
        "{{ row['药品'] }}（{{ row['用量'] }}）：{{ row['现象'] }}；"
        "{% endfor %}"
    )
    _h(doc, "八、数据分析")
    doc.add_paragraph("{{数据分析}}")
    _h(doc, "九、结论")
    doc.add_paragraph("{{结论}}")

    _save_docx(doc, path)
    print(f"模板已生成: {path}")


def make_csv(path: Path, rows: list[list[str]] | None = None) -> None:
    """生成 UTF-8（带 BOM）CSV 数据，默认使用通用样例数据。"""
    if rows is None:
        rows = _SAMPLE_ROWS
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerows(rows)
    print(f"数据已生成: {path}")


def main() -> None:
    SAMPLES.mkdir(parents=True, exist_ok=True)
    make_template(SAMPLES / "实验报告模板.docx")
    make_csv(SAMPLES / "实验数据.csv")
    make_template_physics(SAMPLES / "物理实验模板.docx")
    make_csv(SAMPLES / "物理实验数据.csv", _PHYSICS_ROWS)
    make_template_chemistry(SAMPLES / "化学实验模板.docx")
    make_csv(SAMPLES / "化学实验数据.csv", _CHEMISTRY_ROWS)


if __name__ == "__main__":
    main()
