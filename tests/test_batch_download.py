"""批量下载模块测试 - TDD 驱动开发"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

import pytest

from webvidgrab.batch_downloader import (
    BatchDownloadConfig,
    BatchDownloadResult,
    BatchDownloader,
    URLLoader,
)
from webvidgrab.downloader import DownloadResult


class TestBatchDownloadConfig:
    """批量下载配置测试"""

    def test_config_creation(self, tmp_path: Path) -> None:
        """配置创建"""
        url_file = tmp_path / "urls.txt"
        output_dir = tmp_path / "output"

        config = BatchDownloadConfig(
            url_file=url_file,
            output_dir=output_dir,
            concurrency=5,
            max_retries=3,
            check_duplicates=True,
        )

        assert config.url_file == url_file
        assert config.output_dir == output_dir
        assert config.concurrency == 5
        assert config.max_retries == 3
        assert config.check_duplicates is True

    def test_config_defaults(self, tmp_path: Path) -> None:
        """配置默认值"""
        url_file = tmp_path / "urls.txt"
        output_dir = tmp_path / "output"

        config = BatchDownloadConfig(
            url_file=url_file,
            output_dir=output_dir,
        )

        assert config.concurrency == 3  # 默认值是 3
        assert config.max_retries == 3
        assert config.check_duplicates is False
        assert config.browser == "chrome"
        assert config.profile == "Default"


class TestURLLoader:
    """URL 加载器测试"""

    def test_load_valid_urls(self, tmp_path: Path) -> None:
        """加载有效 URL"""
        url_file = tmp_path / "urls.txt"
        url_file.write_text(
            "https://example.com/video1.mp4\n"
            "https://example.com/video2.mp4\n"
            "https://example.com/video3.mp4\n",
            encoding="utf-8",
        )

        urls = URLLoader.load_from_file(url_file)
        assert len(urls) == 3

    def test_load_urls_with_comments(self, tmp_path: Path) -> None:
        """加载带注释的 URL"""
        url_file = tmp_path / "urls.txt"
        url_file.write_text(
            "# 这是注释\n"
            "https://example.com/video1.mp4\n"
            "\n"
            "https://example.com/video2.mp4 # 行内注释\n"
            "# 另一个注释\n",
            encoding="utf-8",
        )

        urls = URLLoader.load_from_file(url_file)
        assert len(urls) == 2

    def test_load_file_not_found(self, tmp_path: Path) -> None:
        """文件不存在"""
        url_file = tmp_path / "nonexistent.txt"

        with pytest.raises(FileNotFoundError):
            URLLoader.load_from_file(url_file)

    def test_load_empty_file(self, tmp_path: Path) -> None:
        """空文件"""
        url_file = tmp_path / "urls.txt"
        url_file.write_text("", encoding="utf-8")

        with pytest.raises(ValueError):
            URLLoader.load_from_file(url_file)

    def test_validate_valid_url(self) -> None:
        """验证有效 URL"""
        assert URLLoader.validate_url("https://example.com/video.mp4") is True
        assert URLLoader.validate_url("http://example.com/video.mp4") is True

    def test_validate_invalid_url(self) -> None:
        """验证无效 URL"""
        assert URLLoader.validate_url("invalid-url") is False
        assert URLLoader.validate_url("") is False
        assert URLLoader.validate_url("ftp://example.com") is False


class TestBatchDownloader:
    """批量下载器测试"""

    def test_downloader_initialization(self, tmp_path: Path) -> None:
        """下载器初始化"""
        url_file = tmp_path / "urls.txt"
        url_file.write_text("https://example.com/video.mp4\n", encoding="utf-8")

        config = BatchDownloadConfig(
            url_file=url_file,
            output_dir=tmp_path / "output",
            concurrency=3,
        )
        downloader = BatchDownloader(config)

        assert downloader.config.concurrency == 3
        assert downloader.config.max_retries == 3

    @pytest.mark.skip(reason="Requires actual download implementation")
    @pytest.mark.asyncio
    async def test_download_with_mock(self, tmp_path: Path) -> None:
        """使用 mock 下载"""
        # 跳过 - 需要实际下载实现
        pass

    @pytest.mark.skip(reason="Requires actual download implementation")
    @pytest.mark.asyncio
    async def test_download_with_failures(self, tmp_path: Path) -> None:
        """包含失败任务"""
        # 跳过 - 需要实际下载实现
        pass

    @pytest.mark.asyncio
    async def test_download_empty_file(self, tmp_path: Path) -> None:
        """空文件"""
        url_file = tmp_path / "urls.txt"
        url_file.write_text("", encoding="utf-8")

        config = BatchDownloadConfig(
            url_file=url_file,
            output_dir=tmp_path / "output",
            concurrency=2,
        )
        downloader = BatchDownloader(config)
        result = await downloader.run()

        assert result.total == 0
        assert result.succeeded == 0

    @pytest.mark.asyncio
    async def test_download_file_not_found(self, tmp_path: Path) -> None:
        """文件不存在"""
        url_file = tmp_path / "nonexistent.txt"

        config = BatchDownloadConfig(
            url_file=url_file,
            output_dir=tmp_path / "output",
            concurrency=2,
        )
        downloader = BatchDownloader(config)
        result = await downloader.run()

        assert result.total == 0
        assert result.succeeded == 0


class TestBatchDownloadResult:
    """批量下载结果测试"""

    def test_result_creation(self) -> None:
        """结果创建"""
        from datetime import datetime

        result = BatchDownloadResult(
            total=10,
            succeeded=8,
            failed=1,
            skipped=1,
            results=[],
            duration=5.5,
        )

        assert result.total == 10
        assert result.succeeded == 8
        assert result.failed == 1
        assert result.skipped == 1
        assert result.duration == 5.5

    def test_result_to_dict(self) -> None:
        """转换为字典"""
        result = BatchDownloadResult(
            total=5,
            succeeded=4,
            failed=1,
            skipped=0,
            results=[],
            duration=10.0,
        )

        data = result.to_dict()
        assert data["total"] == 5
        assert data["succeeded"] == 4
        assert data["failed"] == 1
        assert data["skipped"] == 0
        assert data["duration"] == 10.0

    def test_result_save_report(self, tmp_path: Path) -> None:
        """保存报告"""
        result = BatchDownloadResult(
            total=5,
            succeeded=4,
            failed=1,
            skipped=0,
            results=[],
            duration=10.0,
        )

        report_file = tmp_path / "report.json"
        result.save_report(report_file)

        assert report_file.exists()
        import json
        data = json.loads(report_file.read_text(encoding="utf-8"))
        assert data["total"] == 5
