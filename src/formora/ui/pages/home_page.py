"""首页：新建任务 + 最近任务。"""
from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QVBoxLayout, QWidget

from formora.services.history import load_history
from formora.ui.widgets import Card, primary_button, secondary_button


class HomePage(QWidget):
    def __init__(self, state, navigate):
        super().__init__()
        self.state = state
        self.navigate = navigate
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)

        title = QLabel("FormoraReport")
        title.setObjectName("AppTitle")
        lay.addWidget(title)
        sub = QLabel("Windows 实验报告自动填写工具 · 无 AI 模式为默认")
        sub.setObjectName("HintText")
        lay.addWidget(sub)

        # 快捷操作
        actions = Card("快速开始")
        row = QHBoxLayout()
        new_btn = primary_button("＋ 新建任务")
        new_btn.clicked.connect(lambda: self.navigate("import"))
        template_btn = secondary_button("导入模板")
        template_btn.clicked.connect(lambda: self.navigate("import"))
        row.addWidget(new_btn)
        row.addWidget(template_btn)
        row.addStretch(1)
        actions.add_layout(row)
        lay.addWidget(actions)

        # 最近任务
        recent = Card("最近任务")
        self.list_widget = QListWidget()
        recent.add_widget(self.list_widget)
        lay.addWidget(recent, 1)

        self.refresh()

    def refresh(self):
        self.list_widget.clear()
        entries = load_history(limit=10)
        if not entries:
            self.list_widget.addItem("暂无历史记录，点击「新建任务」开始。")
            return
        for e in entries:
            name = e.get("name", "未命名任务")
            status = e.get("status", "")
            out = e.get("output_path") or ""
            self.list_widget.addItem(f"{name}  [{status}]  {out}")