#!/usr/bin/env python3
"""FormoraReport 启动入口：python main.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from formora.ui.app import run

if __name__ == "__main__":
    run()