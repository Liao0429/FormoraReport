"""轻量动画工具测试：减少动态效果开关下的降级行为。"""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QStackedWidget, QWidget

from formora.ui import animations


@pytest.fixture
def reduce_motion():
    """开启减少动态效果，测试结束后复位。"""
    animations.set_reduce_motion(True)
    yield
    animations.set_reduce_motion(False)


@pytest.fixture
def normal_motion():
    animations.set_reduce_motion(False)
    yield
    animations.set_reduce_motion(False)


class TestSetReduceMotion:
    def test_toggle(self, normal_motion):
        animations.set_reduce_motion(True)
        assert animations._REDUCE_MOTION is True
        animations.set_reduce_motion(False)
        assert animations._REDUCE_MOTION is False


class TestFadeInReduced:
    def test_returns_none_and_clears_effect(self, qapp, reduce_motion):
        w = QWidget()
        assert animations.fade_in(w) is None


class TestFadeOutReduced:
    def test_calls_callback_immediately(self, qapp, reduce_motion):
        called = []
        w = QWidget()
        animations.fade_out_then(w, on_finished=lambda: called.append(1))
        assert called == [1]


class TestPageTransitionReduced:
    def test_sets_current_widget(self, qapp, reduce_motion):
        stack = QStackedWidget()
        page1 = QWidget()
        page2 = QWidget()
        stack.addWidget(page1)
        stack.addWidget(page2)
        result = animations.page_transition(stack, page2)
        assert result is None
        assert stack.currentWidget() is page2
