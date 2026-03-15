"""PSiteDL 测试套件 - 共享 fixtures 和工具"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def temp_dir() -> Path:
    """创建临时目录用于测试"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_config(temp_dir: Path) -> dict[str, Any]:
    """示例配置数据"""
    return {
        "output_dir": str(temp_dir / "downloads"),
        "browser": "chrome",
        "profile": "Default",
        "concurrency": 3,
        "max_retries": 3,
        "timeout": 30,
        "log_level": "INFO",
        "log_file": str(temp_dir / "psitedl.log"),
    }


@pytest.fixture
def config_file(temp_dir: Path, sample_config: dict[str, Any]) -> Path:
    """创建临时配置文件"""
    config_path = temp_dir / "config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(sample_config, f, indent=2)
    return config_path


@pytest.fixture
def sample_html() -> str:
    """示例 HTML 页面内容"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>测试视频页面</title>
        <meta property="og:title" content="测试视频标题">
    </head>
    <body>
        <video src="https://example.com/video.mp4"></video>
        <source src="https://example.com/stream.m3u8">
        <script>
            var playlist = "https://example.com/playlist.m3u8";
        </script>
    </body>
    </html>
    """


@pytest.fixture
def sample_html_file(temp_dir: Path, sample_html: str) -> Path:
    """创建临时 HTML 文件"""
    html_path = temp_dir / "test_page.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(sample_html)
    return html_path


@pytest.fixture
def url_list_file(temp_dir: Path) -> Path:
    """创建 URL 列表文件"""
    urls = [
        "https://example.com/video1",
        "https://example.com/video2",
        "https://example.com/video3",
    ]
    url_file = temp_dir / "urls.txt"
    with open(url_file, "w", encoding="utf-8") as f:
        f.write("\n".join(urls))
    return url_file
