"""统一日志：滚动文件 + 控制台。

错误类别由异常类型决定：
- UserError -> category=user
- DocumentFormatError -> category=format
- ExternalDependencyError -> category=dependency
- 其他 -> category=bug
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

_LOGGER: logging.Logger | None = None


def setup_logging(
    log_dir: Path | None = None, level: int = logging.INFO
) -> logging.Logger:
    global _LOGGER
    if _LOGGER is not None:
        return _LOGGER
    log_dir = log_dir or LOG_DIR
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("formora")
    logger.setLevel(level)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    # 滚动文件（保留 5 个 2MB 文件）
    fh = logging.handlers.RotatingFileHandler(
        log_dir / "formora.log", maxBytes=2_000_000, backupCount=5, encoding="utf-8"
    )
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # 控制台
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    _LOGGER = logger
    return logger


def get_logger() -> logging.Logger:
    return setup_logging()


def category_of(exc: BaseException) -> str:
    if isinstance(exc, UserError):
        return "user"
    if isinstance(exc, DocumentFormatError):
        return "format"
    if isinstance(exc, ExternalDependencyError):
        return "dependency"
    return "bug"
