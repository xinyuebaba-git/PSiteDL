# 变更日志

所有重要变更将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [未发布]

### Added
- **批量下载文档**: 新增完整的批量下载用户指南
  - `docs/BATCH_DOWNLOAD.md` - 批量下载完整指南
    - URL 文件格式说明
    - 并发控制策略
    - 错误处理与重试机制
    - 带宽管理技巧
    - 进度监控方法
    - 最佳实践和故障排除
  - `docs/URL_DEDUP.md` - URL 去重和清洗指南
    - 去重方法和工具
    - URL 清洗技巧
    - 自动化脚本示例
  - `examples/urls_sample.txt` - 示例 URL 文件模板
- **README 更新**: 增强批量下载示例和参数说明
  - 添加 `--url-file` 参数详细说明
  - 新增批量下载示例 (并发/带宽限制)
  - 更新快速开始章节
- **GUI 图标兼容资源**: 新增 `assets/icon-64.gif`，提升 Tk 环境图标加载成功率
- **修改说明文档**: 新增 `docs/MODIFICATION_NOTE_2026-03-16.md`

### Changed
- 优化文档结构，批量下载相关文档独立成篇
- **CLI 与下载链路增强**
  - `site_cli.py` 新增并完善配置/并发/重试/超时/限速/日志级别等参数
  - `batch_downloader.py` 修复批量下载调用路径并实现真实并发与任务级重试
  - `downloader.py` 增加 `download()` 入口，补充重试与带宽参数透传
  - `config.py` 完善默认值与校验（浏览器枚举、timeout、max_retries、bandwidth_limit）
- **GUI 启动链路加固**
  - `run_psitedl_gui.sh` 与桌面启动脚本优先使用 `.venv`，回退到 Homebrew Python，再回退系统 Python
  - 统一设置 `TK_SILENCE_DEPRECATION=1`
- **GUI 交互与布局优化**
  - URL 区补充明确标题“待下载 URL”
  - 设置区首行改为三列等宽网格，修复浏览器/配置文件/输出目录水平对齐
  - `Profile` 文案改为“配置文件”
  - 输入框、文本框、下拉框统一圆角风格（含 URL 与日志区）

### Removed
- 删除已跟踪的运行产物与构建产物：
  - `.coverage`
  - `gui_startup.log`
  - `logs/sitegrab/*.log`
  - `src/PSiteDL.egg-info/*`

## [0.4.0] - 2026-03-15

### Added
- **并发下载器** (Phase 4): 新增 `downloader.py` 模块
  - `ConcurrentDownloader` - 并发下载器核心类
    - `max_concurrent` - 最大并发数配置
    - `active_count()` - 获取当前活跃下载数
    - `download_sync()` - 同步单文件下载
    - `download_batch()` - 异步批量下载
  - `DownloadQueue` - 下载队列管理
    - `add()` / `get()` - 队列操作
    - `size()` / `is_empty()` - 状态查询
  - `RetryQueue` - 失败重试队列
    - `max_retries` - 最大重试次数
    - `pending_count()` - 待重试任务数
    - `get_retryable()` - 获取可重试任务
  - `PriorityDownloadQueue` - 优先级队列
    - 支持任务优先级调度
  - `BandwidthLimiter` - 带宽限制器
    - `limit_mbps` - 带宽限制 (Mbps)
    - `acquire()` - 令牌获取
    - `release()` - 令牌释放

### Improved
- 批量下载性能大幅提升，支持并发处理多个 URL
- 下载任务支持优先级调度，重要任务优先处理
- 带宽限制功能避免占用全部网络资源
- 失败任务自动重试，提高下载成功率

## [0.3.0] - 2026-03-15

### Added
- **错误处理增强** (Phase 3): 新增 `errors.py` 模块
  - `@retry_on_error` - 重试装饰器，支持指定异常类型和重试次数
  - `RetryExhaustedError` - 重试用尽异常
  - `handle_network_error()` - 网络错误上下文管理器
  - `NetworkTimeoutError` - 网络超时异常
  - `DNSResolutionError` - DNS 解析失败异常
  - `ConnectionResetError_` - 连接重置异常
  - `safe_extract_videos()` - 安全视频提取 (优雅降级)
  - `safe_export_cookies()` - Cookie 导出错误处理
  - `ErrorHandler` - 错误日志记录器

- **进度显示增强** (Phase 3): 新增 `progress.py` 模块
  - `DownloadProgress` - 单文件进度跟踪
    - 实时更新已下载字节数
    - 百分比计算
    - 下载速度计算 (bytes/s)
    - 预计剩余时间 (ETA)
  - `MultiProgressTracker` - 多文件进度跟踪
    - 批量文件管理
    - 整体进度计算
    - 文件状态汇总
  - `render_progress_bar()` - 文本进度条渲染
  - `render_progress_info()` - 进度信息格式化
  - `RichProgressDisplay` - Rich 库集成进度显示
  - 进度持久化支持 (断点续传)

### Changed
- 更新 `pyproject.toml` 依赖
  - 新增 `rich` (终端美化进度条)
- 版本号从 0.2.0 升级到 0.3.0

### Improved
- 错误处理机制完善，支持自动重试和优雅降级
- 进度显示更加友好，支持实时速度和剩余时间
- 网络错误分类更精细，便于诊断问题

## [0.2.0] - 2026-03-15

### Added
- **配置管理** (Phase 2): 完善 `config.py` 模块
  - `load_config()` - 从 JSON 文件加载配置
  - `save_config()` - 保存配置到文件
  - `validate_config()` - 配置验证 (路径、范围、枚举)
  - `get_default_config()` - 获取默认配置
  - `merge_configs()` - CLI 参数与配置文件合并
  - `ConfigError` - 配置相关异常

- **日志系统** (Phase 2): 完善 `logging.py` 模块
  - `create_logger()` - 创建基础日志器
  - `create_logger_with_rotation()` - 按大小轮转日志
  - `create_date_logger()` - 按日期轮转日志
  - `create_audit_logger()` - 审计日志器
  - `AuditLogger` - 审计日志类
  - `log_context()` - 日志上下文管理器
  - `log_execution_time()` - 执行时间装饰器
  - `log_if_slow()` - 慢操作检测装饰器
  - `StructuredFormatter` - JSON 格式日志输出

### Added
- **配置管理**: 新增 `config.py` 模块，支持 JSON 配置文件
  - `load_config()` - 加载配置
  - `save_config()` - 保存配置
  - `validate_config()` - 验证配置
  - `get_default_config()` - 默认配置
- **日志系统**: 新增 `logging.py` 模块，支持结构化日志
  - 多种日志级别 (DEBUG/INFO/WARNING/ERROR)
  - 日志文件轮转 (按大小/日期)
  - 审计日志支持
  - 执行时间装饰器
- **错误处理**: 新增 `errors.py` 模块
  - 重试装饰器 `@retry_on_error`
  - 网络错误上下文管理
  - 安全提取函数 (优雅降级)
  - 错误统计和建议
- **进度显示**: 新增 `progress.py` 模块
  - 单文件进度跟踪
  - 多文件进度跟踪
  - 实时速度计算
  - 预计剩余时间
  - Rich 库集成
- **并发下载**: 新增 `downloader.py` 模块
  - 并发下载器 `ConcurrentDownloader`
  - 下载队列管理
  - 重试队列
  - 带宽限制器
  - 结果汇总报告
- **测试框架**: 完整的 TDD 测试套件
  - pytest 配置
  - 测试 fixtures (`conftest.py`)
  - 配置测试 (`test_config.py`)
  - 日志测试 (`test_logging.py`)
  - 错误处理测试 (`test_errors.py`)
  - 进度测试 (`test_progress.py`)
  - 下载器测试 (`test_downloader.py`)
- **文档**: 完善的开发文档
  - README.md - 用户指南
  - DEVELOPMENT.md - 开发者指南
  - CHANGELOG.md - 变更日志
  - CONTRIBUTING.md - 贡献指南
  - DEVELOPMENT_PLAN.md - 开发计划

### Changed
- 更新 `pyproject.toml` 依赖
  - 新增 `rich` (终端美化)
  - 新增 `aiohttp` (异步 HTTP)
  - 新增 `pydantic` (数据验证)
  - 新增 `structlog` (结构化日志)
  - 新增开发依赖 (pytest, black, ruff, mypy)
- 版本号从 0.1.0 升级到 0.2.0

### Improved
- 代码质量工具集成 (Black, Ruff, MyPy)
- 测试覆盖率目标 >= 80%
- 开发流程规范化 (TDD)

## [0.1.0] - 2026-03-01

### Added
- 初始版本发布
- 基本视频探测功能
- 命令行界面
- 图形界面
- 浏览器 Cookie 导出
- 批量 URL 支持

---

## 版本说明

### 语义化版本

- **MAJOR.MINOR.PATCH** (主版本号。次版本号。修订号)
- **MAJOR**: 不兼容的 API 变更
- **MINOR**: 向后兼容的功能新增
- **PATCH**: 向后兼容的问题修正

### 发布周期

- **PATCH**: 按需发布 (Bug 修复)
- **MINOR**: 每月发布 (功能迭代)
- **MAJOR**: 每季度发布 (重大更新)

---

**维护者**: PSiteDL 开发团队  
**联系方式**: (待添加)

---

**最后更新**: 2026-03-15  
**版本**: 0.4.0
