"""统一日志：滚动文件 + 控制台。

错误类别由异常类型决定：
- UserError -> category=user
- DocumentFormatError -> category=format
- ExternalDependencyError -> category=dependency
- 其他 -> category=bug

接入位置：
- GUI 入口 main.py 通过 ``formora.ui.app.run()`` 启动，run() 已调用
  ``setup_logging()`` 完成初始化；
- API 入口 api_server.py 应在 ``uvicorn.run(...)`` 之前调用一次
  ``get_logger()``（或 ``setup_logging()``）；
- 其它模块需要写日志时，统一使用 ``get_logger()`` 获取全局 logger。
"""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

from formora.core.errors import (
    DocumentFormatError,
    ExternalDependencyError,
    UserError,
)
from formora.services.config import LOG_DIR

__all__ = ["category_of", "get_logger", "setup_logging"]

_LOGGER: logging.Logger | None = None

# 滚动文件配置：单个文件最大 2MB，保留 5 个备份，UTF-8 编码
_LOG_FILE_NAME = "formora.log"
_MAX_BYTES = 2_000_000
_BACKUP_COUNT = 5
_ENCODING = "utf-8"


def category_of(exc: BaseException) -> str:
    """按异常类型返回日志分类：user / format / dependency / bug。"""
    if isinstance(exc, UserError):
        return "user"
    if isinstance(exc, DocumentFormatError):
        return "format"
    if isinstance(exc, ExternalDependencyError):
        return "dependency"
    return "bug"


class _CategoryFilter(logging.Filter):
    """为带异常的日志记录附加 category 属性（由 category_of 分类）。

    这样错误分类逻辑会真实作用于每条带堆栈的日志记录，
    便于日志消费端按 user/format/dependency/bug 过滤或统计。
    """

    def filter(self, record: logging.LogRecord) -> bool:
        exc_info = getattr(record, "exc_info", None)
        exc = exc_info[1] if isinstance(exc_info, tuple) and len(exc_info) > 1 else None
        record.category = category_of(exc) if isinstance(exc, BaseException) else ""
        return True


def _build_logger(log_dir: Path, level: int) -> logging.Logger:
    """创建并配置全局 "formora" logger（不更新 _LOGGER 缓存）。"""
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("formora")
    # 统一日志模块持有该 logger：先清掉旧 handler，避免重复初始化叠加重复输出
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()

    logger.setLevel(level)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    # 滚动文件（保留 5 个 2MB 文件，UTF-8 编码）
    fh = logging.handlers.RotatingFileHandler(
        log_dir / _LOG_FILE_NAME,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding=_ENCODING,
    )
    fh.setFormatter(fmt)
    fh.addFilter(_CategoryFilter())
    logger.addHandler(fh)

    # 控制台
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    ch.addFilter(_CategoryFilter())
    logger.addHandler(ch)

    return logger


def setup_logging(
    log_dir: Path | None = None, level: int = logging.INFO
) -> logging.Logger:
    """初始化日志并返回全局 logger（单例）。

    项目入口（GUI：main.py -> formora.ui.app.run；API：api_server.py）
    调用本函数完成显式初始化；重复调用只返回同一个 logger。
    """
    global _LOGGER
    if _LOGGER is None:
        _LOGGER = _build_logger(log_dir or LOG_DIR, level)
    return get_logger()


def get_logger() -> logging.Logger:
    """全局日志入口：首次调用自动完成初始化，之后返回同一 logger。

    任何模块需要写日志时都通过它获取已配置的 "formora" logger。
    """
    global _LOGGER
    if _LOGGER is None:
        _LOGGER = _build_logger(LOG_DIR, logging.INFO)
    return _LOGGER
