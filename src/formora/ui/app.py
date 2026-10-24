"""应用入口：创建 QApplication、应用主题、显示主窗口。"""
from __future__ import annotations

import logging
import sys


def _install_excepthook():
    """安装全局异常钩子：未捕获异常写日志并弹窗提示，避免静默退出。"""
    def hook(exc_type, exc_value, exc_tb):
        logger = logging.getLogger("formora")
        logger.exception("未捕获异常", exc_info=(exc_type, exc_value, exc_tb))
        try:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(
                None, "程序错误",
                f"发生未预期的错误：\n{exc_value}\n\n详细信息已写入日志。")
        except Exception:
            pass
    sys.excepthook = hook


def _apply_reduce_motion():
    """读取 Windows「在 Windows 中显示动画」设置，关闭应用内动画（可访问性）。"""
    try:
        import winreg
        with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Control Panel\Accessibility\Visual Effects") as key:
            value, _ = winreg.QueryValueEx(key, "VisualFXSetting")
            # 1 = 显示动画；2 = 无动画
            reduce_motion = (value == "2")
    except Exception:
        reduce_motion = False
    try:
        from formora.ui.animations import set_reduce_motion
        set_reduce_motion(reduce_motion)
    except Exception:
        pass


def run():
    from PySide6.QtWidgets import QApplication
    from formora.services.config import Config, ensure_dirs
    from formora.services.logging_setup import setup_logging
    from formora.ui.app_state import AppState
    from formora.ui.main_window import MainWindow
    from formora.ui.theme import apply_theme

    ensure_dirs()
    setup_logging()
    _install_excepthook()
    cfg = Config()
    app = QApplication(sys.argv)
    app.setApplicationName("FormoraReport")
    app.setOrganizationName("FormoraReport")
    _apply_reduce_motion()
    apply_theme(app, cfg.get("theme", "light"))
    state = AppState(config=cfg)
    win = MainWindow(state)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run()