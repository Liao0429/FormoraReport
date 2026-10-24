"""主窗口：无边框 + 自定义标题栏 + 液态玻璃侧边栏导航 + 页面栈。

- 无边框窗口：FramelessWindowHint + 自定义标题栏（拖动 / 最小化 / 最大化 / 关闭）
- 系统 Mica 背景：show 后尝试启用，失败自动降级为 QSS 渐变背景
- 页面切换：淡入动画（animations.page_transition）
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from formora.ui.animations import fade_in, page_transition
from formora.ui.app_state import AppState
from formora.ui.pages.generate_page import GeneratePage
from formora.ui.pages.home_page import HomePage
from formora.ui.pages.import_page import ImportPage
from formora.ui.pages.mapping_page import MappingPage
from formora.ui.pages.preview_page import PreviewPage
from formora.ui.pages.settings_page import SettingsPage
from formora.ui.theme import apply_theme
from formora.ui.window_effects import WindowMover, setup_glass_window

NAV = [
    ("home", "🏠 首页"),
    ("import", "📥 文档导入"),
    ("mapping", "🔗 字段映射"),
    ("generate", "⚙️ 报告生成"),
    ("preview", "👁 结果预览"),
    ("settings", "🛠 设置"),
]


class MainWindow(QMainWindow):
    def __init__(self, state: AppState):
        super().__init__()
        self.state = state
        self.setWindowTitle("FormoraReport — 实验报告自动填写")
        self.resize(1080, 720)
        self.setMinimumSize(900, 600)
        self._mica_ok = False
        self._build()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)

    def _build(self):
        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # 自定义标题栏
        self._build_titlebar(outer)

        # 主体：侧边栏 + 页面栈
        body = QWidget()
        body_lay = QHBoxLayout(body)
        body_lay.setContentsMargins(12, 4, 12, 12)
        body_lay.setSpacing(12)
        outer.addWidget(body, 1)

        sidebar = _make_sidebar()
        self.sidebar = sidebar
        body_lay.addWidget(sidebar, 0)
        sidebar_lay = QVBoxLayout(sidebar)
        sidebar_lay.setContentsMargins(12, 16, 12, 16)
        sidebar_lay.setSpacing(6)

        app_title = QLabel("FormoraReport")
        app_title.setObjectName("AppTitle")
        sidebar_lay.addWidget(app_title)
        sub = QLabel("实验报告自动填写")
        sub.setObjectName("HintText")
        sidebar_lay.addWidget(sub)
        sidebar_lay.addSpacing(12)

        self.nav_buttons = {}
        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)
        for key, text in NAV:
            btn = QPushButton(text)
            btn.setObjectName("NavButton")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, k=key: self.navigate(k))
            self.nav_buttons[key] = btn
            self.btn_group.addButton(btn)
            sidebar_lay.addWidget(btn)
        sidebar_lay.addStretch(1)

        # 右侧页面栈
        self.stack = QStackedWidget()
        self.pages = {}
        self.pages["home"] = HomePage(self.state, self.navigate)
        self.pages["import"] = ImportPage(self.state, self.navigate)
        self.pages["mapping"] = MappingPage(self.state, self.navigate)
        self.pages["generate"] = GeneratePage(self.state, self.navigate)
        self.pages["preview"] = PreviewPage(self.state, self.navigate)
        self.pages["settings"] = SettingsPage(self.state, self._on_theme_change)
        for key, page in self.pages.items():
            self.stack.addWidget(page)
        body_lay.addWidget(self.stack, 1)

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("就绪 · 无 AI 模式（默认）")

        self.navigate("home")

    # ---------- 自定义标题栏 ----------

    def _build_titlebar(self, outer: QVBoxLayout):
        bar = QWidget()
        bar.setObjectName("TitleBar")
        bar.setFixedHeight(44)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(16, 0, 8, 0)
        lay.setSpacing(8)

        title = QLabel("FormoraReport")
        title.setObjectName("WindowTitle")
        lay.addWidget(title)
        lay.addStretch(1)

        # 拖动支持：挂到标题栏空白区域（用 bar 本身）
        WindowMover(bar)

        self.btn_min = _win_button("—", "WinButton")
        self.btn_max = _win_button("□", "WinButton")
        self.btn_close = _win_button("✕", "WinButton WinClose")
        self.btn_min.clicked.connect(self.showMinimized)
        self.btn_max.clicked.connect(self._toggle_maximize)
        self.btn_close.clicked.connect(self.close)
        lay.addWidget(self.btn_min)
        lay.addWidget(self.btn_max)
        lay.addWidget(self.btn_close)
        outer.addWidget(bar)

    def _toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
            self.btn_max.setText("□")
        else:
            self.showMaximized()
            self.btn_max.setText("❐")

    # ---------- 无边框窗口边缘缩放 ----------

    def nativeEvent(self, event_type, message):
        """处理 WM_NCHITTEST，支持无边框窗口 8 向边缘缩放。"""
        import ctypes
        import ctypes.wintypes
        try:
            msg = ctypes.wintypes.MSG.from_address(int(message))
            if msg.message == 0x0084:  # WM_NCHITTEST
                x = ctypes.c_short(msg.lParam & 0xFFFF).value
                y = ctypes.c_short((msg.lParam >> 16) & 0xFFFF).value
                rect = ctypes.wintypes.RECT()
                ctypes.windll.user32.GetWindowRect(int(self.winId()), ctypes.byref(rect))
                border = 6
                left = x < rect.left + border
                right = x > rect.right - border
                top = y < rect.top + border
                bottom = y > rect.bottom - border
                if top and left:
                    return (True, 0x000D)  # HTTOPLEFT
                if top and right:
                    return (True, 0x000E)  # HTTOPRIGHT
                if bottom and left:
                    return (True, 0x0010)  # HTBOTTOMLEFT
                if bottom and right:
                    return (True, 0x0011)  # HTBOTTOMRIGHT
                if left:
                    return (True, 0x000A)  # HTLEFT
                if right:
                    return (True, 0x000B)  # HTRIGHT
                if top:
                    return (True, 0x000C)  # HTTOP
                if bottom:
                    return (True, 0x000F)  # HTBOTTOM
        except Exception:
            pass
        return super().nativeEvent(event_type, message)

    # ---------- 系统玻璃 ----------

    def showEvent(self, event):
        super().showEvent(event)
        if not self._mica_ok:
            dark = self.state.config.get("theme", "light") == "dark"
            self._mica_ok = setup_glass_window(self, dark=dark)
            if self._mica_ok:
                # Mica 生效时让根背景透明，完全透出系统磨砂
                root = self.centralWidget()
                if root:
                    root.setStyleSheet("background: transparent;")
            fade_in(self, duration=220)

    # ---------- 导航与主题 ----------

    def navigate(self, key: str):
        if key not in self.pages:
            return
        page = self.pages[key]
        if self.stack.currentWidget() is not page:
            page_transition(self.stack, page)
        btn = self.nav_buttons.get(key)
        if btn:
            btn.setChecked(True)
        if hasattr(page, "refresh"):
            page.refresh()

    def _on_theme_change(self, name: str):
        apply_theme(self.window(), name)
        if self._mica_ok:
            from formora.ui.window_effects import apply_immersive_dark_mode
            try:
                apply_immersive_dark_mode(int(self.winId()), dark=(name == "dark"))
            except Exception:
                pass


def _win_button(text: str, object_name: str) -> QPushButton:
    btn = QPushButton(text)
    btn.setObjectName(object_name)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    # 无障碍：为读屏提供可朗读名称，并加 tooltip
    if object_name == "WinButton WinClose":
        btn.setAccessibleName("关闭")
        btn.setToolTip("关闭")
    elif text in ("—", "□", "❐", "✕"):
        if text == "—":
            btn.setAccessibleName("最小化")
            btn.setToolTip("最小化")
        elif text in ("□", "❐"):
            btn.setAccessibleName("最大化")
            btn.setToolTip("最大化")
    return btn


def _make_sidebar() -> QWidget:
    from PySide6.QtWidgets import QFrame
    f = QFrame()
    f.setObjectName("Sidebar")
    f.setFixedWidth(200)
    return f
