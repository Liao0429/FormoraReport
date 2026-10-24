"""轻量动画工具：页面淡入、按钮反馈、卡片悬浮。

所有动画基于 QPropertyAnimation，时长短（150-220ms），
并尊重系统「减少动态效果」设置（QApplication.styleHints().showShortcutContext() 不适用，
改用 QGuiApplication.styleHints().setFocusScrollAnimationsEnabled 无关；这里用静态开关）。
"""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QTimer

# 全局开关：系统启用「减少动态效果」时关闭动画
_REDUCE_MOTION = False


def set_reduce_motion(enabled: bool):
    global _REDUCE_MOTION
    _REDUCE_MOTION = enabled


def fade_in(widget, duration: int = 200, delay: int = 0):
    """让 widget 淡入（从透明到不透明）。返回动画对象（需保持引用）。"""
    from PySide6.QtWidgets import QGraphicsOpacityEffect

    if _REDUCE_MOTION:
        widget.setGraphicsEffect(None)
        return None
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)
    effect.setOpacity(0.0)
    anim = QPropertyAnimation(effect, b"opacity", widget)
    anim.setDuration(duration)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    if delay:
        QTimer.singleShot(delay, anim.start)
    else:
        anim.start()
    # 动画结束后移除 effect，避免影响后续渲染
    anim.finished.connect(lambda: widget.setGraphicsEffect(None))
    return anim


def fade_out_then(widget, duration: int = 150, on_finished=None):
    """淡出 widget，结束后回调（用于页面切换）。"""
    from PySide6.QtWidgets import QGraphicsOpacityEffect

    if _REDUCE_MOTION:
        if on_finished:
            on_finished()
        return None
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)
    effect.setOpacity(1.0)
    anim = QPropertyAnimation(effect, b"opacity", widget)
    anim.setDuration(duration)
    anim.setStartValue(1.0)
    anim.setEndValue(0.0)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    anim.finished.connect(
        lambda: (widget.setGraphicsEffect(None), on_finished() if on_finished else None)
    )
    anim.start()
    return anim


def page_transition(stack, new_page, duration: int = 180):
    """QStackedWidget 页面切换：新页淡入。"""
    if _REDUCE_MOTION:
        stack.setCurrentWidget(new_page)
        return None
    from PySide6.QtWidgets import QGraphicsOpacityEffect

    effect = QGraphicsOpacityEffect(new_page)
    new_page.setGraphicsEffect(effect)
    effect.setOpacity(0.0)
    stack.setCurrentWidget(new_page)
    anim = QPropertyAnimation(effect, b"opacity", new_page)
    anim.setDuration(duration)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    anim.finished.connect(lambda: new_page.setGraphicsEffect(None))
    anim.start()
    return anim
