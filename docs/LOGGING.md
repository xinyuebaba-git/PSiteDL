# 日志系统使用指南

本文档详细介绍 PSiteDL 的日志系统。

## 目录

- [概述](#概述)
- [日志级别](#日志级别)
- [日志输出格式](#日志输出格式)
- [日志器创建](#日志器创建)
- [日志轮转](#日志轮转)
- [审计日志](#审计日志)
- [高级功能](#高级功能)
- [最佳实践](#最佳实践)

## 概述

PSiteDL 使用 Python 标准 `logging` 模块，并进行了增强:

- ✅ 多种日志级别 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- ✅ 结构化日志输出 (JSON 格式)
- ✅ 日志文件轮转 (按大小、按日期)
- ✅ 审计日志 (关键操作追踪)
- ✅ 日志上下文管理器
- ✅ 性能监控装饰器

## 日志级别

PSiteDL 支持标准 Python 日志级别:

| 级别 | 数值 | 说明 | 使用场景 |
|------|------|------|----------|
| `DEBUG` | 10 | 详细调试信息 | 开发调试，追踪程序执行流程 |
| `INFO` | 20 | 一般信息 | 正常运行状态，下载开始/结束 |
| `WARNING` | 30 | 警告信息 | 非致命问题，自动恢复的情况 |
| `ERROR` | 40 | 错误信息 | 下载失败、网络错误等 |
| `CRITICAL` | 50 | 严重错误 | 程序无法继续运行的错误 |

### 日志级别使用示例

```python
from webvidgrab.logging import create_logger

logger = create_logger("myapp", level="DEBUG")

logger.debug("正在解析页面 HTML...")           # 详细调试信息
logger.info("开始下载视频...")                  # 一般信息
logger.warning("Cookie 导出失败，使用无 Cookie 模式")  # 警告
logger.error("下载失败：连接超时")              # 错误
logger.critical("磁盘空间不足，无法继续")        # 严重错误
```

### 日志级别选择建议

**开发阶段**: 使用 `DEBUG` 级别，获取最详细的信息

```json
{
  "log_level": "DEBUG"
}
```

**生产环境**: 使用 `INFO` 或 `WARNING` 级别

```json
{
  "log_level": "INFO"
}
```

**静默模式**: 使用 `ERROR` 级别，仅记录错误

```json
{
  "log_level": "ERROR"
}
```

## 日志输出格式

### 人类可读格式 (控制台默认)

```
2026-03-15 13:30:00 | INFO     | webvidgrab | Download started
2026-03-15 13:30:05 | INFO     | webvidgrab | Download completed: 50.0 MB
2026-03-15 13:30:06 | WARNING  | webvidgrab | Retry 1/3 after connection error
```

格式说明:
```
<时间戳> | <级别> | <日志器名称> | <消息>
```

### JSON 格式 (文件输出/日志分析)

```json
{"timestamp": "2026-03-15T13:30:00+00:00", "level": "INFO", "logger": "webvidgrab", "message": "Download started"}
{"timestamp": "2026-03-15T13:30:05+00:00", "level": "INFO", "logger": "webvidgrab", "message": "Download completed: 50.0 MB", "context": {"size": 52428800}}
{"timestamp": "2026-03-15T13:30:06+00:00", "level": "WARNING", "logger": "webvidgrab", "message": "Retry 1/3 after connection error", "context": {"retry_count": 1}}
```

JSON 格式优势:
- 便于机器解析和日志分析系统处理
- 支持结构化上下文信息
- 可以轻松导入 ELK、Splunk 等日志平台

### 启用 JSON 格式

```python
from webvidgrab.logging import create_logger

# 启用 JSON 格式
logger = create_logger("myapp", json_format=True, log_file="app.log")
```

## 日志器创建

### 基础日志器

```python
from webvidgrab.logging import create_logger

# 仅控制台输出
logger = create_logger("myapp", level="INFO")

# 控制台 + 文件输出
logger = create_logger(
    "myapp",
    level="INFO",
    log_file="app.log",
    json_format=False,  # 人类可读格式
)
```

### 按大小轮转的日志器

当日志文件达到指定大小时自动轮转:

```python
from webvidgrab.logging import create_logger_with_rotation

logger = create_logger_with_rotation(
    "myapp",
    log_file="logs/app.log",
    max_bytes=10485760,  # 10 MB
    backup_count=5,      # 保留 5 个备份文件
    level="INFO",
)
```

轮转后的文件命名:
```
app.log          # 当前日志
app.log.1        # 最近的备份
app.log.2
app.log.3
app.log.4
app.log.5        # 最旧的备份
```

### 按日期轮转的日志器

按日期自动创建新的日志文件:

```python
from webvidgrab.logging import create_date_logger

logger = create_date_logger(
    "myapp",
    log_dir="logs/",
    format="%Y-%m-%d",  # 文件名格式：app.2026-03-15.log
    level="INFO",
)
```

生成的文件:
```
logs/
├── app.2026-03-14.log
├── app.2026-03-15.log  # 今天的日志
└── app.2026-03-16.log  # 明天的日志 (自动创建)
```

## 审计日志

审计日志用于追踪关键操作，便于安全审计和问题排查。

### 创建审计日志器

```python
from webvidgrab.logging import create_audit_logger

audit = create_audit_logger("audit", log_file="audit.log")
```

### 记录审计事件

```python
from webvidgrab.logging import AuditLogger

audit = AuditLogger("audit", log_file="audit.log")

# 记录用户操作
audit.log_action(
    action="download_start",
    user="admin",
    target="https://example.com/video",
    status="success",
)

# 记录配置变更
audit.log_config_change(
    key="concurrency",
    old_value=3,
    new_value=5,
    user="admin",
)

# 记录错误事件
audit.log_error(
    error_type="NetworkTimeout",
    message="Connection timed out after 30s",
    context={"url": "https://example.com/video"},
)
```

### 审计日志格式

```json
{
  "timestamp": "2026-03-15T13:30:00+00:00",
  "event_type": "action",
  "action": "download_start",
  "user": "admin",
  "target": "https://example.com/video",
  "status": "success"
}
```

## 高级功能

### 日志上下文管理器

使用上下文管理器自动记录操作的开始和结束:

```python
from webvidgrab.logging import create_logger, log_context

logger = create_logger("myapp")

# 基本用法
with log_context(logger, "download", url="https://example.com"):
    download_video("https://example.com")
# 输出:
# [download] Starting... (url=https://example.com)
# [download] Completed in 5.2s

# 带异常处理
try:
    with log_context(logger, "download", url="https://example.com"):
        download_video("https://example.com")
except Exception as e:
    logger.error(f"Download failed: {e}")
# 输出:
# [download] Starting... (url=https://example.com)
# [download] Failed after 2.1s: Connection timeout
```

### 执行时间装饰器

自动记录函数的执行时间:

```python
from webvidgrab.logging import create_logger, log_execution_time

logger = create_logger("myapp")

@log_execution_time(logger, "process_video")
def process_video(url):
    # 处理视频的逻辑
    time.sleep(2)
    return "processed"

# 输出:
# [process_video] Completed in 2.0s
```

### 慢操作检测

仅当操作超过指定时间时才记录日志:

```python
from webvidgrab.logging import create_logger, log_if_slow

logger = create_logger("myapp")

@log_if_slow(logger, "slow_operation", threshold=1.0)
def potentially_slow_operation():
    time.sleep(1.5)  # 超过 1 秒阈值
    return "done"

# 输出 (仅当超过阈值时):
# [slow_operation] Took 1.5s (threshold: 1.0s)
```

### 带上下文的日志记录

```python
from webvidgrab.logging import create_logger

logger = create_logger("myapp")

# 添加额外上下文
logger.info(
    "Download started",
    extra={
        "context": {
            "url": "https://example.com/video",
            "filename": "video.mp4",
            "size": 1024000,
        }
    },
)
```

## 最佳实践

### 1. 选择合适的日志级别

```python
# ✅ 好的做法
logger.debug(f"Parsed {len(videos)} video candidates")  # 详细调试信息
logger.info(f"Downloading {url}")                        # 用户关心的信息
logger.warning(f"Retry {count}/{max_retries}")          # 需要注意的情况
logger.error(f"Download failed: {error}")               # 错误情况

# ❌ 避免
logger.info(f"Loop iteration {i}")  # 过于详细，应该用 DEBUG
logger.debug("Download failed")     # 错误应该用 ERROR 级别
```

### 2. 使用结构化上下文

```python
# ✅ 好的做法
logger.info(
    "Download completed",
    extra={"context": {"url": url, "size": size, "duration": duration}},
)

# ❌ 避免
logger.info(f"Download completed: {url} ({size} bytes, {duration}s)")
```

### 3. 合理配置日志轮转

```python
# 生产环境推荐配置
logger = create_logger_with_rotation(
    "myapp",
    log_file="logs/app.log",
    max_bytes=52428800,  # 50 MB
    backup_count=10,     # 保留 10 个文件
)
# 最大占用空间：50 MB × 10 = 500 MB
```

### 4. 敏感信息处理

```python
# ✅ 好的做法 - 脱敏处理
def log_user_action(user_email, action):
    masked_email = user_email.split('@')[0][:2] + "***@" + user_email.split('@')[1]
    logger.info(f"User action: {action}", extra={"user": masked_email})

# ❌ 避免 - 记录敏感信息
logger.info(f"User {user_email} performed {action}")  # 可能泄露隐私
```

### 5. 日志性能优化

```python
# ✅ 好的做法 - 避免不必要的字符串拼接
if logger.isEnabledFor(logging.DEBUG):
    logger.debug(f"Expensive operation: {expensive_computation()}")

# ❌ 避免 - 即使不输出也会执行
logger.debug(f"Expensive operation: {expensive_computation()}")
```

## 日志配置示例

### 开发环境配置

```python
from webvidgrab.logging import create_logger

logger = create_logger(
    "myapp",
    level="DEBUG",
    log_file="logs/debug.log",
    json_format=False,  # 人类可读，便于调试
)
```

### 生产环境配置

```python
from webvidgrab.logging import create_logger_with_rotation

logger = create_logger_with_rotation(
    "myapp",
    log_file="logs/app.log",
    max_bytes=52428800,  # 50 MB
    backup_count=10,
    level="INFO",
    json_format=True,  # JSON 格式，便于日志分析
)
```

### 审计日志配置

```python
from webvidgrab.logging import create_audit_logger

audit = create_audit_logger(
    "audit",
    log_file="logs/audit.log",
    level="INFO",
)

# 记录关键操作
audit.log_action("config_change", user="admin", details={"key": "concurrency"})
```

## 常见问题

### Q: 日志文件太大怎么办？

A: 使用日志轮转功能:

```python
logger = create_logger_with_rotation(
    "myapp",
    max_bytes=10485760,  # 10 MB
    backup_count=5,
)
```

### Q: 如何查看 JSON 格式的日志？

A: 使用 `jq` 工具格式化输出:

```bash
cat app.log | jq .
```

或在 Python 中:

```python
import json
with open("app.log") as f:
    for line in f:
        entry = json.loads(line)
        print(f"{entry['timestamp']} - {entry['message']}")
```

### Q: 如何临时提高日志级别？

A: 动态修改日志级别:

```python
logger.setLevel(logging.DEBUG)  # 临时提高级别
# ... 调试代码 ...
logger.setLevel(logging.INFO)   # 恢复原级别
```

### Q: 如何将日志输出到多个文件？

A: 创建多个处理器:

```python
import logging
from webvidgrab.logging import create_logger

logger = create_logger("myapp", level="DEBUG")

# 添加额外的文件处理器
file_handler = logging.FileHandler("errors.log")
file_handler.setLevel(logging.ERROR)
logger.addHandler(file_handler)
```

---

**最后更新**: 2026-03-15  
**版本**: 0.4.0
