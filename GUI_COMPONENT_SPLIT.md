# PSiteDL GUI 组件拆分建议

**文档版本**: 1.0  
**创建日期**: 2026-03-15  
**关联文档**: [GUI_ARCH_REVIEW.md](GUI_ARCH_REVIEW.md)

---

## 📐 拆分原则

### 单一职责原则 (SRP)

每个组件只负责一个明确的职责：
- UI 组件 → 只负责显示和用户交互
- 管理器 → 只负责状态管理
- 服务 → 只负责业务逻辑

### 依赖倒置原则 (DIP)

高层模块不依赖低层模块，都依赖抽象：
```python
# ❌ 错误：UI 直接依赖具体下载函数
class App:
    def _run_task(self):
        return run_site_download(...)  # 紧耦合

# ✅ 正确：UI 依赖抽象接口
class MainPanel:
    def __init__(self, download_service: DownloadServiceProtocol):
        self.service = download_service  # 依赖抽象
```

### 接口隔离原则 (ISP)

使用 Protocol 定义细粒度接口：
```python
from typing import Protocol

class TaskViewProtocol(Protocol):
    def update_task_status(self, task_id: int, status: str) -> None: ...
    def append_log(self, text: str) -> None: ...

class DownloadServiceProtocol(Protocol):
    def submit_task(self, task_id: int, url: str, config: dict) -> Future: ...
    def get_active_count(self) -> int: ...
```

---

## 📁 目录结构

### 建议结构

```
src/webvidgrab/
├── site_gui.py                 # 入口文件 (保持兼容)
├── gui/                        # GUI 模块 (新增)
│   ├── __init__.py
│   ├── app.py                  # 主应用协调器
│   │
│   ├── components/             # UI 组件
│   │   ├── __init__.py
│   │   ├── main_panel.py       # 主面板
│   │   ├── form_panel.py       # 表单面板
│   │   ├── task_list_view.py   # 任务列表视图
│   │   └── log_viewer.py       # 日志查看器
│   │
│   ├── managers/               # 管理器
│   │   ├── __init__.py
│   │   ├── task_manager.py     # 任务管理器
│   │   └── state_machine.py    # 状态机
│   │
│   ├── services/               # 服务层
│   │   ├── __init__.py
│   │   ├── download_service.py # 下载服务
│   │   └── config_service.py   # 配置服务
│   │
│   └── core/                   # 核心工具
│       ├── __init__.py
│       ├── event_bridge.py     # 事件总线
│       └── types.py            # 类型定义
│
└── ... (其他模块)
```

### 迁移策略

```bash
# 第 1 步：创建新目录结构
mkdir -p src/webvidgrab/gui/{components,managers,services,core}
touch src/webvidgrab/gui/__init__.py
touch src/webvidgrab/gui/{app.py,components/__init__.py,managers/__init__.py,services/__init__.py,core/__init__.py}

# 第 2 步：逐个组件迁移 (保持旧代码可用)
# 第 3 步：更新 site_gui.py 导入新组件
# 第 4 步：删除旧代码
```

---

## 🔧 组件实现

### 1. MainPanel (主面板)

**文件**: `gui/components/main_panel.py`

```python
"""主面板组件 - 纯 UI 展示"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Callable, Any

from .form_panel import FormPanel
from .task_list_view import TaskListView
from .log_viewer import LogViewer


class MainPanel(ttk.Frame):
    """
    主面板组件
    
    职责:
    - 布局管理
    - 子组件协调
    - UI 事件转发
    
    不包含:
    - 业务逻辑
    - 状态管理
    - 数据持久化
    """
    
    def __init__(
        self,
        parent: tk.Widget,
        callbacks: dict[str, Callable],
    ):
        """
        初始化主面板
        
        Args:
            parent: 父容器
            callbacks: 回调函数字典
                - on_add_task: 添加任务回调
                - on_start_download: 开始下载回调
                - on_clear_pending: 清空待下载回调
                - on_pick_output_dir: 选择目录回调
                - on_clear_log: 清空日志回调
        """
        super().__init__(parent, padding=12)
        self.callbacks = callbacks
        self._build_ui()
    
    def _build_ui(self) -> None:
        """构建 UI"""
        # 顶部表单
        self.form = FormPanel(
            self,
            on_add_task=self.callbacks["on_add_task"],
            on_pick_output_dir=self.callbacks["on_pick_output_dir"],
        )
        self.form.pack(fill=tk.BOTH)
        
        # 控制按钮
        self._build_controls()
        
        # 任务列表和日志
        self._build_content_area()
    
    def _build_controls(self) -> None:
        """构建控制按钮区域"""
        ctrl_frame = ttk.Frame(self)
        ctrl_frame.pack(fill=tk.BOTH, pady=(10, 0))
        
        ttk.Button(
            ctrl_frame,
            text="加入待下载",
            command=self.callbacks["on_add_task"],
        ).pack(side=tk.LEFT)
        
        ttk.Button(
            ctrl_frame,
            text="启动队列下载 (3 并发)",
            command=self.callbacks["on_start_download"],
        ).pack(side=tk.LEFT, padx=(8, 0))
        
        ttk.Button(
            ctrl_frame,
            text="清空待下载",
            command=self.callbacks["on_clear_pending"],
        ).pack(side=tk.LEFT, padx=(8, 0))
        
        ttk.Button(
            ctrl_frame,
            text="清空日志",
            command=self.callbacks["on_clear_log"],
        ).pack(side=tk.LEFT, padx=(8, 0))
        
        self.status_label = ttk.Label(ctrl_frame, text="就绪")
        self.status_label.pack(side=tk.LEFT, padx=(12, 0))
    
    def _build_content_area(self) -> None:
        """构建内容区域 (任务列表 + 日志)"""
        from tkinter import BOTH, VERTICAL
        
        split = ttk.Panedwindow(self, orient=VERTICAL)
        split.pack(fill=BOTH, expand=True, pady=(10, 0))
        
        # 任务列表区域
        list_frame = ttk.Frame(split)
        split.add(list_frame, weight=3)
        
        self.task_list = TaskListView(list_frame)
        self.task_list.pack(fill=BOTH, expand=True)
        
        # 日志区域
        log_frame = ttk.LabelFrame(split, text="运行日志", padding=10)
        split.add(log_frame, weight=2)
        
        self.log_viewer = LogViewer(log_frame)
        self.log_viewer.pack(fill=BOTH, expand=True)
    
    # ========== 数据绑定方法 (由外部调用) ==========
    
    def set_status_text(self, text: str) -> None:
        """设置状态栏文本"""
        self.status_label.config(text=text)
    
    def update_task_list(
        self,
        pending: list[dict],
        active: list[dict],
        completed: list[dict],
    ) -> None:
        """
        更新任务列表
        
        Args:
            pending: 待下载任务列表
            active: 正在下载任务列表
            completed: 已完成任务列表
        """
        self.task_list.update_pending(pending)
        self.task_list.update_active(active)
        self.task_list.update_completed(completed)
    
    def append_log(self, text: str) -> None:
        """添加日志"""
        self.log_viewer.append(text)
    
    def clear_log(self) -> None:
        """清空日志"""
        self.log_viewer.clear()
    
    def get_form_data(self) -> dict[str, Any]:
        """获取表单数据"""
        return self.form.get_data()
    
    def show_warning(self, title: str, message: str) -> None:
        """显示警告对话框"""
        messagebox.showwarning(title, message, parent=self)
    
    def show_error(self, title: str, message: str) -> None:
        """显示错误对话框"""
        messagebox.showerror(title, message, parent=self)
```

---

### 2. FormPanel (表单面板)

**文件**: `gui/components/form_panel.py`

```python
"""表单面板组件"""

import tkinter as tk
from tkinter import ttk
from typing import Callable


class FormPanel(ttk.LabelFrame):
    """
    表单面板组件
    
    职责:
    - 表单字段渲染
    - 表单验证
    - 数据收集
    """
    
    def __init__(
        self,
        parent: tk.Widget,
        on_add_task: Callable,
        on_pick_output_dir: Callable,
    ):
        super().__init__(parent, text="任务输入", padding=10)
        self.on_add_task = on_add_task
        self.on_pick_output_dir = on_pick_output_dir
        self._init_vars()
        self._build_ui()
    
    def _init_vars(self) -> None:
        """初始化 Tkinter 变量"""
        from pathlib import Path
        
        self.output_dir = tk.StringVar(
            value=str((Path.home() / "Downloads").resolve())
        )
        self.browser = tk.StringVar(value="chrome")
        self.profile = tk.StringVar(value="Default")
        self.capture_seconds = tk.StringVar(value="30")
        self.use_runtime_capture = tk.BooleanVar(value=True)
    
    def _build_ui(self) -> None:
        """构建表单 UI"""
        # 第 0 行：URL 输入
        ttk.Label(self, text="网页播放 URL（每行一个）").grid(
            row=0, column=0, sticky=tk.W, padx=(0, 8), pady=4
        )
        self.url_text = tk.Text(self, height=3)
        self.url_text.grid(row=0, column=1, columnspan=3, sticky="ew", pady=4)
        
        # 第 1 行：输出目录
        ttk.Label(self, text="输出目录").grid(
            row=1, column=0, sticky=tk.W, padx=(0, 8), pady=4
        )
        ttk.Entry(self, textvariable=self.output_dir).grid(
            row=1, column=1, columnspan=2, sticky="ew", pady=4
        )
        ttk.Button(
            self,
            text="浏览",
            command=self.on_pick_output_dir,
        ).grid(row=1, column=3, sticky="ew", pady=4)
        
        # 第 2 行：浏览器选择
        ttk.Label(self, text="浏览器").grid(
            row=2, column=0, sticky=tk.W, padx=(0, 8), pady=4
        )
        ttk.Combobox(
            self,
            textvariable=self.browser,
            values=["chrome", "chromium", "edge", "brave"],
            state="readonly",
        ).grid(row=2, column=1, sticky="ew", pady=4)
        
        ttk.Label(self, text="Profile").grid(
            row=2, column=2, sticky=tk.W, padx=(12, 8), pady=4
        )
        ttk.Entry(self, textvariable=self.profile).grid(
            row=2, column=3, sticky="ew", pady=4
        )
        
        # 第 3 行：运行时探测
        ttk.Label(self, text="运行时探测秒数").grid(
            row=3, column=0, sticky=tk.W, padx=(0, 8), pady=4
        )
        ttk.Entry(self, textvariable=self.capture_seconds).grid(
            row=3, column=1, sticky="ew", pady=4
        )
        ttk.Checkbutton(
            self,
            text="启用运行时探测 (会打开浏览器并抓播放请求)",
            variable=self.use_runtime_capture,
        ).grid(row=3, column=2, columnspan=2, sticky=tk.W, pady=4)
        
        # 第 4 行：说明文字
        note = "支持并发 3 线程下载；显示切片进度 (已下载/总切片)；完成后自动进入"已完成任务"。"
        ttk.Label(self, text=note, foreground="#666").grid(
            row=4, column=0, columnspan=4, sticky=tk.W, pady=(4, 2)
        )
        
        # 列权重
        self.columnconfigure(1, weight=1)
        self.columnconfigure(3, weight=1)
    
    def get_data(self) -> dict:
        """获取表单数据"""
        return {
            "urls": self.url_text.get("1.0", tk.END).strip().splitlines(),
            "output_dir": self.output_dir.get().strip(),
            "browser": self.browser.get().strip() or "chrome",
            "profile": self.profile.get().strip() or "Default",
            "capture_seconds": self.capture_seconds.get().strip(),
            "use_runtime_capture": self.use_runtime_capture.get(),
        }
    
    def set_data(self, data: dict) -> None:
        """设置表单数据"""
        if "output_dir" in data:
            self.output_dir.set(data["output_dir"])
        if "browser" in data:
            self.browser.set(data["browser"])
        if "profile" in data:
            self.profile.set(data["profile"])
        if "capture_seconds" in data:
            self.capture_seconds.set(data["capture_seconds"])
        if "use_runtime_capture" in data:
            self.use_runtime_capture.set(data["use_runtime_capture"])
    
    def clear_urls(self) -> None:
        """清空 URL 输入"""
        self.url_text.delete("1.0", tk.END)
    
    def validate(self) -> tuple[bool, str]:
        """
        验证表单数据
        
        Returns:
            (是否有效，错误信息)
        """
        data = self.get_data()
        
        if not data["urls"]:
            return False, "请填写至少一个 URL"
        
        if not data["output_dir"]:
            return False, "请填写输出目录"
        
        try:
            seconds = int(data["capture_seconds"])
            if seconds < 10:
                raise ValueError()
        except ValueError:
            return False, "运行时探测秒数建议 >= 10"
        
        return True, ""
```

---

### 3. TaskManager (任务管理器)

**文件**: `gui/managers/task_manager.py`

```python
"""任务管理器 - 统一状态管理"""

import queue
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Any

from ..core.event_bridge import EventBridge


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = auto()
    RUNNING = auto()
    DONE = auto()
    FAILED = auto()
    RETRYING = auto()


@dataclass
class Task:
    """任务数据类"""
    task_id: int
    url: str
    status: TaskStatus = TaskStatus.PENDING
    downloaded_fragments: int = 0
    total_fragments: int | None = None
    output_file: Path | None = None
    log_file: Path | None = None
    error: str | None = None
    retries: int = 0
    
    def to_dict(self) -> dict[str, Any]:
        """转换为字典 (用于 UI 更新)"""
        return {
            "task_id": self.task_id,
            "url": self.url,
            "status": self.status.name.lower(),
            "downloaded_fragments": self.downloaded_fragments,
            "total_fragments": self.total_fragments,
            "progress_text": self._progress_text(),
        }
    
    def _progress_text(self) -> str:
        """获取进度文本"""
        if self.total_fragments is None:
            if self.downloaded_fragments > 0:
                return f"{self.downloaded_fragments}/?"
            return "-"
        return f"{self.downloaded_fragments}/{self.total_fragments}"


class TaskManager:
    """
    任务管理器
    
    职责:
    - 任务生命周期管理
    - 状态流转控制
    - 任务队列维护
    - 事件发布
    """
    
    def __init__(self, event_bridge: EventBridge, max_workers: int = 3):
        """
        初始化任务管理器
        
        Args:
            event_bridge: 事件总线
            max_workers: 最大并发数
        """
        self.event_bridge = event_bridge
        self.max_workers = max_workers
        
        self.tasks: dict[int, Task] = {}
        self.next_task_id = 1
        
        # 状态队列
        self.pending_ids: list[int] = []
        self.running_ids: list[int] = []
        self.done_ids: list[int] = []
        self.failed_ids: list[int] = []
        
        # 回调
        self._on_status_change: Callable[[int, TaskStatus, TaskStatus], None] | None = None
    
    def set_status_change_callback(
        self,
        callback: Callable[[int, TaskStatus, TaskStatus], None],
    ) -> None:
        """设置状态变更回调"""
        self._on_status_change = callback
    
    def add_task(self, url: str) -> int:
        """
        添加新任务
        
        Args:
            url: 下载 URL
            
        Returns:
            任务 ID
        """
        tid = self.next_task_id
        self.next_task_id += 1
        
        task = Task(task_id=tid, url=url)
        self.tasks[tid] = task
        self.pending_ids.append(tid)
        
        self.event_bridge.publish("task_added", {"task_id": tid, "url": url})
        
        return tid
    
    def add_tasks(self, urls: list[str]) -> list[int]:
        """批量添加任务"""
        return [self.add_task(url) for url in urls]
    
    def get_pending_tasks(self) -> list[Task]:
        """获取待下载任务"""
        return [self.tasks[tid] for tid in self.pending_ids]
    
    def get_running_tasks(self) -> list[Task]:
        """获取正在下载任务"""
        return [self.tasks[tid] for tid in self.running_ids]
    
    def get_done_tasks(self) -> list[Task]:
        """获取已完成任务"""
        return [self.tasks[tid] for tid in self.done_ids]
    
    def get_failed_tasks(self) -> list[Task]:
        """获取失败任务"""
        return [self.tasks[tid] for tid in self.failed_ids]
    
    def mark_running(self, task_id: int) -> None:
        """标记任务为运行中"""
        self._transition(task_id, TaskStatus.RUNNING)
    
    def mark_done(
        self,
        task_id: int,
        output_file: Path,
        log_file: Path,
    ) -> None:
        """标记任务为完成"""
        task = self.tasks[task_id]
        task.output_file = output_file
        task.log_file = log_file
        self._transition(task_id, TaskStatus.DONE)
    
    def mark_failed(self, task_id: int, error: str) -> None:
        """标记任务为失败"""
        task = self.tasks[task_id]
        task.error = error
        self._transition(task_id, TaskStatus.FAILED)
    
    def update_progress(
        self,
        task_id: int,
        downloaded: int,
        total: int | None,
    ) -> None:
        """更新任务进度"""
        task = self.tasks.get(task_id)
        if task:
            task.downloaded_fragments = downloaded
            task.total_fragments = total
            self.event_bridge.publish(
                "task_progress_updated",
                {"task_id": task_id, "downloaded": downloaded, "total": total},
            )
    
    def clear_pending(self) -> None:
        """清空待下载任务"""
        for tid in self.pending_ids:
            self.tasks[tid].status = TaskStatus.FAILED
            self.tasks[tid].error = "用户取消"
            self.failed_ids.append(tid)
        
        old_count = len(self.pending_ids)
        self.pending_ids = []
        
        self.event_bridge.publish(
            "pending_cleared",
            {"cleared_count": old_count},
        )
    
    def _transition(self, task_id: int, new_status: TaskStatus) -> None:
        """
        执行状态流转
        
        Args:
            task_id: 任务 ID
            new_status: 新状态
        """
        task = self.tasks[task_id]
        old_status = task.status
        
        # 从旧队列移除
        self._remove_from_queues(task_id)
        
        # 添加到新队列
        self._add_to_queue(task_id, new_status)
        
        # 更新状态
        task.status = new_status
        
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
            },
        )
    
    def _remove_from_queues(self, task_id: int) -> None:
        """从所有队列移除任务 ID"""
        for queue_list in [
            self.pending_ids,
            self.running_ids,
            self.done_ids,
            self.failed_ids,
        ]:
            if task_id in queue_list:
                queue_list.remove(task_id)
    
    def _add_to_queue(self, task_id: int, status: TaskStatus) -> None:
        """添加到对应状态队列"""
        if status == TaskStatus.PENDING:
            self.pending_ids.append(task_id)
        elif status == TaskStatus.RUNNING:
            self.running_ids.append(task_id)
        elif status == TaskStatus.DONE:
            self.done_ids.append(task_id)
        elif status == TaskStatus.FAILED:
            self.failed_ids.append(task_id)
    
    def get_summary(self) -> dict[str, int]:
        """获取任务摘要"""
        return {
            "total": len(self.tasks),
            "pending": len(self.pending_ids),
            "running": len(self.running_ids),
            "done": len(self.done_ids),
            "failed": len(self.failed_ids),
        }
```

---

### 4. DownloadService (下载服务)

**文件**: `gui/services/download_service.py`

```python
"""下载服务 - 业务逻辑封装"""

from concurrent.futures import ThreadPoolExecutor, Future
from pathlib import Path
from typing import Callable, Any

from webvidgrab.site_cli import ProbeResult, run_site_download


class DownloadService:
    """
    下载服务
    
    职责:
    - 下载任务执行
    - 并发控制
    - 进度回调
    - 错误处理
    """
    
    def __init__(self, max_workers: int = 3):
        """
        初始化下载服务
        
        Args:
            max_workers: 最大并发数
        """
        self.max_workers = max_workers
        self.executor: ThreadPoolExecutor | None = None
        self.active_futures: dict[Future, int] = {}
    
    def start(self) -> None:
        """启动服务"""
        self.executor = ThreadPoolExecutor(
            max_workers=self.max_workers,
            thread_name_prefix="download",
        )
    
    def stop(self, cancel_futures: bool = False) -> None:
        """
        停止服务
        
        Args:
            cancel_futures: 是否取消活跃任务
        """
        if self.executor:
            self.executor.shutdown(
                wait=not cancel_futures,
                cancel_futures=cancel_futures,
            )
            self.executor = None
            self.active_futures.clear()
    
    def submit_task(
        self,
        task_id: int,
        url: str,
        output_dir: Path,
        config: dict[str, Any],
        on_progress: Callable[[int, int | None], None],
        on_log: Callable[[str], None],
    ) -> Future:
        """
        提交下载任务
        
        Args:
            task_id: 任务 ID
            url: 下载 URL
            output_dir: 输出目录
            config: 下载配置
            on_progress: 进度回调 (downloaded, total)
            on_log: 日志回调 (message)
            
        Returns:
            Future 对象
        """
        if not self.executor:
            raise RuntimeError("DownloadService not started")
        
        future = self.executor.submit(
            self._execute_download,
            task_id,
            url,
            output_dir,
            config,
            on_progress,
            on_log,
        )
        self.active_futures[future] = task_id
        
        # 任务完成时自动从 active_futures 移除
        future.add_done_callback(
            lambda fut: self.active_futures.pop(fut, None)
        )
        
        return future
    
    def get_active_count(self) -> int:
        """获取活跃任务数"""
        return len(self.active_futures)
    
    def _execute_download(
        self,
        task_id: int,
        url: str,
        output_dir: Path,
        config: dict[str, Any],
        on_progress: Callable[[int, int | None], None],
        on_log: Callable[[str], None],
    ) -> tuple[int, ProbeResult | Exception]:
        """
        执行单个下载任务
        
        Args:
            task_id: 任务 ID
            url: 下载 URL
            output_dir: 输出目录
            config: 下载配置
            on_progress: 进度回调
            on_log: 日志回调
            
        Returns:
            (任务 ID, 结果或异常)
        """
        try:
            result = run_site_download(
                page_url=url,
                output_dir=output_dir,
                browser=config.get("browser", "chrome"),
                profile=config.get("profile", "Default"),
                capture_seconds=config.get("capture_seconds", 30),
                use_runtime_capture=config.get("use_runtime_capture", True),
                log_func=lambda msg: on_log(f"[task-{task_id}] {msg}"),
                progress_callback=on_progress,
            )
            return (task_id, result)
        except Exception as e:
            return (task_id, e)
```

---

### 5. EventBridge (事件总线)

**文件**: `gui/core/event_bridge.py`

```python
"""事件总线 - 组件间通信"""

import queue
import time
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Event:
    """事件数据类"""
    type: str
    payload: Any
    timestamp: float = field(default_factory=time.time)


class EventBridge:
    """
    事件总线
    
    职责:
    - 事件发布
    - 事件订阅
    - 事件轮询处理
    """
    
    def __init__(self):
        self._queue: queue.Queue[Event] = queue.Queue()
        self._handlers: dict[str, list[Callable]] = {}
    
    def subscribe(self, event_type: str, handler: Callable) -> None:
        """
        订阅事件
        
        Args:
            event_type: 事件类型
            handler: 处理函数 (接收 payload)
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    def publish(self, event_type: str, payload: Any = None) -> None:
        """
        发布事件
        
        Args:
            event_type: 事件类型
            payload: 事件数据
        """
        event = Event(type=event_type, payload=payload)
        self._queue.put(event)
    
    def poll(self, timeout_ms: int = 50) -> list[Event]:
        """
        轮询并处理事件
        
        Args:
            timeout_ms: 超时时间 (毫秒)
            
        Returns:
            处理的事件列表
        """
        processed = []
        
        try:
            while True:
                event = self._queue.get_nowait()
                handlers = self._handlers.get(event.type, [])
                
                for handler in handlers:
                    try:
                        handler(event.payload)
                    except Exception as e:
                        # 记录 handler 错误，但不影响其他 handler
                        print(f"Event handler error: {e}")
                
                processed.append(event)
        except queue.Empty:
            pass
        
        return processed
    
    def clear(self) -> int:
        """
        清空事件队列
        
        Returns:
            清空的事件数量
        """
        count = 0
        while not self._queue.empty():
            self._queue.get_nowait()
            count += 1
        return count
```

---

### 6. App 协调器

**文件**: `gui/app.py`

```python
"""应用协调器 - 组装各组件"""

import tkinter as tk
from pathlib import Path

from .components.main_panel import MainPanel
from .managers.task_manager import TaskManager, Task
from .services.download_service import DownloadService
from .core.event_bridge import EventBridge


class App:
    """
    应用协调器
    
    职责:
    - 组件初始化
    - 事件绑定
    - 主循环协调
    
    不包含:
    - UI 构建细节
    - 业务逻辑实现
    - 状态管理
    """
    
    def __init__(self, root: tk.Tk):
        """初始化应用"""
        self.root = root
        self.root.title("PSiteDL")
        self.root.geometry("1180x820")
        
        # 初始化核心组件
        self.event_bridge = EventBridge()
        self.task_manager = TaskManager(self.event_bridge, max_workers=3)
        self.download_service = DownloadService(max_workers=3)
        
        # 初始化 UI
        self._setup_callbacks()
        self.main_panel = MainPanel(self.root, self.callbacks)
        self.main_panel.pack(fill=tk.BOTH, expand=True)
        
        # 绑定事件
        self._bind_events()
        
        # 启动下载服务
        self.download_service.start()
        
        # 启动事件轮询
        self._poll_events()
    
    def _setup_callbacks(self) -> None:
        """设置 UI 回调"""
        self.callbacks = {
            "on_add_task": self._handle_add_task,
            "on_start_download": self._handle_start_download,
            "on_clear_pending": self._handle_clear_pending,
            "on_pick_output_dir": self._handle_pick_output_dir,
            "on_clear_log": self._handle_clear_log,
        }
    
    def _bind_events(self) -> None:
        """绑定事件处理器"""
        # 任务状态变更 → 更新 UI
        self.event_bridge.subscribe(
            "task_status_changed",
            self._on_task_status_changed,
        )
        
        # 任务进度更新 → 更新 UI
        self.event_bridge.subscribe(
            "task_progress_updated",
            self._on_task_progress_updated,
        )
        
        # 任务添加 → 刷新列表
        self.event_bridge.subscribe(
            "task_added",
            lambda _: self._refresh_task_list(),
        )
        
        # 待下载清空 → 刷新列表
        self.event_bridge.subscribe(
            "pending_cleared",
            lambda _: self._refresh_task_list(),
        )
    
    def _poll_events(self) -> None:
        """轮询事件 (主循环)"""
        self.event_bridge.poll()
        self.root.after(50, self._poll_events)
    
    # ========== 事件处理器 ==========
    
    def _handle_add_task(self) -> None:
        """处理添加任务"""
        form_data = self.main_panel.get_form_data()
        urls = [u.strip() for u in form_data["urls"] if u.strip()]
        
        if not urls:
            self.main_panel.show_warning("提示", "请填写至少一个 URL。")
            return
        
        # 去重
        existing_urls = {task.url for task in self.task_manager.tasks.values()}
        new_urls = [u for u in urls if u not in existing_urls]
        
        if not new_urls:
            self.main_panel.show_warning("提示", "所有 URL 已存在。")
            return
        
        # 添加任务
        self.task_manager.add_tasks(new_urls)
        self.main_panel.clear_urls()
        self._refresh_task_list()
        self.main_panel.append_log(f"[queue] 新增任务 {len(new_urls)} 个。")
    
    def _handle_start_download(self) -> None:
        """处理开始下载"""
        pending = self.task_manager.get_pending_tasks()
        
        if not pending:
            self.main_panel.show_warning("提示", "待下载任务为空。")
            return
        
        form_data = self.main_panel.get_form_data()
        output_dir = Path(form_data["output_dir"]).expanduser()
        
        config = {
            "browser": form_data["browser"],
            "profile": form_data["profile"],
            "capture_seconds": int(form_data["capture_seconds"]),
            "use_runtime_capture": form_data["use_runtime_capture"],
        }
        
        # 启动下载
        self.main_panel.set_status_text("队列下载中...")
        
        for task in pending[:3]:  # 最多 3 并发
            self.task_manager.mark_running(task.task_id)
            self.download_service.submit_task(
                task_id=task.task_id,
                url=task.url,
                output_dir=output_dir,
                config=config,
                on_progress=lambda d, t, tid=task.task_id: self._on_progress(tid, d, t),
                on_log=lambda msg: self.main_panel.append_log(msg),
            )
        
        self._refresh_task_list()
    
    def _handle_clear_pending(self) -> None:
        """处理清空待下载"""
        if self.task_manager.running_ids:
            self.main_panel.show_warning("提示", "下载进行中，暂不允许清空待下载。")
            return
        
        self.task_manager.clear_pending()
        self._refresh_task_list()
        self.main_panel.append_log("[queue] 已清空待下载任务。")
    
    def _handle_pick_output_dir(self) -> None:
        """处理选择目录"""
        from tkinter import filedialog
        
        path = filedialog.askdirectory(title="选择输出目录")
        if path:
            # 更新表单
            form_data = self.main_panel.get_form_data()
            form_data["output_dir"] = str(Path(path).resolve())
            self.main_panel.set_data(form_data)
    
    def _handle_clear_log(self) -> None:
        """处理清空日志"""
        self.main_panel.clear_log()
    
    # ========== 事件回调 ==========
    
    def _on_task_status_changed(
        self,
        payload: dict,
    ) -> None:
        """任务状态变更回调"""
        task_id = payload["task_id"]
        new_status = payload["new_status"]
        
        if new_status == "DONE":
            task = self.task_manager.tasks[task_id]
            self.main_panel.append_log(f"[task-{task_id}] [saved] {task.output_file}")
        elif new_status == "FAILED":
            task = self.task_manager.tasks[task_id]
            self.main_panel.append_log(f"[task-{task_id}] [failed] {task.error}")
        
        self._refresh_task_list()
        self._update_status_line()
    
    def _on_task_progress_updated(
        self,
        payload: dict,
    ) -> None:
        """任务进度更新回调"""
        self._refresh_task_list()
    
    def _on_progress(
        self,
        task_id: int,
        downloaded: int,
        total: int | None,
    ) -> None:
        """下载进度回调 (从工作线程调用)"""
        self.event_bridge.publish(
            "task_progress_updated",
            {"task_id": task_id, "downloaded": downloaded, "total": total},
        )
    
    def _refresh_task_list(self) -> None:
        """刷新任务列表"""
        pending = [t.to_dict() for t in self.task_manager.get_pending_tasks()]
        active = [t.to_dict() for t in self.task_manager.get_running_tasks()]
        completed = [t.to_dict() for t in self.task_manager.get_done_tasks()]
        self.main_panel.update_task_list(pending, active, completed)
    
    def _update_status_line(self) -> None:
        """更新状态行"""
        summary = self.task_manager.get_summary()
        status = (
            f"下载中：正在{summary['running']} | "
            f"待下载{summary['pending']} | "
            f"已完成{summary['done']}"
        )
        self.main_panel.set_status_text(status)
    
    def on_close(self) -> None:
        """应用关闭处理"""
        self.download_service.stop(cancel_futures=True)
        self.root.destroy()
```

---

## 🔗 组件依赖图

```
┌────────────────────────────────────────────────────────────┐
│                      组件依赖关系                          │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  site_gui.py (入口)                                        │
│      │                                                     │
│      │ imports                                             │
│      ▼                                                     │
│  ┌──────────────────────────────────────────────────────┐ │
│  │                   gui/app.py                         │ │
│  │                  (App 协调器)                          │ │
│  └──────────────────────────────────────────────────────┘ │
│      │                                                     │
│      │ uses                                                │
│      ├──→ gui/components/main_panel.py                    │
│      │       ├──→ gui/components/form_panel.py            │
│      │       ├──→ gui/components/task_list_view.py        │
│      │       └──→ gui/components/log_viewer.py            │
│      │                                                     │
│      ├──→ gui/managers/task_manager.py                    │
│      │       └──→ gui/core/event_bridge.py                │
│      │                                                     │
│      ├──→ gui/services/download_service.py                │
│      │       └──→ webvidgrab/site_cli.py (业务逻辑)       │
│      │                                                     │
│      └──→ gui/core/event_bridge.py                        │
│                                                            │
│  依赖方向：上层依赖下层，下层不依赖上层                    │
│  事件方向：Manager/Service → EventBridge → Component       │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

## ✅ 迁移检查清单

### Phase 1: 基础拆分

- [ ] 创建目录结构
- [ ] 实现 `EventBridge`
- [ ] 实现 `TaskManager`
- [ ] 实现 `DownloadService`
- [ ] 实现 `MainPanel` 及子组件
- [ ] 实现 `App` 协调器
- [ ] 更新 `site_gui.py` 导入新组件
- [ ] 运行测试确保功能正常

### Phase 2: 测试覆盖

- [ ] 编写 `TaskManager` 单元测试
- [ ] 编写 `DownloadService` 单元测试
- [ ] 编写 `EventBridge` 单元测试
- [ ] 编写组件集成测试
- [ ] 确保覆盖率 > 80%

### Phase 3: 清理旧代码

- [ ] 确认新代码稳定运行
- [ ] 删除旧 `App` 类代码
- [ ] 更新文档
- [ ] 发布新版本

---

**文档完成时间**: 2026-03-15
