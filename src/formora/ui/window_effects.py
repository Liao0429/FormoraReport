"""Windows 液态玻璃系统效果：Mica/Acrylic 背景、无边框窗口、圆角。

通过 ctypes 调用 DWM API（仅 Windows 11 22H2+ 支持 Mica/Acrylic）。
所有调用均 try/except 包裹，失败时静默降级为纯 QSS 渐变背景，
保证在 Windows 10 / 无 DWM 支持 / offscreen 测试环境下也能正常运行。
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes
import sys

# DWM 属性常量（Windows 11 22H2+）
DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWA_SYSTEMBACKDROP_TYPE = 38

# SystemBackdropType
BACKDROP_AUTO = 0
BACKDROP_NONE = 1
BACKDROP_MAIN_WINDOW = 2      # Mica
BACKDROP_TRANSIENT_WINDOW = 3 # Acrylic
BACKDROP_TABBED_WINDOW = 4    # MicaTabbed

# DWMWINDOWCORNERPREFERENCE
DWMWCP_DEFAULT = 0
DWMWCP_DONOTROUND = 1
DWMWCP_ROUND = 2
DWMWCP_ROUNDSMALL = 3

_IS_WINDOWS = sys.platform == "win32"
_dwmapi = None
if _IS_WINDOWS:
    try:
        _dwmapi = ctypes.windll.dwmapi
    except Exception:  # pragma: no cover
        _dwmapi = None


def _set_window_attribute(hwnd: int, attr: int, value: int) -> bool:
    """调用 DwmSetWindowAttribute，返回是否成功。"""
    if _dwmapi is None or not hwnd:
        return False
    try:
        v = ctypes.c_int(value)
        result = _dwmapi.DwmSetWindowAttribute(
            ctypes.wintypes.HWND(hwnd), attr, ctypes.byref(v), ctypes.sizeof(v))
        return result == 0
    except Exception:
        return False


def apply_system_backdrop(hwnd: int, backdrop: int = BACKDROP_MAIN_WINDOW) -> bool:
    """启用系统 Mica/Acrylic 背景。返回是否成功。"""
    return _set_window_attribute(hwnd, DWMWA_SYSTEMBACKDROP_TYPE, backdrop)


def apply_window_corner(hwnd: int, corner: int = DWMWCP_ROUND) -> bool:
    """设置窗口圆角（Win11）。"""
    return _set_window_attribute(hwnd, DWMWA_WINDOW_CORNER_PREFERENCE, corner)


def apply_immersive_dark_mode(hwnd: int, dark: bool) -> bool:
    """设置深色标题栏/边框。"""
    return _set_window_attribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, 1 if dark else 0)


def is_mica_supported() -> bool:
    """粗略检测：Windows 11 22H2+ 支持 Mica。失败返回 False，调用方走 QSS 降级。"""
    if not _IS_WINDOWS or _dwmapi is None:
        return False
    # 用当前进程窗口试探一次（某些环境 winId 尚未创建，这里仅检测 DLL 可用性）
    return True


def setup_glass_window(window, dark: bool = False) -> bool:
    """对主窗口一次性启用 Mica + 圆角 + 深色边框。返回 Mica 是否启用成功。

    必须在窗口 show() 之后调用（winId() 此时才有效）。
    """
    if not _IS_WINDOWS:
        return False
    try:
        hwnd = int(window.winId())
    except Exception:
        return False
    if not hwnd:
        return False
    ok = apply_system_backdrop(hwnd, BACKDROP_MAIN_WINDOW)
    apply_window_corner(hwnd, DWMWCP_ROUND)
    apply_immersive_dark_mode(hwnd, dark)
    return ok


class WindowMover:
    """无边框窗口拖动支持：挂到标题栏 widget 上。"""

    def __init__(self, widget):
        self._widget = widget
        self._window = widget.window()
        self._drag_pos = None
        widget.mousePressEvent = self._on_press
        widget.mouseMoveEvent = self._on_move
        widget.mouseReleaseEvent = self._on_release

    def _on_press(self, event):
        from PySide6.QtCore import Qt
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()

    def _on_move(self, event):
        from PySide6.QtCore import Qt
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - self._drag_pos
            self._window.move(self._window.pos() + delta)
            self._drag_pos = event.globalPosition().toPoint()
        super(type(self._widget), self._widget).mouseMoveEvent(event)

    def _on_release(self, event):
        self._drag_pos = None
        super(type(self._widget), self._widget).mouseReleaseEvent(event)