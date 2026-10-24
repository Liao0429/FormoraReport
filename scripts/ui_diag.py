#!/usr/bin/env python3
"""诊断 UI 冒烟测试卡点。"""
import os, sys, time
from pathlib import Path
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

def log(msg):
    print(f"[{time.time():.1f}] {msg}", flush=True)

log("import Qt")
from PySide6.QtWidgets import QApplication
from formora.services.config import Config
from formora.ui.app_state import AppState
from formora.ui.theme import apply_theme

log("create app")
app = QApplication([])
apply_theme(app, "light")
log("create state")
state = AppState(config=Config())
log("create MainWindow")
from formora.ui.main_window import MainWindow
t0 = time.time()
win = MainWindow(state)
log(f"MainWindow created in {time.time()-t0:.1f}s")
log("show")
t0 = time.time()
win.show()
log(f"show returned in {time.time()-t0:.1f}s")
log("navigate")
for key in win.pages:
    win.navigate(key)
log("processEvents")
app.processEvents()
log("DONE")