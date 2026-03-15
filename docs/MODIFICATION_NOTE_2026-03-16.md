# PSiteDL 修改说明（2026-03-16）

本文档汇总本轮对 PSiteDL 的功能修复、界面优化和工程清理改动，便于回溯与发布说明整理。

## 1. 目标与背景

- 完成批量下载链路可用性修复（CLI、并发下载、重试、参数透传）。
- 解决 macOS 上 GUI 启动后控件缺失/空白的问题。
- 按使用反馈优化界面细节：URL 区标题、设置项对齐、输入控件圆角化。
- 清理不应入库的运行产物（日志、coverage、egg-info）。

## 2. 核心改动

### 2.1 CLI 与批量下载能力增强

- `site_cli.py`
  - 增加/完善参数：`--config`、`--concurrency/-c`、`--max-retries/-r`、`--timeout/-t`、`--bandwidth-limit/-B`、`--log-level/-l`、`--version`。
  - 接入配置加载、合并与校验流程。
  - 将超时、重试、限速等参数传递到下载执行链路。

- `batch_downloader.py`
  - 修复批量任务调用错误（原先调用了不存在的方法）。
  - 改为基于 `asyncio + semaphore` 的真实并发下载。
  - 增加任务级重试流程与状态汇总。

- `downloader.py`
  - `ConcurrentDownloader` 支持 `max_retries`、`bandwidth_limit`。
  - 补齐 `download()` 能力，统一批处理调用路径。

- `config.py`
  - 默认值与文档对齐（下载目录、日志路径、带宽参数等）。
  - 浏览器枚举扩展，参数边界校验完善（timeout、max_retries、bandwidth_limit）。

### 2.2 GUI 稳定性修复与启动链路加固

- `site_gui.py`
  - 图标加载流程增强（优先 GIF，兼容 PNG）。
  - 增加 macOS 系统 Tk 8.5 兼容分支，避免控件渲染异常导致页面空白。
  - 修复布局容器在特定环境下的尺寸计算异常。

- 启动脚本
  - `run_psitedl_gui.sh`、桌面 `PSiteDL GUI.command` 增加解释器兜底顺序：
    1) 项目 `.venv/bin/python`
    2) `/opt/homebrew/bin/python3.11`
    3) 系统 `python3`
  - 统一注入 `TK_SILENCE_DEPRECATION=1`。

- 资源
  - 增加 `assets/icon-64.gif`，用于 Tk 兼容图标加载。

### 2.3 GUI 视觉与易用性优化（基于使用反馈）

- URL 输入卡片补充明确标题：`待下载 URL`。
- 设置区第一行改为三列等宽网格，修复 `浏览器 / 配置文件 / 输出目录` 的水平对齐。
- `Profile` 文案改为中文：`配置文件`。
- 输入控件统一圆角化：
  - 单行输入框（`DarkOrangeEntry`）
  - 多行文本框（`DarkOrangeText`，含 URL 与日志区）
  - 下拉框（`DarkOrangeCombobox`）

## 3. 工程与仓库清理

- 新增 `.gitignore` 与 `LICENSE`。
- 删除已跟踪的运行产物与构建产物：
  - `.coverage`
  - `logs/sitegrab/*`
  - `gui_startup.log`
  - `src/PSiteDL.egg-info/*`

## 4. 文档与测试更新

- 文档更新：
  - `README.md`
  - `docs/CONFIGURATION.md`

- 测试更新：
  - `tests/test_batch_download.py`
  - `tests/conftest.py`

## 5. 建议验证清单

1. CLI 参数链路：
   - 使用 `--url-file` + `--concurrency` + `--max-retries` + `--timeout` + `--bandwidth-limit` 执行批量下载。
2. GUI 启动：
   - 双击桌面 `PSiteDL GUI.command`，确认主界面完整显示。
3. GUI 细节：
   - 核对“待下载 URL”标题。
   - 核对设置区三列对齐与“配置文件”文案。
   - 核对 URL、输出目录、探测秒数、日志框均为圆角输入样式。
