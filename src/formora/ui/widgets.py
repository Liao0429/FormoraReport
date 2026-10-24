"""可复用 UI 组件：卡片、按钮、标题、文件选择行。"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class Card(QFrame):
    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(18, 16, 18, 16)
        self.layout.setSpacing(10)
        if title:
            self.title_label = QLabel(title)
            self.title_label.setObjectName("CardTitle")
            self.layout.addWidget(self.title_label)
        # 柔和阴影
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 28))
        self.setGraphicsEffect(shadow)

    def add_widget(self, w: QWidget):
        self.layout.addWidget(w)

    def add_layout(self, layout):
        self.layout.addLayout(layout)


def primary_button(text: str, parent=None) -> QPushButton:
    btn = QPushButton(text, parent)
    btn.setObjectName("PrimaryButton")
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    return btn


def secondary_button(text: str, parent=None) -> QPushButton:
    btn = QPushButton(text, parent)
    btn.setObjectName("SecondaryButton")
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    return btn


def hint_label(text: str, parent=None) -> QLabel:
    lbl = QLabel(text, parent)
    lbl.setObjectName("HintText")
    lbl.setWordWrap(True)
    return lbl


def file_row(label_text: str, edit_widget: QWidget, button: QPushButton) -> QWidget:
    row = QWidget()
    lay = QHBoxLayout(row)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(8)
    lbl = QLabel(label_text)
    lbl.setFixedWidth(90)
    lay.addWidget(lbl)
    lay.addWidget(edit_widget, 1)
    lay.addWidget(button)
    return row


def card(title: str) -> Card:
    return Card(title)