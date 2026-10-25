"""异常分类：明确区分用户错误/文档格式错误/外部依赖错误/程序缺陷。"""


class FormoraError(Exception):
    """领域异常基类。"""

    @property
    def user_message(self) -> str:
        """给用户看的安全消息（默认等于 str(self)）。

        UI 层统一取此字段展示，避免把内部路径/调试细节暴露给用户；
        需要时子类可覆盖以提供更友好的文案。
        """
        return str(self)


class UserError(FormoraError):
    """用户输入错误：文件不存在、格式不支持、必填缺失等。"""


class DocumentFormatError(FormoraError):
    """文档格式错误：DOCX损坏、CSV乱码、模板无占位符等。"""


class ExternalDependencyError(FormoraError):
    """外部依赖错误：LibreOffice缺失、OCR模型未安装、网络/AI 服务不可用等。"""


class BugError(FormoraError):
    """程序缺陷：未知异常（服务边界捕获非预期异常时包装为它）。

    注意：业务代码当前不直接抛出此异常，它是「预留的公开标记类型」——
    服务边界捕获非预期异常时用它包装，日志分类（logging_setup.category_of）
    以及测试（tests/test_errors.py、tests/test_logging_setup_extra.py）均引用
    它。请勿删除，避免破坏公共 API 与测试契约。
    """
