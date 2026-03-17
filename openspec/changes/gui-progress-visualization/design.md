# GUI 进度可视化 - 技术设计

## Architecture

### 组件架构

```
┌─────────────────────────────────────────────────────────┐
│                     MainWindow                          │
│  ┌─────────────────┐  ┌───────────────────────────────┐ │
│  │  DownloadPanel  │  │    ProgressChartPanel         │ │
│  │  - URL 输入      │  │    - 速度曲线图 (PyQtGraph)   │ │
│  │  - 开始按钮      │  │    - 当前速度显示             │ │
│  │  - 进度条       │  │    - 平均速度                 │ │
│  │  - 暂停/恢复    │  │    - 峰值速度                 │ │
│  └─────────────────┘  │    - ETA 预测                 │ │
│                       │    - 带宽使用图               │ │
│  ┌─────────────────┐  └───────────────────────────────┘ │
│  │ TaskQueuePanel  │  ┌───────────────────────────────┐ │
│  │  - 任务列表      │  │    ControlPanel               │ │
│  │  - 状态图标      │  │    - 全部暂停/恢复            │ │
│  │  - 进度条 (每个) │  │    - 带宽限制滑块             │ │
│  │  - 单任务控制    │  │    - 并发数调节               │ │
│  └─────────────────┘  └───────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### 数据流

```
Downloader (Backend)
    │
    ├─> SpeedHistory (环形缓冲区，60 秒)
    │       │
    │       └─> QTimer (1Hz) ──> ProgressChart.update()
    │
    ├─> ProgressData ──> Signal ──> GUI 更新
    │
    └─> TaskState ──> Signal ──> TaskQueueView.update()
```

## Components

### 1. SpeedHistory (速度历史记录)

**位置**: `src/webvidgrab/progress.py`

```python
from collections import deque
import numpy as np

class SpeedHistory:
    """环形缓冲区存储最近 60 秒的速度数据"""
    
    def __init__(self, max_seconds=60):
        self.max_seconds = max_seconds
        self.buffer = deque(maxlen=max_seconds)
        self.timestamps = deque(maxlen=max_seconds)
    
    def add(self, speed_bps: float, timestamp: float):
        """添加速度样本"""
        self.buffer.append(speed_bps)
        self.timestamps.append(timestamp)
    
    def get_recent(self, seconds=10) -> np.ndarray:
        """获取最近 N 秒的数据"""
        if not self.buffer:
            return np.array([])
        
        cutoff = self.timestamps[-1] - seconds
        indices = [i for i, t in enumerate(self.timestamps) if t >= cutoff]
        return np.array([self.buffer[i] for i in indices])
    
    def get_average(self, seconds=10) -> float:
        """计算最近 N 秒的平均速度"""
        recent = self.get_recent(seconds)
        return np.mean(recent) if len(recent) > 0 else 0.0
```

### 2. ETAPredictor (ETA 预测器)

**位置**: `src/webvidgrab/progress.py`

```python
class ETAPredictor:
    """智能 ETA 预测（指数加权滑动平均）"""
    
    def __init__(self, alpha=0.3):
        self.alpha = alpha  # 平滑因子
        self.ema_speed = None
    
    def update(self, current_speed: float) -> float:
        """更新速度并返回预测 ETA"""
        if self.ema_speed is None:
            self.ema_speed = current_speed
        else:
            # 指数加权移动平均
            self.ema_speed = (self.alpha * current_speed + 
                            (1 - self.alpha) * self.ema_speed)
        
        return self.ema_speed
    
    def calculate_eta(self, remaining_bytes: int) -> int:
        """计算剩余时间（秒）"""
        if self.ema_speed <= 0:
            return float('inf')
        return int(remaining_bytes / self.ema_speed)
    
    def format_eta(self, seconds: int) -> str:
        """格式化 ETA 显示"""
        if seconds == float('inf'):
            return "--:--"
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"
```

### 3. ProgressChartWidget (进度图表组件)

**位置**: `src/webvidgrab/gui/progress_chart.py`

```python
import pyqtgraph as pg
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import QTimer

class ProgressChartWidget(QWidget):
    """实时进度图表组件"""
    
    def __init__(self):
        super().__init__()
        self.speed_history = SpeedHistory()
        self.eta_predictor = ETAPredictor()
        
        self._init_ui()
        self._init_timer()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # 速度图表
        self.speed_plot = pg.PlotWidget()
        self.speed_plot.setTitle("下载速度")
        self.speed_plot.setLabel('left', '速度', units='Mbps')
        self.speed_plot.setLabel('bottom', '时间', units='秒')
        self.speed_curve = self.speed_plot.plot(pen='b')
        
        # 统计信息
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                padding: 10px;
                background-color: #f0f0f0;
                border-radius: 5px;
            }
        """)
        
        # 带宽使用图表
        self.bandwidth_plot = pg.PlotWidget()
        self.bandwidth_plot.setTitle("带宽使用")
        self.bandwidth_plot.setLabel('left', '使用率', units='%')
        self.bandwidth_curve = self.bandwidth_plot.plot(pen='g')
        
        layout.addWidget(self.stats_label)
        layout.addWidget(self.speed_plot)
        layout.addWidget(self.bandwidth_plot)
    
    def _init_timer(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_charts)
        self.timer.start(1000)  # 1Hz 更新
    
    def update_speed(self, speed_bps: float, total_bandwidth_bps: float):
        """更新速度数据"""
        import time
        self.speed_history.add(speed_bps, time.time())
        self.eta_predictor.update(speed_bps)
        
        # 更新带宽限制使用率
        self.bandwidth_usage = (speed_bps / total_bandwidth_bps * 100) if total_bandwidth_bps > 0 else 0
    
    def _update_charts(self):
        """更新图表显示"""
        # 更新速度曲线
        speeds = self.speed_history.get_recent(60) / 1_000_000  # 转换为 Mbps
        self.speed_curve.setData(speeds)
        
        # 更新带宽使用曲线
        self.bandwidth_curve.setData([self.bandwidth_usage])
        
        # 更新统计信息
        current_speed = speeds[-1] if len(speeds) > 0 else 0
        avg_speed = np.mean(speeds) if len(speeds) > 0 else 0
        peak_speed = np.max(speeds) if len(speeds) > 0 else 0
        
        self.stats_label.setText(f"""
        当前速度：{current_speed:.2f} Mbps
        平均速度：{avg_speed:.2f} Mbps
        峰值速度：{peak_speed:.2f} Mbps
        """)
```

### 4. TaskQueueView (任务队列视图)

**位置**: `src/webvidgrab/gui/task_queue_view.py`

```python
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QScrollArea, 
                             QLabel, QPushButton, QProgressBar)
from PyQt5.QtCore import pyqtSignal

class TaskItemWidget(QWidget):
    """单个任务项组件"""
    
    pause_clicked = pyqtSignal(int)
    resume_clicked = pyqtSignal(int)
    
    def __init__(self, task_id: int, url: str):
        super().__init__()
        self.task_id = task_id
        self._init_ui(url)
    
    def _init_ui(self, url):
        layout = QVBoxLayout(self)
        
        # URL 标签
        url_label = QLabel(url)
        url_label.setWordWrap(True)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        
        # 状态标签
        self.status_label = QLabel("等待中")
        
        # 控制按钮
        self.control_btn = QPushButton("暂停")
        self.control_btn.clicked.connect(self._on_control_click)
        
        layout.addWidget(url_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.status_label)
        layout.addWidget(self.control_btn)
    
    def _on_control_click(self):
        if self.control_btn.text() == "暂停":
            self.pause_clicked.emit(self.task_id)
        else:
            self.resume_clicked.emit(self.task_id)
    
    def update_status(self, status: str, progress: float):
        """更新任务状态"""
        self.status_label.setText(status)
        self.progress_bar.setValue(int(progress * 100))
        
        if status == "下载中":
            self.control_btn.setText("暂停")
        elif status == "已暂停":
            self.control_btn.setText("恢复")
```

## Integration Points

### 与 Downloader 集成

```python
# src/webvidgrab/downloader.py
from .progress import SpeedHistory, ETAPredictor
from .gui.progress_chart import ProgressChartWidget

class ConcurrentDownloader:
    def __init__(self, config):
        self.speed_history = SpeedHistory()
        self.eta_predictor = ETAPredictor()
        self.progress_widget = None  # GUI 组件
    
    def set_gui_callback(self, widget: ProgressChartWidget):
        """设置 GUI 回调"""
        self.progress_widget = widget
    
    def _download_segment(self, segment_url, output_path):
        """下载单个片段（带速度跟踪）"""
        start_time = time.time()
        # ... 下载逻辑 ...
        elapsed = time.time() - start_time
        speed = downloaded_bytes / elapsed if elapsed > 0 else 0
        
        # 更新速度历史
        self.speed_history.add(speed, time.time())
        
        # 通知 GUI 更新
        if self.progress_widget:
            self.progress_widget.update_speed(speed, self.config.bandwidth_limit)
```

### 与 GUI 集成

```python
# src/webvidgrab/site_gui.py
from .gui.progress_chart import ProgressChartWidget
from .gui.task_queue_view import TaskQueueView

class DownloadGUI:
    def __init__(self):
        self.progress_chart = ProgressChartWidget()
        self.task_queue = TaskQueueView()
        
        self._layout_widgets()
    
    def _layout_widgets(self):
        """布局组件"""
        main_layout = QHBoxLayout()
        
        # 左侧：下载控制
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(self.download_panel)
        left_layout.addWidget(self.task_queue)
        
        # 右侧：进度图表
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.addWidget(self.progress_chart)
        right_layout.addWidget(self.control_panel)
        
        main_layout.addWidget(left_panel, stretch=1)
        main_layout.addWidget(right_panel, stretch=2)
        
        self.central_widget.setLayout(main_layout)
```

## Testing Strategy

### 单元测试

```python
# tests/test_progress_chart.py
def test_speed_history_buffer():
    """测试速度历史环形缓冲区"""
    history = SpeedHistory(max_seconds=60)
    
    for i in range(100):
        history.add(i * 1000, time.time() + i)
    
    assert len(history.buffer) <= 60  # 不超过最大值
    assert len(history.get_recent(10)) <= 10

def test_eta_prediction_accuracy():
    """测试 ETA 预测准确性"""
    predictor = ETAPredictor(alpha=0.3)
    
    # 模拟稳定速度
    for _ in range(20):
        predictor.update(1_000_000)  # 1 Mbps
    
    eta = predictor.calculate_eta(10_000_000)  # 10 MB 剩余
    assert 8 <= eta <= 12  # 应该在 10 秒左右（±20%）
```

### 集成测试

```python
# tests/test_gui_integration.py
def test_realtime_chart_update():
    """测试实时图表更新"""
    downloader = ConcurrentDownloader(config)
    gui = DownloadGUI()
    
    downloader.set_gui_callback(gui.progress_chart)
    
    # 启动下载
    thread = threading.Thread(target=downloader.download_batch, args=(urls,))
    thread.start()
    
    # 等待 5 秒
    time.sleep(5)
    
    # 验证图表已更新
    assert len(gui.progress_chart.speed_history.buffer) > 0
    assert gui.progress_chart.stats_label.text() != ""
    
    thread.join()
```

## Performance Considerations

### 优化策略

1. **图表更新节流**: 1Hz 更新频率，避免频繁重绘
2. **环形缓冲区**: 固定大小内存占用，避免内存泄漏
3. **NumPy 向量化**: 使用 NumPy 加速统计计算
4. **独立线程**: 图表更新在独立线程，不阻塞下载

### 性能目标

- 图表更新延迟：< 100ms
- 内存占用：< 10MB (60 秒历史数据)
- CPU 占用：< 5% (下载 + 图表)

## Migration Plan

### Phase 1: 核心功能 (2026-03-20)
- [ ] 实现 `SpeedHistory` 和 `ETAPredictor`
- [ ] 实现 `ProgressChartWidget`
- [ ] 集成到 `site_gui.py`

### Phase 2: 任务队列 (2026-03-25)
- [ ] 实现 `TaskQueueView`
- [ ] 实现单任务暂停/恢复
- [ ] 实现全局控制

### Phase 3: 优化测试 (2026-03-31)
- [ ] 性能优化
- [ ] 单元测试
- [ ] 集成测试
- [ ] 文档更新

---

**Design Version**: 1.0  
**Created**: 2026-03-17  
**Author**: OpenSpec + AI TDD  
**Status**: Ready for Implementation
