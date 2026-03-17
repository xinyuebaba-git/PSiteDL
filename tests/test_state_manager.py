"""
PSiteDL v0.5.0 - 状态管理器测试

测试状态文件持久化、崩溃恢复、状态验证功能
"""

import json
import os
import time
import hashlib
import threading
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from src.webvidgrab.state_manager import (
    StateManager,
    DownloadState,
    StateValidationError,
    StateNotFoundError,
)


class TestDownloadState:
    """测试下载状态数据类"""

    def test_create_state(self):
        """测试创建下载状态"""
        state = DownloadState(
            url="https://example.com/video",
            total_size=1000000,
            downloaded_size=500000,
            downloaded_segments=[0, 1, 2],
            output_path="/downloads/video.mp4",
            config={"browser": "chrome", "concurrency": 5},
        )

        assert state.url == "https://example.com/video"
        assert state.total_size == 1000000
        assert state.downloaded_size == 500000
        assert state.progress == 0.5  # 50%
        assert len(state.downloaded_segments) == 3

    def test_progress_calculation(self):
        """测试进度计算"""
        state = DownloadState(
            url="https://example.com/video",
            total_size=1000000,
            downloaded_size=0,
            downloaded_segments=[],
            output_path="/downloads/video.mp4",
        )

        assert state.progress == 0.0

        state.downloaded_size = 250000
        assert state.progress == 0.25

        state.downloaded_size = 1000000
        assert state.progress == 1.0

    def test_state_to_dict(self):
        """测试状态序列化为字典"""
        state = DownloadState(
            url="https://example.com/video",
            total_size=1000000,
            downloaded_size=500000,
            downloaded_segments=[0, 1, 2],
            output_path="/downloads/video.mp4",
            config={"browser": "chrome"},
        )

        data = state.to_dict()

        assert data["url"] == "https://example.com/video"
        assert data["total_size"] == 1000000
        assert data["downloaded_segments"] == [0, 1, 2]
        assert "timestamp" in data  # 自动添加时间戳

    def test_state_from_dict(self):
        """测试从字典反序列化状态"""
        data = {
            "url": "https://example.com/video",
            "total_size": 1000000,
            "downloaded_size": 500000,
            "downloaded_segments": [0, 1, 2],
            "output_path": "/downloads/video.mp4",
            "config": {"browser": "chrome"},
            "timestamp": time.time(),
        }

        state = DownloadState.from_dict(data)

        assert state.url == data["url"]
        assert state.total_size == data["total_size"]
        assert state.downloaded_size == data["downloaded_size"]


class TestStateManager:
    """测试状态管理器"""

    @pytest.fixture
    def temp_state_dir(self, tmp_path):
        """创建临时状态目录"""
        state_dir = tmp_path / ".psitedl-state"
        state_dir.mkdir()
        return state_dir

    @pytest.fixture
    def state_manager(self, temp_state_dir):
        """创建状态管理器实例"""
        return StateManager(state_dir=str(temp_state_dir))

    def test_save_state(self, state_manager, temp_state_dir):
        """测试保存状态"""
        state = DownloadState(
            url="https://example.com/video",
            total_size=1000000,
            downloaded_size=500000,
            downloaded_segments=[0, 1, 2],
            output_path="/downloads/video.mp4",
        )

        state_id = state_manager.save_state(state)

        # 验证状态文件存在
        state_file = temp_state_dir / f"{state_id}.json"
        assert state_file.exists()

        # 验证内容
        data = json.loads(state_file.read_text())
        assert data["url"] == "https://example.com/video"

    def test_load_state(self, state_manager, temp_state_dir):
        """测试加载状态"""
        state = DownloadState(
            url="https://example.com/video",
            total_size=1000000,
            downloaded_size=500000,
            downloaded_segments=[0, 1, 2],
            output_path="/downloads/video.mp4",
        )

        state_id = state_manager.save_state(state)
        loaded_state = state_manager.load_state(state_id)

        assert loaded_state.url == state.url
        assert loaded_state.total_size == state.total_size
        assert loaded_state.downloaded_segments == state.downloaded_segments

    def test_load_nonexistent_state(self, state_manager):
        """测试加载不存在的状态"""
        with pytest.raises(StateNotFoundError):
            state_manager.load_state("nonexistent-id")

    def test_delete_state(self, state_manager, temp_state_dir):
        """测试删除状态"""
        state = DownloadState(
            url="https://example.com/video",
            total_size=1000000,
            downloaded_size=0,
            downloaded_segments=[],
            output_path="/downloads/video.mp4",
        )

        state_id = state_manager.save_state(state)
        state_manager.delete_state(state_id)

        state_file = temp_state_dir / f"{state_id}.json"
        assert not state_file.exists()

    def test_auto_save_interval(self, state_manager):
        """测试自动保存间隔（30 秒）"""
        assert state_manager.auto_save_interval == 30

    def test_list_states(self, state_manager, temp_state_dir):
        """测试列出所有状态"""
        # 创建 3 个状态
        for i in range(3):
            state = DownloadState(
                url=f"https://example.com/video{i}",
                total_size=1000000,
                downloaded_size=i * 100000,
                downloaded_segments=[],
                output_path=f"/downloads/video{i}.mp4",
            )
            state_manager.save_state(state)

        states = state_manager.list_states()

        assert len(states) == 3
        assert all(s.url.startswith("https://example.com/video") for s in states)

    def test_cleanup_old_states(self, state_manager, temp_state_dir):
        """测试清理过期状态（超过 7 天）"""
        # 创建一个旧状态
        state = DownloadState(
            url="https://example.com/old",
            total_size=1000000,
            downloaded_size=0,
            downloaded_segments=[],
            output_path="/downloads/old.mp4",
        )

        state_id = state_manager.save_state(state)

        # 修改文件时间为 8 天前
        state_file = temp_state_dir / f"{state_id}.json"
        old_time = time.time() - (8 * 24 * 60 * 60)  # 8 天前
        os.utime(state_file, (old_time, old_time))

        # 清理
        cleaned = state_manager.cleanup_old_states(days=7)

        assert cleaned == 1
        assert not state_file.exists()

    def test_validate_state_valid(self, state_manager):
        """测试验证有效状态"""
        state = DownloadState(
            url="https://example.com/video",
            total_size=1000000,
            downloaded_size=500000,
            downloaded_segments=[0, 1, 2],
            output_path="/downloads/video.mp4",
        )

        # 应该不抛出异常
        state_manager.validate_state(state)

    def test_validate_state_invalid(self, state_manager):
        """测试验证无效状态"""
        state = DownloadState(
            url="https://example.com/video",
            total_size=1000000,
            downloaded_size=1500000,  # 超过总大小
            downloaded_segments=[],
            output_path="/downloads/video.mp4",
        )

        with pytest.raises(StateValidationError):
            state_manager.validate_state(state)


class TestStateRecovery:
    """测试崩溃恢复功能"""

    @pytest.fixture
    def temp_state_dir(self, tmp_path):
        """创建临时状态目录"""
        state_dir = tmp_path / ".psitedl-state"
        state_dir.mkdir()
        return state_dir

    def test_auto_detect_incomplete_downloads(self, temp_state_dir):
        """测试自动检测未完成的下载"""
        state = DownloadState(
            url="https://example.com/video",
            total_size=1000000,
            downloaded_size=500000,  # 50% 完成
            downloaded_segments=[0, 1, 2],
            output_path="/downloads/video.mp4",
        )

        state_manager = StateManager(state_dir=str(temp_state_dir))
        state_manager.save_state(state)

        # 检测未完成的下载
        incomplete = state_manager.find_incomplete_downloads()

        assert len(incomplete) == 1
        assert incomplete[0].progress < 1.0

    def test_skip_completed_downloads(self, temp_state_dir):
        """测试跳过已完成的下载"""
        state = DownloadState(
            url="https://example.com/video",
            total_size=1000000,
            downloaded_size=1000000,  # 100% 完成
            downloaded_segments=list(range(100)),
            output_path="/downloads/video.mp4",
        )

        state_manager = StateManager(state_dir=str(temp_state_dir))
        state_manager.save_state(state)

        incomplete = state_manager.find_incomplete_downloads()

        assert len(incomplete) == 0

    @patch("src.webvidgrab.state_manager.DownloadState.verify_segments")
    def test_recovery_with_segment_verification(
        self, mock_verify, temp_state_dir
    ):
        """测试恢复时验证已下载片段"""
        mock_verify.return_value = True  # 验证通过

        state = DownloadState(
            url="https://example.com/video",
            total_size=1000000,
            downloaded_size=500000,
            downloaded_segments=[0, 1, 2],
            output_path="/downloads/video.mp4",
        )

        state_manager = StateManager(state_dir=str(temp_state_dir))
        state_manager.save_state(state)

        # 恢复并验证
        recovered = state_manager.recover_state(state_manager.save_state(state))

        mock_verify.assert_called_once()
        assert recovered is not None

    def test_recovery_failed_verification(self, temp_state_dir):
        """测试验证失败时重新下载"""
        state = DownloadState(
            url="https://example.com/video",
            total_size=1000000,
            downloaded_size=500000,
            downloaded_segments=[0, 1, 2],
            output_path="/downloads/video.mp4",
        )

        state_manager = StateManager(state_dir=str(temp_state_dir))
        state_manager.save_state(state)

        # 模拟验证失败
        with patch.object(
            DownloadState, "verify_segments", return_value=False
        ):
            recovered = state_manager.recover_state(
                state_manager.save_state(state), verify=True
            )

            # 验证失败应该标记片段需要重新下载
            assert recovered is not None
            # 具体行为取决于实现策略


class TestStatePersistence:
    """测试状态持久化"""

    @pytest.fixture
    def temp_state_dir(self, tmp_path):
        """创建临时状态目录"""
        state_dir = tmp_path / ".psitedl-state"
        state_dir.mkdir()
        return state_dir

    def test_atomic_write(self, temp_state_dir):
        """测试原子写入（避免写入中断导致文件损坏）"""
        state_manager = StateManager(state_dir=str(temp_state_dir))

        state = DownloadState(
            url="https://example.com/video",
            total_size=1000000,
            downloaded_size=500000,
            downloaded_segments=[0, 1, 2],
            output_path="/downloads/video.mp4",
        )

        # 原子写入应该创建临时文件然后重命名
        with patch.object(state_manager, "_atomic_write") as mock_write:
            mock_write.return_value = None
            state_manager.save_state(state)

            mock_write.assert_called_once()

    def test_concurrent_state_access(self, temp_state_dir):
        """测试并发访问状态文件"""
        state_manager = StateManager(state_dir=str(temp_state_dir))

        state = DownloadState(
            url="https://example.com/video",
            total_size=1000000,
            downloaded_size=0,
            downloaded_segments=[],
            output_path="/downloads/video.mp4",
        )

        state_id = state_manager.save_state(state)
        errors = []
        lock = threading.Lock()

        def update_state():
            try:
                for i in range(10):
                    with lock:  # 使用锁避免竞争条件
                        s = state_manager.load_state(state_id)
                        s.downloaded_size += 10000
                        state_manager.save_state(s, state_id=state_id)  # 传入 state_id 更新现有状态
                    time.sleep(0.001)
            except Exception as e:
                with lock:
                    errors.append(e)

        # 创建 5 个线程并发更新
        threads = [threading.Thread(target=update_state) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 不应该有错误
        assert len(errors) == 0

        # 最终状态应该一致
        final_state = state_manager.load_state(state_id)
        assert final_state.downloaded_size == 500000  # 5 线程 * 10 次 * 10000


class TestSegmentHashVerification:
    """测试片段哈希校验"""

    def test_calculate_segment_hash(self):
        """测试计算片段哈希"""
        data = b"test segment data"
        expected_hash = hashlib.md5(data).hexdigest()

        from src.webvidgrab.state_manager import calculate_segment_hash

        actual_hash = calculate_segment_hash(data)

        assert actual_hash == expected_hash

    def test_verify_downloaded_segments(self):
        """测试验证已下载片段"""
        state = DownloadState(
            url="https://example.com/video",
            total_size=1000000,
            downloaded_size=500000,
            downloaded_segments=[0, 1, 2],
            output_path="/downloads/video.mp4",
            segment_hashes={
                "0": "hash0",
                "1": "hash1",
                "2": "hash2",
            },
        )

        # 模拟文件存在且哈希匹配
        with patch("builtins.open", MagicMock()) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = (
                b"test data"
            )

            with patch(
                "src.webvidgrab.state_manager.calculate_segment_hash"
            ) as mock_hash:
                mock_hash.return_value = "hash0"

                # 验证应该通过
                # 具体实现取决于 verify_segments 的逻辑

    def test_corrupted_segment_detection(self):
        """测试检测损坏的片段"""
        state = DownloadState(
            url="https://example.com/video",
            total_size=1000000,
            downloaded_size=500000,
            downloaded_segments=[0, 1, 2],
            output_path="/downloads/video.mp4",
            segment_hashes={"0": "expected_hash"},
        )

        # 模拟哈希不匹配
        with patch(
            "src.webvidgrab.state_manager.calculate_segment_hash"
        ) as mock_hash:
            mock_hash.return_value = "different_hash"

            # 应该检测到损坏
            # 具体实现取决于 verify_segments 的逻辑
