#!/usr/bin/env python3
"""UI 冒烟测试（offscreen）：用真实样例跑通 首页→导入→映射→生成→预览→导出 PDF→设置 全流程。

覆盖范围：
- 页面流转：首页 → 模板导入 → 字段映射 → 生成报告 → 结果预览 → 导出 PDF → 设置
- 设置页打开/保存：图表样式卡片（颜色主题 / DPI / 网格）修改后保存并重新加载验证
- 异常路径：导入非模板文件应弹出错误提示且应用不崩溃
- 断言一律使用 isHidden（而非 isVisible），适配 offscreen 平台
- 配置/历史/输出全部隔离在临时目录，结束后清理，脚本可重复运行
"""

import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

# GitHub Actions/Windows 控制台默认 cp1252，强制 UTF-8，避免打印中文时 UnicodeEncodeError
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# 必须在导入 PySide6 之前强制 offscreen 平台，否则 CI/无显示器环境会尝试创建真实窗口
os.environ["QT_QPA_PLATFORM"] = "offscreen"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLES = PROJECT_ROOT / "tests" / "samples"
TEMPLATE = SAMPLES / "实验报告模板.docx"
DATA = SAMPLES / "实验数据.csv"

# 临时根目录：配置/历史/输出全部隔离于此，结束整体清理，保证可重复运行
_TMP_ROOT = Path(tempfile.mkdtemp(prefix="formora_ui_smoke_"))
os.environ["APPDATA"] = str(_TMP_ROOT / "appdata")
os.environ["XDG_CONFIG_HOME"] = str(_TMP_ROOT / "xdg")

sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from PySide6.QtWidgets import QApplication, QMessageBox

from formora.core import data_reader, template_parser
from formora.core.chart import BLUE_ORANGE_COLORS
from formora.services.config import Config
from formora.ui.app_state import AppState
from formora.ui.main_window import MainWindow
from formora.ui.theme import apply_theme

# 确保样例存在（make_samples 生成的样例，重复运行输出一致）
from make_samples import make_csv, make_template

SAMPLES.mkdir(parents=True, exist_ok=True)
if not TEMPLATE.exists():
    make_template(TEMPLATE)
if not DATA.exists():
    make_csv(DATA)

# 记录弹窗；将模态 QMessageBox 替换为非阻塞捕获，避免 offscreen 测试卡在弹窗
_MESSAGE_BOXES: list[tuple[str, tuple, dict]] = []


def _capture(kind: str):
    def _box(*args, **kwargs):
        _MESSAGE_BOXES.append((kind, args, kwargs))
        return QMessageBox.StandardButton.Ok

    return staticmethod(_box)


QMessageBox.information = _capture("information")
QMessageBox.warning = _capture("warning")
QMessageBox.critical = _capture("critical")
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)


def _assert_page_shown(win: MainWindow, key: str) -> None:
    """断言 key 页为当前页（用 isHidden 而非 isVisible）。"""
    assert not win.pages[key].isHidden(), f"页面 {key} 应为当前可见页"
    for k, page in win.pages.items():
        if k != key:
            assert page.isHidden(), f"非当前页 {k} 应处于隐藏状态"


def _wait_until(predicate, timeout: float = 30.0) -> bool:
    """轮询等待后台线程/状态完成（保持现有轮询等待风格）。"""
    deadline = time.time() + timeout
    while time.time() < deadline and not predicate():
        app.processEvents()
        time.sleep(0.05)
    app.processEvents()
    return predicate()


def main() -> int:
    global app
    app = QApplication([])
    apply_theme(app, "light")
    cfg = Config()  # 位于 _TMP_ROOT/appdata/... 的临时配置
    cfg.set("output_dir", str(_TMP_ROOT / "out"))
    state = AppState(config=cfg)
    win = MainWindow(state)
    win.show()
    app.processEvents()
    print("主窗口 OK, 页面:", len(win.pages))

    try:
        # ---------- 首页 ----------
        win.navigate("home")
        app.processEvents()
        _assert_page_shown(win, "home")
        print("首页 OK")

        # ---------- 异常路径：导入非模板文件应弹错误且不崩溃 ----------
        imp = win.pages["import"]
        win.navigate("import")
        app.processEvents()
        _assert_page_shown(win, "import")
        imp.template_edit.setText(str(DATA))  # CSV 不是 .docx 模板
        imp.data_edit.setText("")
        _MESSAGE_BOXES.clear()
        imp._parse()
        app.processEvents()
        err_shown = any(
            kind == "critical" and len(args) >= 3 and "解析失败" in str(args[1])
            for kind, args, _ in _MESSAGE_BOXES
        )
        assert err_shown, "导入非模板文件应弹出「解析失败」错误"
        assert state.template is None, "错误后不应残留模板状态"
        assert not imp.next_btn.isEnabled(), "未成功解析前不应允许进入映射"
        # 应用未崩溃：可继续导航
        win.navigate("home")
        app.processEvents()
        _assert_page_shown(win, "home")
        print("异常路径 OK: 非模板文件弹出错误且应用未崩溃")

        # ---------- 正常导入（模板 + 数据） ----------
        win.navigate("import")
        app.processEvents()
        _assert_page_shown(win, "import")
        imp.template_edit.setText(str(TEMPLATE))
        imp.data_edit.setText(str(DATA))
        _MESSAGE_BOXES.clear()
        imp._parse()
        app.processEvents()
        assert state.template is not None, "模板应解析成功"
        assert "模板解析成功" in imp.info_text.toPlainText()
        assert imp.next_btn.isEnabled(), "解析成功后应允许进入映射"
        print("导入页 OK: 模板解析成功")

        # ---------- 字段映射 ----------
        win.navigate("mapping")
        app.processEvents()
        _assert_page_shown(win, "mapping")
        mp = win.pages["mapping"]
        print("映射页 OK, 行数:", mp.table.rowCount())
        assert mp.table.rowCount() > 0, "映射表应有行"

        # 填充分段：给常量字段赋值
        constants = {
            "实验名称": "冒烟测试实验",
            "实验目的": "验证 UI 全流程",
            "实验环境": "Windows 10 + Python",
            "实验步骤": "1. 导入；2. 映射；3. 生成",
            "实验结果": "流程通过",
            "问题分析": "无",
            "实验结论": "结论正确",
        }
        for m in state.mappings:
            if m.source_type == "constant" and m.template_field in constants:
                m.constant_value = constants[m.template_field]

        # 把模型值同步进表格控件（真实使用中用户直接在表格输入）
        mp._fill_table()
        app.processEvents()

        # 触发校验（非阻塞）
        mp._validate()
        app.processEvents()
        print("校验 OK:", mp.issues_text.toPlainText()[:60])

        # ---------- 生成报告（异步线程，轮询等待） ----------
        mp._generate()
        assert _wait_until(lambda: bool(state.output_path), 30), "单份生成超时"
        print("生成后 output_path:", state.output_path)
        assert state.output_path and Path(state.output_path).exists(), "输出文件不存在"

        # 生成页
        win.navigate("generate")
        app.processEvents()
        _assert_page_shown(win, "generate")
        assert state.output_path in win.pages["generate"].out_edit.text(), "生成页应显示输出路径"
        print("生成页 OK")

        # ---------- 预览 ----------
        win.navigate("preview")
        app.processEvents()
        _assert_page_shown(win, "preview")
        preview_text = win.pages["preview"].text_edit.toPlainText()
        print("预览页 OK, 包含冒烟测试实验:", "冒烟测试实验" in preview_text)
        assert "冒烟测试实验" in preview_text

        # 图片绑定：chart 字段应作为图片类型，且自动图表产生 image_var
        img_vars = mp._image_vars()
        print("图片变量:", img_vars)
        assert any(
            m.source_type == "image" or m.template_field in img_vars
            for m in state.mappings
        ), "应有图片字段"

        # ---------- 导出 PDF（异步线程） ----------
        win.pages["preview"].export_btn.click()
        pdf_thread = win.pages["preview"]._export_thread
        assert pdf_thread is not None, "导出 PDF 线程应已启动"
        assert _wait_until(lambda: not pdf_thread.isRunning(), 60), "导出 PDF 超时"
        pdf_path = Path(state.output_path).with_suffix(".pdf")
        if pdf_path.exists():
            assert pdf_path.stat().st_size > 0, "PDF 文件不应为空"
            print("导出 PDF OK:", pdf_path)
        else:
            # 环境缺少 LibreOffice/Word 时允许跳过，但导出流程应执行完并弹出失败提示
            print("⚠️ 导出 PDF 未产生文件（可能缺少 LibreOffice/Word），跳过断言")
            assert any(
                kind == "critical" and len(args) >= 3 and "导出 PDF 失败" in str(args[1])
                for kind, args, _ in _MESSAGE_BOXES
            ), "导出失败时应弹出错误提示"

        # ---------- 批量生成全部数据行 ----------
        mp._generate_batch()
        assert _wait_until(lambda: bool(getattr(state, "last_batch_dir", None)), 30), "批量生成超时"
        batch_dir = getattr(state, "last_batch_dir", None)
        batch_files = sorted(Path(batch_dir).glob("*.docx")) if batch_dir else []
        print("批量生成文件数:", len(batch_files), "目录:", batch_dir)
        assert len(batch_files) == len(state.data.rows), (
            f"批量数量不符: {len(batch_files)} != {len(state.data.rows)}"
        )
        assert all(f.exists() for f in batch_files)

        # ---------- 设置页：打开 + 保存图表样式 ----------
        win.navigate("settings")
        app.processEvents()
        _assert_page_shown(win, "settings")
        setp = win.pages["settings"]
        # 初始状态（默认配置的图表颜色即蓝橙，config.DEFAULTS.chart.colors == BLUE_ORANGE_COLORS）
        assert setp.chart_colors_combo.currentIndex() == 1, "默认图表颜色应为蓝橙"
        assert setp.chart_dpi_combo.currentText() == "150", "默认 DPI 应为 150"
        assert setp.chart_grid_check.isChecked(), "默认应显示网格"
        # 修改设置并保存：主题切深色、图表颜色切「默认」、DPI 200、关闭网格
        setp.theme_combo.setCurrentIndex(1)  # 深色
        setp.chart_colors_combo.setCurrentIndex(0)  # 默认
        setp.chart_dpi_combo.setCurrentText("200")
        setp.chart_grid_check.setChecked(False)
        _MESSAGE_BOXES.clear()
        setp._save()
        app.processEvents()
        chart_cfg = cfg.get("chart", {})
        assert cfg.get("theme") == "dark", "主题应保存为深色"
        assert list(chart_cfg.get("colors") or []) == [], "图表颜色应保存为「默认」"
        assert chart_cfg.get("dpi") == 200, "图表 DPI 应保存为 200"
        assert chart_cfg.get("grid") is False, "图表网格应保存为关闭"
        assert any(
            kind == "information" and len(args) >= 3 and "已保存" in str(args[1])
            for kind, args, _ in _MESSAGE_BOXES
        ), "保存后应弹出「设置已保存」提示"
        # 重新加载（模拟再次打开设置页）：控件应反映已保存值
        setp._load()
        assert setp.theme_combo.currentIndex() == 1, "重新加载后主题应为深色"
        assert setp.chart_colors_combo.currentIndex() == 0, "重新加载后图表颜色应为默认"
        assert setp.chart_dpi_combo.currentText() == "200", "重新加载后 DPI 应为 200"
        assert not setp.chart_grid_check.isChecked(), "重新加载后网格应关闭"
        print("设置页 OK: 图表样式保存/重新加载一致, theme =", cfg.get("theme"))

        print("✅ UI 全流程冒烟测试通过（含异常路径 + 导出 PDF + 批量生成 + 设置保存）")
        return 0
    finally:
        win.close()
        app.processEvents()
        shutil.rmtree(_TMP_ROOT, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())