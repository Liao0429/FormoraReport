#!/usr/bin/env python3
"""真实界面截图：启动 FormoraReport，自动加载示例数据，
对浅色/深色主题的每个页面进行屏幕捕获（含系统 Mica 背景）。

仅用于开发/发布流程（需真实桌面会话），不参与自动化测试。
用法：python scripts/capture_screenshots.py
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
from formora.ui.animations import set_reduce_motion
from formora.ui.app_state import AppState
from formora.ui.main_window import MainWindow
from formora.ui.theme import apply_theme

OUT = Path(__file__).resolve().parent.parent / "docs" / "screenshots"
SAMPLES = Path(__file__).resolve().parent.parent / "tests" / "samples"

# 示例内容：让截图页面看起来真实
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
    """解析样例模板 + 数据 + 自动映射，填充示例常量。"""
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
            m.constant_value = {"姓名": "张三", "学号": "20230001"}.get(
                m.template_field, ""
            )
    state.task.name = "示例实验报告"


def capture(window, name: str):
    """渲染窗口内容到画布（只含 FormoraReport，不抓屏幕，避免带入其他程序）。

    先绘制主题渐变底色（模拟系统背景），再把窗口内容 render 上去，
    半透明玻璃卡片会与底色自然混合。
    """
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPixmap

    time.sleep(1.6)  # 等待页面布局与渲染完全稳定
    for _ in range(5):
        app.processEvents()

    theme = (
        window.state.config.get("theme", "light")
        if hasattr(window, "state")
        else "light"
    )
    size = window.size()
    pix = QPixmap(size)

    painter = QPainter(pix)
    grad = QLinearGradient(0, 0, size.width(), size.height())
    if theme == "dark":
        grad.setColorAt(0.0, QColor("#151724"))
        grad.setColorAt(0.5, QColor("#1a1d2b"))
        grad.setColorAt(1.0, QColor("#101220"))
    else:
        grad.setColorAt(0.0, QColor("#eef2f8"))
        grad.setColorAt(0.5, QColor("#e8edf6"))
        grad.setColorAt(1.0, QColor("#f0f2f9"))
    painter.fillRect(pix.rect(), grad)
    painter.end()

    window.render(pix, QPoint(0, 0))
    pix.save(str(OUT / name))
    print("saved", name, pix.width(), "x", pix.height())


def main():
    global app
    ensure_dirs()
    setup_logging()
    OUT.mkdir(parents=True, exist_ok=True)

    app = QApplication(sys.argv)
    app.setApplicationName("FormoraReport")
    set_reduce_motion(True)  # 截图模式：禁用动画，确保页面以最终状态渲染

    cfg = Config()
    # 截图模式：使用中性示例路径，避免泄露真实用户目录（如 C:\Users\<用户名>\...）
    cfg.data["output_dir"] = "D:\\FormoraReport\\输出示例"
    state = AppState(config=cfg)
    win = MainWindow(state)
    win.move(60, 40)
    win.show()
    app.processEvents()
    time.sleep(1.2)
    prepare_state(state)

    pages = ["home", "import", "mapping", "generate", "preview", "settings"]
    for theme in ("light", "dark"):
        apply_theme(app, theme)
        app.processEvents()
        time.sleep(1.2)
        for key in pages:
            win.navigate(key)
            app.processEvents()
            capture(win, f"{theme}_{key}.png")
    win.close()
    print("\n✅ 截图完成，输出目录:", OUT)


if __name__ == "__main__":
    main()
