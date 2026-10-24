"""应用入口：创建 QApplication、应用主题、显示主窗口。"""
from __future__ import annotations

import sys


def run():
    from PySide6.QtWidgets import QApplication
    from formora.services.config import Config, ensure_dirs
    from formora.services.logging_setup import setup_logging
    from formora.ui.app_state import AppState
    from formora.ui.main_window import MainWindow
    from formora.ui.theme import apply_theme

    ensure_dirs()
    setup_logging()
    cfg = Config()
    app = QApplication(sys.argv)
    app.setApplicationName("FormoraReport")
    app.setOrganizationName("FormoraReport")
    apply_theme(app, cfg.get("theme", "light"))
    state = AppState(config=cfg)
    win = MainWindow(state)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run()