"""进度显示模块测试 - TDD 驱动开发"""

from __future__ import annotations

import io
import time
from pathlib import Path


class TestDownloadProgress:
    """下载进度测试"""

    def test_progress_initialization(self) -> None:
        """进度初始化"""
        from webvidgrab.progress import DownloadProgress

        progress = DownloadProgress(total=1000)
        assert progress.total == 1000
        assert progress.current == 0
        assert progress.percentage == 0.0

    def test_progress_update(self) -> None:
        """进度更新"""
        from webvidgrab.progress import DownloadProgress

        progress = DownloadProgress(total=1000)
        progress.update(500)
        assert progress.current == 500
        assert progress.percentage == 50.0

    def test_progress_complete(self) -> None:
        """进度完成"""
        from webvidgrab.progress import DownloadProgress

        progress = DownloadProgress(total=1000)
        progress.update(1000)
        assert progress.is_complete()
        assert progress.percentage == 100.0

    def test_progress_speed_calculation(self) -> None:
        """速度计算"""
        from webvidgrab.progress import DownloadProgress

        progress = DownloadProgress(total=1000)
        progress.start_time = time.time() - 10  # 10 秒前开始
        progress.update(500)

        speed = progress.get_speed()
        assert speed > 0  # bytes per second

    def test_progress_eta(self) -> None:
        """预计剩余时间"""
        from webvidgrab.progress import DownloadProgress

        progress = DownloadProgress(total=1000)
        progress.start_time = time.time() - 10
        progress.update(500)

        eta = progress.get_eta()
        assert eta > 0  # seconds


class TestProgressBarDisplay:
    """进度条显示测试"""

    def test_text_progress_bar(self) -> None:
        """文本进度条"""
        from webvidgrab.progress import render_progress_bar

        bar = render_progress_bar(50, 100, width=20)
        assert "█" in bar or "#" in bar or "=" in bar
        assert len(bar) >= 20

    def test_rich_progress_bar(self) -> None:
        """Rich 库进度条"""
        from webvidgrab.progress import RichProgressDisplay

        output = io.StringIO()
        display = RichProgressDisplay(output=output)
        display.start_task("download", total=1000)
        display.update_task("download", completed=500)
        display.stop()

    def test_progress_with_filename(self) -> None:
        """带文件名的进度显示"""
        from webvidgrab.progress import render_progress_info

        info = render_progress_info(
            filename="video.mp4",
            current=500,
            total=1000,
            speed=100,
            eta=5,
        )
        assert "video.mp4" in info
        assert "50%" in info or "50.0%" in info


class TestMultiFileProgress:
    """多文件进度测试"""

    def test_multi_progress_tracker(self) -> None:
        """多文件进度跟踪"""
        from webvidgrab.progress import MultiProgressTracker

        tracker = MultiProgressTracker(total_files=3)
        tracker.add_file("file1.mp4", 1000)
        tracker.add_file("file2.mp4", 2000)
        tracker.add_file("file3.mp4", 1500)

        assert tracker.total_files == 3
        assert tracker.overall_percentage() == 0.0

    def test_multi_progress_update(self) -> None:
        """多文件进度更新"""
        from webvidgrab.progress import MultiProgressTracker

        tracker = MultiProgressTracker(total_files=2)
        tracker.add_file("file1.mp4", 1000)
        tracker.add_file("file2.mp4", 1000)

        tracker.update_file("file1.mp4", 500)
        assert tracker.overall_percentage() == 25.0

        tracker.update_file("file2.mp4", 1000)
        assert tracker.overall_percentage() == 75.0

    def test_multi_progress_summary(self) -> None:
        """多文件进度摘要"""
        from webvidgrab.progress import MultiProgressTracker

        tracker = MultiProgressTracker(total_files=3)
        tracker.add_file("file1.mp4", 1000)
        tracker.add_file("file2.mp4", 1000)
        tracker.add_file("file3.mp4", 1000)

        tracker.update_file("file1.mp4", 1000)  # 完成
        tracker.update_file("file2.mp4", 500)  # 50%
        # file3 未开始

        summary = tracker.get_summary()
        assert "completed" in summary or "total" in summary


class TestProgressPersistence:
    """进度持久化测试"""

    def test_save_progress_state(self, temp_dir: Path) -> None:
        """保存进度状态"""
        from webvidgrab.progress import DownloadProgress, save_progress

        progress = DownloadProgress(total=1000)
        progress.update(500)

        state_file = temp_dir / "progress.json"
        save_progress(progress, state_file)

        assert state_file.exists()

    def test_resume_progress(self, temp_dir: Path) -> None:
        """恢复进度"""
        from webvidgrab.progress import DownloadProgress, load_progress, save_progress

        progress = DownloadProgress(total=1000)
        progress.update(750)

        state_file = temp_dir / "progress.json"
        save_progress(progress, state_file)

        resumed = load_progress(state_file)
        assert resumed.total == 1000
        assert resumed.current == 750


class TestProgressCallback:
    """进度回调测试"""

    def test_progress_callback(self) -> None:
        """进度回调函数"""
        from webvidgrab.progress import DownloadProgress

        callback_called = []

        def callback(progress: DownloadProgress):
            callback_called.append(progress.percentage)

        progress = DownloadProgress(total=100, callback=callback)
        progress.update(25)
        progress.update(50)

        assert len(callback_called) == 2
        assert 25.0 in callback_called
        assert 50.0 in callback_called
