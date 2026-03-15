# PSiteDL GUI 状态管理方案

**文档版本**: 1.0  
**创建日期**: 2026-03-15  
**关联文档**: [GUI_ARCH_REVIEW.md](GUI_ARCH_REVIEW.md), [GUI_COMPONENT_SPLIT.md](GUI_COMPONENT_SPLIT.md)

---

## 📋 概述

本文档详细描述 PSiteDL GUI 的状态管理方案，包括状态定义、状态机设计、持久化策略和事件驱动更新机制。

### 设计目标

1. **单一数据源** - 所有状态集中在 `TaskManager` 中管理
2. **状态流转可追溯** - 记录每次状态变更历史
3. **线程安全** - 支持工作线程和 UI 线程并发访问
4. **可持久化** - 支持应用重启后恢复状态
5. **事件驱动** - 状态变更自动触发 UI 更新

---

## 🎯 状态定义

### 任务状态枚举

```python
from enum import Enum, auto


class TaskStatus(Enum):
    """
    任务状态枚举
    
    状态流转:
    PENDING → RUNNING → DONE
                       → FAILED → PENDING (重试)
                       → RETRYING → PENDING
    """
    
    PENDING = auto()    # 待下载 - 任务已创建，等待调度
    RUNNING = auto()    # 下载中 - 正在执行下载
    DONE = auto()       # 已完成 - 下载成功
    FAILED = auto()     # 失败 - 下载失败 (可重试)
    RETRYING = auto()   # 重试中 - 等待重试调度
    PAUSED = auto()     # 已暂停 - 用户手动暂停 (未来扩展)
```

### 状态说明

| 状态 | 说明 | 可流转到 | 终态 |
|------|------|----------|------|
| PENDING | 待下载 | RUNNING, FAILED | ❌ |
| RUNNING | 下载中 | DONE, FAILED, RETRYING, PAUSED | ❌ |
| DONE | 已完成 | 无 | ✅ |
| FAILED | 失败 | PENDING (手动重试) | ❌ |
| RETRYING | 重试中 | PENDING, FAILED | ❌ |
| PAUSED | 已暂停 | RUNNING, FAILED | ❌ |

---

## 🏗️ 状态机设计

### 状态流转规则

```python
from typing import Dict, Set

# 状态流转规则定义
STATE_TRANSITIONS: Dict[TaskStatus, Set[TaskStatus]] = {
    TaskStatus.PENDING: {
        TaskStatus.RUNNING,    # 开始下载
        TaskStatus.FAILED,     # 验证失败
    },
    TaskStatus.RUNNING: {
        TaskStatus.DONE,       # 下载完成
        TaskStatus.FAILED,     # 下载错误
        TaskStatus.RETRYING,   # 准备重试
        TaskStatus.PAUSED,     # 用户暂停
    },
    TaskStatus.RETRYING: {
        TaskStatus.PENDING,    # 重试排队
        TaskStatus.FAILED,     # 重试用尽
    },
    TaskStatus.PAUSED: {
        TaskStatus.RUNNING,    # 用户恢复
        TaskStatus.FAILED,     # 暂停错误
    },
    TaskStatus.DONE: set(),    # 终态，不可流转
    TaskStatus.FAILED: {
        TaskStatus.PENDING,    # 手动重试
    },
}
```

### 状态机实现

```python
"""任务状态机模块"""

import time
from dataclasses import dataclass, field
from typing import Optional, List

from .types import TaskStatus, STATE_TRANSITIONS


@dataclass
class StateTransition:
    """
    状态流转记录
    
    Attributes:
        task_id: 任务 ID
        from_status: 原状态
        to_status: 新状态
        timestamp: 流转时间戳
        reason: 流转原因
        metadata: 额外元数据
    """
    task_id: int
    from_status: TaskStatus
    to_status: TaskStatus
    timestamp: float = field(default_factory=time.time)
    reason: str = ""
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """转换为字典 (用于序列化)"""
        return {
            "task_id": self.task_id,
            "from_status": self.from_status.name,
            "to_status": self.to_status.name,
            "timestamp": self.timestamp,
            "reason": self.reason,
            "metadata": self.metadata,
        }


class InvalidStateTransition(Exception):
    """非法状态流转异常"""
    pass


class TaskStateMachine:
    """
    任务状态机
    
    职责:
    - 验证状态流转合法性
    - 记录状态流转历史
    - 触发状态变更事件
    
    使用示例:
        fsm = TaskStateMachine(task_id=1)
        fsm.transition_to(TaskStatus.RUNNING, reason="start_download")
        print(fsm.current_status)  # TaskStatus.RUNNING
        print(fsm.history)  # [StateTransition(...)]
    """
    
    def __init__(
        self,
        task_id: int,
        initial_status: TaskStatus = TaskStatus.PENDING,
    ):
        """
        初始化状态机
        
        Args:
            task_id: 任务 ID
            initial_status: 初始状态
        """
        self.task_id = task_id
        self.current_status = initial_status
        self.history: List[StateTransition] = []
        self._transition_count = 0
    
    def can_transition_to(self, target: TaskStatus) -> bool:
        """
        检查是否可以流转到目标状态
        
        Args:
            target: 目标状态
            
        Returns:
            True 如果可以流转
        """
        allowed = STATE_TRANSITIONS.get(self.current_status, set())
        return target in allowed
    
    def transition_to(
        self,
        target: TaskStatus,
        reason: str = "",
        metadata: Optional[dict] = None,
    ) -> StateTransition:
        """
        执行状态流转
        
        Args:
            target: 目标状态
            reason: 流转原因
            metadata: 额外元数据
            
        Returns:
            状态流转记录
            
        Raises:
            InvalidStateTransition: 非法流转
        """
        if not self.can_transition_to(target):
            raise InvalidStateTransition(
                f"Cannot transition from {self.current_status.name} "
                f"to {target.name} for task {self.task_id}"
            )
        
        transition = StateTransition(
            task_id=self.task_id,
            from_status=self.current_status,
            to_status=target,
            reason=reason,
            metadata=metadata or {},
        )
        
        self.current_status = target
        self.history.append(transition)
        self._transition_count += 1
        
        return transition
    
    def get_transition_history(
        self,
        from_status: Optional[TaskStatus] = None,
        to_status: Optional[TaskStatus] = None,
    ) -> List[StateTransition]:
        """
        获取状态流转历史 (支持过滤)
        
        Args:
            from_status: 过滤原状态
            to_status: 过滤目标状态
            
        Returns:
            流转历史列表
        """
        history = self.history
        
        if from_status:
            history = [h for h in history if h.from_status == from_status]
        if to_status:
            history = [h for h in history if h.to_status == to_status]
        
        return history
    
    def get_time_in_status(self) -> float:
        """
        获取在当前状态停留的时间 (秒)
        
        Returns:
            停留时间
        """
        if not self.history:
            return time.time() - self.created_at  # type: ignore
        
        last_transition = self.history[-1]
        return time.time() - last_transition.timestamp
    
    @property
    def transition_count(self) -> int:
        """获取状态流转次数"""
        return self._transition_count
    
    def to_dict(self) -> dict:
        """转换为字典 (用于序列化)"""
        return {
            "task_id": self.task_id,
            "current_status": self.current_status.name,
            "transition_count": self._transition_count,
            "history": [h.to_dict() for h in self.history[-10:]],  # 最近 10 次
        }
```

---

## 📦 任务数据结构

### Task 数据类

```python
"""任务数据结构模块"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .types import TaskStatus
from .state_machine import TaskStateMachine


@dataclass
class Task:
    """
    任务数据类
    
    职责:
    - 存储任务所有属性
    - 提供状态机访问
    - 支持序列化
    
    Attributes:
        task_id: 任务 ID
        url: 下载 URL
        status: 当前状态
        downloaded_fragments: 已下载切片数
        total_fragments: 总切片数
        output_file: 输出文件路径
        log_file: 日志文件路径
        error: 错误信息
        retries: 重试次数
        created_at: 创建时间戳
        updated_at: 更新时间戳
    """
    task_id: int
    url: str
    status: TaskStatus = TaskStatus.PENDING
    downloaded_fragments: int = 0
    total_fragments: Optional[int] = None
    output_file: Optional[Path] = None
    log_file: Optional[Path] = None
    error: Optional[str] = None
    retries: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    
    # 状态机 (延迟初始化)
    _state_machine: Optional[TaskStateMachine] = field(
        default=None,
        repr=False,
        compare=False,
    )
    
    def __post_init__(self):
        """初始化状态机"""
        if self._state_machine is None:
            self._state_machine = TaskStateMachine(
                task_id=self.task_id,
                initial_status=self.status,
            )
    
    @property
    def state_machine(self) -> TaskStateMachine:
        """获取状态机"""
        return self._state_machine  # type: ignore
    
    def transition_to(
        self,
        target: TaskStatus,
        reason: str = "",
        metadata: Optional[dict] = None,
    ) -> None:
        """
        执行状态流转
        
        Args:
            target: 目标状态
            reason: 流转原因
            metadata: 额外元数据
        """
        self.state_machine.transition_to(target, reason, metadata)
        self.status = target
        self.updated_at = time.time()
    
    @property
    def progress_percentage(self) -> float:
        """获取进度百分比"""
        if self.total_fragments is None or self.total_fragments == 0:
            return 0.0
        return (self.downloaded_fragments / self.total_fragments) * 100
    
    @property
    def progress_text(self) -> str:
        """获取进度文本"""
        if self.total_fragments is None:
            if self.downloaded_fragments > 0:
                return f"{self.downloaded_fragments}/?"
            return "-"
        return f"{self.downloaded_fragments}/{self.total_fragments}"
    
    @property
    def is_terminal(self) -> bool:
        """是否为终态"""
        return self.status in (TaskStatus.DONE, TaskStatus.FAILED)
    
    def to_dict(self) -> dict:
        """转换为字典 (用于 UI 更新)"""
        return {
            "task_id": self.task_id,
            "url": self.url,
            "status": self.status.name.lower(),
            "downloaded_fragments": self.downloaded_fragments,
            "total_fragments": self.total_fragments,
            "progress_text": self.progress_text,
            "progress_percentage": self.progress_percentage,
            "output_file": str(self.output_file) if self.output_file else None,
            "error": self.error,
            "retries": self.retries,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        """从字典创建任务"""
        return cls(
            task_id=data["task_id"],
            url=data["url"],
            status=TaskStatus[data["status"]],
            downloaded_fragments=data.get("downloaded_fragments", 0),
            total_fragments=data.get("total_fragments"),
            output_file=Path(data["output_file"]) if data.get("output_file") else None,
            log_file=Path(data["log_file"]) if data.get("log_file") else None,
            error=data.get("error"),
            retries=data.get("retries", 0),
        )
```

---

## 🔄 状态管理器

### TaskManager 实现

```python
"""任务管理器 - 统一状态管理"""

import queue
import threading
from pathlib import Path
from typing import Callable, Optional, List, Dict

from .state_machine import TaskStateMachine, StateTransition
from .task import Task
from .types import TaskStatus
from .event_bridge import EventBridge


class TaskManager:
    """
    任务管理器
    
    职责:
    - 任务生命周期管理
    - 状态流转控制
    - 任务队列维护
    - 状态持久化
    - 事件发布
    
    线程安全:
    - 使用读写锁保护状态
    - 支持多线程并发访问
    """
    
    def __init__(
        self,
        event_bridge: EventBridge,
        max_workers: int = 3,
    ):
        """
        初始化任务管理器
        
        Args:
            event_bridge: 事件总线
            max_workers: 最大并发数
        """
        self.event_bridge = event_bridge
        self.max_workers = max_workers
        
        # 任务存储
        self.tasks: Dict[int, Task] = {}
        self.next_task_id = 1
        
        # 状态队列 (索引)
        self._pending_ids: List[int] = []
        self._running_ids: List[int] = []
        self._done_ids: List[int] = []
        self._failed_ids: List[int] = []
        self._retrying_ids: List[int] = []
        
        # 线程安全
        self._lock = threading.RLock()
        
        # 回调
        self._on_status_change: Optional[
            Callable[[int, TaskStatus, TaskStatus], None]
        ] = None
        
        # 持久化
        self._state_file: Optional[Path] = None
        self._auto_save = False
    
    # ========== 任务操作 ==========
    
    def add_task(self, url: str) -> int:
        """
        添加新任务
        
        Args:
            url: 下载 URL
            
        Returns:
            任务 ID
        """
        with self._lock:
            tid = self.next_task_id
            self.next_task_id += 1
            
            task = Task(task_id=tid, url=url)
            self.tasks[tid] = task
            self._pending_ids.append(tid)
            
            self.event_bridge.publish(
                "task_added",
                {"task_id": tid, "url": url},
            )
            
            self._maybe_save_state()
            
            return tid
    
    def add_tasks(self, urls: List[str]) -> List[int]:
        """批量添加任务"""
        return [self.add_task(url) for url in urls]
    
    def get_task(self, task_id: int) -> Optional[Task]:
        """获取任务"""
        with self._lock:
            return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> List[Task]:
        """获取所有任务"""
        with self._lock:
            return list(self.tasks.values())
    
    # ========== 状态查询 ==========
    
    def get_pending_tasks(self) -> List[Task]:
        """获取待下载任务"""
        with self._lock:
            return [self.tasks[tid] for tid in self._pending_ids]
    
    def get_running_tasks(self) -> List[Task]:
        """获取正在下载任务"""
        with self._lock:
            return [self.tasks[tid] for tid in self._running_ids]
    
    def get_done_tasks(self) -> List[Task]:
        """获取已完成任务"""
        with self._lock:
            return [self.tasks[tid] for tid in self._done_ids]
    
    def get_failed_tasks(self) -> List[Task]:
        """获取失败任务"""
        with self._lock:
            return [self.tasks[tid] for tid in self._failed_ids]
    
    def get_retrying_tasks(self) -> List[Task]:
        """获取重试中任务"""
        with self._lock:
            return [self.tasks[tid] for tid in self._retrying_ids]
    
    # ========== 状态流转 ==========
    
    def mark_running(self, task_id: int) -> None:
        """标记任务为运行中"""
        self._transition(task_id, TaskStatus.RUNNING, "start_download")
    
    def mark_done(
        self,
        task_id: int,
        output_file: Path,
        log_file: Path,
    ) -> None:
        """标记任务为完成"""
        with self._lock:
            task = self.tasks.get(task_id)
            if task:
                task.output_file = output_file
                task.log_file = log_file
        self._transition(task_id, TaskStatus.DONE, "download_complete")
    
    def mark_failed(self, task_id: int, error: str) -> None:
        """标记任务为失败"""
        with self._lock:
            task = self.tasks.get(task_id)
            if task:
                task.error = error
        self._transition(task_id, TaskStatus.FAILED, "download_error")
    
    def mark_retrying(self, task_id: int, retry_count: int) -> None:
        """标记任务为重试中"""
        with self._lock:
            task = self.tasks.get(task_id)
            if task:
                task.retries = retry_count
        self._transition(task_id, TaskStatus.RETRYING, "prepare_retry")
    
    def update_progress(
        self,
        task_id: int,
        downloaded: int,
        total: Optional[int],
    ) -> None:
        """更新任务进度"""
        with self._lock:
            task = self.tasks.get(task_id)
            if task:
                task.downloaded_fragments = downloaded
                task.total_fragments = total
                task.updated_at = time.time()
        
        self.event_bridge.publish(
            "task_progress_updated",
            {
                "task_id": task_id,
                "downloaded": downloaded,
                "total": total,
            },
        )
    
    def retry_task(self, task_id: int) -> bool:
        """
        重试失败任务
        
        Args:
            task_id: 任务 ID
            
        Returns:
            True 如果重试成功
        """
        with self._lock:
            task = self.tasks.get(task_id)
            if not task or task.status != TaskStatus.FAILED:
                return False
            
            # 重置任务状态
            task.error = None
            task.downloaded_fragments = 0
            task.total_fragments = None
            task.output_file = None
            task.log_file = None
            
        self._transition(task_id, TaskStatus.PENDING, "user_retry")
        return True
    
    def cancel_task(self, task_id: int) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务 ID
            
        Returns:
            True 如果取消成功
        """
        with self._lock:
            task = self.tasks.get(task_id)
            if not task or task.is_terminal:
                return False
            
        self._transition(task_id, TaskStatus.FAILED, "user_cancel")
        return True
    
    # ========== 批量操作 ==========
    
    def clear_pending(self) -> int:
        """
        清空待下载任务
        
        Returns:
            清空的任务数量
        """
        with self._lock:
            count = len(self._pending_ids)
            
            for tid in self._pending_ids:
                task = self.tasks[tid]
                task.error = "用户取消"
                self._move_to_queue(tid, TaskStatus.FAILED)
            
            self._pending_ids.clear()
            
            self.event_bridge.publish(
                "pending_cleared",
                {"cleared_count": count},
            )
            
            self._maybe_save_state()
            
            return count
    
    def clear_completed(self) -> int:
        """清空已完成任务"""
        with self._lock:
            count = len(self._done_ids)
            
            for tid in self._done_ids:
                del self.tasks[tid]
            
            self._done_ids.clear()
            
            self.event_bridge.publish(
                "completed_cleared",
                {"cleared_count": count},
            )
            
            return count
    
    def retry_all_failed(self) -> int:
        """重试所有失败任务"""
        with self._lock:
            failed_ids = self._failed_ids.copy()
        
        count = 0
        for tid in failed_ids:
            if self.retry_task(tid):
                count += 1
        
        return count
    
    # ========== 内部方法 ==========
    
    def _transition(
        self,
        task_id: int,
        new_status: TaskStatus,
        reason: str = "",
    ) -> None:
        """
        执行状态流转
        
        Args:
            task_id: 任务 ID
            new_status: 新状态
            reason: 流转原因
        """
        with self._lock:
            task = self.tasks.get(task_id)
            if not task:
                return
            
            old_status = task.status
            
            # 更新状态机
            task.transition_to(new_status, reason)
            
            # 更新队列索引
            self._move_to_queue(task_id, new_status)
            
            # 触发回调
            if self._on_status_change:
                self._on_status_change(task_id, old_status, new_status)
            
            # 发布事件
            self.event_bridge.publish(
                "task_status_changed",
                {
                    "task_id": task_id,
                    "old_status": old_status.name,
                    "new_status": new_status.name,
                    "reason": reason,
                },
            )
            
            self._maybe_save_state()
    
    def _move_to_queue(self, task_id: int, status: TaskStatus) -> None:
        """移动任务 ID 到对应队列"""
        # 从所有队列移除
        for queue_list in [
            self._pending_ids,
            self._running_ids,
            self._done_ids,
            self._failed_ids,
            self._retrying_ids,
        ]:
            if task_id in queue_list:
                queue_list.remove(task_id)
        
        # 添加到新队列
        if status == TaskStatus.PENDING:
            self._pending_ids.append(task_id)
        elif status == TaskStatus.RUNNING:
            self._running_ids.append(task_id)
        elif status == TaskStatus.DONE:
            self._done_ids.append(task_id)
        elif status == TaskStatus.FAILED:
            self._failed_ids.append(task_id)
        elif status == TaskStatus.RETRYING:
            self._retrying_ids.append(task_id)
    
    # ========== 回调设置 ==========
    
    def set_status_change_callback(
        self,
        callback: Callable[[int, TaskStatus, TaskStatus], None],
    ) -> None:
        """设置状态变更回调"""
        self._on_status_change = callback
    
    # ========== 持久化 ==========
    
    def enable_persistence(self, state_file: Path) -> None:
        """启用状态持久化"""
        self._state_file = state_file
        self._auto_save = True
        self._load_state()
    
    def save_state(self) -> None:
        """保存状态到文件"""
        if not self._state_file:
            return
        
        with self._lock:
            data = {
                "next_task_id": self.next_task_id,
                "tasks": [task.to_dict() for task in self.tasks.values()],
            }
            
            self._state_file.parent.mkdir(parents=True, exist_ok=True)
            self._state_file.write_text(json.dumps(data, indent=2))
    
    def _load_state(self) -> None:
        """从文件加载状态"""
        if not self._state_file or not self._state_file.exists():
            return
        
        try:
            data = json.loads(self._state_file.read_text())
            
            with self._lock:
                self.next_task_id = data.get("next_task_id", 1)
                
                for task_data in data.get("tasks", []):
                    task = Task.from_dict(task_data)
                    self.tasks[task.task_id] = task
                    
                    # 重建队列索引
                    if task.status == TaskStatus.PENDING:
                        self._pending_ids.append(task.task_id)
                    elif task.status == TaskStatus.RUNNING:
                        self._running_ids.append(task.task_id)
                    elif task.status == TaskStatus.DONE:
                        self._done_ids.append(task.task_id)
                    elif task.status == TaskStatus.FAILED:
                        self._failed_ids.append(task.task_id)
                    elif task.status == TaskStatus.RETRYING:
                        self._retrying_ids.append(task.task_id)
        except Exception as e:
            print(f"Failed to load state: {e}")
    
    def _maybe_save_state(self) -> None:
        """自动保存状态 (如果启用)"""
        if self._auto_save:
            self.save_state()
    
    # ========== 统计信息 ==========
    
    def get_summary(self) -> Dict[str, int]:
        """获取任务摘要"""
        with self._lock:
            return {
                "total": len(self.tasks),
                "pending": len(self._pending_ids),
                "running": len(self._running_ids),
                "done": len(self._done_ids),
                "failed": len(self._failed_ids),
                "retrying": len(self._retrying_ids),
            }
    
    def get_statistics(self) -> Dict[str, any]:
        """获取详细统计"""
        with self._lock:
            tasks = list(self.tasks.values())
        
        total_fragments = sum(
            t.downloaded_fragments for t in tasks if t.total_fragments
        )
        total_expected = sum(
            t.total_fragments for t in tasks if t.total_fragments
        )
        
        return {
            **self.get_summary(),
            "total_fragments_downloaded": total_fragments,
            "total_fragments_expected": total_expected,
            "overall_progress": (
                total_fragments / total_expected * 100
                if total_expected > 0
                else 0
            ),
        }
```

---

## 📊 状态持久化

### 持久化策略

```python
"""状态持久化模块"""

import json
import time
from pathlib import Path
from typing import Dict, Any, List

from .task import Task
from .types import TaskStatus


class StatePersistence:
    """
    状态持久化
    
    职责:
    - 保存任务状态到文件
    - 从文件加载任务状态
    - 状态版本管理
    - 数据迁移
    """
    
    CURRENT_VERSION = 1
    
    def __init__(self, state_file: Path):
        """
        初始化持久化
        
        Args:
            state_file: 状态文件路径
        """
        self.state_file = state_file
    
    def save(
        self,
        tasks: Dict[int, Task],
        next_task_id: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        保存状态
        
        Args:
            tasks: 任务字典
            next_task_id: 下一个任务 ID
            metadata: 额外元数据
        """
        data = {
            "version": self.CURRENT_VERSION,
            "saved_at": time.time(),
            "next_task_id": next_task_id,
            "tasks": [self._task_to_dict(task) for task in tasks.values()],
            "metadata": metadata or {},
        }
        
        # 原子写入 (先写临时文件，再重命名)
        temp_file = self.state_file.with_suffix(".tmp")
        temp_file.write_text(json.dumps(data, indent=2, default=str))
        temp_file.rename(self.state_file)
    
    def load(self) -> Dict[str, Any]:
        """
        加载状态
        
        Returns:
            状态字典
        """
        if not self.state_file.exists():
            return {}
        
        data = json.loads(self.state_file.read_text())
        
        # 版本检查
        version = data.get("version", 0)
        if version != self.CURRENT_VERSION:
            data = self._migrate(data, version)
        
        return data
    
    def _task_to_dict(self, task: Task) -> Dict[str, Any]:
        """任务转字典"""
        return {
            "task_id": task.task_id,
            "url": task.url,
            "status": task.status.name,
            "downloaded_fragments": task.downloaded_fragments,
            "total_fragments": task.total_fragments,
            "output_file": str(task.output_file) if task.output_file else None,
            "log_file": str(task.log_file) if task.log_file else None,
            "error": task.error,
            "retries": task.retries,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
        }
    
    def _task_from_dict(self, data: Dict[str, Any]) -> Task:
        """字典转任务"""
        return Task(
            task_id=data["task_id"],
            url=data["url"],
            status=TaskStatus[data["status"]],
            downloaded_fragments=data.get("downloaded_fragments", 0),
            total_fragments=data.get("total_fragments"),
            output_file=Path(data["output_file"]) if data.get("output_file") else None,
            log_file=Path(data["log_file"]) if data.get("log_file") else None,
            error=data.get("error"),
            retries=data.get("retries", 0),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
        )
    
    def _migrate(
        self,
        data: Dict[str, Any],
        from_version: int,
    ) -> Dict[str, Any]:
        """
        数据迁移
        
        Args:
            data: 旧数据
            from_version: 旧版本号
            
        Returns:
            新数据
        """
        # 未来版本迁移逻辑
        if from_version < 1:
            # v0 → v1 迁移
            data["version"] = 1
        
        return data
```

---

## 🎪 事件驱动更新

### 事件类型定义

```python
"""GUI 事件类型定义"""

from dataclasses import dataclass
from typing import Any, Optional

@dataclass
class GuiEvent:
    """GUI 事件基类"""
    type: str
    payload: Any
    timestamp: float


# ========== 任务事件 ==========

TASK_ADDED = "task_added"
# payload: {"task_id": int, "url": str}

TASK_STATUS_CHANGED = "task_status_changed"
# payload: {"task_id": int, "old_status": str, "new_status": str, "reason": str}

TASK_PROGRESS_UPDATED = "task_progress_updated"
# payload: {"task_id": int, "downloaded": int, "total": int|None}

TASK_LOG_ADDED = "task_log_added"
# payload: {"task_id": int, "message": str}

# ========== 队列事件 ==========

PENDING_CLEARED = "pending_cleared"
# payload: {"cleared_count": int}

COMPLETED_CLEARED = "completed_cleared"
# payload: {"cleared_count": int}

# ========== 下载事件 ==========

DOWNLOAD_STARTED = "download_started"
# payload: {"task_ids": List[int]}

DOWNLOAD_COMPLETED = "download_completed"
# payload: {"task_id": int, "output_file": str}

DOWNLOAD_FAILED = "download_failed"
# payload: {"task_id": int, "error": str}

# ========== UI 事件 ==========

STATUS_TEXT_UPDATED = "status_text_updated"
# payload: {"text": str}

FORM_DATA_CHANGED = "form_data_changed"
# payload: {"field": str, "value": Any}
```

### 事件订阅示例

```python
"""事件订阅使用示例"""

from gui.core.event_bridge import EventBridge
from gui.components.main_panel import MainPanel
from gui.managers.task_manager import TaskManager


def setup_event_bindings(
    event_bridge: EventBridge,
    main_panel: MainPanel,
    task_manager: TaskManager,
) -> None:
    """设置事件绑定"""
    
    # 任务状态变更 → 更新 UI
    def on_task_status_changed(payload: dict):
        task_id = payload["task_id"]
        new_status = payload["new_status"]
        
        if new_status == "DONE":
            task = task_manager.get_task(task_id)
            main_panel.append_log(
                f"[task-{task_id}] [saved] {task.output_file}"
            )
        elif new_status == "FAILED":
            task = task_manager.get_task(task_id)
            main_panel.append_log(
                f"[task-{task_id}] [failed] {task.error}"
            )
        
        refresh_task_list()
    
    event_bridge.subscribe("task_status_changed", on_task_status_changed)
    
    # 任务进度更新 → 更新 UI
    def on_task_progress_updated(payload: dict):
        refresh_task_list()
    
    event_bridge.subscribe("task_progress_updated", on_task_progress_updated)
    
    # 任务添加 → 刷新列表
    def on_task_added(payload: dict):
        refresh_task_list()
    
    event_bridge.subscribe("task_added", on_task_added)
    
    # 待下载清空 → 刷新列表
    def on_pending_cleared(payload: dict):
        refresh_task_list()
        main_panel.append_log("[queue] 已清空待下载任务。")
    
    event_bridge.subscribe("pending_cleared", on_pending_cleared)
    
    def refresh_task_list():
        """刷新任务列表"""
        pending = [t.to_dict() for t in task_manager.get_pending_tasks()]
        active = [t.to_dict() for t in task_manager.get_running_tasks()]
        completed = [t.to_dict() for t in task_manager.get_done_tasks()]
        main_panel.update_task_list(pending, active, completed)
```

---

## 🧪 测试策略

### 状态机测试

```python
"""状态机测试"""

import pytest
from gui.state_machine import TaskStateMachine, InvalidStateTransition
from gui.types import TaskStatus


class TestTaskStateMachine:
    """状态机测试类"""
    
    def test_initial_status(self):
        """测试初始状态"""
        fsm = TaskStateMachine(task_id=1)
        assert fsm.current_status == TaskStatus.PENDING
    
    def test_valid_transition_pending_to_running(self):
        """测试合法流转：PENDING → RUNNING"""
        fsm = TaskStateMachine(task_id=1)
        
        transition = fsm.transition_to(
            TaskStatus.RUNNING,
            reason="start_download",
        )
        
        assert fsm.current_status == TaskStatus.RUNNING
        assert transition.reason == "start_download"
        assert len(fsm.history) == 1
    
    def test_invalid_transition_pending_to_done(self):
        """测试非法流转：PENDING → DONE"""
        fsm = TaskStateMachine(task_id=1)
        
        with pytest.raises(InvalidStateTransition):
            fsm.transition_to(TaskStatus.DONE)
    
    def test_state_history(self):
        """测试状态历史"""
        fsm = TaskStateMachine(task_id=1)
        fsm.transition_to(TaskStatus.RUNNING)
        fsm.transition_to(TaskStatus.DONE, reason="download_complete")
        
        assert len(fsm.history) == 2
        assert fsm.history[0].to_status == TaskStatus.RUNNING
        assert fsm.history[1].to_status == TaskStatus.DONE
        assert fsm.history[1].reason == "download_complete"
    
    def test_can_transition_to(self):
        """测试流转检查"""
        fsm = TaskStateMachine(task_id=1)
        
        assert fsm.can_transition_to(TaskStatus.RUNNING)
        assert not fsm.can_transition_to(TaskStatus.DONE)
    
    def test_terminal_state(self):
        """测试终态"""
        fsm = TaskStateMachine(task_id=1)
        fsm.transition_to(TaskStatus.RUNNING)
        fsm.transition_to(TaskStatus.DONE)
        
        assert not fsm.can_transition_to(TaskStatus.PENDING)
        assert len(fsm.history) == 2
```

### 任务管理器测试

```python
"""任务管理器测试"""

import pytest
from pathlib import Path
from gui.managers.task_manager import TaskManager
from gui.core.event_bridge import EventBridge
from gui.types import TaskStatus


@pytest.fixture
def event_bridge():
    return EventBridge()


@pytest.fixture
def task_manager(event_bridge):
    return TaskManager(event_bridge)


class TestTaskManager:
    """任务管理器测试类"""
    
    def test_add_task(self, task_manager):
        """测试添加任务"""
        tid = task_manager.add_task("https://example.com/video")
        
        assert tid == 1
        assert task_manager.next_task_id == 2
        
        task = task_manager.get_task(tid)
        assert task is not None
        assert task.url == "https://example.com/video"
        assert task.status == TaskStatus.PENDING
    
    def test_transition_running(self, task_manager):
        """测试流转到运行中"""
        tid = task_manager.add_task("https://example.com")
        task_manager.mark_running(tid)
        
        task = task_manager.get_task(tid)
        assert task.status == TaskStatus.RUNNING
        assert tid in task_manager._running_ids
    
    def test_transition_done(self, task_manager):
        """测试流转到完成"""
        tid = task_manager.add_task("https://example.com")
        task_manager.mark_running(tid)
        task_manager.mark_done(
            tid,
            output_file=Path("/tmp/video.mp4"),
            log_file=Path("/tmp/video.log"),
        )
        
        task = task_manager.get_task(tid)
        assert task.status == TaskStatus.DONE
        assert task.output_file == Path("/tmp/video.mp4")
        assert tid in task_manager._done_ids
    
    def test_transition_failed(self, task_manager):
        """测试流转到失败"""
        tid = task_manager.add_task("https://example.com")
        task_manager.mark_running(tid)
        task_manager.mark_failed(tid, "Network error")
        
        task = task_manager.get_task(tid)
        assert task.status == TaskStatus.FAILED
        assert task.error == "Network error"
    
    def test_retry_failed_task(self, task_manager):
        """测试重试失败任务"""
        tid = task_manager.add_task("https://example.com")
        task_manager.mark_running(tid)
        task_manager.mark_failed(tid, "Network error")
        
        success = task_manager.retry_task(tid)
        
        assert success is True
        task = task_manager.get_task(tid)
        assert task.status == TaskStatus.PENDING
        assert task.error is None
        assert task.downloaded_fragments == 0
    
    def test_get_summary(self, task_manager):
        """测试获取摘要"""
        task_manager.add_task("https://example.com/1")
        task_manager.add_task("https://example.com/2")
        task_manager.mark_running(1)
        task_manager.mark_done(2, Path("/tmp/1.mp4"), Path("/tmp/1.log"))
        
        summary = task_manager.get_summary()
        
        assert summary == {
            "total": 2,
            "pending": 0,
            "running": 1,
            "done": 1,
            "failed": 0,
        }
```

---

## 📈 性能优化

### 1. 批量更新

```python
def batch_update(self, updates: List[Callable]) -> None:
    """
    批量执行更新 (减少事件发布次数)
    
    Args:
        updates: 更新函数列表
    """
    self._batch_mode = True
    self._batch_events = []
    
    try:
        for update_fn in updates:
            update_fn()
    finally:
        self._batch_mode = False
        
        # 批量发布事件
        for event in self._batch_events:
            self.event_bridge.publish(event["type"], event["payload"])
        
        self._batch_events.clear()
```

### 2. 增量持久化

```python
def save_state_incremental(self, changed_task_ids: List[int]) -> None:
    """
    增量保存状态 (仅保存变更的任务)
    
    Args:
        changed_task_ids: 变更的任务 ID 列表
    """
    if not self._state_file:
        return
    
    # 读取现有数据
    existing_data = {}
    if self._state_file.exists():
        existing_data = json.loads(self._state_file.read_text())
    
    # 仅更新变更的任务
    for tid in changed_task_ids:
        task = self.tasks.get(tid)
        if task:
            existing_data["tasks"][str(tid)] = self._task_to_dict(task)
    
    # 写入
    self._state_file.write_text(json.dumps(existing_data, indent=2))
```

### 3. 状态缓存

```python
from functools import lru_cache

class TaskManager:
    @lru_cache(maxsize=100)
    def get_task_cached(self, task_id: int) -> Optional[Task]:
        """获取任务 (带缓存)"""
        return self.tasks.get(task_id)
    
    def invalidate_cache(self, task_id: int) -> None:
        """使缓存失效"""
        self.get_task_cached.cache_clear()
```

---

## 🔒 线程安全

### 读写锁实现

```python
import threading
from contextlib import contextmanager

class TaskManager:
    def __init__(self):
        self._lock = threading.RLock()
        self._read_lock = threading.Lock()
        self._write_lock = threading.Lock()
        self._readers = 0
    
    @contextmanager
    def read_lock(self):
        """读锁 (允许多个读者)"""
        with self._read_lock:
            self._readers += 1
            if self._readers == 1:
                self._write_lock.acquire()
        
        try:
            yield
        finally:
            with self._read_lock:
                self._readers -= 1
                if self._readers == 0:
                    self._write_lock.release()
    
    @contextmanager
    def write_lock(self):
        """写锁 (独占)"""
        with self._write_lock:
            yield
    
    def get_task(self, task_id: int) -> Optional[Task]:
        """读操作"""
        with self.read_lock():
            return self.tasks.get(task_id)
    
    def add_task(self, url: str) -> int:
        """写操作"""
        with self.write_lock():
            tid = self.next_task_id
            self.next_task_id += 1
            task = Task(task_id=tid, url=url)
            self.tasks[tid] = task
            return tid
```

---

## 📌 总结

### 方案优势

1. **单一数据源** - 所有状态在 `TaskManager` 中集中管理
2. **状态可追溯** - 完整的状态流转历史记录
3. **线程安全** - 支持多线程并发访问
4. **可持久化** - 支持应用重启后恢复
5. **事件驱动** - 状态变更自动触发 UI 更新

### 实施步骤

1. **Phase 1**: 实现 `TaskStatus` 枚举和 `TaskStateMachine`
2. **Phase 2**: 重构 `Task` 数据类，集成状态机
3. **Phase 3**: 实现 `TaskManager` 统一状态管理
4. **Phase 4**: 添加持久化支持
5. **Phase 5**: 完善事件驱动更新机制

### 预期收益

| 指标 | 重构前 | 重构后 | 提升 |
|------|--------|--------|------|
| 状态一致性 | 中 | 高 | +50% |
| Bug 可追溯性 | 低 | 高 | +80% |
| 代码可维护性 | 中 | 高 | +40% |
| 测试覆盖率 | <20% | >80% | +300% |

---

**文档完成时间**: 2026-03-15
