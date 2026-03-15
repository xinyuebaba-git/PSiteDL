"""日志系统模块测试 - TDD 驱动开发"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest


class TestStructuredLogger:
    """结构化日志测试"""

    def test_create_logger(self) -> None:
        """创建日志记录器"""
        from webvidgrab.logging import create_logger

        logger = create_logger("test_logger", level="INFO")
        assert logger is not None
        assert logger.name == "test_logger"

    def test_logger_levels(self) -> None:
        """测试日志级别"""
        from webvidgrab.logging import create_logger

        logger = create_logger("test_levels", level="DEBUG")
        assert logger.level == logging.DEBUG

        logger_debug = create_logger("test_debug", level="DEBUG")
        logger_info = create_logger("test_info", level="INFO")
        logger_warning = create_logger("test_warning", level="WARNING")
        logger_error = create_logger("test_error", level="ERROR")

        assert logger_debug.level < logger_info.level < logger_warning.level < logger_error.level

    def test_json_log_format(self, temp_dir: Path) -> None:
        """测试 JSON 格式日志输出"""
        from webvidgrab.logging import create_logger

        log_file = temp_dir / "test.json.log"
        logger = create_logger(
            "test_json",
            level="INFO",
            log_file=str(log_file),
            json_format=True,
        )

        logger.info("Test message", extra={"user": "test", "action": "download"})
        assert log_file.exists()

        # 验证 JSON 格式
        import json

        with open(log_file, encoding="utf-8") as f:
            log_entry = json.loads(f.readline())
        assert "message" in log_entry or "event" in log_entry
        assert "timestamp" in log_entry


class TestLogFileRotation:
    """日志文件轮转测试"""

    def test_rotate_by_size(self, temp_dir: Path) -> None:
        """按大小轮转日志文件"""
        from webvidgrab.logging import create_logger_with_rotation

        log_file = temp_dir / "rotating.log"
        logger = create_logger_with_rotation(
            "test_rotate",
            log_file=str(log_file),
            max_bytes=1024,  # 1KB
            backup_count=3,
        )

        # 写入足够日志触发轮转
        for i in range(100):
            logger.info(f"Log message {i} with some extra text to increase size")

        # 检查是否生成了轮转文件
        log_files = list(temp_dir.glob("rotating.log*"))
        assert len(log_files) >= 1

    def test_rotate_by_date(self, temp_dir: Path) -> None:
        """按日期轮转日志文件"""
        from webvidgrab.logging import create_date_logger

        log_dir = temp_dir / "logs"
        logger = create_date_logger(
            "test_date",
            log_dir=str(log_dir),
            format="%Y-%m-%d",
        )

        logger.info("Test message")
        assert log_dir.exists()


class TestAuditLogging:
    """审计日志测试"""

    def test_audit_critical_operations(self, temp_dir: Path) -> None:
        """记录关键操作的审计日志"""
        from webvidgrab.logging import create_audit_logger

        audit_file = temp_dir / "audit.log"
        logger = create_audit_logger(str(audit_file))

        logger.audit("download_started", user="test", url="https://example.com")
        logger.audit("download_completed", user="test", file="video.mp4")

        content = audit_file.read_text(encoding="utf-8")
        assert "download_started" in content
        assert "download_completed" in content

    def test_audit_log_immutable(self, temp_dir: Path) -> None:
        """审计日志应追加写入，不覆盖"""
        from webvidgrab.logging import create_audit_logger

        audit_file = temp_dir / "audit.log"
        logger = create_audit_logger(str(audit_file))

        logger.audit("event1")
        logger.audit("event2")

        lines = audit_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) >= 2
        assert "event1" in lines[0]
        assert "event2" in lines[1]


class TestLogContext:
    """日志上下文测试"""

    def test_context_manager(self) -> None:
        """日志上下文管理器"""
        from webvidgrab.logging import create_logger, log_context

        logger = create_logger("test_context", level="INFO")

        with log_context(logger, operation="test_operation"):
            logger.info("Inside context")

        # 上下文应自动记录开始和结束

    def test_context_with_error(self) -> None:
        """错误时记录上下文"""
        from webvidgrab.logging import create_logger, log_context

        logger = create_logger("test_error_context", level="INFO")

        with pytest.raises(ValueError):
            with log_context(logger, operation="failing_operation"):
                raise ValueError("Test error")


class TestPerformanceLogging:
    """性能日志测试"""

    def test_log_execution_time(self) -> None:
        """记录函数执行时间"""
        from webvidgrab.logging import create_logger, log_execution_time

        logger = create_logger("test_perf", level="INFO")

        @log_execution_time(logger, "slow_function")
        def slow_function():
            import time

            time.sleep(0.1)
            return "done"

        result = slow_function()
        assert result == "done"

    def test_log_slow_operations(self, temp_dir: Path) -> None:
        """记录慢操作警告"""
        from webvidgrab.logging import create_logger, log_if_slow

        log_file = temp_dir / "slow.log"
        logger = create_logger("test_slow", level="WARNING", log_file=str(log_file))

        @log_if_slow(logger, threshold=0.05)
        def slow_op():
            import time

            time.sleep(0.1)

        slow_op()
        # 日志文件中应有慢操作警告
        assert "slow" in log_file.read_text(encoding="utf-8").lower()
