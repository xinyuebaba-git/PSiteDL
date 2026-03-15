"""批量下载模块 - PSiteDL 批量下载功能

功能:
- 从 URL 列表文件批量下载视频
- 支持去重检测
- 进度显示
- 失败重试

用法:
    python -m webvidgrab.batch_downloader \\
        --url-file urls.txt \\
        --output-dir ~/Downloads \\
        --check-duplicates \\
        --concurrency 3 \\
        --max-retries 3

URL 列表文件格式:
    # 这是注释
    https://example.com/video1
    https://example.com/video2
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# 复用现有模块
from .downloader import DownloadResult
from .logger import create_logger
from .url_dedup import URLDeduplicator

try:
    from rich.console import Console
    from rich.progress import (
        BarColumn,
        MofNCompleteColumn,
        Progress,
        TaskProgressColumn,
        TextColumn,
        TimeRemainingColumn,
    )

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None  # type: ignore

__all__ = [
    "BatchDownloader",
    "BatchDownloadResult",
    "BatchDownloadConfig",
    "main",
]


# =============================================================================
# 数据结构
# =============================================================================


@dataclass
class BatchDownloadConfig:
    """批量下载配置"""

    url_file: Path
    output_dir: Path = field(default_factory=lambda: Path.home() / "Downloads")
    check_duplicates: bool = False
    concurrency: int = 3
    max_retries: int = 3
    browser: str = "chrome"
    profile: str = "Default"
    capture_seconds: int = 30
    use_runtime_capture: bool = True
    timeout: int = 30
    bandwidth_limit_mbps: float = 0.0
    log_level: str = "INFO"
    dedup_history_file: Path | None = None


@dataclass
class BatchDownloadResult:
    """批量下载结果"""

    total: int  # 总 URL 数
    succeeded: int  # 成功数
    failed: int  # 失败数
    skipped: int  # 跳过数（重复）
    results: list[DownloadResult] = field(default_factory=list)
    duration: float = 0.0  # 总耗时（秒）
    started_at: datetime | None = None
    completed_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "total": self.total,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "skipped": self.skipped,
            "duration": round(self.duration, 2),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "results": [
                {
                    "url": r.url,
                    "success": r.success,
                    "output_file": str(r.output_file) if r.output_file else None,
                    "error": r.error,
                    "file_size": r.file_size,
                    "duration": round(r.duration, 2),
                    "retries": r.retries,
                }
                for r in self.results
            ],
        }

    def save_report(self, path: Path) -> None:
        """保存结果报告到 JSON 文件"""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)


# =============================================================================
# URL 加载器
# =============================================================================


class URLLoader:
    """URL 加载器"""

    @staticmethod
    def load_from_file(path: Path) -> list[str]:
        """
        从文件加载 URL 列表

        Args:
            path: URL 列表文件路径

        Returns:
            URL 列表

        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件格式错误
        """
        if not path.exists():
            raise FileNotFoundError(f"URL file not found: {path}")

        urls: list[str] = []
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as e:
            raise ValueError(f"Failed to read URL file (encoding error): {e}") from e

        for line_num, line in enumerate(content.splitlines(), start=1):
            line = line.strip()

            # 跳过空行
            if not line:
                continue

            # 跳过整行注释
            if line.startswith("#"):
                continue

            # 处理行内注释
            if "#" in line:
                line = line.split("#", 1)[0].strip()

            # 验证 URL 格式
            if URLLoader.validate_url(line):
                urls.append(line)
            else:
                # 记录警告但继续处理
                print(f"[WARNING] 跳过无效 URL (行 {line_num}): {line}", file=sys.stderr)

        if not urls:
            raise ValueError("URL file contains no valid URLs")

        return urls

    @staticmethod
    def validate_url(url: str) -> bool:
        """
        验证 URL 格式

        Args:
            url: URL 字符串

        Returns:
            True 如果 URL 格式有效
        """
        if not url:
            return False

        # 基本 URL 格式检查
        return url.startswith(("http://", "https://"))


# =============================================================================
# 批量下载器
# =============================================================================


class BatchDownloader:
    """批量下载器"""

    def __init__(self, config: BatchDownloadConfig) -> None:
        """
        初始化批量下载器

        Args:
            config: 批量下载配置
        """
        self.config = config
        self.logger = create_logger(__name__, level=config.log_level)
        self.console = Console() if RICH_AVAILABLE else None

        # 初始化去重器
        self.deduplicator = (
            URLDeduplicator(history_file=config.dedup_history_file)
            if config.check_duplicates
            else None
        )

    async def run(self) -> BatchDownloadResult:
        """
        执行批量下载

        Returns:
            批量下载结果
        """
        start_time = time.time()
        started_at = datetime.now()

        self.logger.info(f"批量下载开始：从 {self.config.url_file} 加载 URL")

        # 1. 加载 URL
        try:
            all_urls = URLLoader.load_from_file(self.config.url_file)
            self.logger.info(f"加载了 {len(all_urls)} 个 URL")
        except (FileNotFoundError, ValueError) as e:
            self.logger.error(f"加载 URL 失败：{e}")
            return BatchDownloadResult(
                total=0,
                succeeded=0,
                failed=0,
                skipped=0,
                duration=time.time() - start_time,
                started_at=started_at,
                completed_at=datetime.now(),
            )

        # 2. 去重检测
        urls_to_download = all_urls
        skipped_count = 0

        if self.deduplicator:
            self.logger.info("执行去重检测...")
            duplicates = self.deduplicator.find_duplicates(all_urls)
            skipped_count = sum(
                len(indices) - 1 for indices in duplicates.values() if len(indices) > 1
            )
            urls_to_download = self.deduplicator.deduplicate(all_urls)
            self.logger.info(
                f"去重后剩余 {len(urls_to_download)} 个唯 URL，跳过 {skipped_count} 个重复"
            )

        if not urls_to_download:
            self.logger.warning("没有需要下载的 URL")
            return BatchDownloadResult(
                total=len(all_urls),
                succeeded=0,
                failed=0,
                skipped=skipped_count,
                duration=time.time() - start_time,
                started_at=started_at,
                completed_at=datetime.now(),
            )

        # 3. 确保输出目录存在
        self.config.output_dir.mkdir(parents=True, exist_ok=True)

        # 4. 执行下载
        results = await self._download_all(urls_to_download)

        # 5. 保存到历史记录
        if self.deduplicator:
            successful_urls = [r.url for r in results if r.success]
            if successful_urls:
                self.deduplicator.save_to_history(successful_urls)

        # 6. 汇总结果
        succeeded = sum(1 for r in results if r.success)
        failed = len(results) - succeeded

        result = BatchDownloadResult(
            total=len(all_urls),
            succeeded=succeeded,
            failed=failed,
            skipped=skipped_count,
            results=results,
            duration=time.time() - start_time,
            started_at=started_at,
            completed_at=datetime.now(),
        )

        # 7. 输出摘要
        self._print_summary(result)

        return result

    async def _download_one(
        self,
        *,
        idx: int,
        total: int,
        url: str,
        semaphore: asyncio.Semaphore,
    ) -> tuple[int, DownloadResult]:
        """下载单个 URL（带任务级重试）"""
        from .site_cli import run_site_download

        async with semaphore:
            self.logger.info(f"[{idx + 1}/{total}] 开始下载：{url}")
            started = time.monotonic()
            last_error = "Download failed"

            for attempt in range(self.config.max_retries + 1):
                try:
                    result_obj = await asyncio.to_thread(
                        run_site_download,
                        page_url=url,
                        output_dir=self.config.output_dir,
                        browser=self.config.browser,
                        profile=self.config.profile,
                        capture_seconds=max(10, int(self.config.capture_seconds)),
                        timeout=max(1, int(self.config.timeout)),
                        max_retries=0,
                        bandwidth_limit_mbps=max(0.0, float(self.config.bandwidth_limit_mbps)),
                        use_runtime_capture=self.config.use_runtime_capture,
                        log_func=lambda msg: None,
                    )

                    duration = time.monotonic() - started
                    if result_obj.ok:
                        file_size = 0
                        if result_obj.output_file and result_obj.output_file.exists():
                            file_size = result_obj.output_file.stat().st_size
                        result = DownloadResult(
                            url=url,
                            success=True,
                            output_file=result_obj.output_file,
                            error=None,
                            file_size=file_size,
                            duration=duration,
                            retries=attempt,
                        )
                        self.logger.info(
                            f"[{idx + 1}/{total}] 下载完成："
                            f"{result.output_file.name if result.output_file else 'unknown'}"
                        )
                        return idx, result

                    last_error = f"Download failed (log: {result_obj.log_file})"
                except Exception as exc:
                    last_error = str(exc)

                if attempt < self.config.max_retries:
                    self.logger.warning(
                        f"[{idx + 1}/{total}] 下载失败，准备重试 "
                        f"({attempt + 1}/{self.config.max_retries})：{last_error}"
                    )

            duration = time.monotonic() - started
            self.logger.error(f"[{idx + 1}/{total}] 下载失败：{last_error}")
            return idx, DownloadResult(
                url=url,
                success=False,
                error=last_error,
                duration=duration,
                retries=self.config.max_retries,
            )

    async def _download_all(
        self,
        urls: list[str],
    ) -> list[DownloadResult]:
        """
        下载所有 URL

        Args:
            urls: URL 列表

        Returns:
            下载结果列表
        """
        semaphore = asyncio.Semaphore(max(1, int(self.config.concurrency)))
        tasks = [
            asyncio.create_task(
                self._download_one(
                    idx=idx,
                    total=len(urls),
                    url=url,
                    semaphore=semaphore,
                )
            )
            for idx, url in enumerate(urls)
        ]
        ordered_results: list[DownloadResult | None] = [None] * len(urls)

        if RICH_AVAILABLE and self.console:
            with Progress(
                TextColumn("[bold blue]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                MofNCompleteColumn(),
                TimeRemainingColumn(),
                console=self.console,
            ) as progress:
                task = progress.add_task("下载中...", total=len(urls))
                for done in asyncio.as_completed(tasks):
                    idx, result = await done
                    ordered_results[idx] = result
                    progress.update(task, advance=1)
        else:
            for done in asyncio.as_completed(tasks):
                idx, result = await done
                ordered_results[idx] = result

        return [r for r in ordered_results if r is not None]

    def _print_summary(self, result: BatchDownloadResult) -> None:
        """打印下载摘要"""
        print("\n" + "=" * 60)
        print("批量下载完成")
        print("=" * 60)
        print(f"总 URL 数：    {result.total}")
        print(f"成功：        {result.succeeded}")
        print(f"失败：        {result.failed}")
        print(f"跳过 (重复):  {result.skipped}")
        print(f"总耗时：      {result.duration:.1f} 秒")
        print("=" * 60)

        if result.failed > 0:
            print("\n失败任务:")
            for r in result.results:
                if not r.success:
                    print(f"  - {r.url}: {r.error}")
            print("=" * 60)


# =============================================================================
# 命令行接口
# =============================================================================


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="PSiteDL 批量下载工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
URL 列表文件格式:
  # 这是注释
  https://example.com/video1
  https://example.com/video2

示例:
  python -m webvidgrab.batch_downloader --url-file urls.txt
  python -m webvidgrab.batch_downloader --url-file urls.txt --check-duplicates
  python -m webvidgrab.batch_downloader --url-file urls.txt --output-dir ./videos --concurrency 5
        """,
    )

    parser.add_argument(
        "--url-file",
        type=Path,
        required=True,
        help="URL 列表文件路径（每行一个 URL）",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.home() / "Downloads",
        help="输出目录（默认：~/Downloads）",
    )

    parser.add_argument(
        "--check-duplicates",
        action="store_true",
        help="检测重复 URL（包括历史下载记录）",
    )

    parser.add_argument(
        "--concurrency",
        type=int,
        default=3,
        help="并发下载数（默认：3）",
    )

    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="最大重试次数（默认：3）",
    )

    parser.add_argument(
        "--browser",
        type=str,
        default="chrome",
        choices=["chrome", "chromium", "edge", "brave", "firefox", "safari"],
        help="浏览器类型（默认：chrome）",
    )

    parser.add_argument(
        "--profile",
        type=str,
        default="Default",
        help="浏览器配置文件名称（默认：Default）",
    )

    parser.add_argument(
        "--capture-seconds",
        type=int,
        default=30,
        help="运行时探测时长（默认：30 秒）",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="网络超时（默认：30 秒）",
    )

    parser.add_argument(
        "--bandwidth-limit",
        type=float,
        default=0,
        help="下载限速 Mbps（默认：0，无限制）",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="日志级别（默认：INFO）",
    )

    parser.add_argument(
        "--no-runtime-capture",
        action="store_true",
        help="禁用 Playwright 运行时探测",
    )

    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="保存结果报告到 JSON 文件",
    )

    return parser.parse_args()


def main() -> int:
    """主函数"""
    args = parse_args()

    # 创建配置
    config = BatchDownloadConfig(
        url_file=args.url_file,
        output_dir=args.output_dir,
        check_duplicates=args.check_duplicates,
        concurrency=args.concurrency,
        max_retries=args.max_retries,
        browser=args.browser,
        profile=args.profile,
        capture_seconds=max(10, int(args.capture_seconds)),
        use_runtime_capture=not args.no_runtime_capture,
        timeout=max(1, int(args.timeout)),
        bandwidth_limit_mbps=max(0.0, float(args.bandwidth_limit)),
        log_level=args.log_level,
    )

    # 创建下载器并运行
    downloader = BatchDownloader(config)

    try:
        result = asyncio.run(downloader.run())

        # 保存报告（如果指定）
        if args.report:
            result.save_report(args.report)
            print(f"\n结果报告已保存到：{args.report}")

        # 返回状态码
        return 0 if result.failed == 0 else 1

    except KeyboardInterrupt:
        print("\n[INFO] 用户中断下载")
        return 130
    except Exception as e:
        print(f"\n[ERROR] 批量下载失败：{e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
