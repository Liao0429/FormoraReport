"""异常体系补充测试：层级关系与消息传递。"""

from __future__ import annotations

from formora.core.errors import (
    BugError,
    DocumentFormatError,
    ExternalDependencyError,
    FormoraError,
    UserError,
)


def test_hierarchy():
    """所有业务异常都应继承 FormoraError，且 FormoraError 继承 Exception。"""
    assert issubclass(FormoraError, Exception)
    assert issubclass(UserError, FormoraError)
    assert issubclass(DocumentFormatError, FormoraError)
    assert issubclass(ExternalDependencyError, FormoraError)
    assert issubclass(BugError, FormoraError)


def test_user_error_not_subclass_of_doc_format():
    """用户错误与文档格式错误应是平行分支，避免被误分类。"""
    assert not issubclass(UserError, DocumentFormatError)
    assert not issubclass(DocumentFormatError, UserError)


def test_str_contains_message():
    assert str(UserError("文件不存在")) == "文件不存在"
    assert str(DocumentFormatError("格式错误")) == "格式错误"
    assert str(ExternalDependencyError("依赖缺失")) == "依赖缺失"
    assert str(BugError("未知异常")) == "未知异常"
