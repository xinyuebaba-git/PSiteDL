# PSiteDL API 参考

本文档提供 PSiteDL 核心模块的完整 API 参考。

## 目录

- [配置管理 (config.py)](#配置管理-configpy)
- [日志系统 (logging.py)](#日志系统-loggingpy)
- [错误处理 (errors.py)](#错误处理-errorspy)
- [进度显示 (progress.py)](#进度显示-progresspy)
- [并发下载 (downloader.py)](#并发下载-downloaderpy)

---

## 配置管理 (config.py)

配置管理模块负责加载、验证、保存和合并配置。

### 常量

#### `DEFAULT_CONFIG`

默认配置字典。

```python
DEFAULT_CONFIG = {
    "output_dir": "./downloads",
    "browser": "chrome",
    "profile": "Default",
    "concurrency": 3,
    "max_retries": 3,
    "timeout": 30,
    "log_level": "INFO",
    "log_file": "./logs/psitedl.log",
}
```

#### `VALID_BROWSERS`

有效的浏览器类型集合。

```python
VALID_BROWSERS = {"chrome", "firefox", "edge", "safari"}
```

#### `VALID_LOG_LEVELS`

有效的日志级别集合。

```python
VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
```

### 异常类

#### `ConfigError`

配置相关异常。

**属性**:
- `message` (str): 错误描述
- `path` (Path | None): 相关文件路径

**示例**:
```python
from webvidgrab.config import ConfigError, load_config

try:
    config = load_config(invalid_file)
except ConfigError as e:
    print(f"配置加载失败：{e.message}")
    if e.path:
        print(f"文件路径：{e.path}")
```

### 公共 API

#### `get_default_config()`

获取默认配置字典。

**返回**: `dict[str, Any]` - 默认配置字典

**示例**:
```python
from webvidgrab.config import get_default_config

config = get_default_config()
print(config["concurrency"])  # 输出：3
```

---

#### `load_config(config_path: Path) -> dict[str, Any]`

从 JSON 文件加载配置。

**参数**:
- `config_path` (Path): 配置文件路径

**返回**: `dict[str, Any]` - 加载的配置字典

**异常**:
- `ConfigError`: JSON 解析失败或文件权限问题

**示例**:
```python
from webvidgrab.config import load_config
from pathlib import Path

config = load_config(Path("~/.psitedl/config.json").expanduser())
```

**行为**:
- 文件不存在：返回默认配置
- 文件格式错误：抛出 `ConfigError`
- 文件权限问题：抛出 `ConfigError`

---

#### `save_config(config: dict[str, Any], config_path: Path) -> None`

保存配置到 JSON 文件。

**参数**:
- `config` (dict[str, Any]): 配置字典
- `config_path` (Path): 保存路径

**异常**:
- `ConfigError`: 文件写入失败

**示例**:
```python
from webvidgrab.config import save_config
from pathlib import Path

config = {
    "output_dir": "~/Downloads",
    "concurrency": 5,
}

save_config(config, Path("./config.json"))
```

---

#### `validate_config(config: dict[str, Any]) -> bool`

验证配置项的有效性。

**参数**:
- `config` (dict[str, Any]): 待验证的配置字典

**返回**: `bool` - 验证通过返回 `True`

**异常**:
- `ValueError`: 验证失败，包含详细错误信息

**验证规则**:
- `output_dir`: 不能包含特殊字符 (`< > : " | ? *`)
- `browser`: 必须在 `VALID_BROWSERS` 中
- `concurrency`: 必须在 1-10 范围内
- `max_retries`: 必须在 0-10 范围内
- `timeout`: 必须在 1-300 范围内
- `log_level`: 必须在 `VALID_LOG_LEVELS` 中
- `bandwidth_limit_mbps`: 必须 >= 0

**示例**:
```python
from webvidgrab.config import validate_config

config = {"concurrency": 5, "browser": "chrome"}

try:
    validate_config(config)
    print("配置有效")
except ValueError as e:
    print(f"配置无效：{e}")
```

---

#### `merge_configs(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]`

合并两个配置字典，`override` 优先级更高。

**参数**:
- `base` (dict[str, Any]): 基础配置
- `override` (dict[str, Any]): 覆盖配置 (优先级更高)

**返回**: `dict[str, Any]` - 合并后的配置

**示例**:
```python
from webvidgrab.config import merge_configs

base = {"concurrency": 3, "timeout": 30}
override = {"concurrency": 5}  # 覆盖 base

merged = merge_configs(base, override)
print(merged["concurrency"])  # 输出：5 (override 优先级更高)
print(merged["timeout"])      # 输出：30 (来自 base)
```

---

## 日志系统 (logging.py)

日志系统模块提供结构化日志、轮转和审计功能。

### 类

#### `StructuredFormatter`

结构化日志格式化器。

**属性**:
- `json_format` (bool): 是否输出 JSON 格式

**示例**:
```python
from webvidgrab.logging import StructuredFormatter
import logging

formatter = StructuredFormatter(json_format=True)
handler = logging.StreamHandler()
handler.setFormatter(formatter)
```

---

#### `AuditLogger`

审计日志器类。

**方法**:

##### `log_action(action: str, **kwargs) -> None`

记录用户操作。

**参数**:
- `action` (str): 操作名称
- `**kwargs`: 额外上下文信息

**示例**:
```python
from webvidgrab.logging import AuditLogger

audit = AuditLogger("audit", log_file="audit.log")
audit.log_action("download_start", url="https://example.com", user="admin")
```

---

##### `log_config_change(key: str, old_value: Any, new_value: Any, user: str) -> None`

记录配置变更。

**参数**:
- `key` (str): 配置项名称
- `old_value` (Any): 原值
- `new_value` (Any): 新值
- `user` (str): 操作用户

**示例**:
```python
audit.log_config_change(
    key="concurrency",
    old_value=3,
    new_value=5,
    user="admin",
)
```

---

##### `log_error(error_type: str, message: str, context: dict | None = None) -> None`

记录错误事件。

**参数**:
- `error_type` (str): 错误类型
- `message` (str): 错误消息
- `context` (dict | None): 额外上下文

**示例**:
```python
audit.log_error(
    error_type="NetworkTimeout",
    message="Connection timed out after 30s",
    context={"url": "https://example.com"},
)
```

### 公共 API

#### `create_logger(...)`

创建日志记录器。

**参数**:
- `name` (str): 日志器名称
- `level` (str): 日志级别，默认 `"INFO"`
- `log_file` (str | None): 日志文件路径，默认 `None`
- `json_format` (bool): 是否 JSON 格式，默认 `False`

**返回**: `logging.Logger`

**示例**:
```python
from webvidgrab.logging import create_logger

logger = create_logger(
    "myapp",
    level="DEBUG",
    log_file="app.log",
    json_format=True,
)

logger.info("Application started")
```

---

#### `create_logger_with_rotation(...)`

创建带大小轮转的日志器。

**参数**:
- `name` (str): 日志器名称
- `log_file` (str): 日志文件路径
- `max_bytes` (int): 单个文件最大字节数，默认 `10485760` (10MB)
- `backup_count` (int): 备份文件数量，默认 `5`
- `level` (str): 日志级别，默认 `"INFO"`

**返回**: `logging.Logger`

**示例**:
```python
from webvidgrab.logging import create_logger_with_rotation

logger = create_logger_with_rotation(
    "myapp",
    log_file="logs/app.log",
    max_bytes=52428800,  # 50MB
    backup_count=10,
)
```

---

#### `create_date_logger(...)`

创建带日期轮转的日志器。

**参数**:
- `name` (str): 日志器名称
- `log_dir` (str): 日志目录
- `format` (str): 日期格式，默认 `"%Y-%m-%d"`
- `level` (str): 日志级别，默认 `"INFO"`

**返回**: `logging.Logger`

**示例**:
```python
from webvidgrab.logging import create_date_logger

logger = create_date_logger(
    "myapp",
    log_dir="logs/",
    format="%Y-%m-%d",
)
```

---

#### `create_audit_logger(name: str, log_file: str) -> AuditLogger`

创建审计日志器。

**参数**:
- `name` (str): 日志器名称
- `log_file` (str): 审计日志文件路径

**返回**: `AuditLogger`

**示例**:
```python
from webvidgrab.logging import create_audit_logger

audit = create_audit_logger("audit", log_file="audit.log")
audit.log_action("user_login", user="admin")
```

---

#### `log_context(logger: logging.Logger, operation: str, **context) -> ContextManager`

日志上下文管理器。

**参数**:
- `logger` (logging.Logger): 日志器
- `operation` (str): 操作名称
- `**context`: 额外上下文信息

**返回**: `ContextManager`

**示例**:
```python
from webvidgrab.logging import create_logger, log_context

logger = create_logger("myapp")

with log_context(logger, "download", url="https://example.com"):
    download_video()
# 自动记录开始和结束时间
```

---

#### `log_execution_time(logger: logging.Logger, operation: str) -> Callable`

执行时间装饰器。

**参数**:
- `logger` (logging.Logger): 日志器
- `operation` (str): 操作名称

**返回**: 装饰器函数

**示例**:
```python
from webvidgrab.logging import create_logger, log_execution_time

logger = create_logger("myapp")

@log_execution_time(logger, "process_video")
def process_video(url):
    time.sleep(2)
    return "processed"
```

---

#### `log_if_slow(logger: logging.Logger, operation: str, threshold: float = 1.0) -> Callable`

慢操作检测装饰器。

**参数**:
- `logger` (logging.Logger): 日志器
- `operation` (str): 操作名称
- `threshold` (float): 阈值 (秒)，默认 `1.0`

**返回**: 装饰器函数

**示例**:
```python
@log_if_slow(logger, "slow_operation", threshold=2.0)
def potentially_slow():
    time.sleep(2.5)  # 超过阈值，会记录日志
```

---

## 错误处理 (errors.py)

错误处理模块提供重试、错误分类和优雅降级功能。

### 异常类

#### `RetryExhaustedError`

重试用尽后抛出的异常。

**属性**:
- `message` (str): 错误消息
- `last_exception` (Exception | None): 最后一次异常

**示例**:
```python
from webvidgrab.errors import retry_on_error, RetryExhaustedError

@retry_on_error(max_retries=3, exceptions=(ValueError,))
def always_fails():
    raise ValueError("Always fails")

try:
    always_fails()
except RetryExhaustedError as e:
    print(f"重试用尽：{e.message}")
```

---

#### `NetworkTimeoutError`

网络超时异常。

**属性**:
- `timeout` (int): 超时时间 (秒)
- `url` (str | None): 相关 URL

**示例**:
```python
from webvidgrab.errors import NetworkTimeoutError

try:
    response = requests.get(url, timeout=30)
except TimeoutError:
    raise NetworkTimeoutError(timeout=30, url=url)
```

---

#### `DNSResolutionError`

DNS 解析失败异常。

**属性**:
- `hostname` (str | None): 无法解析的主机名

---

#### `ConnectionResetError_`

连接重置异常。

**注意**: 末尾的下划线避免与内置 `ConnectionResetError` 冲突。

### 装饰器

#### `retry_on_error(max_retries: int = 3, exceptions: tuple[type[Exception]] = (Exception,), delay: float = 1.0) -> Callable`

重试装饰器。

**参数**:
- `max_retries` (int): 最大重试次数，默认 `3`
- `exceptions` (tuple[type[Exception]]): 需要重试的异常类型，默认 `(Exception,)`
- `delay` (float): 重试间隔 (秒)，默认 `1.0`

**返回**: 装饰器函数

**示例**:
```python
from webvidgrab.errors import retry_on_error

@retry_on_error(max_retries=3, exceptions=(ConnectionError, TimeoutError))
def download_with_retry(url):
    return requests.get(url)

# 使用
try:
    response = download_with_retry("https://example.com")
except RetryExhaustedError:
    print("下载失败，重试用尽")
```

### 上下文管理器

#### `handle_network_error(timeout: int | None = None) -> ContextManager`

网络错误上下文管理器。

**参数**:
- `timeout` (int | None): 超时时间 (秒)

**返回**: `ContextManager`

**捕获并转换的异常**:
- `TimeoutError` → `NetworkTimeoutError`
- `OSError` (DNS 相关) → `DNSResolutionError`
- `ConnectionResetError` → `ConnectionResetError_`

**示例**:
```python
from webvidgrab.errors import handle_network_error, NetworkTimeoutError

try:
    with handle_network_error(timeout=30):
        response = requests.get(url)
except NetworkTimeoutError as e:
    print(f"请求超时：{e.timeout}秒")
except DNSResolutionError as e:
    print(f"DNS 解析失败：{e.hostname}")
```

### 公共 API

#### `safe_extract_videos(html: str, base_url: str) -> list[str]`

安全提取视频 URL。

**参数**:
- `html` (str): 页面 HTML 内容
- `base_url` (str): 基础 URL (用于解析相对路径)

**返回**: `list[str]` - 视频 URL 列表，失败时返回空列表

**特点**:
- 使用多个正则模式提取
- 失败时返回空列表而非抛出异常 (优雅降级)
- 自动解析相对 URL 为绝对 URL

**示例**:
```python
from webvidgrab.errors import safe_extract_videos

html = """
<html>
  <video src="https://example.com/video.mp4"></video>
  <source src="/stream.m3u8">
</html>
"""

videos = safe_extract_videos(html, "https://example.com/page")
# 返回：["https://example.com/video.mp4", "https://example.com/stream.m3u8"]
```

---

#### `safe_export_cookies(browser: str, profile: str, logger: logging.Logger | None = None) -> Path | None`

安全导出 Cookie。

**参数**:
- `browser` (str): 浏览器类型
- `profile` (str): 浏览器 Profile 名称
- `logger` (logging.Logger | None): 日志器

**返回**: `Path | None` - Cookie 文件路径，失败时返回 `None`

**特点**:
- 浏览器不可用时返回 `None` 而非抛出异常
- 自动记录导出过程日志
- 支持 Chrome/Firefox/Edge/Safari

**示例**:
```python
from webvidgrab.errors import safe_export_cookies

cookie_file = safe_export_cookies("chrome", "Default", logger)
if cookie_file:
    print(f"Cookie 导出成功：{cookie_file}")
else:
    print("Cookie 导出失败，使用无 Cookie 模式")
```

---

#### `ErrorHandler`

错误处理器类。

**方法**:

##### `__init__(logger: logging.Logger) -> None`

初始化错误处理器。

**参数**:
- `logger` (logging.Logger): 日志器

---

##### `log_error(error: Exception, context: dict | None = None) -> None`

记录错误日志。

**参数**:
- `error` (Exception): 异常对象
- `context` (dict | None): 额外上下文

**示例**:
```python
from webvidgrab.errors import ErrorHandler

handler = ErrorHandler(logger)
handler.log_error(ValueError("Invalid input"), {"user": "admin"})
```

---

##### `get_error_stats() -> dict[str, Any]`

获取错误统计。

**返回**: `dict[str, Any]` - 错误统计信息

**示例**:
```python
stats = handler.get_error_stats()
print(f"总错误数：{stats['total_errors']}")
print(f"错误类型分布：{stats['error_types']}")
```

---

## 进度显示 (progress.py)

进度显示模块提供单文件和批量文件的进度跟踪。

### 类

#### `DownloadProgress`

单文件下载进度跟踪。

**属性**:
- `total` (int): 总字节数
- `current` (int): 已下载字节数
- `start_time` (float): 开始时间戳
- `percentage` (float): 完成百分比 (0-100)

**方法**:

##### `__init__(total: int) -> None`

初始化进度跟踪。

**参数**:
- `total` (int): 文件总大小 (字节)

---

##### `update(bytes_downloaded: int) -> None`

更新进度。

**参数**:
- `bytes_downloaded` (int): 本次下载的字节数 (累加)

**示例**:
```python
from webvidgrab.progress import DownloadProgress

progress = DownloadProgress(total=1000000)
progress.update(500000)
print(f"{progress.percentage:.1f}%")  # 输出：50.0%
```

---

##### `is_complete() -> bool`

检查是否完成。

**返回**: `bool` - 完成返回 `True`

---

##### `get_speed() -> float`

获取下载速度。

**返回**: `float` - 字节/秒

**示例**:
```python
speed = progress.get_speed()
print(f"下载速度：{speed:.2f} bytes/s")
```

---

##### `get_eta() -> float`

获取预计剩余时间。

**返回**: `float` - 剩余秒数

**示例**:
```python
eta = progress.get_eta()
print(f"预计剩余：{eta:.1f}秒")
```

---

#### `MultiProgressTracker`

多文件进度跟踪。

**属性**:
- `total_files` (int): 总文件数

**方法**:

##### `__init__(total_files: int) -> None`

初始化多文件跟踪。

**参数**:
- `total_files` (int): 总文件数

---

##### `add_file(filename: str, size: int) -> None`

添加文件到跟踪。

**参数**:
- `filename` (str): 文件名
- `size` (int): 文件大小 (字节)

**示例**:
```python
from webvidgrab.progress import MultiProgressTracker

tracker = MultiProgressTracker(total_files=3)
tracker.add_file("video1.mp4", 1000000)
tracker.add_file("video2.mp4", 2000000)
tracker.add_file("video3.mp4", 1500000)
```

---

##### `update_file(filename: str, bytes_downloaded: int) -> None`

更新文件进度。

**参数**:
- `filename` (str): 文件名
- `bytes_downloaded` (int): 已下载字节数

**示例**:
```python
tracker.update_file("video1.mp4", 500000)
```

---

##### `overall_percentage() -> float`

获取整体进度百分比。

**返回**: `float` - 整体百分比 (0-100)

**示例**:
```python
print(f"整体进度：{tracker.overall_percentage():.1f}%")
```

---

##### `get_summary() -> dict[str, Any]`

获取进度摘要。

**返回**: `dict[str, Any]` - 包含完成数、总数等信息

**示例**:
```python
summary = tracker.get_summary()
print(f"已完成：{summary['completed']}/{summary['total']}")
```

---

#### `RichProgressDisplay`

Rich 库进度显示。

**方法**:

##### `__init__(output: TextIO | None = None) -> None`

初始化 Rich 显示。

**参数**:
- `output` (TextIO | None): 输出流，默认 `sys.stdout`

---

##### `start_task(task_name: str, total: int) -> None`

开始任务。

**参数**:
- `task_name` (str): 任务名称
- `total` (int): 总工作量

---

##### `update_task(task_name: str, completed: int) -> None`

更新任务进度。

**参数**:
- `task_name` (str): 任务名称
- `completed` (int): 已完成量

---

##### `stop() -> None`

停止显示。

### 公共 API

#### `render_progress_bar(current: int, total: int, width: int = 30) -> str`

渲染文本进度条。

**参数**:
- `current` (int): 当前值
- `total` (int): 总值
- `width` (int): 进度条宽度，默认 `30`

**返回**: `str` - 进度条字符串

**示例**:
```python
from webvidgrab.progress import render_progress_bar

bar = render_progress_bar(50, 100, width=30)
print(bar)
# 输出：[███████████████░░░░░░░░░░░] 50%
```

---

#### `render_progress_info(filename: str, current: int, total: int, speed: float, eta: float) -> str`

渲染进度信息。

**参数**:
- `filename` (str): 文件名
- `current` (int): 已下载字节数
- `total` (int): 总字节数
- `speed` (float): 下载速度 (bytes/s)
- `eta` (float): 预计剩余时间 (秒)

**返回**: `str` - 格式化的进度信息

**示例**:
```python
from webvidgrab.progress import render_progress_info

info = render_progress_info(
    filename="video.mp4",
    current=500000,
    total=1000000,
    speed=100000,
    eta=5,
)
print(info)
# 输出：video.mp4: 50.0% | 100.00 KB/s | 剩余 5 秒
```

---

#### `save_progress_state(progress: DownloadProgress, state_file: Path) -> None`

保存进度状态 (用于断点续传)。

**参数**:
- `progress` (DownloadProgress): 进度对象
- `state_file` (Path): 状态文件路径

**示例**:
```python
from webvidgrab.progress import save_progress_state

save_progress_state(progress, Path(".download_state"))
```

---

#### `load_progress_state(state_file: Path) -> DownloadProgress | None`

加载进度状态。

**参数**:
- `state_file` (Path): 状态文件路径

**返回**: `DownloadProgress | None` - 进度对象，文件不存在返回 `None`

**示例**:
```python
from webvidgrab.progress import load_progress_state

progress = load_progress_state(Path(".download_state"))
if progress:
    print(f"恢复进度：{progress.percentage:.1f}%")
```

---

## 完整示例

### 配置 + 日志 + 错误处理 + 进度 综合示例

```python
from pathlib import Path
from webvidgrab.config import load_config, validate_config
from webvidgrab.logging import create_logger, log_context
from webvidgrab.errors import retry_on_error, handle_network_error, safe_extract_videos
from webvidgrab.progress import DownloadProgress, render_progress_info

# 1. 加载配置
config = load_config(Path("~/.psitedl/config.json").expanduser())
validate_config(config)

# 2. 创建日志器
logger = create_logger(
    "myapp",
    level=config["log_level"],
    log_file=config["log_file"],
)

# 3. 定义带重试的下载函数
@retry_on_error(max_retries=config["max_retries"], exceptions=(ConnectionError,))
def download_video(url, output_path):
    with handle_network_error(timeout=config["timeout"]):
        # 模拟下载
        import requests
        response = requests.get(url, timeout=config["timeout"])
        response.raise_for_status()
        
        # 写入文件
        with open(output_path, "wb") as f:
            f.write(response.content)

# 4. 执行下载并显示进度
url = "https://example.com/video.mp4"
output_path = Path(config["output_dir"]) / "video.mp4"

with log_context(logger, "download", url=url):
    try:
        # 获取文件大小
        import requests
        head = requests.head(url)
        total_size = int(head.headers.get("content-length", 0))
        
        # 创建进度跟踪
        progress = DownloadProgress(total=total_size)
        
        # 下载 (实际应用中需要在下载过程中更新进度)
        download_video(url, output_path)
        progress.update(total_size)
        
        # 显示最终进度
        info = render_progress_info(
            filename=output_path.name,
            current=progress.current,
            total=progress.total,
            speed=progress.get_speed(),
            eta=0,
        )
        logger.info(info)
        
    except Exception as e:
        logger.error(f"下载失败：{e}")
```

---

## 并发下载 (downloader.py)

并发下载模块提供高性 能的批量下载功能。

### 类

#### `ConcurrentDownloader`

并发下载器核心类。

**属性**:
- `max_concurrent` (int): 最大并发数
- `max_retries` (int): 最大重试次数
- `bandwidth_limit` (float): 带宽限制 (Mbps)

**方法**:

##### `__init__(max_concurrent: int = 3, max_retries: int = 3, bandwidth_limit: float = 0) -> None`

初始化下载器。

**参数**:
- `max_concurrent` (int): 最大并发数，默认 `3`
- `max_retries` (int): 最大重试次数，默认 `3`
- `bandwidth_limit` (float): 带宽限制 (Mbps)，`0` 表示无限制

**示例**:
```python
from webvidgrab.downloader import ConcurrentDownloader

downloader = ConcurrentDownloader(
    max_concurrent=5,
    max_retries=3,
    bandwidth_limit=20,  # 限制为 20 Mbps
)
```

---

##### `active_count() -> int`

获取当前活跃下载数。

**返回**: `int` - 正在进行的下载任务数

**示例**:
```python
active = downloader.active_count()
print(f"当前活跃下载数：{active}")
```

---

##### `download_sync(url: str, output_dir: Path) -> dict[str, Any]`

同步单文件下载。

**参数**:
- `url` (str): 下载 URL
- `output_dir` (Path): 输出目录

**返回**: `dict[str, Any]` - 下载结果，包含 `success`, `url`, `output_path` 等

**示例**:
```python
result = downloader.download_sync(
    url="https://example.com/video.mp4",
    output_dir=Path("./downloads"),
)

if result["success"]:
    print(f"下载成功：{result['output_path']}")
```

---

##### `async download_batch(urls: list[str], output_dir: Path, download_fn: Callable | None = None) -> list[dict[str, Any]]`

异步批量下载。

**参数**:
- `urls` (list[str]): URL 列表
- `output_dir` (Path): 输出目录
- `download_fn` (Callable | None): 自定义下载函数，默认使用内置下载

**返回**: `list[dict[str, Any]]` - 下载结果列表

**示例**:
```python
import asyncio
from pathlib import Path

async def main():
    urls = [
        "https://example.com/video1.mp4",
        "https://example.com/video2.mp4",
        "https://example.com/video3.mp4",
    ]
    
    results = await downloader.download_batch(
        urls=urls,
        output_dir=Path("./downloads"),
    )
    
    for result in results:
        status = "成功" if result["success"] else "失败"
        print(f"{result['url']}: {status}")

asyncio.run(main())
```

---

#### `DownloadQueue`

下载任务队列 (FIFO)。

**方法**:

##### `__init__() -> None`

创建下载队列。

---

##### `add(url: str) -> None`

添加任务到队列。

**参数**:
- `url` (str): 下载 URL

**示例**:
```python
from webvidgrab.downloader import DownloadQueue

queue = DownloadQueue()
queue.add("https://example.com/video1.mp4")
queue.add("https://example.com/video2.mp4")
```

---

##### `get() -> str`

从队列获取任务。

**返回**: `str` - URL

**示例**:
```python
url = queue.get()
```

---

##### `size() -> int`

获取队列大小。

**返回**: `int` - 队列中的任务数

---

##### `is_empty() -> bool`

检查队列是否为空。

**返回**: `bool` - 空队列返回 `True`

---

#### `RetryQueue`

失败任务重试队列。

**属性**:
- `max_retries` (int): 最大重试次数

**方法**:

##### `__init__(max_retries: int = 3) -> None`

初始化重试队列。

**参数**:
- `max_retries` (int): 最大重试次数

---

##### `add(url: str, error: str) -> None`

添加失败任务到重试队列。

**参数**:
- `url` (str): 下载 URL
- `error` (str): 错误信息

**示例**:
```python
from webvidgrab.downloader import RetryQueue

retry_queue = RetryQueue(max_retries=3)
retry_queue.add("https://example.com/failed.mp4", error="timeout")
```

---

##### `get_retryable() -> list[str]`

获取可重试的任务列表。

**返回**: `list[str]` - 可重试的 URL 列表

**说明**: 仅返回距离上次失败足够长时间的任务 (指数退避)。

---

##### `pending_count() -> int`

获取待重试任务数。

**返回**: `int` - 待重试任务数

---

#### `PriorityDownloadQueue`

优先级下载队列。

**方法**:

##### `__init__() -> None`

创建优先级队列。

---

##### `add(url: str, priority: int = 5) -> None`

添加任务到队列。

**参数**:
- `url` (str): 下载 URL
- `priority` (int): 优先级 (1-10)，默认 `5`

**示例**:
```python
from webvidgrab.downloader import PriorityDownloadQueue

queue = PriorityDownloadQueue()
queue.add("https://example.com/urgent.mp4", priority=10)
queue.add("https://example.com/normal.mp4", priority=5)
queue.add("https://example.com/low.mp4", priority=1)

# 高优先级先出队
first = queue.get()  # "urgent.mp4"
```

---

##### `get() -> str`

获取最高优先级任务。

**返回**: `str` - URL

---

#### `BandwidthLimiter`

带宽限制器 (令牌桶算法)。

**属性**:
- `limit_mbps` (float): 带宽限制 (Mbps)

**方法**:

##### `__init__(limit_mbps: float = 0) -> None`

初始化带宽限制器。

**参数**:
- `limit_mbps` (float): 带宽限制 (Mbps)，`0` 表示无限制

---

##### `acquire(bytes_count: int) -> None`

获取令牌 (消耗带宽配额)。

**参数**:
- `bytes_count` (int): 需要下载的字节数

**说明**: 如果配额不足，会阻塞直到有足够令牌。

**示例**:
```python
from webvidgrab.downloader import BandwidthLimiter

limiter = BandwidthLimiter(limit_mbps=10)
limiter.acquire(1024 * 1024)  # 下载 1MB 前调用
```

---

##### `release(bytes_count: int) -> None`

释放令牌 (归还带宽配额)。

**参数**:
- `bytes_count` (int): 释放的字节数

---

### 完整示例

**批量并发下载**:

```python
import asyncio
from pathlib import Path
from webvidgrab.downloader import ConcurrentDownloader
from webvidgrab.logging import create_logger

async def batch_download():
    # 创建日志器
    logger = create_logger("downloader", level="INFO")
    
    # 初始化下载器
    downloader = ConcurrentDownloader(
        max_concurrent=5,
        max_retries=3,
        bandwidth_limit=20,
    )
    
    # URL 列表
    urls = [
        "https://example.com/video1.mp4",
        "https://example.com/video2.mp4",
        "https://example.com/video3.mp4",
    ]
    
    # 执行批量下载
    output_dir = Path("./downloads")
    results = await downloader.download_batch(urls, output_dir)
    
    # 处理结果
    success_count = sum(1 for r in results if r["success"])
    logger.info(f"下载完成：{success_count}/{len(urls)} 成功")

asyncio.run(batch_download())
```

**使用优先级队列**:

```python
from webvidgrab.downloader import PriorityDownloadQueue, ConcurrentDownloader

# 创建优先级队列
queue = PriorityDownloadQueue()

# 添加不同优先级的任务
queue.add("https://example.com/urgent.mp4", priority=10)
queue.add("https://example.com/normal.mp4", priority=5)

# 按优先级下载
downloader = ConcurrentDownloader(max_concurrent=3)

while not queue.is_empty():
    url = queue.get()
    result = downloader.download_sync(url, Path("./downloads"))
```

---

**最后更新**: 2026-03-15  
**版本**: 0.4.0
