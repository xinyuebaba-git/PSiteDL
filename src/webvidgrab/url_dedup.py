"""URL 去重模块 - PSiteDL 批量下载功能

功能:
- URL 标准化
- 会话内去重
- 历史下载记录去重
- 持久化历史记录

用法:
    from webvidgrab.url_dedup import URLDeduplicator
    
    dedup = URLDeduplicator(history_file="~/.config/psitedl/download_history.json")
    
    # 查找重复
    duplicates = dedup.find_duplicates(urls)
    
    # 去重
    unique_urls = dedup.deduplicate(urls)
    
    # 保存到历史记录
    dedup.save_to_history(successful_urls)
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

__all__ = [
    "URLDeduplicator",
    "DownloadHistoryEntry",
    "DownloadHistory",
]


# =============================================================================
# 数据结构
# =============================================================================


@dataclass
class DownloadHistoryEntry:
    """下载历史记录条目"""

    url: str
    downloaded_at: str  # ISO format datetime
    output_file: str | None = None
    file_hash: str | None = None  # SHA256 hash
    file_size: int = 0

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "url": self.url,
            "downloaded_at": self.downloaded_at,
            "output_file": self.output_file,
            "file_hash": self.file_hash,
            "file_size": self.file_size,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DownloadHistoryEntry":
        """从字典创建"""
        return cls(
            url=data["url"],
            downloaded_at=data["downloaded_at"],
            output_file=data.get("output_file"),
            file_hash=data.get("file_hash"),
            file_size=data.get("file_size", 0),
        )


@dataclass
class DownloadHistory:
    """下载历史记录"""

    version: int = 1
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    urls: list[DownloadHistoryEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "version": self.version,
            "updated_at": self.updated_at,
            "urls": [entry.to_dict() for entry in self.urls],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DownloadHistory":
        """从字典创建"""
        return cls(
            version=data.get("version", 1),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            urls=[
                DownloadHistoryEntry.from_dict(entry_data)
                for entry_data in data.get("urls", [])
            ],
        )

    def add(self, url: str, output_file: Path | None = None, file_size: int = 0) -> None:
        """添加下载记录"""
        entry = DownloadHistoryEntry(
            url=url,
            downloaded_at=datetime.now().isoformat(),
            output_file=str(output_file) if output_file else None,
            file_size=file_size,
        )
        self.urls.append(entry)
        self.updated_at = datetime.now().isoformat()

    def contains_url(self, url: str) -> bool:
        """检查 URL 是否已存在"""
        normalized = normalize_url(url)
        return any(normalize_url(entry.url) == normalized for entry in self.urls)

    def get_url_indices(self, url: str) -> list[int]:
        """获取 URL 的所有索引位置"""
        normalized = normalize_url(url)
        return [
            idx for idx, entry in enumerate(self.urls)
            if normalize_url(entry.url) == normalized
        ]


# =============================================================================
# URL 标准化工具
# =============================================================================


def normalize_url(url: str) -> str:
    """
    标准化 URL

    处理:
    - 移除 trailing slash
    - 统一 scheme 为小写
    - 统一 host 为小写
    - 移除 fragment
    - 排序 query parameters

    Args:
        url: 原始 URL

    Returns:
        标准化后的 URL
    """
    try:
        parsed = urlparse(url)

        # 统一 scheme 和 host 为小写
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()

        # 移除 path 末尾的斜杠（但保留根路径）
        path = parsed.path
        if path and path != "/":
            path = path.rstrip("/")

        # 排序 query parameters 并移除跟踪参数
        query = parsed.query
        if query:
            # 解析 query parameters 并排序
            from urllib.parse import parse_qsl, urlencode
            params = parse_qsl(query, keep_blank_values=True)
            # 移除常见跟踪参数
            tracking_params = {'utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term', 
                              'fbclid', 'gclid', 'yclid', '_hsenc', '_hsmi', 'mc_cid', 'mc_eid'}
            params = [(k, v) for k, v in params if k not in tracking_params]
            params.sort()
            query = urlencode(params)

        # 移除 fragment
        fragment = ""

        # 重新构建 URL
        normalized = urlunparse((scheme, netloc, path, "", query, fragment))

        return normalized
    except Exception:
        # 如果解析失败，返回原始 URL
        return url


def compute_url_hash(url: str) -> str:
    """
    计算 URL 的哈希值（用于快速比较）

    Args:
        url: URL 字符串

    Returns:
        SHA256 哈希值（十六进制）
    """
    normalized = normalize_url(url)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


# =============================================================================
# URL 去重器
# =============================================================================


class URLDeduplicator:
    """URL 去重器"""

    def __init__(
        self,
        history_file: Path | str | None = None,
        max_history_entries: int = 10000,
    ) -> None:
        """
        初始化去重器

        Args:
            history_file: 历史记录文件路径（默认：~/.config/psitedl/download_history.json）
            max_history_entries: 最大历史记录数量（超过时自动清理旧记录）
        """
        if history_file is None:
            history_file = Path.home() / ".config" / "psitedl" / "download_history.json"
        elif isinstance(history_file, str):
            history_file = Path(history_file)

        self.history_file = history_file
        self.max_history_entries = max_history_entries
        self.history = self._load_history()

    def _load_history(self) -> DownloadHistory:
        """加载历史记录"""
        if not self.history_file.exists():
            return DownloadHistory()

        try:
            content = self.history_file.read_text(encoding="utf-8")
            data = json.loads(content)
            return DownloadHistory.from_dict(data)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # 如果加载失败，返回空历史记录
            print(f"[WARNING] 加载历史记录失败：{e}，使用空历史记录")
            return DownloadHistory()

    def save_history(self) -> None:
        """保存历史记录到文件"""
        # 清理旧记录（如果超过最大数量）
        if len(self.history.urls) > self.max_history_entries:
            # 保留最新的记录
            self.history.urls = self.history.urls[-self.max_history_entries:]

        # 确保目录存在
        self.history_file.parent.mkdir(parents=True, exist_ok=True)

        # 保存
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(self.history.to_dict(), f, indent=2, ensure_ascii=False)

    def find_duplicates(
        self,
        urls: list[str],
    ) -> dict[str, list[int]]:
        """
        查找重复 URL

        Args:
            urls: URL 列表

        Returns:
            字典：{ normalized_url: [index1, index2, ...] }
            只包含重复的 URL（出现次数 > 1）
        """
        # 构建映射表：normalized_url -> [indices]
        url_map: dict[str, list[int]] = defaultdict(list)

        for idx, url in enumerate(urls):
            normalized = normalize_url(url)
            url_map[normalized].append(idx)

        # 只返回重复项
        duplicates = {
            normalized: indices
            for normalized, indices in url_map.items()
            if len(indices) > 1
        }

        # 检查历史记录中的重复
        for idx, url in enumerate(urls):
            normalized = normalize_url(url)
            if self.history.contains_url(url):
                # 如果 URL 已在历史记录中，也视为重复
                if normalized not in duplicates:
                    duplicates[normalized] = []
                # 添加特殊标记表示历史记录中的重复
                if -1 not in duplicates[normalized]:
                    duplicates[normalized].append(-1)  # -1 表示历史记录中已存在

        return duplicates

    def deduplicate(self, urls: list[str]) -> list[str]:
        """
        去重并返回唯一 URL 列表

        Args:
            urls: URL 列表

        Returns:
            去重后的 URL 列表（保持原始顺序）
        """
        seen: set[str] = set()
        result: list[str] = []

        for url in urls:
            normalized = normalize_url(url)

            # 检查是否在会话中已见过
            if normalized in seen:
                continue

            # 检查是否在历史记录中已存在
            if self.history.contains_url(url):
                continue

            seen.add(normalized)
            result.append(url)

        return result

    def save_to_history(
        self,
        urls: list[str],
        output_files: dict[str, Path] | None = None,
        file_sizes: dict[str, int] | None = None,
    ) -> None:
        """
        保存 URL 到历史记录

        Args:
            urls: URL 列表
            output_files: URL 到输出文件的映射（可选）
            file_sizes: URL 到文件大小的映射（可选）
        """
        for url in urls:
            output_file = output_files.get(url) if output_files else None
            file_size = file_sizes.get(url, 0) if file_sizes else 0
            self.history.add(url, output_file, file_size)

        # 保存到文件
        self.save_history()

    def get_duplicate_report(
        self,
        urls: list[str],
    ) -> str:
        """
        生成去重报告

        Args:
            urls: URL 列表

        Returns:
            人类可读的去重报告
        """
        duplicates = self.find_duplicates(urls)

        if not duplicates:
            return "未发现重复 URL"

        lines: list[str] = []
        lines.append(f"发现 {len(duplicates)} 组重复 URL:")
        lines.append("")

        for normalized, indices in duplicates.items():
            if -1 in indices:
                # 历史记录中的重复
                lines.append(f"  [历史记录] {normalized}")
                lines.append(f"    已在历史记录中存在")
            else:
                # 当前列表中的重复
                urls_in_group = [urls[idx] for idx in indices]
                lines.append(f"  {len(indices)} 次出现:")
                for idx, url in zip(indices, urls_in_group):
                    lines.append(f"    [{idx + 1}] {url}")
            lines.append("")

        return "\n".join(lines)


# =============================================================================
# 辅助函数
# =============================================================================


def find_session_duplicates(urls: list[str]) -> dict[str, list[int]]:
    """
    查找会话内重复（不检查历史记录）

    Args:
        urls: URL 列表

    Returns:
        字典：{ normalized_url: [index1, index2, ...] }
    """
    url_map: dict[str, list[int]] = defaultdict(list)

    for idx, url in enumerate(urls):
        normalized = normalize_url(url)
        url_map[normalized].append(idx)

    return {
        normalized: indices
        for normalized, indices in url_map.items()
        if len(indices) > 1
    }


def deduplicate_urls(urls: list[str]) -> list[str]:
    """
    简单去重（不检查历史记录）

    Args:
        urls: URL 列表

    Returns:
        去重后的 URL 列表
    """
    seen: set[str] = set()
    result: list[str] = []

    for url in urls:
        normalized = normalize_url(url)
        if normalized not in seen:
            seen.add(normalized)
            result.append(url)

    return result


# =============================================================================
# 批量下载支持函数
# =============================================================================


@dataclass
class DedupResult:
    """去重结果"""

    original_count: int
    unique_count: int
    duplicate_count: int
    unique_urls: list[str]
    duplicates: dict[str, list[int]]  # url -> [line_numbers]


@dataclass
class DuplicateReport:
    """重复 URL 报告"""

    url: str
    line_numbers: list[int]
    domain: str
    normalized_url: str


def detect_duplicates(urls: list[str]) -> DedupResult:
    """
    检测 URL 列表中的重复项

    Args:
        urls: URL 列表

    Returns:
        DedupResult 包含去重结果
    """
    seen: dict[str, list[int]] = {}  # normalized_url -> [line_numbers]

    for idx, url in enumerate(urls, start=1):
        normalized = normalize_url(url)
        if normalized not in seen:
            seen[normalized] = []
        seen[normalized].append(idx)

    # 分离唯一 URL 和重复项
    unique_urls: list[str] = []
    duplicates: dict[str, list[int]] = {}

    for normalized, line_numbers in seen.items():
        # 找到第一个出现的原始 URL
        first_idx = line_numbers[0] - 1
        unique_urls.append(urls[first_idx])

        if len(line_numbers) > 1:
            duplicates[normalized] = line_numbers

    return DedupResult(
        original_count=len(urls),
        unique_count=len(unique_urls),
        duplicate_count=len(urls) - len(unique_urls),
        unique_urls=unique_urls,
        duplicates=duplicates,
    )


def generate_duplicate_report(urls: list[str]) -> list[DuplicateReport]:
    """
    生成重复 URL 报告

    Args:
        urls: URL 列表

    Returns:
        DuplicateReport 列表
    """
    dedup_result = detect_duplicates(urls)
    reports: list[DuplicateReport] = []

    for normalized_url, line_numbers in dedup_result.duplicates.items():
        # 获取原始 URL
        first_idx = line_numbers[0] - 1
        original_url = urls[first_idx]

        # 提取域名
        parsed = urlparse(original_url)
        domain = parsed.netloc

        reports.append(
            DuplicateReport(
                url=original_url,
                line_numbers=line_numbers,
                domain=domain,
                normalized_url=normalized_url,
            )
        )

    # 按出现次数排序
    reports.sort(key=lambda r: len(r.line_numbers), reverse=True)

    return reports


def format_duplicate_report(reports: list[DuplicateReport]) -> str:
    """
    格式化重复 URL 报告为文本

    Args:
        reports: DuplicateReport 列表

    Returns:
        格式化的文本报告
    """
    if not reports:
        return "✓ 未检测到重复 URL"

    lines = [
        "⚠ 检测到 {} 组重复 URL:".format(len(reports)),
        "",
    ]

    for idx, report in enumerate(reports, start=1):
        lines.append("{}. {}".format(idx, report.url))
        lines.append("   域名：{}".format(report.domain))
        lines.append("   出现位置：第 {} 行".format(", ".join(map(str, report.line_numbers))))
        if len(report.line_numbers) > 1:
            lines.append("   重复次数：{} 次".format(len(report.line_numbers)))
        lines.append("")

    return "\n".join(lines)


def load_urls_from_file(file_path: Path) -> list[str]:
    """
    从文件加载 URL 列表

    支持格式:
    - 每行一个 URL
    - 支持 # 注释
    - 支持行内注释 (# 后的内容被忽略)
    - 自动跳过空行

    Args:
        file_path: 文件路径

    Returns:
        URL 列表
    """
    path = file_path.expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError("URL 文件不存在：{}".format(path))

    urls: list[str] = []
    content = path.read_text(encoding="utf-8", errors="ignore")

    for line in content.splitlines():
        line = line.strip()

        # 跳过空行和注释行
        if not line or line.startswith("#"):
            continue

        # 处理行内注释
        if "#" in line:
            line = line.split("#", 1)[0].strip()

        # 验证 URL 格式
        if line.startswith(("http://", "https://")):
            urls.append(line)

    return urls


def remove_duplicates(urls: list[str]) -> list[str]:
    """
    移除重复的 URL，保持首次出现的顺序

    Args:
        urls: URL 列表

    Returns:
        去重后的 URL 列表
    """
    result = detect_duplicates(urls)
    return result.unique_urls


def check_url_file_duplicates(file_path: Path) -> tuple[list[str], str]:
    """
    检查文件中的 URL 重复情况

    Args:
        file_path: 文件路径

    Returns:
        (去重后的 URL 列表，报告文本)
    """
    urls = load_urls_from_file(file_path)
    reports = generate_duplicate_report(urls)
    report_text = format_duplicate_report(reports)

    unique_urls = remove_duplicates(urls)

    return unique_urls, report_text


# Update __all__ to export new functions
__all__ = [
    "URLDeduplicator",
    "DownloadHistoryEntry",
    "DownloadHistory",
    # New batch download functions
    "DedupResult",
    "DuplicateReport",
    "detect_duplicates",
    "generate_duplicate_report",
    "format_duplicate_report",
    "load_urls_from_file",
    "remove_duplicates",
    "check_url_file_duplicates",
    "deduplicate_urls",
    "find_session_duplicates",
    "normalize_url",
]
