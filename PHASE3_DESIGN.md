# PSiteDL Phase 3 架构设计文档

## 概述

Phase 3 目标：实现错误处理 + 进度显示模块，通过 29 个测试用例

**设计原则：**
- 遵循 TDD（测试驱动开发）
- 类型注解完整
- 优雅降级（Graceful Degradation）
- 用户友好的进度反馈
- 可恢复的下载任务

---

## 1. 错误处理模块 (errors.py)

### 1.1 设计目标

1. **统一的异常层次结构** - 便于捕获和处理
2. **智能重试机制** - 自动处理临时性错误
3. **优雅降级** - 功能失败时不影响整体流程
4. **错误上下文** - 记录足够的调试信息
5. **恢复建议** - 为用户提供解决方案

### 1.2 异常层次结构

```
Exception
├── PSiteDLError (Base Exception)
│   ├── ConfigError
│   ├── NetworkError
│   │   ├── NetworkTimeoutError
│   │   ├── DNSResolutionError
│   │   └── ConnectionResetError_
│   ├── PageParseError
│   ├── DownloadError
│   │   ├── DownloadFailedError
│   │   └── PartialDownloadError
│   ├── CookieError
│   └── RetryExhaustedError
```

### 1.3 重试装饰器

**设计思路：**
- 使用装饰器模式包装可能失败的函数
- 支持自定义重试次数和异常类型
- 指数退避（Exponential Backoff）避免雪崩
- 重试用尽后抛出 `RetryExhaustedError`

**API：**
```python
def retry_on_error(
    max_retries: int = 3,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    delay: float = 1.0,
    backoff: float = 2.0,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    重试装饰器
    
    Args:
        max_retries: 最大重试次数
        exceptions: 需要重试的异常类型元组
        delay: 初始延迟（秒）
        backoff: 退避倍数
        
    Returns:
        装饰器函数
    """
```

### 1.4 网络错误处理上下文管理器

**设计思路：**
- 捕获底层网络异常并转换为业务异常
- 提供统一的错误处理接口
- 支持超时配置

**API：**
```python
@contextmanager
def handle_network_error(timeout: int = 30) -> Iterator[None]:
    """
    网络错误处理上下文管理器
    
    Args:
        timeout: 超时时间（秒）
        
    Yields:
        None
        
    Raises:
        NetworkTimeoutError: 超时
        DNSResolutionError: DNS 失败
        ConnectionResetError_: 连接重置
        
    Example:
        with handle_network_error(timeout=30):
            response = requests.get(url, timeout=timeout)
    """
```

### 1.5 安全提取函数

**设计思路：**
- 页面解析失败时返回空列表而非抛出异常
- 支持多个正则模式匹配
- 记录警告日志但不中断流程

**API：**
```python
def safe_extract_videos(
    html: str,
    base_url: str,
    patterns: list[re.Pattern] | None = None,
) -> list[str]:
    """
    安全提取视频 URL
    
    Args:
        html: HTML 内容
        base_url: 基础 URL（用于解析相对路径）
        patterns: 正则模式列表（可选，使用默认模式）
        
    Returns:
        视频 URL 列表（可能为空）
    """
```

### 1.6 Cookie 导出

**设计思路：**
- 调用 yt-dlp 的 Cookie 导出功能
- 浏览器不可用时返回 None
- 支持主流浏览器（Chrome, Firefox, Edge, Safari）

**API：**
```python
def safe_export_cookies(
    browser: str = "chrome",
    profile: str = "Default",
    logger: logging.Logger | None = None,
) -> Path | None:
    """
    安全导出 Cookie
    
    Args:
        browser: 浏览器类型
        profile: 配置文件名
        logger: 日志记录器
        
    Returns:
        Cookie 文件路径，失败时返回 None
    """
```

### 1.7 错误处理器

**设计思路：**
- 集中记录所有错误
- 支持错误统计和分析
- 提供恢复建议

**API：**
```python
class ErrorHandler:
    """错误处理器"""
    
    def __init__(
        self,
        log_file: str | None = None,
        max_history: int = 1000,
    ) -> None:
        """初始化错误处理器"""
        ...
    
    def log_error(
        self,
        error_code: str,
        error: Exception,
        context: dict[str, Any] | None = None,
    ) -> None:
        """记录错误"""
        ...
    
    def get_error_stats(self) -> dict[str, int]:
        """获取错误统计"""
        ...
    
    def clear_history(self) -> None:
        """清除错误历史"""
        ...


def get_recovery_suggestion(error_code: str) -> str:
    """
    获取恢复建议
    
    Args:
        error_code: 错误代码
        
    Returns:
        恢复建议文本
    """
```

### 1.8 类图

```
┌─────────────────────────────────────────────────────────┐
│                      errors.py                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │              Exception Hierarchy                 │  │
│  │                                                  │  │
│  │  PSiteDLError (base)                             │  │
│  │  ├── ConfigError                                 │  │
│  │  ├── NetworkError                                │  │
│  │  │   ├── NetworkTimeoutError                     │  │
│  │  │   ├── DNSResolutionError                      │  │
│  │  │   └── ConnectionResetError_                   │  │
│  │  ├── PageParseError                              │  │
│  │  ├── DownloadError                               │  │
│  │  │   ├── DownloadFailedError                     │  │
│  │  │   └── PartialDownloadError                    │  │
│  │  ├── CookieError                                 │  │
│  │  └── RetryExhaustedError                         │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
│  ┌─────────────────────────┐    ┌────────────────────┐ │
│  │  retry_on_error()       │    │ handle_network_    │ │
│  │  (decorator)            │    │ error()            │ │
│  │                         │    │ (context manager)  │ │
│  └─────────────────────────┘    └────────────────────┘ │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │              Safe Helpers                        │  │
│  │                                                  │  │
│  │  safe_extract_videos() -> list[str]              │  │
│  │  safe_export_cookies() -> Path | None            │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │              ErrorHandler                        │  │
│  │                                                  │  │
│  │  - errors: list[ErrorRecord]                     │  │
│  │  - log_file: Path | None                         │  │
│  │                                                  │  │
│  │  + log_error()                                   │  │
│  │  + get_error_stats() -> dict                     │  │
│  │  + clear_history()                               │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │              Recovery Helper                     │  │
│  │                                                  │  │
│  │  get_recovery_suggestion() -> str                │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 1.9 数据流

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  业务代码     │────▶│  @retry_on_  │────▶│  目标函数     │
│  (调用)      │     │  error        │     │              │
└──────────────┘     └──────────────┘     └──────────────┘
                            │
                   ┌────────┴────────┐
                   │                 │
                   ▼                 ▼
          ┌──────────────┐  ┌──────────────┐
          │  成功返回     │  │  捕获异常     │
          └──────────────┘  └──────────────┘
                                    │
                          ┌─────────┴─────────┐
                          │                   │
                          ▼                   ▼
                 ┌──────────────┐    ┌──────────────┐
                 │  重试计数     │    │  重试用尽     │
                 │  < max        │    │  抛出        │
                 └──────────────┘    │ RetryExhausted│
                          │          └──────────────┘
                          ▼
                 ┌──────────────┐
                 │  指数退避     │
                 │  再次尝试     │
                 └──────────────┘


┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  网络操作     │────▶│ handle_      │────▶│  转换异常     │
│              │     │ network_error│     │              │
└──────────────┘     └──────────────┘     └──────────────┘
                                                 │
                          ┌──────────────────────┤
                          │
                          ▼
                   ┌──────────────┐
                   │ PSiteDL 异常  │
                   │ (业务友好)    │
                   └──────────────┘
```

---

## 2. 进度显示模块 (progress.py)

### 2.1 设计目标

1. **实时反馈** - 用户随时了解下载状态
2. **多文件支持** - 批量下载时显示总体进度
3. **速度估算** - 计算下载速度和剩余时间
4. **持久化** - 支持断点续传
5. **多种显示方式** - 文本进度条、Rich 库、回调函数

### 2.2 下载进度类

**设计思路：**
- 跟踪单个文件的下载进度
- 自动计算百分比、速度、ETA
- 支持回调函数通知进度更新

**API：**
```python
class DownloadProgress:
    """单个文件下载进度"""
    
    def __init__(
        self,
        total: int,
        callback: Callable[[DownloadProgress], None] | None = None,
    ) -> None:
        """
        初始化进度
        
        Args:
            total: 总字节数
            callback: 进度更新回调函数
        """
        self.total = total
        self.current = 0
        self.start_time = time.time()
        self.callback = callback
    
    def update(self, bytes_downloaded: int) -> None:
        """更新进度"""
        ...
    
    @property
    def percentage(self) -> float:
        """下载百分比"""
        ...
    
    def is_complete(self) -> bool:
        """是否完成"""
        ...
    
    def get_speed(self) -> float:
        """获取下载速度 (bytes/s)"""
        ...
    
    def get_eta(self) -> float:
        """获取预计剩余时间 (秒)"""
        ...
```

### 2.3 进度条渲染

**设计思路：**
- 纯文本进度条（无依赖）
- 可选 Rich 库美化显示
- 支持自定义宽度

**API：**
```python
def render_progress_bar(
    current: int,
    total: int,
    width: int = 40,
    filled_char: str = "█",
    empty_char: str = "░",
) -> str:
    """
    渲染文本进度条
    
    Args:
        current: 当前字节数
        total: 总字节数
        width: 进度条宽度
        filled_char: 已填充字符
        empty_char: 未填充字符
        
    Returns:
        进度条字符串
    """


def render_progress_info(
    filename: str,
    current: int,
    total: int,
    speed: float,
    eta: float,
) -> str:
    """
    渲染完整进度信息
    
    Args:
        filename: 文件名
        current: 当前字节数
        total: 总字节数
        speed: 下载速度
        eta: 预计剩余时间
        
    Returns:
        格式化的进度信息字符串
    """
```

### 2.4 Rich 进度显示

**设计思路：**
- 使用 Rich 库提供美观的终端输出
- 支持多任务并行显示
- 自动刷新和清屏

**API：**
```python
class RichProgressDisplay:
    """Rich 库进度显示"""
    
    def __init__(self, output: TextIO | None = None) -> None:
        """初始化 Rich 进度显示"""
        ...
    
    def start_task(
        self,
        description: str,
        total: int,
    ) -> str:
        """
        开始任务
        
        Args:
            description: 任务描述
            total: 总字节数
            
        Returns:
            任务 ID
        """
        ...
    
    def update_task(
        self,
        task_id: str,
        completed: int,
    ) -> None:
        """更新任务进度"""
        ...
    
    def stop(self) -> None:
        """停止显示"""
        ...
```

### 2.5 多文件进度跟踪

**设计思路：**
- 跟踪批量下载的总进度
- 支持动态添加文件
- 计算整体完成百分比

**API：**
```python
class MultiProgressTracker:
    """多文件进度跟踪器"""
    
    def __init__(self, total_files: int) -> None:
        """初始化多文件跟踪器"""
        ...
    
    def add_file(
        self,
        filename: str,
        size: int,
    ) -> None:
        """添加文件到跟踪"""
        ...
    
    def update_file(
        self,
        filename: str,
        bytes_downloaded: int,
    ) -> None:
        """更新文件进度"""
        ...
    
    def overall_percentage(self) -> float:
        """获取整体进度百分比"""
        ...
    
    def get_summary(self) -> dict[str, Any]:
        """获取进度摘要"""
        ...
```

### 2.6 进度持久化

**设计思路：**
- 定期保存进度到 JSON 文件
- 支持从中断点恢复
- 自动清理过期的进度文件

**API：**
```python
def save_progress(
    progress: DownloadProgress,
    state_file: Path,
) -> None:
    """
    保存进度状态
    
    Args:
        progress: 进度对象
        state_file: 状态文件路径
    """


def load_progress(
    state_file: Path,
) -> DownloadProgress:
    """
    加载进度状态
    
    Args:
        state_file: 状态文件路径
        
    Returns:
        进度对象
    """
```

### 2.7 类图

```
┌─────────────────────────────────────────────────────────┐
│                     progress.py                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │              DownloadProgress                    │  │
│  │                                                  │  │
│  │  - total: int                                    │  │
│  │  - current: int                                  │  │
│  │  - start_time: float                             │  │
│  │  - callback: Callable | None                     │  │
│  │                                                  │  │
│  │  + update(bytes: int)                            │  │
│  │  + percentage: float                             │  │
│  │  + is_complete() -> bool                         │  │
│  │  + get_speed() -> float                          │  │
│  │  + get_eta() -> float                            │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
│  ┌─────────────────────────┐    ┌────────────────────┐ │
│  │  render_progress_bar()  │    │ render_progress_   │ │
│  │                         │    │ info()             │ │
│  └─────────────────────────┘    └────────────────────┘ │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │              RichProgressDisplay                 │  │
│  │                                                  │  │
│  │  - console: Console                              │  │
│  │  - tasks: dict[str, Task]                        │  │
│  │                                                  │  │
│  │  + start_task() -> str                           │  │
│  │  + update_task()                                 │  │
│  │  + stop()                                        │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │              MultiProgressTracker                │  │
│  │                                                  │  │
│  │  - total_files: int                              │  │
│  │  - files: dict[str, FileProgress]                │  │
│  │                                                  │  │
│  │  + add_file()                                    │  │
│  │  + update_file()                                 │  │
│  │  + overall_percentage() -> float                 │  │
│  │  + get_summary() -> dict                         │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
│  ┌─────────────────────────┐    ┌────────────────────┐ │
│  │  save_progress()        │    │ load_progress()    │ │
│  └─────────────────────────┘    └────────────────────┘ │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 2.8 数据流

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  下载器       │────▶│ Download     │────▶│  更新进度     │
│  (chunk)     │     │ Progress     │     │              │
└──────────────┘     └──────────────┘     └──────────────┘
                            │
                    ┌───────┴───────┐
                    │               │
                    ▼               ▼
           ┌──────────────┐ ┌──────────────┐
           │ 计算速度/ETA  │ │ 触发回调     │
           └──────────────┘ └──────────────┘
                                    │
                                    ▼
                           ┌──────────────┐
                           │ UI 更新       │
                           │ (进度条/日志) │
                           └──────────────┘


┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  多文件下载   │────▶│ Multi        │────▶│  整体进度     │
│              │     │ Progress     │     │  百分比       │
└──────────────┘     │ Tracker      │     └──────────────┘
                     └──────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │ 保存状态      │
                     │ (断点续传)    │
                     └──────────────┘
```

---

## 3. 模块依赖关系

```
PSiteDL
├── src/
│   └── webvidgrab/
│       ├── __init__.py
│       ├── config.py          # Phase 2 ✓
│       ├── logging.py         # Phase 2 ✓
│       ├── errors.py          # Phase 3 (本阶段)
│       ├── progress.py        # Phase 3 (本阶段)
│       ├── downloader.py      # Phase 4
│       ├── extractor.py       # Phase 4
│       └── cli.py             # Phase 5
├── tests/
│   ├── test_config.py         # Phase 2 ✓
│   ├── test_logging.py        # Phase 2 ✓
│   ├── test_errors.py         # Phase 3 (本阶段 - 13 用例)
│   ├── test_progress.py       # Phase 3 (本阶段 - 16 用例)
│   └── ...
└── config/
    └── default.json
```

---

## 4. 测试覆盖要求

### 4.1 错误处理模块测试 (13 个用例)

#### 重试装饰器 (4 个用例)
- [ ] `test_retry_on_success` - 成功时不重试
- [ ] `test_retry_on_failure` - 失败时重试
- [ ] `test_retry_exhausted` - 重试用尽后抛出异常
- [ ] `test_retry_only_specified_exceptions` - 只重试指定异常

#### 网络错误处理 (3 个用例)
- [ ] `test_handle_timeout` - 处理超时错误
- [ ] `test_handle_dns_failure` - 处理 DNS 失败
- [ ] `test_handle_connection_reset` - 处理连接重置

#### 页面解析错误处理 (2 个用例)
- [ ] `test_extract_video_candidates_fallback` - 降级策略
- [ ] `test_extract_with_multiple_patterns` - 多模式提取

#### Cookie 导出错误处理 (2 个用例)
- [ ] `test_cookie_export_failure_graceful` - 优雅降级
- [ ] `test_cookie_export_success` - 成功导出

#### 错误处理器 (2 个用例)
- [ ] `test_log_error_with_context` - 记录带上下文的错误
- [ ] `test_error_statistics` - 错误统计
- [ ] `test_error_recovery_suggestion` - 恢复建议

### 4.2 进度显示模块测试 (16 个用例)

#### 下载进度 (5 个用例)
- [ ] `test_progress_initialization` - 初始化
- [ ] `test_progress_update` - 更新进度
- [ ] `test_progress_complete` - 完成状态
- [ ] `test_progress_speed_calculation` - 速度计算
- [ ] `test_progress_eta` - 预计剩余时间

#### 进度条显示 (3 个用例)
- [ ] `test_text_progress_bar` - 文本进度条
- [ ] `test_rich_progress_bar` - Rich 库进度条
- [ ] `test_progress_with_filename` - 带文件名的进度

#### 多文件进度 (3 个用例)
- [ ] `test_multi_progress_tracker` - 多文件跟踪
- [ ] `test_multi_progress_update` - 多文件更新
- [ ] `test_multi_progress_summary` - 进度摘要

#### 进度持久化 (2 个用例)
- [ ] `test_save_progress_state` - 保存状态
- [ ] `test_resume_progress` - 恢复进度

#### 进度回调 (1 个用例)
- [ ] `test_progress_callback` - 回调函数

---

## 5. 实现计划

### 5.1 第一阶段：错误处理模块 (3 天)

1. **Day 1**: 异常层次结构和重试装饰器
   - 定义所有异常类
   - 实现 `retry_on_error` 装饰器
   - 运行 4 个重试测试

2. **Day 2**: 网络错误和安全提取
   - 实现 `handle_network_error` 上下文管理器
   - 实现 `safe_extract_videos`
   - 运行 5 个相关测试

3. **Day 3**: Cookie 导出和错误处理器
   - 实现 `safe_export_cookies`
   - 实现 `ErrorHandler` 类
   - 实现 `get_recovery_suggestion`
   - 运行剩余 4 个测试
   - 完整测试通过

### 5.2 第二阶段：进度显示模块 (3 天)

1. **Day 4**: 下载进度类
   - 实现 `DownloadProgress` 类
   - 实现速度/ETA 计算
   - 运行 5 个进度测试

2. **Day 5**: 进度条渲染
   - 实现 `render_progress_bar`
   - 实现 `render_progress_info`
   - 实现 `RichProgressDisplay`
   - 运行 3 个显示测试

3. **Day 6**: 多文件和持久化
   - 实现 `MultiProgressTracker`
   - 实现 `save_progress` / `load_progress`
   - 实现进度回调
   - 运行 6 个相关测试
   - 完整测试通过

### 5.3 第三阶段：集成测试 (1 天)

- 错误处理 + 进度联调
- 端到端测试
- 文档完善
- 代码审查

---

## 6. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 重试逻辑复杂 | 中 | 使用标准库 `time.sleep` + 简单循环 |
| Rich 库未安装 | 低 | 作为可选依赖，提供纯文本降级 |
| 进度计算精度 | 低 | 使用 `time.time()` 高精度时间戳 |
| 持久化状态过期 | 低 | 添加时间戳验证，过期自动失效 |
| Cookie 导出依赖 | 中 | 优雅降级，返回 None 继续无 Cookie 下载 |

---

## 7. 验收标准

- [ ] 29 个测试用例全部通过
- [ ] 代码覆盖率 ≥ 90%
- [ ] 类型注解完整 (mypy 无错误)
- [ ] 文档完整 (docstring + 设计文档)
- [ ] 代码审查通过

---

## 8. 与 Phase 2 的集成

### 8.1 配置集成

错误处理器使用 Phase 2 的配置：
```python
from webvidgrab.config import load_config

config = load_config(config_path)
error_handler = ErrorHandler(log_file=config["log_file"])
```

### 8.2 日志集成

错误处理使用 Phase 2 的日志系统：
```python
from webvidgrab.logging import create_logger

logger = create_logger("webvidgrab.errors")
logger.error("Download failed", exc_info=True)
```

### 8.3 进度集成

进度显示使用 Phase 2 的日志系统输出：
```python
from webvidgrab.logging import create_logger
from webvidgrab.progress import DownloadProgress

logger = create_logger("webvidgrab.progress")

def on_progress(progress: DownloadProgress):
    logger.info(f"Download: {progress.percentage:.1f}%")

progress = DownloadProgress(total=1000, callback=on_progress)
```

---

*文档版本：1.0*
*创建日期：2026-03-15*
*作者：PSiteDL 架构团队*
