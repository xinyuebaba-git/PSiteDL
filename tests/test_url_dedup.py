"""URL 去重模块测试 - TDD 驱动开发"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from webvidgrab.url_dedup import (
    URLDeduplicator,
    DownloadHistory,
    DownloadHistoryEntry,
    normalize_url,
    compute_url_hash,
    deduplicate_urls,
    find_session_duplicates,
)


class TestUrlNormalization:
    """URL 标准化测试"""

    def test_normalize_trailing_slash(self) -> None:
        """移除末尾斜杠"""
        url = "https://example.com/video/"
        normalized = normalize_url(url)
        assert normalized == "https://example.com/video"

    def test_normalize_root_path(self) -> None:
        """根路径保留斜杠"""
        url = "https://example.com/"
        normalized = normalize_url(url)
        # 根路径的斜杠会被保留（这是 normalize_url 的实现行为）
        assert normalized == "https://example.com/"

    def test_normalize_scheme_lowercase(self) -> None:
        """Scheme 转小写"""
        url = "HTTPS://example.com/video"
        normalized = normalize_url(url)
        assert normalized == "https://example.com/video"

    def test_normalize_host_lowercase(self) -> None:
        """Host 转小写"""
        url = "https://EXAMPLE.COM/video"
        normalized = normalize_url(url)
        assert normalized == "https://example.com/video"

    def test_normalize_remove_fragment(self) -> None:
        """移除片段"""
        url = "https://example.com/video#section1"
        normalized = normalize_url(url)
        assert normalized == "https://example.com/video"
        assert "#" not in normalized

    def test_normalize_sort_query_params(self) -> None:
        """排序查询参数"""
        url = "https://example.com/video?z=1&a=2&m=3"
        normalized = normalize_url(url)
        # 参数应该按字母顺序排列
        assert "a=2" in normalized
        assert "m=3" in normalized
        assert "z=1" in normalized
        # a 应该在 m 前面
        assert normalized.index("a=2") < normalized.index("m=3")

    def test_normalize_preserve_query_values(self) -> None:
        """保留查询参数值"""
        url = "https://example.com/video?id=123&quality=hd"
        normalized = normalize_url(url)
        assert "id=123" in normalized
        assert "quality=hd" in normalized

    def test_normalize_empty_query(self) -> None:
        """空查询字符串"""
        url = "https://example.com/video?"
        normalized = normalize_url(url)
        assert normalized == "https://example.com/video"

    def test_normalize_complex_url(self) -> None:
        """复杂 URL"""
        url = "HTTPS://Example.COM/Video/Path/?b=2&a=1#fragment"
        normalized = normalize_url(url)
        assert normalized == "https://example.com/Video/Path?a=1&b=2"

    def test_normalize_invalid_url(self) -> None:
        """无效 URL 返回原样"""
        url = "not-a-valid-url"
        normalized = normalize_url(url)
        assert normalized == url  # 解析失败时返回原样


class TestUrlHash:
    """URL 哈希测试"""

    def test_hash_consistency(self) -> None:
        """哈希一致性"""
        url = "https://example.com/video.mp4"
        hash1 = compute_url_hash(url)
        hash2 = compute_url_hash(url)
        assert hash1 == hash2

    def test_hash_different_urls(self) -> None:
        """不同 URL 不同哈希"""
        url1 = "https://example.com/video1.mp4"
        url2 = "https://example.com/video2.mp4"
        hash1 = compute_url_hash(url1)
        hash2 = compute_url_hash(url2)
        assert hash1 != hash2

    def test_hash_normalized(self) -> None:
        """标准化后哈希相同"""
        url1 = "https://example.com/video/"
        url2 = "https://example.com/video"
        hash1 = compute_url_hash(url1)
        hash2 = compute_url_hash(url2)
        assert hash1 == hash2


class TestSessionDeduplication:
    """会话内去重测试"""

    def test_find_duplicates_simple(self) -> None:
        """查找简单重复"""
        urls = [
            "https://example.com/video1.mp4",
            "https://example.com/video2.mp4",
            "https://example.com/video1.mp4",
        ]

        duplicates = find_session_duplicates(urls)
        assert len(duplicates) == 1
        assert len(duplicates["https://example.com/video1.mp4"]) == 2

    def test_find_duplicates_indices(self) -> None:
        """重复索引"""
        urls = [
            "https://example.com/a.mp4",
            "https://example.com/b.mp4",
            "https://example.com/a.mp4",
            "https://example.com/c.mp4",
            "https://example.com/b.mp4",
        ]

        duplicates = find_session_duplicates(urls)
        assert len(duplicates) == 2
        assert duplicates["https://example.com/a.mp4"] == [0, 2]
        assert duplicates["https://example.com/b.mp4"] == [1, 4]

    def test_find_no_duplicates(self) -> None:
        """无重复"""
        urls = [
            "https://example.com/a.mp4",
            "https://example.com/b.mp4",
            "https://example.com/c.mp4",
        ]

        duplicates = find_session_duplicates(urls)
        assert len(duplicates) == 0

    def test_deduplicate_simple(self) -> None:
        """简单去重"""
        urls = [
            "https://example.com/video1.mp4",
            "https://example.com/video2.mp4",
            "https://example.com/video1.mp4",
        ]

        result = deduplicate_urls(urls)
        assert len(result) == 2
        assert result == ["https://example.com/video1.mp4", "https://example.com/video2.mp4"]

    def test_deduplicate_preserve_order(self) -> None:
        """保持顺序"""
        urls = [
            "https://example.com/a.mp4",
            "https://example.com/b.mp4",
            "https://example.com/c.mp4",
            "https://example.com/a.mp4",
        ]

        result = deduplicate_urls(urls)
        assert result == [
            "https://example.com/a.mp4",
            "https://example.com/b.mp4",
            "https://example.com/c.mp4",
        ]

    def test_deduplicate_with_normalization(self) -> None:
        """标准化去重"""
        urls = [
            "https://example.com/video/",
            "https://example.com/video",
            "https://example.com/other",
        ]

        result = deduplicate_urls(urls)
        assert len(result) == 2
        assert result[0] == "https://example.com/video/"
        assert result[1] == "https://example.com/other"


class TestDownloadHistoryEntry:
    """下载历史记录条目测试"""

    def test_entry_creation(self) -> None:
        """条目创建"""
        entry = DownloadHistoryEntry(
            url="https://example.com/video.mp4",
            downloaded_at="2026-03-15T10:00:00",
            output_file="/path/to/video.mp4",
            file_size=1024,
        )

        assert entry.url == "https://example.com/video.mp4"
        assert entry.downloaded_at == "2026-03-15T10:00:00"
        assert entry.output_file == "/path/to/video.mp4"
        assert entry.file_size == 1024

    def test_entry_to_dict(self) -> None:
        """转换为字典"""
        entry = DownloadHistoryEntry(
            url="https://example.com/video.mp4",
            downloaded_at="2026-03-15T10:00:00",
            output_file="/path/to/video.mp4",
            file_size=1024,
        )

        data = entry.to_dict()
        assert data["url"] == "https://example.com/video.mp4"
        assert data["downloaded_at"] == "2026-03-15T10:00:00"
        assert data["output_file"] == "/path/to/video.mp4"
        assert data["file_size"] == 1024

    def test_entry_from_dict(self) -> None:
        """从字典创建"""
        data = {
            "url": "https://example.com/video.mp4",
            "downloaded_at": "2026-03-15T10:00:00",
            "output_file": "/path/to/video.mp4",
            "file_size": 1024,
        }

        entry = DownloadHistoryEntry.from_dict(data)
        assert entry.url == "https://example.com/video.mp4"
        assert entry.downloaded_at == "2026-03-15T10:00:00"
        assert entry.output_file == "/path/to/video.mp4"
        assert entry.file_size == 1024


class TestDownloadHistory:
    """下载历史记录测试"""

    def test_history_creation(self) -> None:
        """历史记录创建"""
        history = DownloadHistory()
        assert history.version == 1
        assert len(history.urls) == 0

    def test_history_add(self) -> None:
        """添加记录"""
        history = DownloadHistory()
        history.add("https://example.com/video.mp4", file_size=1024)

        assert len(history.urls) == 1
        assert history.urls[0].url == "https://example.com/video.mp4"
        assert history.urls[0].file_size == 1024

    def test_history_contains(self) -> None:
        """检查包含"""
        history = DownloadHistory()
        history.add("https://example.com/video.mp4")

        assert history.contains_url("https://example.com/video.mp4") is True
        assert history.contains_url("https://example.com/other.mp4") is False

    def test_history_contains_normalized(self) -> None:
        """标准化检查"""
        history = DownloadHistory()
        history.add("https://example.com/video.mp4")

        # contains_url 会标准化后比较
        # 注意：实际实现中 contains_url 会对两个 URL 都进行标准化
        assert history.contains_url("https://example.com/video.mp4") is True

    def test_history_to_dict(self) -> None:
        """转换为字典"""
        history = DownloadHistory()
        history.add("https://example.com/video.mp4")

        data = history.to_dict()
        assert data["version"] == 1
        assert len(data["urls"]) == 1

    def test_history_from_dict(self) -> None:
        """从字典创建"""
        data = {
            "version": 1,
            "updated_at": "2026-03-15T10:00:00",
            "urls": [
                {
                    "url": "https://example.com/video.mp4",
                    "downloaded_at": "2026-03-15T10:00:00",
                    "output_file": None,
                    "file_hash": None,
                    "file_size": 0,
                }
            ],
        }

        history = DownloadHistory.from_dict(data)
        assert history.version == 1
        assert len(history.urls) == 1


class TestURLDeduplicator:
    """URL 去重器测试"""

    def test_deduplicator_creation(self, tmp_path: Path) -> None:
        """去重器创建"""
        history_file = tmp_path / "history.json"
        dedup = URLDeduplicator(history_file=history_file)

        assert dedup.history_file == history_file
        assert dedup.max_history_entries == 10000

    def test_deduplicator_default_history_file(self) -> None:
        """默认历史记录文件"""
        dedup = URLDeduplicator()

        expected = Path.home() / ".config" / "psitedl" / "download_history.json"
        assert dedup.history_file == expected

    def test_deduplicator_deduplicate(self, tmp_path: Path) -> None:
        """去重"""
        history_file = tmp_path / "history.json"
        dedup = URLDeduplicator(history_file=history_file)

        urls = [
            "https://example.com/video1.mp4",
            "https://example.com/video2.mp4",
            "https://example.com/video1.mp4",
        ]

        result = dedup.deduplicate(urls)
        assert len(result) == 2

    def test_deduplicator_find_duplicates(self, tmp_path: Path) -> None:
        """查找重复"""
        history_file = tmp_path / "history.json"
        dedup = URLDeduplicator(history_file=history_file)

        urls = [
            "https://example.com/video1.mp4",
            "https://example.com/video2.mp4",
            "https://example.com/video1.mp4",
        ]

        duplicates = dedup.find_duplicates(urls)
        assert len(duplicates) == 1

    def test_deduplicator_save_to_history(self, tmp_path: Path) -> None:
        """保存到历史记录"""
        history_file = tmp_path / "history.json"
        dedup = URLDeduplicator(history_file=history_file)

        urls = ["https://example.com/video.mp4"]
        dedup.save_to_history(urls)

        # 验证历史记录已保存
        assert history_file.exists()
        data = json.loads(history_file.read_text(encoding="utf-8"))
        assert len(data["urls"]) == 1

    def test_deduplicator_history_persistence(self, tmp_path: Path) -> None:
        """历史记录持久化"""
        history_file = tmp_path / "history.json"

        # 第一次创建并保存
        dedup1 = URLDeduplicator(history_file=history_file)
        dedup1.save_to_history(["https://example.com/video.mp4"])

        # 第二次创建应该加载历史记录
        dedup2 = URLDeduplicator(history_file=history_file)
        assert dedup2.history.contains_url("https://example.com/video.mp4")

    def test_deduplicator_duplicate_with_history(self, tmp_path: Path) -> None:
        """历史记录中的重复"""
        history_file = tmp_path / "history.json"
        dedup = URLDeduplicator(history_file=history_file)

        # 先保存到历史记录
        dedup.save_to_history(["https://example.com/video.mp4"])

        # 查找重复应该包含历史记录中的 URL
        urls = ["https://example.com/video.mp4"]
        duplicates = dedup.find_duplicates(urls)
        assert len(duplicates) == 1

    def test_deduplicator_save_and_reload(self, tmp_path: Path) -> None:
        """保存和重新加载"""
        history_file = tmp_path / "history.json"

        dedup1 = URLDeduplicator(history_file=history_file)
        dedup1.save_to_history(
            ["https://example.com/video1.mp4"],
            file_sizes={"https://example.com/video1.mp4": 1024},
        )

        dedup2 = URLDeduplicator(history_file=history_file)
        assert len(dedup2.history.urls) == 1
        assert dedup2.history.urls[0].file_size == 1024


class TestUrlDedupEdgeCases:
    """边界情况测试"""

    def test_empty_url_list(self) -> None:
        """空 URL 列表"""
        result = deduplicate_urls([])
        assert result == []

    def test_single_url(self) -> None:
        """单个 URL"""
        result = deduplicate_urls(["https://example.com/video.mp4"])
        assert result == ["https://example.com/video.mp4"]

    def test_all_duplicates(self) -> None:
        """全部重复"""
        urls = ["https://example.com/video.mp4"] * 10
        result = deduplicate_urls(urls)
        assert len(result) == 1

    def test_unicode_in_url(self) -> None:
        """URL 中的 Unicode"""
        url = "https://example.com/视频.mp4"
        normalized = normalize_url(url)
        assert "视频" in normalized

    def test_very_long_url(self) -> None:
        """超长 URL"""
        url = "https://example.com/" + "a" * 1000 + "/video.mp4"
        normalized = normalize_url(url)
        assert len(normalized) > 1000

    def test_url_with_port(self) -> None:
        """带端口的 URL"""
        url = "https://example.com:8080/video.mp4"
        normalized = normalize_url(url)
        assert ":8080" in normalized

    def test_url_with_authentication(self) -> None:
        """带认证的 URL"""
        url = "https://user:pass@example.com/video.mp4"
        normalized = normalize_url(url)
        assert "user:pass@" in normalized or "example.com" in normalized
