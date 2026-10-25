"""ui.errors 统一异常出口的单元测试（不触发 Qt 弹窗）。"""

import logging
from unittest.mock import Mock

import pytest
from PySide6.QtWidgets import QMessageBox

from formora.core.errors import (
    BugError,
    DocumentFormatError,
    ExternalDependencyError,
    UserError,
)
from formora.ui.errors import (
    inline_message,
    is_expected,
    log_exception,
    show_error,
    show_warning,
    user_message,
)


def test_is_expected_for_expected():
    assert is_expected(UserError("文件不存在"))
    assert is_expected(DocumentFormatError("坏模板"))
    assert is_expected(ExternalDependencyError("LibreOffice 缺失"))


def test_is_expected_false_for_bug():
    assert not is_expected(BugError("未知缺陷"))


def test_is_expected_false_for_plain_exception():
    assert not is_expected(ValueError("普通异常"))


def test_user_message_returns_business_message():
    exc = UserError("文件不存在")
    assert user_message(exc, "兜底文案") == "文件不存在"


def test_user_message_returns_fallback_for_bug():
    exc = BugError("内部细节堆栈")
    assert user_message(exc, "发生意外错误。") == "发生意外错误。"


def test_inline_message_uses_user_message():
    exc = DocumentFormatError("模板损坏")
    assert inline_message(exc, "兜底") == "模板损坏"


@pytest.mark.parametrize(
    ("exc_type", "message"),
    [
        (RuntimeError, "内部细节"),
        (BugError, "未知缺陷"),
    ],
)
def test_log_exception_unexpected_logs_stack(caplog, exc_type, message):
    """非预期异常与 BugError 走 logger.exception，记录完整堆栈。"""
    with caplog.at_level(logging.ERROR, logger="formora.ui.errors"):
        try:
            raise exc_type(message)
        except Exception as exc:
            log_exception(exc)

    matching = [r for r in caplog.records if "未预期异常" in r.getMessage()]
    assert matching, "应记录「未预期异常」日志"
    assert message in caplog.text
    record = matching[0]
    assert record.exc_info is not None
    assert record.exc_info[0] is not None


@pytest.mark.parametrize(
    ("level", "method_name"),
    [
        ("warning", "warning"),
        ("information", "information"),
        ("critical", "critical"),
    ],
)
def test_show_error_levels(monkeypatch, level, method_name):
    """show_error 按 level 调用对应 QMessageBox 静态方法并返回用户文案。"""
    exc = UserError("文件不存在")
    fallback = "发生意外错误。"
    mock_box = Mock()
    monkeypatch.setattr(QMessageBox, method_name, mock_box)

    result = show_error(None, exc, fallback, level=level)

    assert result == "文件不存在"
    mock_box.assert_called_once_with(None, "操作失败", "文件不存在")


def test_show_warning_delegates(monkeypatch):
    """show_warning 透传给 show_error，并强制 level='warning'。"""
    exc = UserError("文件不存在")
    fallback = "发生意外错误。"
    mock_show_error = Mock(return_value="文件不存在")
    monkeypatch.setattr("formora.ui.errors.show_error", mock_show_error)

    result = show_warning(None, exc, fallback, title="自定义标题", prefix="PREFIX")

    assert result == "文件不存在"
    mock_show_error.assert_called_once_with(
        None,
        exc,
        fallback,
        title="自定义标题",
        level="warning",
        logger=None,
        prefix="PREFIX",
    )
