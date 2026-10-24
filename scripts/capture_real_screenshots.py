#!/usr/bin/env python3
"""真实界面截图 v2：启动 FormoraReport 真实窗口，用 window.grab() 抓取窗口实时像素。

与 capture_screenshots.py 的 window.render() 离屏绘制不同，本脚本让窗口真正显示在
桌面会话，再 grab() 窗口的实际渲染结果（含 Mica/透明/阴影合成），得到最接近
用户真实看到的界面截图。只含应用窗口本身，不抓取桌面其他程序。

用法：python scripts/capture_real_screenshots.py   （需真实桌面会话）
输出：docs/screenshots/<theme>_<page>.png
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from PySide6.QtWidgets import QApplication
from formora.services.config import Config, ensure_dirs
from formora.services.logging_setup import setup_logging
from formora.ui.app_state import AppState
from formora.ui.main_window import MainWindow
from formora.ui.animations import set_reduce_motion
from formora.ui.theme import apply_theme

OUT = Path(__file__).resolve().parent.parent / "docs" / "screenshots"
SAMPLES = Path(__file__).resolve().parent.parent / "tests" / "samples"

_CONSTANTS = {
    "实验名称": "基于 Python 的数据排序与查找实验",
    "实验目的": "掌握常见排序与查找算法的原理与实现，理解时间复杂度差异。",
    "实验环境": "Windows 11，Python 3.14，PyCharm",
    "实验步骤": "1. 编写冒泡排序；2. 编写二分查找；3. 用样本数据测试并记录耗时。",
    "实验结果": "三种算法在 1000 个随机数上运行，快速排序最快，冒泡排序最慢。",
    "问题分析": "冒泡排序 O(n²) 在数据量增大时性能明显下降，应选用更优算法。",
    "实验结论": "验证了不同排序算法的性能差异，理解了算法选择的重要性。",
}


def prepare_state(state):
    from formora.core import data_reader, mapper, template_parser
    tpl = SAMPLES / "实验报告模板.docx"
    data = SAMPLES / "实验数据.csv"
    if not tpl.exists() or not data.exists():
        print("样例文件不存在，先运行 make_samples.py")
        return
    state.new_task("示例实验报告")
    state.template = template_parser.parse_template(tpl)
    state.data = data_reader.read_data(data)
    state.mappings = mapper.auto_map(state.template, state.data)
    for m in state.mappings:
        if m.source_type == "constant" and m.template_field in _CONSTANTS:
            m.constant_value = _CONSTANTS[m.template_field]
        if m.source_type == "column" and m.template_field in ("姓名", "学号"):
            m.source_type = "constant"
            m.constant_value = {"姓名": "张三", "学号": "20230001"}.get(m.template_field, "")
    state.task.name = "示例实验报告"


def capture(win, name: str):
    """用 win.grab() 抓取窗口实时渲染像素（真实 GUI 管线），保存 PNG。"""
    time.sleep(1.6)  # 等待布局/渲染稳定
    for _ in range(5):
        QApplication.processEvents()
    pix = win.grab()  # 抓取窗口当前实际渲染内容
    pix.save(str(OUT / name))
    print("saved", name, pix.width(), "x", pix.height())


def main():
    ensure_dirs()
    setup_logging()
    OUT.mkdir(parents=True, exist_ok=True)

    app = QApplication(sys.argv)
    app.setApplicationName("FormoraReport")
    set_reduce_motion(True)  # 禁用动画，确保页面最终状态

    cfg = Config()
    # 中性示例路径，避免泄露真实用户目录
    cfg.data["output_dir"] = "D:\\FormoraReport\\输出示例"
    state = AppState(config=cfg)
    win = MainWindow(state)
    win.move(80, 60)
    win.show()
    app.processEvents()
    time.sleep(1.5)
    prepare_state(state)

    pages = ["home", "import", "mapping", "generate", "preview", "settings"]
    for theme in ("light", "dark"):
        apply_theme(app, theme)
        app.processEvents()
        time.sleep(1.5)
        for key in pages:
            win.navigate(key)
            app.processEvents()
            capture(win, f"{theme}_{key}.png")
    win.close()
    print("\n✅ 真实界面截图完成，输出目录:", OUT)


if __name__ == "__main__":
    main()
