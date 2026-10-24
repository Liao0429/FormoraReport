#!/usr/bin/env python3
"""UI 冒烟测试（offscreen）：用真实样例跑通 首页→导入→映射→生成→预览 全流程。"""
import os
import sys
from pathlib import Path

# GitHub Actions/Windows 控制台默认 cp1252，强制 UTF-8，避免打印中文时 UnicodeEncodeError
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from PySide6.QtWidgets import QApplication

from formora.services.config import Config
from formora.ui.app_state import AppState
from formora.ui.main_window import MainWindow
from formora.ui.theme import apply_theme

SAMPLES = Path(__file__).resolve().parent.parent / "tests" / "samples"
TEMPLATE = SAMPLES / "实验报告模板.docx"
DATA = SAMPLES / "实验数据.csv"

app = QApplication([])
apply_theme(app, "light")
state = AppState(config=Config())
win = MainWindow(state)
win.show()
app.processEvents()
print("主窗口 OK, 页面:", len(win.pages))

# 首页
win.navigate("home")
app.processEvents()
print("首页 OK")

# 模拟导入：先建任务，再填充模板与数据（与导入页实际逻辑一致）
from formora.core import data_reader, template_parser
info = template_parser.parse_template(TEMPLATE)
ds = data_reader.read_data(DATA)
state.new_task(name="UI冒烟测试")
state.task.template_path = TEMPLATE
state.task.data_source = DATA
state.template = info
state.data = ds

win.navigate("mapping")
app.processEvents()
print("映射页 OK, 行数:", win.pages["mapping"].table.rowCount())

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
win.pages["mapping"]._fill_table()
app.processEvents()

# 触发校验（非阻塞）
win.pages["mapping"]._validate()
app.processEvents()
print("校验 OK:", win.pages["mapping"].issues_text.toPlainText()[:60])

# 生成报告
win.pages["mapping"]._generate()
app.processEvents()
print("生成后 output_path:", state.output_path)
assert state.output_path and Path(state.output_path).exists(), "输出文件不存在"

# 生成页和预览页
win.navigate("generate")
app.processEvents()
print("生成页 OK")
win.navigate("preview")
app.processEvents()
preview_text = win.pages["preview"].text_edit.toPlainText()
print("预览页 OK, 包含冒烟测试实验:", "冒烟测试实验" in preview_text)
assert "冒烟测试实验" in preview_text

# 图片绑定：chart 字段应作为图片类型，且自动图表产生 image_var
mp = win.pages["mapping"]
img_vars = mp._image_vars()
print("图片变量:", img_vars)
assert any(m.source_type == "image" or m.template_field in img_vars
           for m in state.mappings), "应有图片字段"

# 批量生成全部数据行
mp._generate_batch()
# 批量生成已异步化：轮询等待后台线程完成（最多 30 秒）
import time
deadline = time.time() + 30
while time.time() < deadline and not getattr(state, "last_batch_dir", None):
    app.processEvents()
    time.sleep(0.05)
batch_dir = getattr(state, "last_batch_dir", None)
batch_files = sorted(Path(batch_dir).glob("*.docx")) if batch_dir else []
print("批量生成文件数:", len(batch_files), "目录:", batch_dir)
assert len(batch_files) == len(ds.rows), f"批量数量不符: {len(batch_files)} != {len(ds.rows)}"
assert all(f.exists() for f in batch_files)

# 深色主题
apply_theme(app, "dark")
win._on_theme_change("dark")
app.processEvents()
print("深色主题 OK")

print("✅ UI 全流程冒烟测试通过（含图片绑定 + 批量生成）")