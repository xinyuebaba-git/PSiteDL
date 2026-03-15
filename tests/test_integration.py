"""批量下载集成测试"""

from __future__ import annotations

from pathlib import Path

import pytest

from webvidgrab.batch_downloader import (
    BatchDownloadConfig,
    BatchDownloader,
)
from webvidgrab.url_dedup import URLDeduplicator, deduplicate_urls, normalize_url


class TestIntegration:
    """集成测试"""

    def test_url_dedup_integration(self, tmp_path: Path) -> None:
        """URL 去重集成测试"""
        # 创建测试 URL 文件
        url_file = tmp_path / "urls.txt"
        url_file.write_text(
            "https://example.com/video1.mp4\n"
            "https://example.com/video2.mp4\n"
            "https://example.com/video1.mp4\n"  # 重复
            "https://example.com/video3.mp4\n"
            "https://example.com/video2.mp4\n"  # 重复
            "# 这是注释\n"
            "invalid-url\n"  # 无效 URL
            "https://example.com/video4.mp4\n",
            encoding="utf-8",
        )

        # 测试去重功能
        dedup = URLDeduplicator(history_file=tmp_path / "history.json")

        # 查找重复
        urls = [
            "https://example.com/video1.mp4",
            "https://example.com/video2.mp4",
            "https://example.com/video1.mp4",
        ]
        duplicates = dedup.find_duplicates(urls)
        assert len(duplicates) == 1

        # 去重
        unique = dedup.deduplicate(urls)
        assert len(unique) == 2

    def test_url_normalization_integration(self) -> None:
        """URL 标准化集成测试"""
        # 测试各种 URL 格式
        test_cases = [
            ("https://example.com/video/", "https://example.com/video"),
            ("HTTPS://EXAMPLE.COM/video", "https://example.com/video"),
            ("https://example.com/video?b=2&a=1", "https://example.com/video?a=1&b=2"),
            ("https://example.com/video#section", "https://example.com/video"),
        ]

        for input_url, expected in test_cases:
            normalized = normalize_url(input_url)
            assert normalized == expected, f"Failed for {input_url}"

    def test_batch_download_empty_file(self, tmp_path: Path) -> None:
        """批量下载空文件"""
        url_file = tmp_path / "urls.txt"
        url_file.write_text("", encoding="utf-8")

        config = BatchDownloadConfig(
            url_file=url_file,
            output_dir=tmp_path / "output",
            concurrency=2,
        )
        downloader = BatchDownloader(config)

        import asyncio

        result = asyncio.run(downloader.run())

        assert result.total == 0
        assert result.succeeded == 0

    def test_batch_download_with_duplicates(self, tmp_path: Path) -> None:
        """批量下载带重复 URL"""
        url_file = tmp_path / "urls.txt"
        url_file.write_text(
            "https://example.com/video1.mp4\n"
            "https://example.com/video2.mp4\n"
            "https://example.com/video1.mp4\n",  # 重复
            encoding="utf-8",
        )

        config = BatchDownloadConfig(
            url_file=url_file,
            output_dir=tmp_path / "output",
            concurrency=2,
            check_duplicates=True,
        )
        downloader = BatchDownloader(config)

        import asyncio

        result = asyncio.run(downloader.run())

        # 应该检测到 3 个 URL，但跳过 1 个重复
        assert result.total == 3
        assert result.skipped >= 1

    def test_url_file_with_comments(self, tmp_path: Path) -> None:
        """带注释的 URL 文件"""
        url_file = tmp_path / "urls.txt"
        url_file.write_text(
            "# 视频列表\n"
            "https://example.com/video1.mp4\n"
            "\n"  # 空行
            "# 另一个视频\n"
            "https://example.com/video2.mp4 # 行内注释\n"
            "invalid-url\n",  # 无效 URL
            encoding="utf-8",
        )

        from webvidgrab.batch_downloader import URLLoader

        urls = URLLoader.load_from_file(url_file)

        # 应该只加载 2 个有效 URL
        assert len(urls) == 2
        assert "https://example.com/video1.mp4" in urls
        assert "https://example.com/video2.mp4" in urls
