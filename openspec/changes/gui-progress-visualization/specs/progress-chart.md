# 能力规范：进度图表 (progress-chart)

## 概述

实时下载速度曲线图组件，使用 PyQtGraph 渲染，支持 1Hz 更新频率。

## 功能需求

### FR1: 速度曲线显示
- **描述**: 显示最近 60 秒的下载速度曲线
- **输入**: 实时速度数据（bps）
- **输出**: PyQtGraph 曲线图
- **更新频率**: 1Hz（每秒）
- **单位**: Mbps（兆比特每秒）

### FR2: 统计信息显示
- **描述**: 显示当前速度、平均速度、峰值速度
- **位置**: 图表上方统计面板
- **格式**: 
  ```
  当前速度：12.34 Mbps
  平均速度：10.56 Mbps
  峰值速度：15.78 Mbps
  ```

### FR3: ETA 预测显示
- **描述**: 显示预计剩余时间
- **算法**: 指数加权滑动平均（alpha=0.3）
- **格式**: `HH:MM:SS` 或 `MM:SS`
- **更新频率**: 每 5 秒（避免频繁跳动）

### FR4: 带宽使用图表
- **描述**: 显示当前带宽使用率
- **输入**: 当前速度 / 带宽限制
- **输出**: 百分比图表
- **范围**: 0-100%

## 非功能需求

### NFR1: 性能
- 图表更新延迟 < 100ms
- CPU 占用 < 3%（仅图表）
- 内存占用 < 5MB

### NFR2: 可用性
- 支持窗口大小调整
- 支持深色/浅色主题
- 图表清晰可读（抗锯齿）

### NFR3: 兼容性
- Python 3.10+
- PyQt5 5.15+ 或 PyQt6
- PyQtGraph 0.13+
- NumPy 1.20+

## 接口定义

### 类接口

```python
class ProgressChartWidget(QWidget):
    """进度图表组件"""
    
    def __init__(self, config: dict = None)
    def update_speed(self, speed_bps: float, total_bandwidth_bps: float)
    def reset(self)
    def set_theme(self, theme: str)
```

### 信号

```python
class ProgressChartWidget:
    speed_updated = pyqtSignal(float)  # 速度更新
    eta_updated = pyqtSignal(int)      # ETA 更新
```

### 配置项

```python
config = {
    "chart_update_interval": 1000,      # ms
    "speed_history_duration": 60,       # seconds
    "eta_smoothing_factor": 0.3,        # alpha
    "theme": "dark",                    # "dark" | "light"
}
```

## 测试场景

### 场景 1: 正常下载
```gherkin
当 下载开始时
那么 速度曲线从 0 开始上升
并且 统计信息显示当前速度
并且 ETA 显示合理值
```

### 场景 2: 网络波动
```gherkin
当 下载速度波动时
那么 曲线平滑显示波动
并且 ETA 不会剧烈跳动
并且 统计信息正确更新
```

### 场景 3: 下载完成
```gherkin
当 下载完成时
那么 速度归零
并且 ETA 显示 "--:--"
并且 统计信息保留最终值
```

## 依赖

- `pyqtgraph`: 图表渲染
- `PyQt5`/`PyQt6`: GUI 框架
- `numpy`: 数值计算
- `SpeedHistory`: 速度数据存储
- `ETAPredictor`: ETA 预测算法

## 验收标准

- [ ] 曲线图正确显示 60 秒历史
- [ ] 更新频率稳定在 1Hz
- [ ] 统计信息准确
- [ ] ETA 误差 < ±20%
- [ ] 性能达标
- [ ] 主题切换正常

---

**Capability**: progress-chart  
**Version**: 1.0  
**Created**: 2026-03-17  
**Status**: Draft
