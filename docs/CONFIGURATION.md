# 配置管理指南

本文档详细介绍 PSiteDL 的配置管理系统。

## 目录

- [概述](#概述)
- [配置文件位置](#配置文件位置)
- [配置项详解](#配置项详解)
- [配置管理 API](#配置管理-api)
- [配置示例](#配置示例)
- [常见问题](#常见问题)

## 概述

PSiteDL 使用 JSON 格式的配置文件来管理用户偏好和运行时参数。配置系统支持:

- ✅ 从 JSON 文件加载配置
- ✅ 配置项验证 (路径、范围、枚举值)
- ✅ 默认配置提供
- ✅ CLI 参数与配置文件合并 (CLI 优先级更高)
- ✅ 配置持久化保存

## 配置文件位置

### 默认位置

```
~/.psitedl/config.json
```

### 自定义位置

使用 `--config` 参数指定自定义配置文件路径:

```bash
psitedl "https://example.com/video" --config /path/to/custom/config.json
```

### 配置目录结构

```
~/.psitedl/
├── config.json      # 主配置文件
├── psitedl.log      # 日志文件 (默认位置)
└── cookies/         # Cookie 文件目录 (可选)
```

## 配置项详解

### 基础配置

| 配置项 | 类型 | 默认值 | 有效范围 | 说明 |
|--------|------|--------|----------|------|
| `output_dir` | string | `~/Downloads` | 有效文件系统路径 | 视频下载输出目录 |
| `browser` | string | `chrome` | `chrome`, `firefox`, `edge`, `safari` | 用于导出 Cookie 的浏览器类型 |
| `profile` | string | `Default` | 浏览器 Profile 名称 | 浏览器配置文件名称 |

### 下载配置

| 配置项 | 类型 | 默认值 | 有效范围 | 说明 |
|--------|------|--------|----------|------|
| `concurrency` | int | `3` | 1-10 | 并发下载数量 |
| `max_retries` | int | `3` | 0-10 | 失败后最大重试次数 |
| `timeout` | int | `30` | 1-300 | 网络请求超时时间 (秒) |
| `bandwidth_limit_mbps` | float | `0` | 0-1000 | 带宽限制 (Mbps), 0 表示无限制 |

### 日志配置

| 配置项 | 类型 | 默认值 | 有效范围 | 说明 |
|--------|------|--------|----------|------|
| `log_level` | string | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` | 日志级别 |
| `log_file` | string | `~/.psitedl/psitedl.log` | 有效文件路径 | 日志文件路径 |

### 配置项详细说明

#### output_dir

下载视频的保存目录。支持相对路径和绝对路径，支持 `~` 展开为用户主目录。

```json
{
  "output_dir": "~/Videos/Downloads"
}
```

**验证规则**:
- 路径不能包含特殊字符: `< > : " | ? *`
- 目录应可创建或已存在

#### browser

用于导出 Cookie 的浏览器类型。对于需要登录的视频网站，需要指定浏览器以获取认证 Cookie。

```json
{
  "browser": "chrome"
}
```

**有效值**:
- `chrome` - Google Chrome
- `firefox` - Mozilla Firefox
- `edge` - Microsoft Edge
- `safari` - Apple Safari

#### profile

浏览器配置文件名称。如果浏览器有多个用户配置，可以指定使用哪个配置。

```json
{
  "profile": "Default"
}
```

**常见 Profile 名称**:
- Chrome: `Default`, `Profile 1`, `Profile 2`
- Firefox: `default`, `default-release`
- Edge: `Default`, `Profile 1`

#### concurrency

并发下载数量。增加并发可以大幅提升批量下载效率，但会占用更多带宽和系统资源。

```json
{
  "concurrency": 5
}
```

**建议值**:
- 1-2: 保守模式，适合网络条件较差的情况
- 3-5: 平衡模式，推荐日常使用
- 6-10: 激进模式，适合高速网络和强大硬件

#### max_retries

下载失败后的最大重试次数。网络波动可能导致临时失败，自动重试可以提高成功率。

```json
{
  "max_retries": 3
}
```

**建议值**:
- `0`: 不重试，立即报错
- `1-3`: 推荐值，平衡效率和耐心
- `4-10`: 网络条件极差时使用

#### timeout

网络请求超时时间 (秒)。超时后请求会被取消并重试 (如果未达到最大重试次数)。

```json
{
  "timeout": 30
}
```

**建议值**:
- `10-30`: 网络条件好
- `30-60`: 一般网络条件
- `60-300`: 网络条件差或下载大文件

#### bandwidth_limit_mbps

带宽限制 (Mbps)。设置后可以避免下载占用全部带宽，影响其他网络使用。

```json
{
  "bandwidth_limit_mbps": 10
}
```

**示例值**:
- `0`: 无限制 (默认)
- `5`: 限制 5 Mbps (约 625 KB/s)
- `10`: 限制 10 Mbps (约 1.25 MB/s)
- `100`: 限制 100 Mbps (约 12.5 MB/s)

#### log_level

日志级别。控制日志输出的详细程度。

```json
{
  "log_level": "INFO"
}
```

**级别说明**:
- `DEBUG`: 详细调试信息，包含所有 API 调用和响应
- `INFO`: 一般信息，下载开始/结束、进度更新
- `WARNING`: 警告信息，非致命问题
- `ERROR`: 错误信息，下载失败等
- `CRITICAL`: 严重错误，程序无法继续

#### log_file

日志文件路径。日志会同时输出到控制台和文件。

```json
{
  "log_file": "~/.psitedl/psitedl.log"
}
```

## 配置管理 API

### 加载配置

```python
from webvidgrab.config import load_config
from pathlib import Path

# 从文件加载配置
config = load_config(Path("~/.psitedl/config.json").expanduser())
```

如果配置文件不存在，返回默认配置。

### 保存配置

```python
from webvidgrab.config import save_config
from pathlib import Path

config = {
    "output_dir": "~/Downloads",
    "browser": "chrome",
    "concurrency": 5,
}

save_config(config, Path("./config.json"))
```

### 获取默认配置

```python
from webvidgrab.config import get_default_config

default = get_default_config()
# 返回:
# {
#     "output_dir": "./downloads",
#     "browser": "chrome",
#     "profile": "Default",
#     "concurrency": 3,
#     "max_retries": 3,
#     "timeout": 30,
#     "log_level": "INFO",
#     "log_file": "./logs/psitedl.log",
# }
```

### 验证配置

```python
from webvidgrab.config import validate_config

config = {
    "output_dir": "~/Downloads",
    "concurrency": 5,
}

try:
    validate_config(config)  # 返回 True 或抛出 ValueError
except ValueError as e:
    print(f"配置验证失败：{e}")
```

### 合并配置

CLI 参数优先级高于配置文件。使用 `merge_configs()` 合并配置:

```python
from webvidgrab.config import merge_configs

base_config = {
    "output_dir": "~/Downloads",
    "concurrency": 3,
    "browser": "chrome",
}

cli_args = {
    "concurrency": 5,  # 覆盖 base_config
    "timeout": 60,     # 新增
}

merged = merge_configs(base_config, cli_args)
# 结果:
# {
#     "output_dir": "~/Downloads",
#     "concurrency": 5,  # CLI 优先级更高
#     "browser": "chrome",
#     "timeout": 60,
# }
```

## 配置示例

### 最小配置

```json
{
  "output_dir": "~/Downloads"
}
```

### 标准配置

```json
{
  "output_dir": "~/Downloads",
  "browser": "chrome",
  "profile": "Default",
  "concurrency": 3,
  "max_retries": 3,
  "timeout": 30,
  "log_level": "INFO",
  "log_file": "~/.psitedl/psitedl.log"
}
```

### 高性能配置

```json
{
  "output_dir": "/Volumes/SSD/Downloads",
  "browser": "chrome",
  "profile": "Default",
  "concurrency": 10,
  "max_retries": 5,
  "timeout": 60,
  "bandwidth_limit_mbps": 0,
  "log_level": "WARNING"
}
```

### 保守配置 (网络条件差)

```json
{
  "output_dir": "~/Downloads",
  "browser": "chrome",
  "profile": "Default",
  "concurrency": 1,
  "max_retries": 10,
  "timeout": 120,
  "bandwidth_limit_mbps": 2,
  "log_level": "DEBUG"
}
```

### 开发调试配置

```json
{
  "output_dir": "./test_downloads",
  "browser": "chrome",
  "profile": "Default",
  "concurrency": 1,
  "max_retries": 1,
  "timeout": 30,
  "log_level": "DEBUG",
  "log_file": "./logs/debug.log"
}
```

## 常见问题

### Q: 配置文件格式错误怎么办？

A: 使用 JSON 验证工具检查格式。常见错误:
- 缺少逗号
- 字符串未加引号
- 使用了注释 (JSON 不支持注释)

可以使用在线工具如 [JSONLint](https://jsonlint.com/) 验证。

### Q: 如何重置为默认配置？

A: 删除或重命名配置文件，PSiteDL 会自动使用默认配置:

```bash
mv ~/.psitedl/config.json ~/.psitedl/config.json.bak
```

### Q: 配置修改后何时生效？

A: 配置在每次运行 PSiteDL 时重新加载。修改配置文件后，下次运行即生效。

### Q: CLI 参数和配置文件冲突时以哪个为准？

A: CLI 参数优先级更高。例如:

```bash
# 配置文件中 concurrency=3, 但 CLI 指定 5
psitedl --url-file urls.txt --concurrency 5
# 实际使用 concurrency=5
```

### Q: 如何为不同场景使用不同配置？

A: 创建多个配置文件，使用时指定:

```bash
# 使用高性能配置
psitedl --config ~/.psitedl/config-performance.json ...

# 使用保守配置
psitedl --config ~/.psitedl/config-conservative.json ...
```

---

**最后更新**: 2026-03-15  
**版本**: 0.4.0
