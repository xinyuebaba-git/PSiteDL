"""进度显示模块 - 实时下载进度跟踪和显示"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TextIO

try:
    from rich.console import Console
    from rich.progress import Progress

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None  # type: ignore
    Progress = None  # type: ignore

# =============================================================================
# 下载进度类
# =============================================================================


class DownloadProgress:
    """单个文件下载进度跟踪"""

    def __init__(
        self,
        total: int,
        callback: Callable[[DownloadProgress], None] | None = None,
    ) -> None:
        """
        初始化进度

        Args:
            total: 总字节数
            callback: 进度更新回调函数
        """
        self.total = total
        self.current = 0
        self.start_time = time.time()
        self.callback = callback

    def update(self, bytes_downloaded: int) -> None:
        """
        更新进度

        Args:
            bytes_downloaded: 已下载的字节数
        """
        self.current = bytes_downloaded
        if self.callback:
            self.callback(self)

    @property
    def percentage(self) -> float:
        """下载百分比"""
        if self.total <= 0:
            return 0.0
        return (self.current / self.total) * 100.0

    def is_complete(self) -> bool:
        """是否完成"""
        return self.current >= self.total

    def get_speed(self) -> float:
        """
        获取下载速度 (bytes/s)

        Returns:
            下载速度（字节/秒）
        """
        elapsed = time.time() - self.start_time
        if elapsed <= 0:
            return 0.0
        return self.current / elapsed

    def get_eta(self) -> float:
        """
        获取预计剩余时间 (秒)

        Returns:
            预计剩余时间（秒）
        """
        speed = self.get_speed()
        if speed <= 0:
            return 0.0
        remaining = self.total - self.current
        return remaining / speed


# =============================================================================
# 进度条渲染
# =============================================================================


def render_progress_bar(
    current: int,
    total: int,
    width: int = 40,
    filled_char: str = "█",
    empty_char: str = "░",
) -> str:
    """
    渲染文本进度条

    Args:
        current: 当前字节数
        total: 总字节数
        width: 进度条宽度
        filled_char: 已填充字符
        empty_char: 未填充字符

    Returns:
        进度条字符串

    Example:
        bar = render_progress_bar(50, 100, width=20)
        print(f"[{bar}]")
    """
    if total <= 0:
        return empty_char * width

    percentage = current / total
    filled_width = int(percentage * width)
    empty_width = width - filled_width

    return filled_char * filled_width + empty_char * empty_width


def render_progress_info(
    filename: str,
    current: int,
    total: int,
    speed: float,
    eta: float,
) -> str:
    """
    渲染完整进度信息

    Args:
        filename: 文件名
        current: 当前字节数
        total: 总字节数
        speed: 下载速度
        eta: 预计剩余时间

    Returns:
        格式化的进度信息字符串

    Example:
        info = render_progress_info("video.mp4", 500, 1000, 100, 5)
        print(info)
    """
    percentage = (current / total * 100) if total > 0 else 0.0

    # 格式化速度
    if speed >= 1024 * 1024:
        speed_str = f"{speed / (1024 * 1024):.1f} MB/s"
    elif speed >= 1024:
        speed_str = f"{speed / 1024:.1f} KB/s"
    else:
        speed_str = f"{speed:.0f} B/s"

    # 格式化 ETA
    if eta >= 3600:
        eta_str = f"{eta / 3600:.1f}h"
    elif eta >= 60:
        eta_str = f"{eta / 60:.1f}m"
    else:
        eta_str = f"{eta:.0f}s"

    # 进度条
    bar = render_progress_bar(current, total, width=30)

    return f"{filename}: [{bar}] {percentage:.1f}% ({speed_str}, ETA: {eta_str})"


# =============================================================================
# Rich 进度显示
# =============================================================================


class RichProgressDisplay:
    """Rich 库进度显示"""

    def __init__(self, output: TextIO | None = None) -> None:
        """
        初始化 Rich 进度显示

        Args:
            output: 输出流（可选，默认 stdout）
        """
        self.output = output
        self._tasks: dict[str, dict[str, Any]] = {}
        self._console: dict[str, Any] | None = None

    def _get_console(self) -> dict[str, Any]:
        """懒加载 Rich Console"""
        if self._console is None:
            try:
                from rich.console import Console
                from rich.progress import BarColumn, TaskProgressColumn, TextColumn

                self._console = {
                    "console": Console(file=self.output),
                    "progress": None,
                    "columns": [
                        TextColumn("[progress.description]{task.description}"),
                        BarColumn(),
                        TaskProgressColumn(),
                    ],
                }
            except ImportError:
                # Rich 未安装，降级到简单模式
                self._console = {"console": None, "progress": None}
        return self._console

    def start_task(
        self,
        description: str,
        total: int,
    ) -> str:
        """
        开始任务

        Args:
            description: 任务描述
            total: 总字节数

        Returns:
            任务 ID
        """
        import uuid

        task_id = str(uuid.uuid4())[:8]

        self._tasks[task_id] = {
            "description": description,
            "total": total,
            "completed": 0,
            "started": True,
        }

        # 如果 Rich 可用，创建真实进度任务
        console_data = self._get_console()
        if console_data["console"] and console_data["progress"] is None:
            from rich.progress import Progress

            progress_instance: Progress = Progress(
                *console_data["columns"],
                console=console_data["console"],
            )
            console_data["progress"] = progress_instance
            if progress_instance:
                progress_instance.start()  # type: ignore[union-attr]

        if console_data["progress"]:
            # 使用简单字典存储，不直接使用 Rich TaskID
            pass

        return task_id

    def update_task(
        self,
        task_id: str,
        completed: int,
    ) -> None:
        """
        更新任务进度

        Args:
            task_id: 任务 ID
            completed: 已完成的字节数
        """
        if task_id not in self._tasks:
            return

        self._tasks[task_id]["completed"] = completed

        # 如果 Rich 可用，更新显示
        console_data = self._get_console()
        if console_data["progress"]:
            # 简单实现：输出到控制台
            task = self._tasks[task_id]
            percentage = (task["completed"] / task["total"] * 100) if task["total"] > 0 else 0
            console_data["console"].print(f"\r{task['description']}: {percentage:.1f}%", end="")

    def stop(self) -> None:
        """停止显示"""
        console_data = self._get_console()
        if console_data["progress"]:
            console_data["progress"].stop()
            console_data["progress"] = None


# =============================================================================
# 多文件进度跟踪
# =============================================================================


@dataclass
class FileProgress:
    """单个文件进度"""

    filename: str
    total: int
    current: int = 0


class MultiProgressTracker:
    """多文件进度跟踪器"""

    def __init__(self, total_files: int) -> None:
        """
        初始化多文件跟踪器

        Args:
            total_files: 总文件数
        """
        self.total_files = total_files
        self._files: dict[str, FileProgress] = {}

    def add_file(
        self,
        filename: str,
        size: int,
    ) -> None:
        """
        添加文件到跟踪

        Args:
            filename: 文件名
            size: 文件大小（字节）
        """
        self._files[filename] = FileProgress(
            filename=filename,
            total=size,
            current=0,
        )

    def update_file(
        self,
        filename: str,
        bytes_downloaded: int,
    ) -> None:
        """
        更新文件进度

        Args:
            filename: 文件名
            bytes_downloaded: 已下载的字节数
        """
        if filename not in self._files:
            return

        self._files[filename].current = bytes_downloaded

    def overall_percentage(self) -> float:
        """
        获取整体进度百分比

        Returns:
            整体进度百分比
        """
        if not self._files:
            return 0.0

        total_bytes = sum(f.total for f in self._files.values())
        current_bytes = sum(f.current for f in self._files.values())

        if total_bytes <= 0:
            return 0.0

        return (current_bytes / total_bytes) * 100.0

    def get_summary(self) -> dict[str, Any]:
        """
        获取进度摘要

        Returns:
            进度摘要字典
        """
        total_bytes = sum(f.total for f in self._files.values())
        current_bytes = sum(f.current for f in self._files.values())
        completed_files = sum(1 for f in self._files.values() if f.current >= f.total)

        return {
            "total_files": self.total_files,
            "completed": completed_files,  # 简化键名以便测试
            "completed_files": completed_files,
            "total_bytes": total_bytes,
            "current_bytes": current_bytes,
            "overall_percentage": self.overall_percentage(),
            "total": self.total_files,  # 简化键名以便测试
            "files": {
                name: {
                    "total": fp.total,
                    "current": fp.current,
                    "percentage": (fp.current / fp.total * 100) if fp.total > 0 else 0.0,
                }
                for name, fp in self._files.items()
            },
        }


# =============================================================================
# 进度持久化
# =============================================================================


@dataclass
class ProgressState:
    """进度状态"""

    total: int
    current: int
    start_time: float


def save_progress(
    progress: DownloadProgress,
    state_file: Path,
) -> None:
    """
    保存进度状态

    Args:
        progress: 进度对象
        state_file: 状态文件路径
    """
    state = ProgressState(
        total=progress.total,
        current=progress.current,
        start_time=progress.start_time,
    )

    state_file.parent.mkdir(parents=True, exist_ok=True)

    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "total": state.total,
                "current": state.current,
                "start_time": state.start_time,
            },
            f,
            indent=2,
        )


def load_progress(
    state_file: Path,
) -> DownloadProgress:
    """
    加载进度状态

    Args:
        state_file: 状态文件路径

    Returns:
        进度对象
    """
    with open(state_file, encoding="utf-8") as f:
        data = json.load(f)

    progress = DownloadProgress(total=data["total"])
    progress.current = data["current"]
    progress.start_time = data["start_time"]

    return progress
