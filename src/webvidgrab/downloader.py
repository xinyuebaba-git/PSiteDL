"""并发下载模块 - PSiteDL Phase 4

核心组件:
- ConcurrentDownloader: 并发下载器
- DownloadQueue: 下载队列管理
- RetryQueue: 重试队列
- BandwidthLimiter: 带宽限制器
- ResultAggregator: 结果汇总器
"""

from __future__ import annotations

import asyncio
import heapq
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

# =============================================================================
# 数据结构
# =============================================================================


@dataclass
class DownloadResult:
    """下载结果"""

    url: str
    success: bool
    output_file: Path | None = None
    error: str | None = None
    file_size: int = 0
    duration: float = 0.0
    retries: int = 0


@dataclass
class RetryTask:
    """重试任务"""

    url: str
    error: str
    attempts: int
    max_retries: int
    next_retry_at: float  # 时间戳
    output_dir: Path | None = None


# =============================================================================
# 协议定义
# =============================================================================


class DownloadCallable(Protocol):
    """下载函数协议"""

    async def __call__(self, url: str, output_dir: Path) -> DownloadResult: ...


# =============================================================================
# 下载队列
# =============================================================================


class DownloadQueue:
    """下载队列管理"""

    def __init__(self) -> None:
        self._queue: list[str] = []

    def size(self) -> int:
        """返回队列大小"""
        return len(self._queue)

    def add(self, url: str, priority: int = 0) -> None:
        """添加到队列"""
        self._queue.append(url)

    def get(self) -> str | None:
        """从队列获取"""
        if self._queue:
            return self._queue.pop(0)
        return None

    def is_empty(self) -> bool:
        """检查是否为空"""
        return len(self._queue) == 0

    def clear(self) -> None:
        """清空队列"""
        self._queue.clear()


class PriorityDownloadQueue:
    """优先级下载队列"""

    def __init__(self) -> None:
        self._heap: list[tuple[int, int, str]] = []  # (priority, counter, url)
        self._counter = 0

    def size(self) -> int:
        """返回队列大小"""
        return len(self._heap)

    def add(self, url: str, priority: int = 0) -> None:
        """添加到队列，优先级越高越先出队"""
        # 使用负数实现最大堆（高优先级先出）
        heapq.heappush(self._heap, (-priority, self._counter, url))
        self._counter += 1

    def get(self) -> str | None:
        """从队列获取（最高优先级）"""
        if self._heap:
            _, _, url = heapq.heappop(self._heap)
            return url
        return None

    def is_empty(self) -> bool:
        """检查是否为空"""
        return len(self._heap) == 0

    def clear(self) -> None:
        """清空队列"""
        self._heap.clear()


# =============================================================================
# 重试队列
# =============================================================================


class RetryQueue:
    """重试队列管理"""

    def __init__(self, max_retries: int = 3, base_delay: float = 1.0) -> None:
        self.max_retries = max_retries
        self.base_delay = base_delay
        self._pending: dict[str, RetryTask] = {}
        self._failed: dict[str, RetryTask] = {}

    def add(self, url: str, error: str, output_dir: Path | None = None) -> None:
        """添加到重试队列"""
        if url in self._pending:
            task = self._pending[url]
            task.attempts += 1
            task.error = error
        else:
            task = RetryTask(
                url=url,
                error=error,
                attempts=1,
                max_retries=self.max_retries,
                next_retry_at=time.time() + self.base_delay,
                output_dir=output_dir,
            )

        if task.attempts <= task.max_retries:
            # 计算指数退避延迟
            delay = self.base_delay * (2 ** (task.attempts - 1))
            task.next_retry_at = time.time() + delay
            self._pending[url] = task
        else:
            # 重试用尽，移到失败队列
            self._failed[url] = task
            if url in self._pending:
                del self._pending[url]

    def get_retryable(self) -> list[RetryTask]:
        """获取当前可重试的任务"""
        now = time.time()
        retryable = []
        for _url, task in list(self._pending.items()):
            if now >= task.next_retry_at:
                retryable.append(task)
        return retryable

    def mark_completed(self, url: str, success: bool) -> None:
        """标记任务完成"""
        if success:
            if url in self._pending:
                del self._pending[url]
            if url in self._failed:
                del self._failed[url]
        else:
            # 失败，已经在 add 中处理
            pass

    def is_exhausted(self, url: str) -> bool:
        """检查是否重试用尽"""
        return url in self._failed

    def pending_count(self) -> int:
        """返回待重试任务数"""
        return len(self._pending)

    def failed_count(self) -> int:
        """返回失败任务数"""
        return len(self._failed)


# =============================================================================
# 带宽限制器
# =============================================================================


class BandwidthLimiter:
    """带宽限制器（令牌桶算法）"""

    def __init__(self, max_speed_mbps: float = 0) -> None:
        """
        初始化带宽限制器

        Args:
            max_speed_mbps: 最大速度 (Mbps), 0 表示无限制
        """
        self.max_speed_mbps = max_speed_mbps
        # 转换为字节/秒
        self.max_speed_bytes = (max_speed_mbps * 1024 * 1024) / 8 if max_speed_mbps > 0 else 0
        self._last_time = time.time()
        self._tokens = 0.0

    def throttle(self, bytes_to_download: int) -> None:
        """
        节流，根据数据量计算需要等待的时间

        Args:
            bytes_to_download: 要下载的数据量（字节）
        """
        if self.max_speed_bytes <= 0:
            return

        # 计算需要等待的时间
        wait_time = bytes_to_download / self.max_speed_bytes
        if wait_time > 0:
            time.sleep(wait_time)

    def throttle_async(self, bytes_to_download: int) -> float:
        """
        异步节流（用于测试）

        Args:
            bytes_to_download: 要下载的数据量（字节）

        Returns:
            等待时间（秒）
        """
        if self.max_speed_bytes <= 0:
            return 0.0

        wait_time = bytes_to_download / self.max_speed_bytes
        return wait_time

    async def acquire(self, bytes_count: int) -> float:
        """
        异步获取下载许可

        Args:
            bytes_count: 要下载的字节数

        Returns:
            需要等待的时间（秒）
        """
        if self.max_speed_bytes <= 0:
            return 0.0

        now = time.time()
        elapsed = now - self._last_time

        # 补充令牌
        self._tokens += elapsed * self.max_speed_bytes
        self._tokens = min(self._tokens, self.max_speed_bytes)  # 限制桶容量

        # 计算等待时间
        if bytes_count > self._tokens:
            wait_time = (bytes_count - self._tokens) / self.max_speed_bytes
            self._tokens = 0
        else:
            self._tokens -= bytes_count
            wait_time = 0

        self._last_time = time.time()

        if wait_time > 0:
            await asyncio.sleep(wait_time)

        return wait_time


# =============================================================================
# 结果汇总器
# =============================================================================


class ResultAggregator:
    """下载结果汇总器"""

    def __init__(self) -> None:
        self._results: list[DownloadResult] = []
        self._success_count = 0
        self._failed_count = 0
        self._total_bytes = 0
        self._total_duration = 0.0

    def add_result(self, result: DownloadResult) -> None:
        """添加下载结果"""
        self._results.append(result)
        if result.success:
            self._success_count += 1
            self._total_bytes += result.file_size
        else:
            self._failed_count += 1
        self._total_duration += result.duration

    def get_summary(self) -> dict[str, Any]:
        """获取汇总统计"""
        total = len(self._results)
        success_rate = (self._success_count / total * 100) if total > 0 else 0
        avg_speed = (self._total_bytes / self._total_duration) if self._total_duration > 0 else 0

        return {
            "total": total,
            "success": self._success_count,
            "failed": self._failed_count,
            "success_rate": success_rate,
            "total_bytes": self._total_bytes,
            "total_duration": self._total_duration,
            "avg_speed": avg_speed,
        }

    def generate_report(self) -> str:
        """生成文本报告"""
        summary = self.get_summary()

        lines = [
            "下载完成报告",
            "============",
            f"总计：{summary['total']} 个 URL",
            f"成功：{summary['success']} 个 ({summary['success_rate']:.1f}%)",
            f"失败：{summary['failed']} 个 ({100 - summary['success_rate']:.1f}%)",
            f"总大小：{self._format_size(summary['total_bytes'])}",
            f"总耗时：{self._format_duration(summary['total_duration'])}",
            f"平均速度：{self._format_size(summary['avg_speed'])}/s",
            "",
            f"success: {summary['success']}",
        ]

        # 添加失败任务详情
        failed_results = [r for r in self._results if not r.success]
        if failed_results:
            lines.append("失败任务:")
            for result in failed_results:
                lines.append(f"  - {result.url} ({result.error})")

        return "\n".join(lines)

    def get_failed_urls(self) -> list[str]:
        """获取失败的 URL 列表"""
        return [r.url for r in self._results if not r.success]

    def get_success_results(self) -> list[DownloadResult]:
        """获取成功的结果列表"""
        return [r for r in self._results if r.success]

    @staticmethod
    def _format_size(size_bytes: float) -> str:
        """格式化文件大小"""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} PB"

    @staticmethod
    def _format_duration(seconds: float) -> str:
        """格式化时长"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}m"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}h"


# =============================================================================
# 并发下载器
# =============================================================================


class ConcurrentDownloader:
    """并发下载器"""

    def __init__(self, max_concurrent: int = 5) -> None:
        """
        初始化并发下载器

        Args:
            max_concurrent: 最大并发下载数
        """
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._active_tasks: set[asyncio.Task] = set()

    def active_count(self) -> int:
        """返回当前活跃下载任务数"""
        # 清理已完成的任务
        self._active_tasks = {task for task in self._active_tasks if not task.done()}
        return len(self._active_tasks)

    async def download_batch(
        self,
        urls: list[str],
        output_dir: Path,
        download_fn: DownloadCallable | None = None,
    ) -> list[DownloadResult]:
        """
        批量下载多个 URL

        Args:
            urls: URL 列表
            output_dir: 输出目录
            download_fn: 自定义下载函数（用于测试）

        Returns:
            下载结果列表
        """
        if download_fn is None:
            download_fn = self._download_single

        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def download_with_semaphore(url: str) -> DownloadResult:
            async with semaphore:
                return await download_fn(url, output_dir)

        tasks = [download_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常结果
        processed_results: list[DownloadResult] = []
        for i, result in enumerate(results):
            if isinstance(result, BaseException):
                processed_results.append(
                    DownloadResult(
                        url=urls[i],
                        success=False,
                        error=str(result),
                    )
                )
            else:
                processed_results.append(result)

        return processed_results

    async def _download_single(self, url: str, output_dir: Path) -> DownloadResult:
        """
        下载单个 URL（基础实现）

        Args:
            url: 下载 URL
            output_dir: 输出目录

        Returns:
            下载结果
        """
        # TODO: 实现实际的下载逻辑
        # 这里使用 aiohttp 进行 HTTP 下载
        # 需要处理：
        # 1. HTTP 请求
        # 2. 文件写入
        # 3. 进度跟踪
        # 4. 错误处理
        raise NotImplementedError("请实现实际的下载逻辑")

    def download_sync(self, url: str, output_dir: Path) -> DownloadResult | None:
        """
        同步下载单个 URL

        Args:
            url: 下载 URL
            output_dir: 输出目录

        Returns:
            下载结果
        """
        try:
            return asyncio.run(self._download_single(url, output_dir))
        except Exception as e:
            return DownloadResult(
                url=url,
                success=False,
                error=str(e),
            )

    async def download_with_retry(
        self,
        urls: list[str],
        output_dir: Path,
        retry_queue: RetryQueue | None = None,
    ) -> list[DownloadResult]:
        """
        带重试的批量下载

        Args:
            urls: URL 列表
            output_dir: 输出目录
            retry_queue: 重试队列

        Returns:
            下载结果列表
        """
        if retry_queue is None:
            retry_queue = RetryQueue()

        aggregator = ResultAggregator()
        pending_urls = list(urls)

        while pending_urls or retry_queue.pending_count() > 0:
            # 处理重试队列中的任务
            retryable = retry_queue.get_retryable()
            for task in retryable:
                pending_urls.append(task.url)

            if not pending_urls:
                break

            # 批量下载
            results = await self.download_batch(pending_urls, output_dir)

            # 处理结果
            for result in results:
                aggregator.add_result(result)
                if not result.success:
                    # 添加到重试队列
                    retry_queue.add(result.url, result.error or "unknown", output_dir)

            # 移除已处理的 URL
            pending_urls.clear()

            # 如果有待重试任务，等待一段时间后继续
            if retry_queue.pending_count() > 0:
                await asyncio.sleep(1.0)

        return aggregator.get_success_results()


# =============================================================================
# 配置
# =============================================================================


@dataclass
class DownloaderConfig:
    """下载器配置"""

    max_concurrent: int = 5  # 最大并发数
    max_speed_mbps: float = 0  # 带宽限制 (0=无限制)
    max_retries: int = 3  # 最大重试次数
    retry_base_delay: float = 1.0  # 重试基础延迟 (秒)
    timeout_per_url: float = 30.0  # 单 URL 超时 (秒)
    chunk_size: int = 8192  # 下载块大小 (字节)
    use_priority_queue: bool = False  # 是否使用优先级队列


# =============================================================================
# 导出
# =============================================================================


__all__ = [
    # 数据结构
    "DownloadResult",
    "RetryTask",
    "DownloaderConfig",
    # 队列
    "DownloadQueue",
    "PriorityDownloadQueue",
    "RetryQueue",
    # 限制器
    "BandwidthLimiter",
    # 汇总器
    "ResultAggregator",
    # 下载器
    "ConcurrentDownloader",
    # 协议
    "DownloadCallable",
]
