"""错误处理模块 - 统一异常管理、重试机制和优雅降级"""

from __future__ import annotations

import functools
import re
import shutil
import subprocess
import time
from collections import defaultdict
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypeVar

T = TypeVar("T")


# =============================================================================
# 异常层次结构
# =============================================================================


class PSiteDLError(Exception):
    """PSiteDL 基础异常类"""

    pass


class ConfigError(PSiteDLError):
    """配置错误"""

    pass


class NetworkError(PSiteDLError):
    """网络错误基类"""

    pass


class NetworkTimeoutError(NetworkError):
    """网络超时错误"""

    pass


class DNSResolutionError(NetworkError):
    """DNS 解析失败"""

    pass


class ConnectionResetNetworkError(NetworkError):
    """连接重置错误"""

    pass


class PageParseError(PSiteDLError):
    """页面解析错误"""

    pass


class DownloadError(PSiteDLError):
    """下载错误基类"""

    pass


class DownloadFailedError(DownloadError):
    """下载失败"""

    pass


class PartialDownloadError(DownloadError):
    """部分下载（未完成）"""

    pass


class CookieError(PSiteDLError):
    """Cookie 相关错误"""

    pass


class RetryExhaustedError(PSiteDLError):
    """重试用尽后抛出的异常"""

    def __init__(
        self,
        message: str = "Max retries exceeded",
        last_error: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.last_error = last_error


# =============================================================================
# 重试装饰器
# =============================================================================


def retry_on_error(
    max_retries: int = 3,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    delay: float = 1.0,
    backoff: float = 2.0,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    重试装饰器

    Args:
        max_retries: 最大重试次数
        exceptions: 需要重试的异常类型元组
        delay: 初始延迟（秒）
        backoff: 退避倍数

    Returns:
        装饰器函数

    Example:
        @retry_on_error(max_retries=3, exceptions=(ValueError,))
        def risky_operation():
            ...
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            current_delay = delay
            last_exception: Exception | None = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        raise RetryExhaustedError(
                            f"Max retries ({max_retries}) exceeded for {func.__name__}",
                            last_error=e,
                        ) from e
                except Exception:
                    # 不在重试范围内的异常直接抛出
                    raise

            # 理论上不会到这里，但为了类型安全
            raise RetryExhaustedError(
                f"Max retries ({max_retries}) exceeded for {func.__name__}",
                last_error=last_exception,
            )

        return wrapper

    return decorator


# =============================================================================
# 网络错误处理上下文管理器
# =============================================================================


@contextmanager
def handle_network_error(timeout: int = 30) -> Iterator[None]:
    """
    网络错误处理上下文管理器

    捕获底层网络异常并转换为 PSiteDL 业务异常

    Args:
        timeout: 超时时间（秒）

    Yields:
        None

    Raises:
        NetworkTimeoutError: 超时
        DNSResolutionError: DNS 失败
        ConnectionResetNetworkError: 连接重置

    Example:
        with handle_network_error(timeout=30):
            response = requests.get(url, timeout=timeout)
    """
    try:
        yield
    except TimeoutError as e:
        raise NetworkTimeoutError(f"Connection timed out after {timeout}s") from e
    except OSError as e:
        error_msg = str(e).lower()
        if "name or service not known" in error_msg or "nodename nor servname" in error_msg:
            raise DNSResolutionError("Failed to resolve hostname") from e
        elif "connection reset" in error_msg or "broken pipe" in error_msg:
            raise ConnectionResetNetworkError("Connection was reset") from e
        else:
            raise NetworkError(f"Network error: {e}") from e
    except ConnectionResetError as e:
        raise ConnectionResetNetworkError("Connection reset by peer") from e


# =============================================================================
# 安全提取函数
# =============================================================================


def safe_extract_videos(
    html: str,
    base_url: str,
    patterns: list[re.Pattern] | None = None,
) -> list[str]:
    """
    安全提取视频 URL

    从 HTML 中提取视频候选 URL，失败时返回空列表而非抛出异常

    Args:
        html: HTML 内容
        base_url: 基础 URL（用于解析相对路径）
        patterns: 正则模式列表（可选，使用默认模式）

    Returns:
        视频 URL 列表（可能为空）

    Example:
        candidates = safe_extract_videos(html_content, "https://example.com")
    """
    if patterns is None:
        patterns = [
            re.compile(r'<video[^>]*\ssrc=["\']([^"\']+)["\']'),
            re.compile(r'<source[^>]*\ssrc=["\']([^"\']+)["\']'),
            re.compile(r'["\']([^"\']*\.m3u8)["\']'),
            re.compile(r'["\']([^"\']*\.mp4)["\']'),
            re.compile(r'["\']([^"\']*\.webm)["\']'),
            re.compile(r'["\']([^"\']*\.mkv)["\']'),
        ]

    video_urls: set[str] = set()

    try:
        for pattern in patterns:
            matches = pattern.findall(html)
            for match in matches:
                url = match.strip()
                # 解析相对路径
                if url.startswith("//"):
                    url = "https:" + url
                elif url.startswith("/"):
                    from urllib.parse import urljoin

                    url = urljoin(base_url, url)
                elif not url.startswith(("http://", "https://")):
                    from urllib.parse import urljoin

                    url = urljoin(base_url, url)

                if url:
                    video_urls.add(url)

    except Exception:
        # 解析失败时返回空列表
        return []

    return list(video_urls)


# =============================================================================
# Cookie 导出
# =============================================================================


def safe_export_cookies(
    browser: str = "chrome",
    profile: str = "Default",
    logger_func: Any = None,
) -> Path | None:
    """
    安全导出 Cookie

    调用 yt-dlp 的 Cookie 导出功能，浏览器不可用时返回 None

    Args:
        browser: 浏览器类型 (chrome, firefox, edge, safari)
        profile: 配置文件名
        logger_func: 日志记录函数（可选）

    Returns:
        Cookie 文件路径，失败时返回 None

    Example:
        cookie_file = safe_export_cookies("chrome", "Default")
        if cookie_file:
            # 使用 Cookie 下载
            ...
    """
    try:
        # 检查 yt-dlp 是否可用
        if not shutil.which("yt-dlp"):
            if logger_func:
                logger_func("yt-dlp not found, cannot export cookies")
            return None

        # 创建临时文件
        import tempfile

        temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
        cookie_file = Path(temp_file.name)
        temp_file.close()

        # 构建 yt-dlp 命令导出 Cookie
        cmd = [
            "yt-dlp",
            "--cookies-from-browser",
            f"{browser}:{profile}",
            "--cookies",
            str(cookie_file),
            "--skip-download",
            "https://example.com",  # 需要一个 URL，但不下载
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0 and cookie_file.exists():
            return cookie_file
        else:
            # 导出失败，清理临时文件
            if cookie_file.exists():
                cookie_file.unlink()
            if logger_func:
                logger_func(f"Failed to export cookies: {result.stderr}")
            return None

    except subprocess.TimeoutExpired:
        if logger_func:
            logger_func("Cookie export timed out")
        return None
    except Exception as e:
        if logger_func:
            logger_func(f"Error exporting cookies: {e}")
        return None


# =============================================================================
# 错误处理器
# =============================================================================


@dataclass
class ErrorRecord:
    """错误记录"""

    error_code: str
    error_type: str
    error_message: str
    context: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class ErrorHandler:
    """错误处理器

    集中记录所有错误，支持错误统计和分析
    """

    def __init__(
        self,
        log_file: str | None = None,
        max_history: int = 1000,
    ) -> None:
        """
        初始化错误处理器

        Args:
            log_file: 错误日志文件路径（可选）
            max_history: 最大错误历史记录数
        """
        self.log_file = Path(log_file) if log_file else None
        self.max_history = max_history
        self._errors: list[ErrorRecord] = []
        self._error_counts: dict[str, int] = defaultdict(int)

    def log_error(
        self,
        error_code: str,
        error: Exception,
        context: dict[str, Any] | None = None,
    ) -> None:
        """
        记录错误

        Args:
            error_code: 错误代码
            error: 异常对象
            context: 额外上下文信息
        """
        record = ErrorRecord(
            error_code=error_code,
            error_type=type(error).__name__,
            error_message=str(error),
            context=context or {},
        )

        self._errors.append(record)
        self._error_counts[error_code] += 1

        # 限制历史记录数量
        if len(self._errors) > self.max_history:
            self._errors = self._errors[-self.max_history :]

        # 写入日志文件
        if self.log_file:
            self._write_to_log(record)

    def _write_to_log(self, record: ErrorRecord) -> None:
        """写入错误到日志文件"""
        if not self.log_file:
            return
        try:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_file, "a", encoding="utf-8") as f:
                import json

                log_entry = {
                    "timestamp": record.timestamp,
                    "error_code": record.error_code,
                    "error_type": record.error_type,
                    "error_message": record.error_message,
                    "context": record.context,
                }
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception:
            # 日志写入失败时不抛出异常
            pass

    def get_error_stats(self) -> dict[str, int]:
        """
        获取错误统计

        Returns:
            错误代码计数字典
        """
        return dict(self._error_counts)

    def clear_history(self) -> None:
        """清除错误历史"""
        self._errors.clear()
        self._error_counts.clear()


# =============================================================================
# 恢复建议
# =============================================================================

# 错误代码到恢复建议的映射
RECOVERY_SUGGESTIONS: dict[str, str] = {
    "timeout": "请检查网络连接，或尝试增加超时时间配置",
    "dns_failure": "请检查 DNS 设置，或尝试更换 DNS 服务器",
    "connection_reset": "服务器可能过载，请稍后重试或检查防火墙设置",
    "download_failed": "请检查 URL 是否有效，或尝试使用 Cookie 认证",
    "parse_error": "页面结构可能已变更，请更新提取规则",
    "cookie_error": "请确保浏览器已关闭，或尝试手动导出 Cookie",
    "config_error": "请检查配置文件格式是否正确",
    "network_error": "请检查网络连接状态",
}


def get_recovery_suggestion(error_code: str) -> str:
    """
    获取恢复建议

    Args:
        error_code: 错误代码

    Returns:
        恢复建议文本

    Example:
        suggestion = get_recovery_suggestion("timeout")
        print(f"建议：{suggestion}")
    """
    # 标准化错误代码
    normalized_code = error_code.lower().replace("-", "_").replace(" ", "_")

    # 查找匹配的建议
    for code, suggestion in RECOVERY_SUGGESTIONS.items():
        if code in normalized_code or normalized_code in code:
            return suggestion

    # 默认建议
    return "请检查网络配置或查看日志获取更多信息"
