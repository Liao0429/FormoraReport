"""UI 层异常统一出口。

把「选文案 + 记日志 + 弹窗」收敛到这一个模块，各页面不再各自写
QMessageBox / logger 样板。

文案规则（与 core/errors.py 的 user_message 契约一致）：
- 预期业务异常（UserError / DocumentFormatError / ExternalDependencyError，
  以及其它非 BugError 的 FormoraError）：弹窗显示 exc.user_message，
  日志按 category_of 分类记录，不刷堆栈；
- 未知异常 / BugError（程序缺陷）：弹窗显示 fallback，
  logger.exception 记录完整堆栈，避免把内部路径/堆栈泄露给用户。
"""

from __future__ import annotations

import logging

from PySide6.QtWidgets import QMessageBox, QWidget

from formora.core.errors import BugError, FormoraError

_LOGGER = logging.getLogger(__name__)


def is_expected(exc: BaseException) -> bool:
    """是否属于「预期内的业务异常」。

    BugError 虽继承 FormoraError，但它标记程序缺陷，应走 fallback + 完整堆栈。
    """
    return isinstance(exc, FormoraError) and not isinstance(exc, BugError)


def user_message(exc: BaseException, fallback: str) -> str:
    """把异常转成安全、对用户友好的文案。"""
    if is_expected(exc):
        return exc.user_message
    return fallback


def log_exception(
    exc: BaseException,
    *,
    logger: logging.Logger | None = None,
    prefix: str = "",
) -> str:
    """按异常类型记录日志（不弹窗），返回供内联展示的安全文案。"""
    log = logger or _LOGGER
    msg = user_message(exc, "发生意外错误。")
    tag = f"{prefix} " if prefix else ""
    if is_expected(exc):
        log.error("%s业务错误: %s", tag, msg)
    else:
        log.exception("%s未预期异常: %s", tag, exc)
    return msg


def show_error(
    parent: QWidget | None,
    exc: BaseException,
    fallback: str,
    *,
    title: str = "操作失败",
    level: str = "critical",
    logger: logging.Logger | None = None,
    prefix: str = "",
) -> str:
    """统一异常出口：记日志 + 弹窗，返回展示给用户的文案。"""
    msg = log_exception(exc, logger=logger, prefix=prefix)
    if level == "warning":
        QMessageBox.warning(parent, title, msg)
    elif level == "information":
        QMessageBox.information(parent, title, msg)
    else:
        QMessageBox.critical(parent, title, msg)
    return msg


def show_warning(
    parent: QWidget | None,
    exc: BaseException,
    fallback: str,
    *,
    title: str = "操作失败",
    logger: logging.Logger | None = None,
    prefix: str = "",
) -> str:
    """warning 级别的便捷封装。"""
    return show_error(
        parent,
        exc,
        fallback,
        title=title,
        level="warning",
        logger=logger,
        prefix=prefix,
    )


def inline_message(exc: BaseException, fallback: str) -> str:
    """内联展示（issues_text / text_edit / 状态栏）用：只取安全文案，不弹窗。"""
    return user_message(exc, fallback)
