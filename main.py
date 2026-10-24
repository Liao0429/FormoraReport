#!/usr/bin/env python3
"""FormoraReport 启动入口：python main.py"""
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    # PyInstaller 打包版：formora 包已打进 _internal/formora
    _bundle = Path(getattr(sys, "_MEIPASS", Path(sys.argv[0]).parent))
    sys.path.insert(0, str(_bundle))
else:
    # 源码运行
    sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from formora.ui.app import run

if __name__ == "__main__":
    run()