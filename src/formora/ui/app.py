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

            # 只展示中文兜底文案，避免把原始异常堆栈/敏感信息直接暴露给用户。
            QMessageBox.critical(
                None,
                "程序错误",
                "发生未预期的错误，详细信息已写入日志。",
            )
        except Exception:
            # 弹窗失败（如 QApplication 尚未创建）也必须确保日志已写入。
            logger.exception("无法显示错误提示对话框")

    sys.excepthook = hook


def _apply_reduce_motion():
    """读取 Windows「在 Windows 中显示动画」设置，关闭应用内动画（可访问性）。"""
    # 非 Windows（无 winreg）或注册表读取失败时默认不减少动画：降级安全。
    reduce_motion = False
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, r"Control Panel\Accessibility\Visual Effects"
        ) as key:
            value, _ = winreg.QueryValueEx(key, "VisualFXSetting")
            # 1 = 显示动画；2 = 无动画（注册表值可能是 str 或 int，统一转字符串比较）
            reduce_motion = str(value).strip() == "2"
    except Exception:
        pass  # 非 Windows 或注册表不可用：保持默认 reduce_motion = False
    try:
        from formora.ui.animations import set_reduce_motion

        set_reduce_motion(reduce_motion)
    except Exception:
        pass


def _schedule_update_check(win) -> None:
    """启动后静默检查更新：后台线程查询，发现新版才弹一次性提示。

    不阻塞主窗口：仅注册一个 3 秒后的 QTimer，网络请求在 daemon 线程执行，
    通过信号回到主线程再弹窗。
    """
    from PySide6.QtCore import QObject, QTimer, QUrl, Signal
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtWidgets import QMessageBox

    from formora.services.update_checker import check_for_update

    class _UpdateNotifier(QObject):
        found = Signal(str, str)

        def start(self):
            import threading

            threading.Thread(target=self._run, daemon=True).start()

        def _run(self):
            try:
                result = check_for_update()
            except Exception:
                result = None
            if result:
                self.found.emit(result[0], result[1])

    class _UpdatePrompter(QObject):
        def __init__(self, main_win):
            super().__init__()
            self._win = main_win

        def on_found(self, version, url):
            try:
                if not self._win.isVisible():
                    return  # 主窗口已隐藏/关闭：不再打扰
            except RuntimeError:
                return  # 主窗口 C++ 对象已销毁
            ret = QMessageBox.question(
                self._win,
                "发现新版本",
                f"发现新版本 FormoraReport {version}，是否打开 Releases 页面下载？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if ret == QMessageBox.StandardButton.Yes:
                QDesktopServices.openUrl(QUrl(url))

    notifier = _UpdateNotifier()
    prompter = _UpdatePrompter(win)
    notifier.found.connect(prompter.on_found)
    # 持有引用，防止局部对象被垃圾回收后信号丢失
    win._update_check_objects = (notifier, prompter)
    QTimer.singleShot(3000, notifier.start)


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
    _schedule_update_check(win)
    sys.exit(app.exec())


if __name__ == "__main__":
    run()
