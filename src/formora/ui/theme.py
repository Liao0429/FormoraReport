"""主题：浅色/深色，iOS 液态玻璃（Liquid Glass）风格。

设计要点（借鉴 iOS 26 液态玻璃与开源 Qt 玻璃拟态项目）：
- 半透明卡片 + 1px 白色高光描边（模拟玻璃边缘反光）
- 大圆角（16-22px）、柔和阴影（widgets.Card 提供）
- 主按钮使用蓝紫渐变 + 高光边，悬停轻微提亮，按下下沉
- 侧边栏为独立浮动玻璃面板
- 根背景半透明（配合 window_effects 的 Mica 系统背景；无 Mica 时叠加浅色渐变）
- 窗口为无边框时由 main_window 提供自定义标题栏
"""

from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

# ---------- 颜色 token（浅色） ----------
_L_BG = "rgba(244,247,253,0.55)"
_L_CARD = "rgba(255,255,255,0.45)"
_L_CARD_BORDER = "rgba(255,255,255,0.65)"
_L_SIDEBAR = "rgba(255,255,255,0.35)"
_L_TEXT = "#1c2430"
_L_TEXT_SUB = "#5a6a7c"
_L_TEXT_HINT = "#7a8a9c"
_L_INPUT = "rgba(255,255,255,0.55)"
_L_ACCENT = "#4a7cf7"
_L_ACCENT_TOP = "#5b8aff"
_L_ACCENT_BOTTOM = "#3d6de8"

# ---------- 颜色 token（深色） ----------
_D_BG = "rgba(18,20,30,0.62)"
_D_CARD = "rgba(38,42,58,0.5)"
_D_CARD_BORDER = "rgba(255,255,255,0.14)"
_D_SIDEBAR = "rgba(30,34,48,0.45)"
_D_TEXT = "#e6eaf2"
_D_TEXT_SUB = "#aab6c8"
_D_TEXT_HINT = "#8a96a8"
_D_INPUT = "rgba(255,255,255,0.08)"
_D_ACCENT = "#4a7cf7"
_D_ACCENT_TOP = "#5b8aff"
_D_ACCENT_BOTTOM = "#3d6de8"


def _light_qss() -> str:
    return f"""
QMainWindow, QWidget#Root {{
    background: {_L_BG};
    color: {_L_TEXT};
}}
QWidget {{ font-family: "Microsoft YaHei UI"; font-size: 13px; }}
QFrame#Sidebar {{
    background: {_L_SIDEBAR};
    border: 1px solid {_L_CARD_BORDER};
    border-radius: 20px;
}}
QLabel#AppTitle {{ font-size: 17px; font-weight: 700; color: {_L_TEXT}; }}
QLabel#WindowTitle {{ font-size: 13px; font-weight: 600; color: {_L_TEXT_SUB}; }}
QPushButton#NavButton {{
    background: transparent; border: none; border-radius: 11px;
    padding: 10px 14px; text-align: left; color: {_L_TEXT_SUB}; font-size: 14px;
}}
QPushButton#NavButton:hover {{ background: rgba(255,255,255,0.6); color: {_L_TEXT}; }}
QPushButton#NavButton:checked {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {_L_ACCENT_TOP}, stop:1 {_L_ACCENT_BOTTOM});
    color: white; font-weight: 600;
    border: 1px solid rgba(255,255,255,0.35);
}}
QFrame#Card {{
    background: {_L_CARD};
    border: 1px solid {_L_CARD_BORDER};
    border-radius: 20px;
}}
QLabel#CardTitle {{ font-size: 15px; font-weight: 600; color: {_L_TEXT}; }}
QPushButton#PrimaryButton {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {_L_ACCENT_TOP}, stop:1 {_L_ACCENT_BOTTOM});
    color: white; border: 1px solid rgba(255,255,255,0.35);
    border-radius: 12px; padding: 9px 18px; font-size: 13px; font-weight: 600;
}}
QPushButton#PrimaryButton:hover {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
    stop:0 #6a95ff, stop:1 #4a74f0); }}
QPushButton#PrimaryButton:pressed {{ background: {_L_ACCENT_BOTTOM}; }}
QPushButton#SecondaryButton {{
    background: rgba(255,255,255,0.55); color: {_L_TEXT};
    border: 1px solid rgba(255,255,255,0.8);
    border-radius: 12px; padding: 8px 16px;
}}
QPushButton#SecondaryButton:hover {{ background: rgba(255,255,255,0.85); }}
QPushButton#SecondaryButton:pressed {{ background: rgba(255,255,255,0.95); }}
QPushButton#WinButton {{
    background: transparent; border: none; border-radius: 8px;
    font-size: 14px; color: {_L_TEXT_SUB}; min-width: 40px; max-width: 40px;
    padding: 6px 0;
}}
QPushButton#WinButton:hover {{ background: rgba(0,0,0,0.08); }}
QPushButton#WinButton#WinClose:hover {{ background: #e81123; color: white; }}
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox {{
    background: {_L_INPUT}; border: 1px solid rgba(210,218,230,0.9);
    border-radius: 12px; padding: 7px 10px; color: {_L_TEXT};
    selection-background-color: {_L_ACCENT}; selection-color: white;
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {{
    border: 1px solid {_L_ACCENT};
    background: rgba(255,255,255,0.75);
}}
QTableWidget {{
    background: rgba(255,255,255,0.4); border: 1px solid rgba(210,218,230,0.7);
    border-radius: 14px; gridline-color: rgba(210,218,230,0.5);
}}
QHeaderView::section {{
    background: rgba(255,255,255,0.65); color: {_L_TEXT_SUB};
    border: none; border-bottom: 1px solid rgba(210,218,230,0.8); padding: 8px;
}}
QTableWidget::item:selected {{ background: rgba(74,124,247,0.25); color: {_L_TEXT}; }}
QListWidget {{
    background: rgba(255,255,255,0.45); border: 1px solid rgba(210,218,230,0.7);
    border-radius: 14px;
}}
QListWidget::item {{ padding: 8px; border-radius: 8px; }}
QListWidget::item:selected {{ background: rgba(74,124,247,0.25); }}
QScrollBar:vertical {{ background: transparent; width: 10px; }}
QScrollBar::handle:vertical {{ background: rgba(0,0,0,0.15); border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: rgba(0,0,0,0.28); }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QStatusBar {{ background: transparent; color: {_L_TEXT_HINT}; }}
QLabel#LogText {{ color: {_L_TEXT_SUB}; }}
QLabel#HintText {{ color: {_L_TEXT_HINT}; font-size: 12px; }}
QMessageBox {{ background: #f5f7fb; }}
"""


def _dark_qss() -> str:
    return f"""
QMainWindow, QWidget#Root {{
    background: {_D_BG};
    color: {_D_TEXT};
}}
QWidget {{ font-family: "Microsoft YaHei UI"; font-size: 13px; }}
QFrame#Sidebar {{
    background: {_D_SIDEBAR};
    border: 1px solid {_D_CARD_BORDER};
    border-radius: 20px;
}}
QLabel#AppTitle {{ font-size: 17px; font-weight: 700; color: {_D_TEXT}; }}
QLabel#WindowTitle {{ font-size: 13px; font-weight: 600; color: {_D_TEXT_SUB}; }}
QPushButton#NavButton {{
    background: transparent; border: none; border-radius: 11px;
    padding: 10px 14px; text-align: left; color: {_D_TEXT_SUB}; font-size: 14px;
}}
QPushButton#NavButton:hover {{ background: rgba(255,255,255,0.08); color: {_D_TEXT}; }}
QPushButton#NavButton:checked {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {_D_ACCENT_TOP}, stop:1 {_D_ACCENT_BOTTOM});
    color: white; font-weight: 600;
    border: 1px solid rgba(255,255,255,0.3);
}}
QFrame#Card {{
    background: {_D_CARD};
    border: 1px solid {_D_CARD_BORDER};
    border-radius: 20px;
}}
QLabel#CardTitle {{ font-size: 15px; font-weight: 600; color: {_D_TEXT}; }}
QPushButton#PrimaryButton {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {_D_ACCENT_TOP}, stop:1 {_D_ACCENT_BOTTOM});
    color: white; border: 1px solid rgba(255,255,255,0.3);
    border-radius: 12px; padding: 9px 18px; font-size: 13px; font-weight: 600;
}}
QPushButton#PrimaryButton:hover {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
    stop:0 #6a95ff, stop:1 #4a74f0); }}
QPushButton#PrimaryButton:pressed {{ background: {_D_ACCENT_BOTTOM}; }}
QPushButton#SecondaryButton {{
    background: rgba(255,255,255,0.08); color: {_D_TEXT};
    border: 1px solid rgba(255,255,255,0.16);
    border-radius: 12px; padding: 8px 16px;
}}
QPushButton#SecondaryButton:hover {{ background: rgba(255,255,255,0.16); }}
QPushButton#SecondaryButton:pressed {{ background: rgba(255,255,255,0.22); }}
QPushButton#WinButton {{
    background: transparent; border: none; border-radius: 8px;
    font-size: 14px; color: {_D_TEXT_SUB}; min-width: 40px; max-width: 40px;
    padding: 6px 0;
}}
QPushButton#WinButton:hover {{ background: rgba(255,255,255,0.12); }}
QPushButton#WinButton#WinClose:hover {{ background: #e81123; color: white; }}
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox {{
    background: {_D_INPUT}; border: 1px solid rgba(255,255,255,0.14);
    border-radius: 12px; padding: 7px 10px; color: {_D_TEXT};
    selection-background-color: {_D_ACCENT}; selection-color: white;
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {{
    border: 1px solid {_D_ACCENT};
    background: rgba(255,255,255,0.12);
}}
QTableWidget {{
    background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);
    border-radius: 14px; gridline-color: rgba(255,255,255,0.08);
}}
QHeaderView::section {{
    background: rgba(255,255,255,0.08); color: {_D_TEXT_SUB};
    border: none; border-bottom: 1px solid rgba(255,255,255,0.12); padding: 8px;
}}
QTableWidget::item {{ color: {_D_TEXT}; }}
QTableWidget::item:selected {{ background: rgba(74,124,247,0.3); color: white; }}
QListWidget {{
    background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);
    border-radius: 14px; color: {_D_TEXT};
}}
QListWidget::item {{ padding: 8px; border-radius: 8px; }}
QListWidget::item:selected {{ background: rgba(74,124,247,0.3); }}
QScrollBar:vertical {{ background: transparent; width: 10px; }}
QScrollBar::handle:vertical {{ background: rgba(255,255,255,0.18); border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: rgba(255,255,255,0.32); }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QStatusBar {{ background: transparent; color: {_D_TEXT_HINT}; }}
QLabel#LogText {{ color: {_D_TEXT_SUB}; }}
QLabel#HintText {{ color: {_D_TEXT_HINT}; font-size: 12px; }}
QMessageBox {{ background: #1a1d28; }}
"""


def apply_theme(app: QApplication, name: str = "light"):
    """应用全局主题。app 可为 QApplication 或任意顶层窗口。"""
    app.setStyleSheet(_light_qss() if name == "light" else _dark_qss())
    font = QFont("Microsoft YaHei UI", 10)
    app.setFont(font)
