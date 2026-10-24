"""异常分类：明确区分用户错误/文档格式错误/外部依赖错误/程序缺陷。"""


class FormoraError(Exception):
    """基类。"""


class UserError(FormoraError):
    """用户输入错误：文件不存在、格式不支持、必填缺失等。"""


class DocumentFormatError(FormoraError):
    """文档格式错误：DOCX损坏、CSV乱码、模板无占位符等。"""


class ExternalDependencyError(FormoraError):
    """外部依赖错误：LibreOffice缺失、OCR模型未安装等。"""


class BugError(FormoraError):
    """程序缺陷：未知异常。"""