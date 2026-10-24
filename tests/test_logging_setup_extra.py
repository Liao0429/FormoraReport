"""日志基础设施补充测试：文件创建、单例、错误分类边界。"""
from __future__ import annotations

from formora.core.errors import BugError, FormoraError
from formora.services import logging_setup
from formora.services.logging_setup import category_of, setup_logging


class TestSetupLogging:
    def test_creates_log_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(logging_setup, "_LOGGER", None)
        log_dir = tmp_path / "logs"
        logger = setup_logging(log_dir=log_dir)
        assert (log_dir / "formora.log").exists()
        assert logger.name == "formora"

    def test_singleton(self, tmp_path, monkeypatch):
        monkeypatch.setattr(logging_setup, "_LOGGER", None)
        log_dir = tmp_path / "logs"
        logger1 = setup_logging(log_dir=log_dir)
        logger2 = setup_logging(log_dir=log_dir)
        assert logger1 is logger2

    def test_get_logger_returns_configured(self, tmp_path, monkeypatch):
        monkeypatch.setattr(logging_setup, "_LOGGER", None)
        log_dir = tmp_path / "logs"
        setup_logging(log_dir=log_dir)
        assert logging_setup.get_logger().name == "formora"


class TestCategoryOfExtra:
    def test_formora_error_base_is_bug(self):
        assert category_of(FormoraError("x")) == "bug"

    def test_bug_error_is_bug(self):
        assert category_of(BugError("x")) == "bug"

    def test_subclass_of_user_error(self):
        """只有继承 UserError 的子类才算 user 分类。"""
        from formora.core.errors import UserError

        class RealUserError(UserError):
            pass
        assert category_of(RealUserError("x")) == "user"
