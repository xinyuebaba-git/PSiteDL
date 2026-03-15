"""日志系统模块 - 提供结构化日志、轮转和审计功能。

本模块提供完整的日志管理功能，支持：
- 多种日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- 结构化日志输出 (JSON 格式)
- 日志文件轮转 (按大小、按日期)
- 审计日志 (关键操作追踪)
- 日志上下文管理器
- 性能监控装饰器

典型用法:
    >>> from webvidgrab.logging import create_logger, log_context
    >>>
    >>> # 创建日志器
    >>> logger = create_logger("myapp", level="INFO")
    >>>
    >>> # 记录日志
    >>> logger.info("Application started")
    >>>
    >>> # 使用上下文管理器
    >>> with log_context(logger, "download", url="https://example.com"):
    ...     download_video()
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable, Generator
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import wraps
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from typing import Any

__all__ = [
    "create_logger",
    "create_logger_with_rotation",
    "create_date_logger",
    "create_audit_logger",
    "AuditLogger",
    "log_context",
    "log_execution_time",
    "log_if_slow",
]


# =============================================================================
# 日志格式化器
# =============================================================================


class StructuredFormatter(logging.Formatter):
    """结构化日志格式化器 (JSON 格式)。

    将日志记录转换为 JSON 格式，便于机器解析和日志分析系统处理。

    Attributes:
        json_format: 是否输出 JSON 格式
    """

    def __init__(self, json_format: bool = True) -> None:
        """初始化格式化器。

        Args:
            json_format: True 输出 JSON 格式，False 输出人类可读格式
        """
        super().__init__()
        self.json_format = json_format

        # 人类可读格式模板
        self.human_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录。

        Args:
            record: 日志记录对象

        Returns:
            格式化后的日志字符串
        """
        if self.json_format:
            return self._format_json(record)
        else:
            # 使用标准格式
            formatter = logging.Formatter(self.human_format)
            return formatter.format(record)

    def _format_json(self, record: logging.LogRecord) -> str:
        """将日志记录格式化为 JSON。

        Args:
            record: 日志记录对象

        Returns:
            JSON 格式的日志字符串
        """
        log_entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # 添加额外上下文
        if hasattr(record, "context") and record.context:
            log_entry["context"] = record.context

        # 添加位置信息 (仅 DEBUG 级别)
        if record.levelno <= logging.DEBUG:
            log_entry["location"] = {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            }

        return json.dumps(log_entry, ensure_ascii=False)


# =============================================================================
# 公共 API - 日志器工厂
# =============================================================================


def create_logger(
    name: str,
    level: str = "INFO",
    log_file: str | None = None,
    json_format: bool = False,
) -> logging.Logger:
    """创建日志记录器。

    创建一个配置好的 Logger 实例，支持控制台和文件输出。

    Args:
        name: 日志器名称 (通常使用模块名 __name__)
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 日志文件路径 (可选，不提供则仅输出到控制台)
        json_format: 是否使用 JSON 格式输出

    Returns:
        配置好的 Logger 实例

    Example:
        >>> logger = create_logger("myapp", level="DEBUG")
        >>> logger.info("Hello, World!")
    """
    # 创建 logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # 避免重复添加 handler
    if logger.handlers:
        return logger

    # 创建格式化器
    formatter = StructuredFormatter(json_format=json_format)

    # 控制台 handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, level.upper()))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件 handler (如果指定)
    if log_file:
        # 确保目录存在
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(getattr(logging, level.upper()))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def create_logger_with_rotation(
    name: str,
    log_file: str,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    level: str = "INFO",
    json_format: bool = False,
) -> logging.Logger:
    """创建带大小轮转的日志记录器。

    当日志文件达到指定大小时自动轮转，保留指定数量的备份文件。

    Args:
        name: 日志器名称
        log_file: 日志文件路径
        max_bytes: 单文件最大字节数 (默认 10MB)
        backup_count: 备份文件数量 (默认 5 个)
        level: 日志级别
        json_format: 是否使用 JSON 格式

    Returns:
        配置好的 Logger 实例

    Example:
        >>> logger = create_logger_with_rotation(
        ...     "myapp",
        ...     "logs/app.log",
        ...     max_bytes=5*1024*1024,  # 5MB
        ...     backup_count=3
        ... )
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    if logger.handlers:
        return logger

    formatter = StructuredFormatter(json_format=json_format)

    # 确保目录存在
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # 轮转文件 handler
    handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setLevel(getattr(logging, level.upper()))
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


def create_date_logger(
    name: str,
    log_dir: str,
    format: str = "%Y-%m-%d",
    level: str = "INFO",
    json_format: bool = False,
) -> logging.Logger:
    """创建按日期轮转的日志记录器。

    每天创建一个新的日志文件，文件名为 {log_dir}/{name}.{date}.log。

    Args:
        name: 日志器名称
        log_dir: 日志目录路径
        format: 日期格式字符串 (默认 "%Y-%m-%d")
        level: 日志级别
        json_format: 是否使用 JSON 格式

    Returns:
        配置好的 Logger 实例

    Example:
        >>> logger = create_date_logger(
        ...     "myapp",
        ...     "logs/",
        ...     format="%Y-%m-%d"
        ... )
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    if logger.handlers:
        return logger

    formatter = StructuredFormatter(json_format=json_format)

    # 确保目录存在
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # 日期轮转 handler
    log_file = log_path / f"{name}.log"
    handler = TimedRotatingFileHandler(
        log_file,
        when="D",  # 每天轮转
        interval=1,
        backupCount=30,  # 保留 30 天
        encoding="utf-8",
    )
    handler.suffix = format  # 日期后缀格式
    handler.setLevel(getattr(logging, level.upper()))
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


# =============================================================================
# 审计日志
# =============================================================================


class AuditLogger:
    """审计日志记录器。

    专门用于记录关键操作的审计日志，如下载开始/结束、配置变更等。
    审计日志只追加写入，保证不可篡改性。

    Attributes:
        audit_file: 审计日志文件路径

    Example:
        >>> audit = AuditLogger("logs/audit.log")
        >>> audit.audit("download_started", user="admin", url="https://example.com")
    """

    def __init__(self, audit_file: str) -> None:
        """初始化审计日志记录器。

        Args:
            audit_file: 审计日志文件路径
        """
        self.audit_file = Path(audit_file)
        # 确保目录存在
        self.audit_file.parent.mkdir(parents=True, exist_ok=True)

    def audit(self, operation: str, **context: Any) -> None:
        """记录审计日志。

        将关键操作记录到审计日志文件，格式为 JSON。

        Args:
            operation: 操作类型 (如 "download_started", "config_changed")
            **context: 额外的上下文信息 (将作为 JSON 字段)

        Example:
            >>> audit.audit(
            ...     "download_completed",
            ...     user="admin",
            ...     file="video.mp4",
            ...     size=1024000
            ... )
        """
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operation": operation,
            **context,
        }

        # 追加写入 (保证不可篡改)
        with open(self.audit_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def create_audit_logger(audit_file: str) -> AuditLogger:
    """创建审计日志记录器。

    工厂函数，用于创建 AuditLogger 实例。

    Args:
        audit_file: 审计日志文件路径

    Returns:
        AuditLogger 实例

    Example:
        >>> audit = create_audit_logger("logs/audit.log")
        >>> audit.audit("download_started", user="admin")
    """
    return AuditLogger(audit_file)


# =============================================================================
# 日志上下文管理器
# =============================================================================


@contextmanager
def log_context(
    logger: logging.Logger, operation: str, **context: Any
) -> Generator[None, None, None]:
    """日志上下文管理器。

    自动记录操作的开始和结束 (或错误)，并提供执行时间。

    Args:
        logger: 日志记录器
        operation: 操作名称
        **context: 上下文信息

    Yields:
        None (在 with 块中执行操作)

    Raises:
        Exception: 重新抛出 with 块中的异常，但会先记录错误日志

    Example:
        >>> with log_context(logger, "download", url=url):
        ...     download_video(url)
    """
    start_time = time.time()

    # 记录开始
    logger.info(
        f"{operation} started",
        extra={"context": {"operation": operation, **context}},
    )

    try:
        yield
        # 记录成功结束
        elapsed = time.time() - start_time
        logger.info(
            f"{operation} completed",
            extra={"context": {"operation": operation, "elapsed_ms": elapsed * 1000, **context}},
        )
    except Exception as e:
        # 记录错误
        elapsed = time.time() - start_time
        logger.error(
            f"{operation} failed",
            extra={
                "context": {
                    "operation": operation,
                    "elapsed_ms": elapsed * 1000,
                    "error": str(e),
                    **context,
                }
            },
        )
        raise


# =============================================================================
# 性能监控装饰器
# =============================================================================


def log_execution_time(logger: logging.Logger, operation: str) -> Callable:
    """记录函数执行时间的装饰器。

    自动记录被装饰函数的执行时间。

    Args:
        logger: 日志记录器
        operation: 操作名称

    Returns:
        装饰器函数

    Example:
        >>> @log_execution_time(logger, "heavy_computation")
        ... def heavy_function():
        ...     time.sleep(1)
        ...     return result
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                logger.debug(
                    f"{operation} completed in {elapsed:.3f}s",
                    extra={"context": {"operation": operation, "elapsed_ms": elapsed * 1000}},
                )
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(
                    f"{operation} failed after {elapsed:.3f}s: {e}",
                    extra={
                        "context": {
                            "operation": operation,
                            "elapsed_ms": elapsed * 1000,
                            "error": str(e),
                        }
                    },
                )
                raise

        return wrapper

    return decorator


def log_if_slow(logger: logging.Logger, threshold: float = 1.0) -> Callable:
    """记录慢操作的装饰器。

    仅当函数执行时间超过阈值时才记录警告日志。

    Args:
        logger: 日志记录器
        threshold: 慢操作阈值 (秒，默认 1.0 秒)

    Returns:
        装饰器函数

    Example:
        >>> @log_if_slow(logger, threshold=0.5)
        ... def potentially_slow_operation():
        ...     # 如果执行超过 0.5 秒，会记录警告
        ...     pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time

                if elapsed > threshold:
                    logger.warning(
                        f"{func.__name__} was slow: {elapsed:.3f}s (threshold: {threshold}s)",
                        extra={
                            "context": {
                                "operation": func.__name__,
                                "elapsed_ms": elapsed * 1000,
                                "threshold_ms": threshold * 1000,
                            }
                        },
                    )
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(
                    f"{func.__name__} failed after {elapsed:.3f}s: {e}",
                    extra={
                        "context": {
                            "operation": func.__name__,
                            "elapsed_ms": elapsed * 1000,
                            "error": str(e),
                        }
                    },
                )
                raise

        return wrapper

    return decorator
