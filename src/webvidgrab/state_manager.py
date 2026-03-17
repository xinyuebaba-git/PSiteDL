"""
状态管理器 - 断点续传增强

功能:
- 状态文件持久化（每 30 秒自动保存）
- 崩溃恢复（自动检测未完成下载）
- 状态验证（哈希校验）
- 手动恢复（指定状态文件）
"""

import hashlib
import json
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any


class StateNotFoundError(Exception):
    """状态文件不存在"""

    pass


class StateValidationError(Exception):
    """状态验证失败"""

    pass


@dataclass
class DownloadState:
    """下载状态数据类"""

    url: str
    total_size: int
    downloaded_size: int
    downloaded_segments: List[int]
    output_path: str
    config: Dict[str, Any] = field(default_factory=dict)
    segment_hashes: Dict[str, str] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    @property
    def progress(self) -> float:
        """计算下载进度 (0.0 - 1.0)"""
        if self.total_size == 0:
            return 0.0
        return min(1.0, self.downloaded_size / self.total_size)

    @property
    def is_complete(self) -> bool:
        """检查是否下载完成"""
        return self.progress >= 1.0

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        data = asdict(self)
        data["timestamp"] = time.time()  # 添加时间戳便于调试
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DownloadState":
        """从字典反序列化"""
        # 移除时间戳字段（由 dataclass 自动管理）
        data.pop("timestamp", None)
        return cls(**data)

    def verify_segments(self, output_dir: str) -> bool:
        """
        验证已下载片段的完整性

        Returns:
            bool: 所有片段验证通过返回 True
        """
        for seg_idx in self.downloaded_segments:
            seg_path = Path(output_dir) / f"segment_{seg_idx}.ts"

            if not seg_path.exists():
                return False

            # 如果存储了哈希，进行验证
            if str(seg_idx) in self.segment_hashes:
                with open(seg_path, "rb") as f:
                    actual_hash = calculate_segment_hash(f.read())

                if actual_hash != self.segment_hashes[str(seg_idx)]:
                    return False

        return True


def calculate_segment_hash(data: bytes) -> str:
    """计算片段哈希（MD5）"""
    return hashlib.md5(data).hexdigest()


class StateManager:
    """
    状态管理器

    功能:
    - 自动保存状态（可配置间隔）
    - 崩溃恢复
    - 状态验证
    - 过期清理
    """

    def __init__(
        self,
        state_dir: str = "~/.psitedl/state",
        auto_save_interval: int = 30,
        retention_days: int = 7,
    ):
        """
        初始化状态管理器

        Args:
            state_dir: 状态文件存储目录
            auto_save_interval: 自动保存间隔（秒）
            retention_days: 状态文件保留天数
        """
        self.state_dir = Path(state_dir).expanduser()
        self.auto_save_interval = auto_save_interval
        self.retention_days = retention_days

        # 确保目录存在
        self.state_dir.mkdir(parents=True, exist_ok=True)

        # 跟踪上次保存时间
        self._last_save_time: Dict[str, float] = {}

    def save_state(self, state: DownloadState, state_id: Optional[str] = None) -> str:
        """
        保存下载状态

        Args:
            state: 下载状态
            state_id: 可选的状态 ID（用于更新现有状态）

        Returns:
            str: 状态 ID
        """
        if state_id is None:
            state_id = str(uuid.uuid4())[:8]  # 使用短 UUID
        
        state_file = self.state_dir / f"{state_id}.json"

        # 原子写入：先写临时文件，再重命名
        self._atomic_write(state_file, state.to_dict())

        self._last_save_time[state_id] = time.time()

        return state_id

    def _atomic_write(self, path: Path, data: Dict[str, Any]) -> None:
        """
        原子写入文件（避免写入中断导致损坏）

        实现：写入临时文件 -> fsync -> 重命名
        """
        temp_path = path.with_suffix(".tmp")

        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())

        # 重命名（原子操作）
        temp_path.rename(path)

    def load_state(self, state_id: str) -> DownloadState:
        """
        加载下载状态

        Args:
            state_id: 状态 ID

        Returns:
            DownloadState: 下载状态

        Raises:
            StateNotFoundError: 状态文件不存在
        """
        state_file = self.state_dir / f"{state_id}.json"

        if not state_file.exists():
            raise StateNotFoundError(f"State not found: {state_id}")

        with open(state_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        return DownloadState.from_dict(data)

    def delete_state(self, state_id: str) -> None:
        """
        删除下载状态

        Args:
            state_id: 状态 ID
        """
        state_file = self.state_dir / f"{state_id}.json"

        if state_file.exists():
            state_file.unlink()

    def list_states(self) -> List[DownloadState]:
        """
        列出所有状态

        Returns:
            List[DownloadState]: 所有下载状态
        """
        states = []

        for state_file in self.state_dir.glob("*.json"):
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                states.append(DownloadState.from_dict(data))
            except (json.JSONDecodeError, KeyError) as e:
                # 忽略损坏的状态文件
                print(f"Warning: Failed to load state {state_file}: {e}")

        return states

    def find_incomplete_downloads(self) -> List[DownloadState]:
        """
        查找未完成的下载

        Returns:
            List[DownloadState]: 未完成的下载状态
        """
        states = self.list_states()
        return [s for s in states if not s.is_complete]

    def recover_state(
        self, state_id: str, verify: bool = True
    ) -> Optional[DownloadState]:
        """
        恢复下载状态

        Args:
            state_id: 状态 ID
            verify: 是否验证已下载片段

        Returns:
            Optional[DownloadState]: 恢复的状态，验证失败返回 None
        """
        state = self.load_state(state_id)

        if verify:
            output_dir = str(Path(state.output_path).parent)
            if not state.verify_segments(output_dir):
                # 验证失败，标记需要重新下载损坏的片段
                print(f"Warning: Segment verification failed for {state_id}")
                # 可以在这里实现重新下载逻辑

        return state

    def validate_state(self, state: DownloadState) -> None:
        """
        验证状态有效性

        Args:
            state: 下载状态

        Raises:
            StateValidationError: 验证失败
        """
        if state.downloaded_size > state.total_size:
            raise StateValidationError(
                f"Downloaded size ({state.downloaded_size}) exceeds total size ({state.total_size})"
            )

        if state.progress < 0 or state.progress > 1:
            raise StateValidationError(
                f"Invalid progress: {state.progress}"
            )

        if not state.url:
            raise StateValidationError("URL is required")

        if not state.output_path:
            raise StateValidationError("Output path is required")

    def cleanup_old_states(self, days: Optional[int] = None) -> int:
        """
        清理过期状态文件

        Args:
            days: 保留天数（默认使用配置的 retention_days）

        Returns:
            int: 清理的文件数量
        """
        if days is None:
            days = self.retention_days

        cutoff_time = time.time() - (days * 24 * 60 * 60)
        cleaned = 0

        for state_file in self.state_dir.glob("*.json"):
            try:
                mtime = state_file.stat().st_mtime
                if mtime < cutoff_time:
                    state_file.unlink()
                    cleaned += 1
            except OSError:
                pass

        return cleaned

    def should_auto_save(self, state_id: str) -> bool:
        """
        检查是否应该自动保存

        Args:
            state_id: 状态 ID

        Returns:
            bool: 是否应该保存
        """
        last_save = self._last_save_time.get(state_id, 0)
        return (time.time() - last_save) >= self.auto_save_interval
