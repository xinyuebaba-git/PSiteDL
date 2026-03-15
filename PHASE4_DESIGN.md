# Phase 4: 并发下载模块架构设计

## 概述

Phase 4 实现 PSiteDL 的核心并发下载能力，支持多 URL 并行下载、失败重试、带宽限制和结果汇总。

**设计目标：**
- 高并发：支持可配置的最大并发数限制
- 高可靠：自动重试失败任务，支持指数退避
- 可控性：带宽限制、进度跟踪、优雅取消
- 可观测：完整的下载结果报告和统计

---

## 核心组件

### 1. ConcurrentDownloader - 并发下载器

**职责：** 控制并发下载的核心调度器

**关键属性：**
- `max_concurrent: int` - 最大并发数
- `semaphore: asyncio.Semaphore` - 并发控制信号量
- `active_tasks: set` - 当前活跃任务集合

**核心方法：**
```python
def __init__(self, max_concurrent: int = 5) -> None
def active_count(self) -> int  # 当前活跃下载数
async def download_batch(
    self,
    urls: list[str],
    output_dir: Path,
    download_fn: Callable | None = None
) -> list[DownloadResult]
def download_sync(
    self,
    url: str,
    output_dir: Path
) -> DownloadResult | None
```

**并发控制策略：**
- 使用 `asyncio.Semaphore` 限制同时进行的下载任务数
- 每个下载任务获取 semaphore，完成后释放
- 支持动态调整 max_concurrent（未来扩展）

---

### 2. DownloadQueue - 下载队列管理

**职责：** 管理待下载 URL 队列，支持优先级

**关键属性：**
- `queue: asyncio.Queue` - 标准队列
- `priority_queue: heapq` - 优先级队列（可选）

**核心方法：**
```python
def __init__(self) -> None
def size(self) -> int
def add(self, url: str, priority: int = 0) -> None
def get(self) -> str | None
def is_empty(self) -> bool
def clear(self) -> None
```

**优先级策略：**
- 默认优先级：0（普通）
- 高优先级：>0，先出队
- 低优先级：<0，后出队
- 使用 `heapq` 实现优先级排序

---

### 3. RetryQueue - 重试队列

**职责：** 管理失败任务的重试逻辑，支持指数退避

**关键属性：**
- `max_retries: int` - 最大重试次数（默认 3）
- `pending: dict[str, RetryTask]` - 待重试任务
- `failed: dict[str, RetryTask]` - 已失败任务（重试用尽）
- `base_delay: float` - 基础延迟秒数（默认 1.0）
- `exponential_backoff: bool` - 是否启用指数退避

**数据结构：**
```python
@dataclass
class RetryTask:
    url: str
    error: str
    attempts: int
    max_retries: int
    next_retry_at: float  # 下次重试时间戳
    output_dir: Path | None
```

**核心方法：**
```python
def __init__(self, max_retries: int = 3, base_delay: float = 1.0) -> None
def add(self, url: str, error: str, output_dir: Path | None = None) -> None
def get_retryable(self) -> list[RetryTask]  # 获取当前可重试的任务
def mark_completed(self, url: str, success: bool) -> None
def is_exhausted(self, url: str) -> bool  # 是否重试用尽
def pending_count(self) -> int
def failed_count(self) -> int
```

**重试策略：**
- 指数退避：`delay = base_delay * (2 ** (attempts - 1))`
- 示例：1s → 2s → 4s → 8s
- 可配置最大延迟上限（防止过长等待）

---

### 4. BandwidthLimiter - 带宽限制器

**职责：** 限制下载速度，避免占用全部带宽

**关键属性：**
- `max_speed_mbps: float` - 最大速度（Mbps）
- `max_speed_bytes: float` - 换算后的字节/秒
- `token_bucket: TokenBucket` - 令牌桶实现

**核心方法：**
```python
def __init__(self, max_speed_mbps: float = 0) -> None  # 0=无限制
def throttle(self, bytes_to_download: int) -> None
def acquire(self, bytes_count: int) -> float  # 获取等待时间
```

**实现策略：**
- **令牌桶算法：** 平滑限速，允许短暂突发
- 桶容量 = `max_speed_bytes`
- 补充速率 = `max_speed_bytes / second`
- 每次下载前计算需要等待的时间

**计算公式：**
```python
max_speed_bytes = (max_speed_mbps * 1024 * 1024) / 8  # Mbps → Bytes/s
wait_time = bytes_to_download / max_speed_bytes
```

---

### 5. ResultAggregator - 结果汇总器

**职责：** 收集下载结果，生成统计报告

**数据结构：**
```python
@dataclass
class DownloadResult:
    url: str
    success: bool
    output_file: Path | None = None
    error: str | None = None
    file_size: int = 0
    duration: float = 0.0
    retries: int = 0
```

**关键属性：**
- `results: list[DownloadResult]` - 所有结果
- `success_count: int` - 成功数
- `failed_count: int` - 失败数
- `total_bytes: int` - 总字节数
- `total_duration: float` - 总耗时

**核心方法：**
```python
def __init__(self) -> None
def add_result(self, result: DownloadResult) -> None
def get_summary(self) -> dict[str, Any]
def generate_report(self) -> str
def get_failed_urls(self) -> list[str]
def get_success_results(self) -> list[DownloadResult]
```

**报告格式：**
```
下载完成报告
============
总计：10 个 URL
成功：8 个 (80%)
失败：2 个 (20%)
总大小：1.5 GB
总耗时：3m 42s
平均速度：6.8 MB/s

失败任务:
- https://example.com/failed1.mp4 (timeout)
- https://example.com/failed2.mp4 (404)
```

---

## 数据流

```
用户请求
    │
    ▼
┌─────────────────┐
│  DownloadQueue  │ 待下载 URL 队列
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ConcurrentDownloader│ 并发控制 (Semaphore)
└────────┬────────┘
         │
         ├──────────────┐
         │              │
         ▼              ▼
    ┌─────────┐   ┌─────────────┐
    │ 成功下载 │   │ 失败 → RetryQueue │
    └────┬────┘   └──────┬──────┘
         │               │
         │               │ 可重试时
         │               ▼
         │         ┌─────────────┐
         │         │ 重新加入队列 │
         │         └─────────────┘
         │
         ▼
┌─────────────────┐
│ResultAggregator │ 结果汇总
└────────┬────────┘
         │
         ▼
    生成报告
```

---

## 并发模型

### asyncio 协程模型

```python
async def download_batch(self, urls, output_dir):
    semaphore = asyncio.Semaphore(self.max_concurrent)
    
    async def download_with_semaphore(url):
        async with semaphore:
            return await self._download_single(url, output_dir)
    
    tasks = [download_with_semaphore(url) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

### 任务取消支持

```python
async def download_batch(self, urls, output_dir, cancel_event=None):
    # 支持外部取消
    if cancel_event and cancel_event.is_set():
        return []
    
    # 每个任务检查取消信号
    if cancel_event and cancel_event.is_set():
        raise asyncio.CancelledError()
```

---

## 错误处理

### 错误分类

| 错误类型 | 是否重试 | 说明 |
|---------|---------|------|
| TimeoutError | ✅ | 网络超时 |
| ConnectionError | ✅ | 连接失败 |
| HTTP 429 | ✅ | 速率限制，带退避 |
| HTTP 404 | ❌ | 资源不存在 |
| HTTP 403 | ❌ | 禁止访问 |
| OSError | ⚠️ | 磁盘错误，视情况 |

### 重试决策树

```
下载失败
    │
    ▼
是否可重试错误？ ──No──→ 标记失败，加入 failed
    │
   Yes
    │
    ▼
重试次数 < max_retries？ ──No──→ 标记失败，加入 failed
    │
   Yes
    │
    ▼
计算下次重试时间（指数退避）
    │
    ▼
加入 RetryQueue 等待
```

---

## 配置参数

### ConcurrentDownloader 配置

```python
@dataclass
class DownloaderConfig:
    max_concurrent: int = 5          # 最大并发数
    max_speed_mbps: float = 0        # 带宽限制 (0=无限制)
    max_retries: int = 3             # 最大重试次数
    retry_base_delay: float = 1.0    # 重试基础延迟 (秒)
    timeout_per_url: float = 30.0    # 单 URL 超时 (秒)
    chunk_size: int = 8192           # 下载块大小 (字节)
    use_priority_queue: bool = False # 是否使用优先级队列
```

---

## 测试策略

参考 `tests/test_downloader.py` 中的 15 个测试用例：

1. **ConcurrentDownloader 测试 (4 个)**
   - 初始化
   - 单 URL 下载
   - 多 URL 并发
   - 并发数限制验证

2. **DownloadQueue 测试 (5 个)**
   - 创建队列
   - 添加任务
   - 获取任务
   - 空队列检测
   - 优先级队列

3. **RetryQueue 测试 (3 个)**
   - 添加重试任务
   - 获取可重试任务
   - 重试用尽检测

4. **DownloadResult 测试 (2 个)**
   - 结果汇总
   - 报告生成

5. **BandwidthManagement 测试 (2 个)**
   - 带宽限制器初始化
   - 节流验证

---

## 性能考虑

### 内存优化

- 使用流式下载，避免一次性加载大文件到内存
- 队列使用 `asyncio.Queue` 而非 list，支持背压
- 结果汇总使用生成器，避免存储所有中间状态

### 连接复用

- 使用 `aiohttp.ClientSession` 复用 TCP 连接
- 配置连接池大小与 max_concurrent 匹配
- 启用 keepalive 减少握手开销

### 磁盘 I/O

- 使用异步文件写入（aiofiles）
- 预分配文件大小（如果 Content-Length 已知）
- 批量写入减少系统调用

---

## 扩展点

### 未来功能

1. **断点续传：** 记录已下载字节，支持从中断处继续
2. **动态限速：** 根据网络状况自动调整带宽限制
3. **分布式下载：** 多机器协同下载（需要任务分发）
4. **进度回调：** 实时进度通知 UI/CLI
5. **下载策略：** 支持按站点、文件类型的差异化策略

### 插件接口

```python
class DownloadHook(Protocol):
    async def on_start(self, url: str) -> None: ...
    async def on_progress(self, url: str, bytes_downloaded: int) -> None: ...
    async def on_complete(self, result: DownloadResult) -> None: ...
    async def on_error(self, url: str, error: Exception) -> None: ...
```

---

## 依赖关系

```
webvidgrab.downloader
├── webvidgrab.errors (自定义异常)
├── webvidgrab.logging (日志记录)
├── webvidgrab.config (配置管理)
├── aiohttp (HTTP 客户端)
├── aiofiles (异步文件 I/O)
└── asyncio (并发原语)
```

---

## 实现优先级

### P0 - 核心功能
- [x] ConcurrentDownloader 基础实现
- [x] DownloadQueue 基础实现
- [x] RetryQueue 基础实现
- [x] ResultAggregator 基础实现

### P1 - 增强功能
- [ ] BandwidthLimiter 实现
- [ ] PriorityDownloadQueue 实现
- [ ] 完整的错误分类和重试逻辑
- [ ] 详细的下载报告

### P2 - 优化功能
- [ ] 断点续传支持
- [ ] 动态并发调整
- [ ] 下载钩子/插件系统
- [ ] 性能监控指标

---

## 总结

Phase 4 并发下载模块是 PSiteDL 的核心引擎，通过合理的组件划分和并发控制，实现高效、可靠的批量下载能力。设计遵循单一职责原则，各组件可独立测试和演进。

**关键设计决策：**
1. 使用 asyncio 而非 threading（Python 异步 I/O 更高效）
2. 信号量控制并发（简单可靠）
3. 指数退避重试（避免雪崩）
4. 令牌桶限速（平滑带宽使用）
5. 数据类记录结果（类型安全、易扩展）
