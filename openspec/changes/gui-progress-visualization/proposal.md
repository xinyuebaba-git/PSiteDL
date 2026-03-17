# GUI 进度可视化增强

## Why

**问题**: 当前 PSiteDL 的 GUI 界面缺少直观的进度可视化，用户无法实时看到：
- 下载速度变化趋势
- 剩余时间预测
- 多任务并发状态
- 带宽使用情况

**为什么现在**: v0.5.0 的核心目标是提升用户体验，断点续传功能已完成（Phase 1-3），现在需要增强 GUI 可视化（Phase 4）来完成 v0.5.0 的核心功能。

## What Changes

**新增功能**:
1. 实时速度曲线图（使用 PyQtGraph）
2. 智能 ETA 预测（基于滑动平均算法）
3. 任务队列视图（等待/下载中/完成/失败）
4. 带宽限制可视化
5. 暂停/恢复控制按钮集成

**修改内容**:
- `site_gui.py` - 添加进度图表组件
- `progress.py` - 增强进度计算逻辑
- `downloader.py` - 集成实时数据推送

## Capabilities

### New Capabilities
- `progress-chart`: 实时下载速度曲线图，支持 1Hz 更新频率
- `eta-prediction`: 智能剩余时间预测，误差 < ±20%
- `task-queue-view`: 多任务队列状态可视化
- `bandwidth-monitor`: 带宽使用实时监控

### Modified Capabilities
- `gui-download`: 集成暂停/恢复控制，支持单任务和全局控制

## Impact

**前端**:
- 新增 `gui/progress_chart.py` (~300 行)
- 修改 `site_gui.py` (添加图表区域)
- 依赖：PyQtGraph (`pip install pyqtgraph`)

**后端**:
- 修改 `progress.py` (添加速度历史记录)
- 修改 `downloader.py` (实时数据推送)

**配置**:
- 新增 GUI 相关配置项（图表更新频率、ETA 算法参数）

## Acceptance Criteria

### AC1: 实时速度图表
```gherkin
场景：下载开始时
  当 用户启动下载
  那么 GUI 显示实时速度曲线图
  并且 图表每秒更新一次
  并且 显示当前速度、平均速度、峰值速度
```

### AC2: ETA 预测
```gherkin
场景：下载进行超过 10 秒
  当 下载持续进行
  那么 显示预计剩余时间 (ETA)
  并且 ETA 根据当前速度动态调整
  并且 预测误差在 ±20% 以内
```

### AC3: 任务队列管理
```gherkin
场景：批量下载时
  当 用户启动多任务下载
  那么 显示所有任务的状态（等待/下载中/完成/失败）
  并且 支持点击暂停单个任务
  并且 支持点击恢复暂停的任务
```

### AC4: 全局控制
```gherkin
场景：点击"全部暂停"按钮
  当 用户点击全局暂停
  那么 所有正在下载的任务暂停
  并且 已暂停的任务保持暂停状态
  
场景：点击"全部恢复"按钮
  当 用户点击全局恢复
  那么 所有暂停的任务恢复下载
```

## Technical Notes

**图表库选择**: PyQtGraph
- 优点：高性能、实时渲染、PyQt 原生集成
- 替代：Matplotlib（较慢，不适合实时更新）

**ETA 算法**: 滑动平均 + 指数加权
```python
# 伪代码
def calculate_eta(downloaded, total, speed_history):
    # 使用最近 10 秒的加权平均速度
    weighted_avg = exponential_moving_average(speed_history[-10:])
    remaining = total - downloaded
    return remaining / weighted_avg if weighted_avg > 0 else float('inf')
```

**性能考虑**:
- 图表更新频率：1Hz（避免 UI 卡顿）
- 速度历史记录：最近 60 秒（环形缓冲区）
- ETA 更新：每 5 秒重新计算（避免频繁跳动）

## Dependencies

```txt
# requirements.txt 新增
pyqtgraph>=0.13.0
PyQt5>=5.15.0  # 或 PyQt6
numpy>=1.20.0  # PyQtGraph 依赖
```

## Risks

1. **性能风险**: 图表更新可能影响下载性能
   - 缓解：使用独立线程更新图表，主线程专注下载

2. **兼容性风险**: PyQtGraph 在某些系统可能安装失败
   - 缓解：提供降级方案（文本进度条）

3. **复杂度风险**: 实时数据推送增加代码复杂度
   - 缓解：使用信号/槽机制，保持松耦合

---

**Change Name**: gui-progress-visualization  
**Created**: 2026-03-17  
**Status**: Proposed  
**Priority**: P0 (v0.5.0 核心功能)
