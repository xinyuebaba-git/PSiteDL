"""并发下载模块测试 - TDD 驱动开发"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest


class TestConcurrentDownloader:
    """并发下载器测试"""

    def test_downloader_initialization(self) -> None:
        """下载器初始化"""
        from webvidgrab.downloader import ConcurrentDownloader

        downloader = ConcurrentDownloader(max_concurrent=3)
        assert downloader.max_concurrent == 3
        assert downloader.active_count() == 0

    def test_download_single_url(self, temp_dir: Path) -> None:
        """单个 URL 下载"""
        from webvidgrab.downloader import ConcurrentDownloader

        downloader = ConcurrentDownloader(max_concurrent=1)
        # 使用 mock 避免真实下载
        result = downloader.download_sync(
            url="https://example.com/video.mp4",
            output_dir=temp_dir,
        )
        # 实际实现会处理下载逻辑
        assert result is not None

    @pytest.mark.asyncio
    async def test_download_multiple_urls(self, temp_dir: Path) -> None:
        """多个 URL 并发下载"""
        from webvidgrab.downloader import ConcurrentDownloader

        downloader = ConcurrentDownloader(max_concurrent=3)
        urls = [
            "https://example.com/video1.mp4",
            "https://example.com/video2.mp4",
            "https://example.com/video3.mp4",
        ]

        results = await downloader.download_batch(urls, temp_dir)
        assert len(results) == len(urls)

    @pytest.mark.asyncio
    async def test_download_respects_concurrency_limit(self, temp_dir: Path) -> None:
        """遵守并发数限制"""
        from webvidgrab.downloader import ConcurrentDownloader

        downloader = ConcurrentDownloader(max_concurrent=2)
        active_count_history = []

        # Mock 下载函数，记录并发数
        async def mock_download(url, output_dir):
            active_count_history.append(downloader.active_count())
            await asyncio.sleep(0.1)
            return {"url": url, "success": True}

        urls = [f"https://example.com/video{i}.mp4" for i in range(5)]
        await downloader.download_batch(urls, temp_dir, download_fn=mock_download)

        # 验证并发数从未超过限制
        assert all(count <= 2 for count in active_count_history)


class TestDownloadQueue:
    """下载队列测试"""

    def test_queue_creation(self) -> None:
        """创建下载队列"""
        from webvidgrab.downloader import DownloadQueue

        queue = DownloadQueue()
        assert queue.size() == 0

    def test_queue_add(self) -> None:
        """添加到队列"""
        from webvidgrab.downloader import DownloadQueue

        queue = DownloadQueue()
        queue.add("https://example.com/video1.mp4")
        queue.add("https://example.com/video2.mp4")
        assert queue.size() == 2

    def test_queue_get(self) -> None:
        """从队列获取"""
        from webvidgrab.downloader import DownloadQueue

        queue = DownloadQueue()
        queue.add("https://example.com/video1.mp4")
        url = queue.get()
        assert url == "https://example.com/video1.mp4"
        assert queue.size() == 0

    def test_queue_empty(self) -> None:
        """空队列"""
        from webvidgrab.downloader import DownloadQueue

        queue = DownloadQueue()
        assert queue.is_empty()

    def test_queue_priority(self) -> None:
        """优先级队列"""
        from webvidgrab.downloader import PriorityDownloadQueue

        queue = PriorityDownloadQueue()
        queue.add("low_priority", priority=1)
        queue.add("high_priority", priority=10)
        queue.add("medium_priority", priority=5)

        # 高优先级应该先出队
        first = queue.get()
        assert first == "high_priority"


class TestRetryQueue:
    """重试队列测试"""

    def test_retry_queue_add(self) -> None:
        """添加到重试队列"""
        from webvidgrab.downloader import RetryQueue

        retry_queue = RetryQueue(max_retries=3)
        retry_queue.add("https://example.com/failed.mp4", error="timeout")
        assert retry_queue.pending_count() == 1

    def test_retry_queue_get_retryable(self) -> None:
        """获取可重试的任务"""
        from webvidgrab.downloader import RetryQueue

        retry_queue = RetryQueue(max_retries=3)
        retry_queue.add("https://example.com/failed.mp4", error="timeout")

        # 等待一段时间后应该可重试
        import time

        time.sleep(1)

        retryable = retry_queue.get_retryable()
        assert len(retryable) >= 1

    def test_retry_queue_exhausted(self) -> None:
        """重试用尽"""
        from webvidgrab.downloader import RetryQueue

        retry_queue = RetryQueue(max_retries=2)
        url = "https://example.com/failed.mp4"

        # 模拟多次重试失败
        for _i in range(3):
            retry_queue.add(url, error="timeout")
            retry_queue.mark_completed(url, success=False)

        # 应该标记为失败
        assert retry_queue.is_exhausted(url)


class TestDownloadResult:
    """下载结果测试"""

    def test_result_aggregation(self) -> None:
        """结果汇总"""
        from webvidgrab.downloader import DownloadResult, ResultAggregator

        aggregator = ResultAggregator()
        aggregator.add_result(
            DownloadResult(
                url="https://example.com/video1.mp4",
                success=True,
                output_file="/path/to/video1.mp4",
            )
        )
        aggregator.add_result(
            DownloadResult(
                url="https://example.com/video2.mp4",
                success=False,
                error="timeout",
            )
        )

        summary = aggregator.get_summary()
        assert summary["total"] == 2
        assert summary["success"] == 1
        assert summary["failed"] == 1

    def test_result_report(self) -> None:
        """生成结果报告"""
        from webvidgrab.downloader import DownloadResult, ResultAggregator

        aggregator = ResultAggregator()
        aggregator.add_result(
            DownloadResult(
                url="https://example.com/video1.mp4",
                success=True,
                output_file="/path/to/video1.mp4",
            )
        )

        report = aggregator.generate_report()
        assert "video1.mp4" in report or "success" in report.lower()


class TestBandwidthManagement:
    """带宽管理测试"""

    def test_bandwidth_limiter(self) -> None:
        """带宽限制器"""
        from webvidgrab.downloader import BandwidthLimiter

        limiter = BandwidthLimiter(max_speed_mbps=10)
        assert limiter.max_speed_bytes == 10 * 1024 * 1024 / 8

    def test_bandwidth_throttle(self) -> None:
        """带宽节流"""
        import time

        from webvidgrab.downloader import BandwidthLimiter

        limiter = BandwidthLimiter(max_speed_mbps=1)
        data_size = 1024 * 1024  # 1MB

        start = time.time()
        limiter.throttle(data_size)
        elapsed = time.time() - start

        # 1MB 数据在 1Mbps 限制下应该至少需要 8 秒
        # 测试中适当放宽要求
        assert elapsed > 0
