# PSiteDL 高级功能

本文档详细介绍 PSiteDL 的高级功能，包括并发下载、重试机制、带宽限制等。

## 目录

- [并发下载架构](#并发下载架构)
- [重试机制](#重试机制)
- [带宽限制](#带宽限制)
- [优先级队列](#优先级队列)
- [性能优化](#性能优化)
- [监控与调试](#监控与调试)

---

## 并发下载架构

### 核心组件

PSiteDL 的并发下载系统由以下组件构成：

```
┌─────────────────────────────────────────────────────┐
│              ConcurrentDownloader                    │
├─────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │ DownloadQueue│  │  RetryQueue  │  │Progress   │ │
│  │   (待下载)    │  │   (待重试)    │  │ Tracker   │ │
│  └──────────────┘  └──────────────┘  └───────────┘ │
│                                                      │
│  ┌────────────────────────────────────────────────┐ │
│  │          Bandwidth Limiter (令牌桶)             │ │
│  └────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

### ConcurrentDownloader

主下载器类，管理整个下载流程。

**核心特性**:
- 可配置并发数 (1-10)
- 自动任务调度
- 实时活跃计数
- 批量下载支持

**API**:

```python
from webvidgrab.downloader import ConcurrentDownloader

# 初始化下载器
downloader = ConcurrentDownloader(
    max_concurrent=5,      # 最大并发数
    max_retries=3,         # 最大重试次数
    bandwidth_limit=10,    # 带宽限制 (Mbps)
)

# 同步单文件下载
result = downloader.download_sync(
    url="https://example.com/video.mp4",
    output_dir=Path("./downloads"),
)

# 异步批量下载
results = await downloader.download_batch(
    urls=["url1", "url2", "url3"],
    output_dir=Path("./downloads"),
)

# 获取当前活跃下载数
active = downloader.active_count()
```

### DownloadQueue

下载任务队列，管理待下载任务。

**特性**:
- FIFO (先进先出)
- 线程安全
- 支持批量添加

**API**:

```python
from webvidgrab.downloader import DownloadQueue

queue = DownloadQueue()

# 添加任务
queue.add("https://example.com/video1.mp4")
queue.add("https://example.com/video2.mp4")

# 获取任务
url = queue.get()

# 状态查询
size = queue.size()        # 队列大小
empty = queue.is_empty()   # 是否为空
```

### RetryQueue

失败任务重试队列。

**特性**:
- 指数退避 (Exponential Backoff)
- 最大重试次数限制
- 自动状态管理

**重试间隔计算**:
```
第 1 次重试：1 秒后
第 2 次重试：2 秒后
第 3 次重试：4 秒后
第 n 次重试：2^(n-1) 秒后
```

**API**:

```python
from webvidgrab.downloader import RetryQueue

retry_queue = RetryQueue(max_retries=3)

# 添加失败任务
retry_queue.add(
    url="https://example.com/failed.mp4",
    error="timeout",
)

# 获取可重试任务 (距离上次失败足够长时间)
retryable = retry_queue.get_retryable()

# 状态查询
pending = retry_queue.pending_count()
```

---

## 重试机制

### 自动重试策略

PSiteDL 对以下错误自动重试：

| 错误类型 | 是否重试 | 说明 |
|----------|----------|------|
| NetworkTimeoutError | ✅ | 网络超时 |
| DNSResolutionError | ✅ | DNS 解析失败 |
| ConnectionResetError_ | ✅ | 连接重置 |
| DownloadFailedError | ✅ | 下载失败 |
| ConfigError | ❌ | 配置错误 |
| PageParseError | ❌ | 页面解析错误 |

### 重试装饰器

使用 `@retry_on_error` 装饰器实现自动重试：

```python
from webvidgrab.errors import retry_on_error, RetryExhaustedError

@retry_on_error(
    max_retries=3,                    # 最多重试 3 次
    exceptions=(ConnectionError,),    # 重试这些异常
    delay=1.0,                        # 初始延迟 1 秒
    backoff=2.0,                      # 退避倍数
)
def download_with_retry(url):
    return requests.get(url)

try:
    response = download_with_retry("https://example.com")
except RetryExhaustedError as e:
    print(f"重试用尽：{e.message}")
    print(f"最后错误：{e.last_exception}")
```

### 重试配置

在配置文件中设置全局重试参数：

```json
{
  "max_retries": 5,
  "retry_delay": 2.0,
  "retry_backoff": 2.0
}
```

**参数说明**:
- `max_retries`: 最大重试次数 (0-10)
- `retry_delay`: 初始重试延迟 (秒)
- `retry_backoff`: 退避倍数 (1.5-3.0 推荐)

### 重试最佳实践

1. **合理设置重试次数**: 
   - 网络不稳定：5-10 次
   - 稳定网络：2-3 次

2. **使用指数退避**: 避免雪崩效应

3. **记录重试日志**: 便于诊断问题

```python
from webvidgrab.logging import create_logger

logger = create_logger("downloader", level="INFO")

@retry_on_error(max_retries=3)
def download(url):
    logger.info(f"下载：{url}")
    # ...
```

---

## 带宽限制

### 令牌桶算法

PSiteDL 使用令牌桶算法实现带宽限制：

```
┌─────────────────────────────────────┐
│         Bandwidth Limiter           │
│  ┌─────────────────────────────┐    │
│  │   Token Bucket (令牌桶)      │    │
│  │  ┌───┬───┬───┬───┬───┐      │    │
│  │  │ 🪙 │ 🪙 │ 🪙 │ 🪙 │ 🪙 │ ...  │    │
│  │  └───┴───┴───┴───┴───┘      │    │
│  │     ↑                       │    │
│  │  以固定速率填充               │    │
│  └─────────────────────────────┘    │
│         ↓ 下载需要消耗令牌            │
└─────────────────────────────────────┘
```

### BandwidthLimiter API

```python
from webvidgrab.downloader import BandwidthLimiter

# 初始化 (限制为 10 Mbps)
limiter = BandwidthLimiter(limit_mbps=10)

# 下载前获取令牌
bytes_to_download = 1024 * 1024  # 1 MB
limiter.acquire(bytes_to_download)

# 执行下载
download_data()

# 释放令牌 (可选，用于精确控制)
limiter.release(bytes_to_download)
```

### 带宽限制配置

**命令行**:
```bash
psitedl --url-file "urls.txt" \
  --bandwidth-limit 20  # 限制为 20 Mbps
```

**配置文件**:
```json
{
  "bandwidth_limit_mbps": 20
}
```

**代码中**:
```python
downloader = ConcurrentDownloader(
    bandwidth_limit=20,  # Mbps
)
```

### 带宽限制场景

| 场景 | 推荐限制 | 配置示例 |
|------|----------|----------|
| 后台下载 | 1-2 Mbps | `--bandwidth-limit 2` |
| 工作时段 | 5-10 Mbps | `--bandwidth-limit 10` |
| 家庭共享 | 10-20 Mbps | `--bandwidth-limit 20` |
| 独享千兆 | 50+ Mbps | `--bandwidth-limit 100` |
| 无限制 | 0 | `--bandwidth-limit 0` |

---

## 优先级队列

### PriorityDownloadQueue

支持任务优先级调度。

**优先级范围**: 1-10 (10 为最高)

**API**:

```python
from webvidgrab.downloader import PriorityDownloadQueue

queue = PriorityDownloadQueue()

# 添加不同优先级的任务
queue.add("https://example.com/urgent.mp4", priority=10)
queue.add("https://example.com/normal.mp4", priority=5)
queue.add("https://example.com/low.mp4", priority=1)

# 高优先级任务先出队
first = queue.get()  # "urgent.mp4"
```

### 使用场景

1. **重要任务优先**:
   ```bash
   # 在代码中使用
   queue.add(important_url, priority=10)
   queue.add(normal_url, priority=5)
   ```

2. **VIP 用户任务**:
   ```python
   if user.is_vip:
       queue.add(url, priority=10)
   else:
       queue.add(url, priority=5)
   ```

---

## 性能优化

### 并发数调优

**网络带宽与并发数关系**:

```
推荐并发数 = 带宽 (Mbps) / 单任务平均带宽 (Mbps)

示例：
- 100 Mbps 宽带，单任务 20 Mbps → 并发数 = 5
- 500 Mbps 宽带，单任务 50 Mbps → 并发数 = 10
```

### 内存优化

批量下载大量 URL 时：

```python
# 分批处理，避免内存溢出
urls = [...]  # 1000 个 URL
batch_size = 50

for i in range(0, len(urls), batch_size):
    batch = urls[i:i + batch_size]
    await downloader.download_batch(batch, output_dir)
```

### 磁盘 I/O 优化

1. **使用 SSD**: 大幅提升写入速度
2. **避免碎片化**: 定期整理磁盘
3. **足够空间**: 确保输出目录有足够空间

### 网络优化

1. **DNS 预解析**:
   ```bash
   # Linux/macOS
   dscacheutil -flushcache
   ```

2. **使用有线连接**: 比 WiFi 更稳定

3. **关闭代理**: 某些代理会降低速度
   ```bash
   export http_proxy=""
   export https_proxy=""
   ```

---

## 监控与调试

### 实时进度监控

**单文件进度**:
```python
from webvidgrab.progress import DownloadProgress

progress = DownloadProgress(total=1000000)
progress.update(500000)

print(f"进度：{progress.percentage:.1f}%")
print(f"速度：{progress.get_speed():.2f} bytes/s")
print(f"剩余：{progress.get_eta():.1f} 秒")
```

**批量进度**:
```python
from webvidgrab.progress import MultiProgressTracker

tracker = MultiProgressTracker(total_files=10)
tracker.add_file("video1.mp4", 1000000)
tracker.update_file("video1.mp4", 500000)

summary = tracker.get_summary()
print(f"已完成：{summary['completed']}/{summary['total']}")
print(f"整体进度：{tracker.overall_percentage():.1f}%")
```

### 日志级别

| 级别 | 说明 | 使用场景 |
|------|------|----------|
| DEBUG | 详细调试信息 | 开发/故障排查 |
| INFO | 一般信息 | 默认，日常使用 |
| WARNING | 警告信息 | 关注潜在问题 |
| ERROR | 错误信息 | 仅关注错误 |
| CRITICAL | 严重错误 | 生产环境监控 |

**设置日志级别**:
```bash
psitedl "url" --log-level DEBUG
```

### 性能分析

**启用性能分析**:
```python
import cProfile
from webvidgrab.downloader import ConcurrentDownloader

downloader = ConcurrentDownloader(max_concurrent=5)

cProfile.run('downloader.download_batch(urls, output_dir)', 'stats.prof')

# 查看分析结果
import pstats
p = pstats.Stats('stats.prof')
p.sort_stats('cumulative').print_stats(10)
```

### 常见问题诊断

**问题 1: 下载速度慢**

```bash
# 1. 检查当前并发数
psitedl --url-file "urls.txt" --concurrency 10

# 2. 检查带宽限制
psitedl --url-file "urls.txt" --bandwidth-limit 0

# 3. 查看详细日志
psitedl "url" --log-level DEBUG
```

**问题 2: 频繁重试**

```bash
# 1. 增加超时时间
psitedl "url" --timeout 60

# 2. 增加重试次数
psitedl "url" --max-retries 10

# 3. 检查网络连接
ping example.com
```

**问题 3: 内存占用高**

```python
# 减少批量大小
batch_size = 20  # 而非 100
urls_batch = all_urls[i:i + batch_size]
```

---

## 完整示例

### 高效批量下载脚本

```python
#!/usr/bin/env python3
"""高效批量下载示例"""

import asyncio
from pathlib import Path
from webvidgrab.downloader import ConcurrentDownloader
from webvidgrab.logging import create_logger
from webvidgrab.progress import MultiProgressTracker

async def main():
    # 1. 创建日志器
    logger = create_logger("batch_download", level="INFO")
    
    # 2. 初始化下载器
    downloader = ConcurrentDownloader(
        max_concurrent=5,
        max_retries=3,
        bandwidth_limit=20,  # Mbps
    )
    
    # 3. 读取 URL 列表
    urls_file = Path("urls.txt")
    urls = [line.strip() for line in urls_file.read_text().splitlines() 
            if line.strip() and not line.startswith("#")]
    
    logger.info(f"共 {len(urls)} 个 URL 待下载")
    
    # 4. 创建进度跟踪
    tracker = MultiProgressTracker(total_files=len(urls))
    
    # 5. 执行批量下载
    output_dir = Path("./downloads")
    results = await downloader.download_batch(urls, output_dir)
    
    # 6. 显示结果
    success_count = sum(1 for r in results if r.get("success", False))
    logger.info(f"下载完成：{success_count}/{len(urls)} 成功")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 相关文档

- [下载使用指南](DOWNLOADING.md) - 基本下载操作
- [API 参考](API_REFERENCE.md) - 完整 API 文档
- [配置详解](CONFIGURATION.md) - 配置项说明

---

**最后更新**: 2026-03-15  
**版本**: 0.4.0
