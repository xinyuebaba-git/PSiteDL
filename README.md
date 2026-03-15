# PSiteDL

**网页视频切片探测与下载工具** - 支持命令行和图形界面

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## ✨ 特性

- 🔍 **智能探测**: 自动提取网页中的 m3u8/mpd/mp4 等视频流
- 🍪 **Cookie 导出**: 支持 Chrome/Edge/Firefox 浏览器 Cookie 捕获
- 📥 **批量下载**: 支持 URL 文件批量并行处理
- 🖥️ **双模式**: CLI 命令行 + GUI 图形界面
- ⚡ **并发下载**: 可配置并发数，大幅提升下载效率
- 📊 **实时进度**: 下载速度、剩余时间、进度条显示
- 🔧 **配置管理**: 持久化用户配置，CLI 参数可覆盖
- 📝 **结构化日志**: 便于调试和审计
- 🛡️ **错误处理**: 自动重试、优雅降级

## 🚀 快速开始

### 安装

```bash
# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
python -m pip install -U pip
python -m pip install -e ".[dev]"  # 包含开发依赖
```

### 命令行使用

**基本用法**:
```bash
psitedl "https://example.com/video-page" \
  --output-dir "$HOME/Downloads" \
  --browser chrome \
  --profile Default \
  --capture-seconds 30
```

**并发下载 (大幅提升效率)**:
```bash
# 同时下载 5 个 URL
psitedl --url-file "/path/to/urls.txt" \
  --output-dir "$HOME/Downloads" \
  --concurrency 5

# 高并发模式 (适合宽带充足场景)
psitedl --url-file "urls.txt" \
  --concurrency 10 \
  --max-retries 5
```

**带宽限制 (避免占用全部网络)**:
```bash
# 限制下载速度为 10 Mbps
psitedl --url-file "urls.txt" \
  --concurrency 5 \
  --bandwidth-limit 10

# 后台下载模式 (低带宽占用)
psitedl --url-file "urls.txt" \
  --bandwidth-limit 2 \
  --log-level WARNING
```

**使用配置文件**:
```bash
psitedl "https://example.com/video" \
  --config ~/.psitedl/config.json
```

**批量下载 (推荐)**:
```bash
# 1. 创建 URL 文件 (urls.txt)
# 每行一个 URL，支持注释 (# 开头)
cat > urls.txt << EOF
https://example.com/video1
https://example.com/video2
https://example.com/video3
EOF

# 2. 执行批量下载
psitedl --url-file "urls.txt" \
  --output-dir "$HOME/Downloads" \
  --concurrency 5

# 3. 使用示例文件 (首次使用)
cp examples/urls_sample.txt ./my_urls.txt
# 编辑 my_urls.txt 替换为真实 URL
psitedl --url-file "my_urls.txt" --output-dir "./downloads"
```

### GUI 使用

```bash
psitedl-gui
```

## 🔧 CLI 参数说明

### 常用参数

| 参数 | 简写 | 说明 | 示例 |
|------|------|------|------|
| `--url-file` | `-f` | URL 文件路径 (批量下载) | `--url-file "urls.txt"` |
| `--output-dir` | `-o` | 输出目录 | `--output-dir "~/Downloads"` |
| `--browser` | `-b` | 浏览器类型 | `--browser chrome` |
| `--profile` | `-p` | 浏览器 Profile | `--profile Default` |
| `--concurrency` | `-c` | 并发下载数 | `--concurrency 5` |
| `--bandwidth-limit` | `-B` | 带宽限制 (Mbps) | `--bandwidth-limit 10` |
| `--max-retries` | `-r` | 最大重试次数 | `--max-retries 5` |
| `--timeout` | `-t` | 网络超时 (秒) | `--timeout 60` |
| `--log-level` | `-l` | 日志级别 | `--log-level DEBUG` |
| `--config` | `-C` | 配置文件路径 | `--config ~/.psitedl/config.json` |
| `--version` | - | 查看版本号 | `--version` |

### `--url-file` 参数详解

**用途**: 从文件读取多个 URL 进行批量下载

**文件格式**:
- 每行一个 URL
- 支持空行 (自动跳过)
- 支持注释 (以 `#` 开头)
- 自动去重 (重复 URL 仅下载一次)

**示例文件**:
```bash
# 使用示例文件
cp examples/urls_sample.txt ./my_urls.txt

# 编辑文件 (替换为真实 URL)
nano my_urls.txt

# 执行批量下载
psitedl --url-file "my_urls.txt" --output-dir "~/Downloads"
```

**完整示例**:
```bash
# 高并发批量下载
psitedl --url-file "urls.txt" \
  --output-dir "$HOME/Downloads" \
  --concurrency 10 \
  --max-retries 5 \
  --bandwidth-limit 50 \
  --log-level INFO
```

**注意事项**:
- URL 文件路径可以是绝对路径或相对路径
- 文件编码推荐 UTF-8
- 大文件 (1000+ URL) 建议分批处理
- 下载前建议去重 (参考 [docs/URL_DEDUP.md](docs/URL_DEDUP.md))

### 查看完整参数

```bash
# 查看帮助
psitedl --help

# 查看版本
psitedl --version
```

## 📖 详细文档

### 用户文档
- [批量下载指南](docs/BATCH_DOWNLOAD.md) - 批量下载完整教程
- [URL 去重说明](docs/URL_DEDUP.md) - URL 清洗和去重方法
- [下载使用指南](docs/DOWNLOADING.md) - 基本下载操作
- [高级功能](docs/ADVANCED.md) - 并发/重试/带宽限制详解
- [配置详解](docs/CONFIGURATION.md) - 配置项完整说明
- [API 参考](docs/API_REFERENCE.md) - 开发者 API 文档

### 开发者文档
- [开发指南](DEVELOPMENT.md) - 开发者文档
- [变更日志](CHANGELOG.md) - 版本历史
- [贡献指南](CONTRIBUTING.md) - 如何贡献

## ⚙️ 配置说明

### 配置文件位置
`~/.psitedl/config.json`

### 配置示例
```json
{
  "output_dir": "~/Downloads",
  "browser": "chrome",
  "profile": "Default",
  "concurrency": 3,
  "max_retries": 3,
  "timeout": 30,
  "log_level": "INFO",
  "log_file": "~/.psitedl/psitedl.log",
  "bandwidth_limit_mbps": 0
}
```

### 配置项说明
| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `output_dir` | string | ~/Downloads | 输出目录 |
| `browser` | string | chrome | 浏览器类型 (chrome/chromium/edge/brave/firefox/safari) |
| `profile` | string | Default | 浏览器 Profile 名称 |
| `concurrency` | int | 3 | 并发下载数 (1-10) |
| `max_retries` | int | 3 | 失败重试次数 |
| `timeout` | int | 30 | 网络超时 (秒) |
| `log_level` | string | INFO | 日志级别 (DEBUG/INFO/WARNING/ERROR) |
| `bandwidth_limit_mbps` | float | 0 | 带宽限制 Mbps (0=无限制) |

### 并发数建议

| 网络环境 | 推荐并发数 | 说明 |
|----------|------------|------|
| 家庭宽带 (<100Mbps) | 2-3 | 避免影响其他网络使用 |
| 千兆宽带 | 5-8 | 充分利用带宽 |
| 企业网络 | 8-10 | 高带宽高并发 |
| 后台下载 | 1-2 | 最低影响模式 |

### 带宽限制说明

`bandwidth_limit_mbps` 用于限制总下载速度，避免占用全部网络资源：

- **0**: 无限制 (默认，全速下载)
- **1-10**: 适合后台下载或共享网络
- **10-50**: 适合家庭网络，不影响视频通话
- **50+**: 适合千兆宽带，充分利用带宽

**示例**:
```json
{
  "concurrency": 5,
  "bandwidth_limit_mbps": 20
}
```

### 配置管理 API

```python
from webvidgrab.config import load_config, save_config, get_default_config, validate_config
from pathlib import Path

# 加载配置
config = load_config(Path("~/.psitedl/config.json").expanduser())

# 获取默认配置
default = get_default_config()

# 验证配置
validate_config(config)  # True 或抛出 ValueError

# 保存配置
save_config(config, Path("./config.json"))
```

详细配置文档请参阅 [docs/CONFIGURATION.md](docs/CONFIGURATION.md)

## 📝 日志系统

### 日志级别

- `DEBUG` - 详细调试信息 (开发时使用)
- `INFO` - 一般信息 (默认级别)
- `WARNING` - 警告信息
- `ERROR` - 错误信息
- `CRITICAL` - 严重错误

### 日志输出

PSiteDL 支持多种日志输出格式:

**控制台输出 (人类可读)**:
```
2026-03-15 13:30:00 | INFO     | webvidgrab | Download started
2026-03-15 13:30:05 | INFO     | webvidgrab | Download completed: 50.0 MB
```

**文件输出 (JSON 格式)**:
```json
{"timestamp": "2026-03-15T13:30:00Z", "level": "INFO", "logger": "webvidgrab", "message": "Download started"}
```

### 日志 API

```python
from webvidgrab.logging import create_logger, log_context, log_execution_time

# 创建日志器
logger = create_logger("myapp", level="INFO", log_file="app.log")

# 记录日志
logger.info("Operation started")
logger.error("Something went wrong", extra={"context": "download"})

# 使用上下文管理器
with log_context(logger, "download", url="https://example.com"):
    download_video()

# 使用装饰器记录执行时间
@log_execution_time(logger, "slow_operation")
def process_video():
    ...
```

详细日志文档请参阅 [docs/LOGGING.md](docs/LOGGING.md)

## 🛡️ 错误处理

PSiteDL 提供完善的错误处理机制:

- **自动重试**: 网络错误自动重试，可配置重试次数
- **优雅降级**: Cookie 导出失败时自动切换到无 Cookie 模式
- **错误分类**: 精细的网络错误分类 (超时、DNS 失败、连接重置)
- **错误日志**: 所有错误自动记录，便于诊断

```python
from webvidgrab.errors import retry_on_error, handle_network_error, safe_extract_videos

# 使用重试装饰器
@retry_on_error(max_retries=3, exceptions=(ConnectionError, TimeoutError))
def download_with_retry():
    ...

# 使用上下文管理器处理网络错误
with handle_network_error(timeout=30):
    response = requests.get(url)

# 安全提取视频 (失败时返回空列表)
videos = safe_extract_videos(html, base_url)
```

详细错误处理文档请参阅 [docs/API_REFERENCE.md](docs/API_REFERENCE.md)

## 📊 进度显示

PSiteDL 提供实时进度显示:

- **单文件进度**: 下载速度、剩余时间、百分比
- **多文件进度**: 批量下载整体进度跟踪
- **Rich 集成**: 美观的终端进度条
- **断点续传**: 进度持久化支持

```python
from webvidgrab.progress import DownloadProgress, MultiProgressTracker, render_progress_bar

# 单文件进度
progress = DownloadProgress(total=1000000)
progress.update(500000)
print(f"{progress.percentage:.1f}%")
print(f"Speed: {progress.get_speed():.2f} bytes/s")
print(f"ETA: {progress.get_eta():.1f} seconds")

# 多文件进度
tracker = MultiProgressTracker(total_files=3)
tracker.add_file("video1.mp4", 1000000)
tracker.update_file("video1.mp4", 500000)
print(f"Overall: {tracker.overall_percentage():.1f}%")

# 文本进度条
bar = render_progress_bar(50, 100, width=30)
print(bar)  # [███████████████░░░░░░░░░░] 50%
```

详细进度显示文档请参阅 [docs/API_REFERENCE.md](docs/API_REFERENCE.md)

## 📖 详细文档

### 用户文档
- [下载使用指南](docs/DOWNLOADING.md) - 基本下载、批量下载、并发下载
- [高级功能](docs/ADVANCED.md) - 并发架构/重试机制/带宽限制
- [配置详解](docs/CONFIGURATION.md) - 配置项完整说明
- [API 参考](docs/API_REFERENCE.md) - 完整 API 文档

### 开发者文档
- [开发指南](DEVELOPMENT.md) - 开发者文档
- [变更日志](CHANGELOG.md) - 版本历史
- [贡献指南](CONTRIBUTING.md) - 如何贡献

## 🧪 测试

```bash
# 运行所有测试
pytest

# 运行测试并生成覆盖率报告
pytest --cov=src/webvidgrab --cov-report=html

# 运行特定测试文件
pytest tests/test_config.py -v

# 运行特定测试函数
pytest tests/test_config.py::TestConfigLoader::test_load_config_from_file -v
```

## 📦 打包部署

```bash
# 构建分发包
python3 scripts/build_psitedl_bundle.py

# 在目标机器上部署
python3 deploy_psitedl_bundle.py --bundle-dir .
./run_psitedl.sh --url-file /path/to/urls.txt
./run_psitedl_gui.sh
```

## 🛠️ 开发

### 代码质量

```bash
# 代码格式化
black src/ tests/

# 代码检查
ruff check src/ tests/

# 类型检查
mypy src/
```

### 添加新功能

PSiteDL 采用 **测试驱动开发 (TDD)** 模式：

1. **先写测试**: 在 `tests/` 目录创建测试文件
2. **运行测试**: 确认测试失败 (红)
3. **实现功能**: 编写最小代码使测试通过
4. **重构优化**: 改进代码结构，保持测试通过

示例：
```bash
# 1. 创建测试文件
touch tests/test_new_feature.py

# 2. 编写测试用例
# (编辑测试文件)

# 3. 运行测试 (应该失败)
pytest tests/test_new_feature.py -v

# 4. 实现功能
# (编辑 src/webvidgrab/new_feature.py)

# 5. 再次运行测试 (应该通过)
pytest tests/test_new_feature.py -v
```

## ❓ 常见问题

### Q: 下载失败怎么办？
A: 检查以下几点：
1. 确认 URL 可访问
2. 尝试使用 `--browser chrome` 导出 Cookie
3. 查看日志文件 (`~/.psitedl/psitedl.log`)
4. 使用 `--log-level DEBUG` 获取详细日志

### Q: 如何加速下载？
A: 增加并发数：
```bash
psitedl --url-file urls.txt --concurrency 5
```

### Q: 支持哪些网站？
A: 理论上支持所有使用标准 HTML5 视频的网站。对于需要登录的网站，使用 `--browser` 参数导出 Cookie。

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE)

## 🙏 致谢

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - 强大的视频下载库
- [Playwright](https://playwright.dev/) - 浏览器自动化
- [Rich](https://github.com/Textualize/rich) - 终端美化

---

**版本**: 0.4.0  
**最后更新**: 2026-03-15
