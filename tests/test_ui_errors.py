"""ui.errors 统一异常出口的单元测试（不触发 Qt 弹窗）。"""

from formora.core.errors import BugError, DocumentFormatError, ExternalDependencyError, FormoraError, UserError
from formora.ui.errors import inline_message, is_expected, user_message


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
