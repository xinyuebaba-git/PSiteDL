"""错误处理模块测试 - TDD 驱动开发"""

from __future__ import annotations

from unittest.mock import patch

import pytest


class TestRetryDecorator:
    """重试装饰器测试"""

    def test_retry_on_success(self) -> None:
        """成功时不重试"""
        from webvidgrab.errors import retry_on_error

        call_count = 0

        @retry_on_error(max_retries=3, exceptions=(ValueError,))
        def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_func()
        assert result == "success"
        assert call_count == 1

    def test_retry_on_failure(self) -> None:
        """失败时重试"""
        from webvidgrab.errors import retry_on_error

        call_count = 0

        @retry_on_error(max_retries=3, exceptions=(ValueError,))
        def failing_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "success"

        result = failing_then_success()
        assert result == "success"
        assert call_count == 3

    def test_retry_exhausted(self) -> None:
        """重试用尽后抛出异常"""
        from webvidgrab.errors import RetryExhaustedError, retry_on_error

        @retry_on_error(max_retries=2, exceptions=(ValueError,))
        def always_fails():
            raise ValueError("Always fails")

        with pytest.raises(RetryExhaustedError):
            always_fails()

    def test_retry_only_specified_exceptions(self) -> None:
        """只重试指定的异常类型"""
        from webvidgrab.errors import retry_on_error

        call_count = 0

        @retry_on_error(max_retries=3, exceptions=(ValueError,))
        def wrong_exception():
            nonlocal call_count
            call_count += 1
            raise TypeError("Wrong type")

        with pytest.raises(TypeError):
            wrong_exception()
        assert call_count == 1  # 不重试


class TestNetworkErrorHandling:
    """网络错误处理测试"""

    def test_handle_timeout(self) -> None:
        """处理超时错误"""
        from webvidgrab.errors import NetworkTimeoutError, handle_network_error

        with pytest.raises(NetworkTimeoutError):
            with handle_network_error(timeout=30):
                raise TimeoutError("Connection timed out")

    def test_handle_dns_failure(self) -> None:
        """处理 DNS 失败"""
        from webvidgrab.errors import DNSResolutionError, handle_network_error

        with pytest.raises(DNSResolutionError):
            with handle_network_error():
                raise OSError("Name or service not known")

    def test_handle_connection_reset(self) -> None:
        """处理连接重置"""
        from webvidgrab.errors import ConnectionResetNetworkError, handle_network_error

        with pytest.raises(ConnectionResetNetworkError):
            with handle_network_error():
                raise ConnectionResetError("Connection reset by peer")


class TestPageParseErrorHandling:
    """页面解析错误处理测试"""

    def test_extract_video_candidates_fallback(self) -> None:
        """视频候选提取失败时的降级策略"""
        from webvidgrab.errors import safe_extract_videos

        # 无效 HTML
        invalid_html = "<html><body>Invalid</body></html>"
        candidates = safe_extract_videos(invalid_html, "https://example.com")
        assert candidates == []  # 返回空列表而不是抛出异常

    def test_extract_with_multiple_patterns(self) -> None:
        """使用多个正则模式提取"""
        from webvidgrab.errors import safe_extract_videos

        html = """
        <video src="https://example.com/video.mp4"></video>
        <source src="https://example.com/stream.m3u8">
        """
        candidates = safe_extract_videos(html, "https://example.com")
        assert len(candidates) >= 1
        assert any(".mp4" in url or ".m3u8" in url for url in candidates)


class TestCookieExportErrorHandling:
    """Cookie 导出错误处理测试"""

    def test_cookie_export_failure_graceful(self) -> None:
        """Cookie 导出失败时优雅降级"""
        from webvidgrab.errors import safe_export_cookies

        # 模拟浏览器不可用
        with patch("shutil.which", return_value=None):
            cookie_file = safe_export_cookies("chrome", "Default", lambda x: None)
            assert cookie_file is None  # 返回 None 而不是抛出异常

    def test_cookie_export_success(self, temp_dir) -> None:
        """Cookie 导出成功"""

        # 这个测试需要真实的 yt-dlp 环境，暂时跳过
        pytest.skip("Requires yt-dlp installation")


class TestErrorHandler:
    """错误处理器测试"""

    def test_log_error_with_context(self, temp_dir, caplog) -> None:
        """记录带上下文的错误"""
        from webvidgrab.errors import ErrorHandler

        handler = ErrorHandler(log_file=str(temp_dir / "errors.log"))
        handler.log_error(
            "download_failed",
            error=ValueError("Test error"),
            context={"url": "https://example.com", "user": "test"},
        )

        assert "download_failed" in caplog.text or (temp_dir / "errors.log").exists()

    def test_error_statistics(self) -> None:
        """错误统计"""
        from webvidgrab.errors import ErrorHandler

        handler = ErrorHandler()
        handler.log_error("error1", error=ValueError("e1"))
        handler.log_error("error2", error=ValueError("e2"))
        handler.log_error("error1", error=ValueError("e1"))

        stats = handler.get_error_stats()
        assert "error1" in stats
        assert stats["error1"] == 2

    def test_error_recovery_suggestion(self) -> None:
        """错误恢复建议"""
        from webvidgrab.errors import get_recovery_suggestion

        suggestion = get_recovery_suggestion("timeout")
        assert suggestion is not None
        assert len(suggestion) > 0
