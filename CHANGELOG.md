# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- GUI 进度可视化功能（v0.5.0）
  - 实时速度曲线图（PyQtGraph，1Hz 更新）
  - 智能 ETA 预测（指数加权滑动平均，误差 < ±20%）
  - 统计信息显示（当前/平均/峰值速度）
  - 带宽使用率图表
  - 参数区与日志区 7:3 布局
- 核心数据结构
  - `SpeedHistory`: 速度历史记录（环形缓冲区，60 秒）
  - `ETAPredictor`: ETA 预测器（指数平滑算法）
  - `DownloadProgress`: 下载进度整合类
- GUI 组件
  - `ProgressChartWidget`: 实时进度图表组件
  - 深色主题支持
  - 可配置的更新频率和平滑因子
- TDD 测试套件
  - 18 个单元测试用例
  - 覆盖核心算法和数据结构
  - 验收标准验证（AC1-AC4）

### Changed
- 界面布局优化（参数区 70%，日志区 30%）
- 使用 OpenSpec + TDD 开发流程

### Fixed
- N/A

### Deprecated
- N/A

### Removed
- N/A

### Security
- N/A

---

## [0.4.0] - 2026-03-15

### Added
- 断点续传功能
- 状态管理器（StateManager）
- 自动状态保存（30 秒间隔）
- 崩溃恢复机制
- 片段哈希校验（MD5）

### Changed
- 优化下载性能
- 改进错误处理

### Fixed
- 修复多任务并发问题
- 修复进度计算错误

---

## [0.3.0] - 2026-03-10

### Added
- 批量下载支持
- URL 去重功能
- 并发控制

### Changed
- 重构下载器架构
- 提升稳定性

---

## [0.2.0] - 2026-03-05

### Added
- GUI 界面
- 基础下载功能
- 进度显示

### Changed
- 初始版本优化

---

## [0.1.0] - 2026-03-01

### Added
- 项目初始化
- 核心下载引擎
- 命令行界面
