# 批量下载模块架构设计

## 1. 概述

批量下载模块为 PSiteDL 提供从 URL 列表文件批量下载视频的能力，支持去重检测、进度显示和失败重试。

## 2. 需求规格

### 2.1 功能需求

| ID | 需求 | 优先级 |
|----|------|--------|
| FR1 | 命令行读取 URL 列表文件（每行一个 URL） | P0 |
| FR2 | 自动开始下载任务 | P0 |
| FR3 | 默认输出目录为 ~/Downloads | P0 |
| FR4 | 支持检测重复 URL | P1 |
| FR5 | 进度显示（支持 Rich 进度条） | P1 |
| FR6 | 失败重试机制 | P1 |

### 2.2 命令行参数

```bash
python -m webvidgrab.batch_downloader \
    --url-file PATH \
    [--output-dir DIR] \
    [--check-duplicates] \
    [--concurrency N] \
    [--max-retries N] \
    [--browser chrome|firefox|edge|safari] \
    [--profile PROFILE_NAME]
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--url-file` | Path | 必需 | URL 列表文件路径 |
| `--output-dir` | Path | ~/Downloads | 输出目录 |
| `--check-duplicates` | Flag | False | 检测重复 URL |
| `--concurrency` | int | 3 | 并发下载数 |
| `--max-retries` | int | 3 | 最大重试次数 |
| `--browser` | str | chrome | 浏览器类型 |
| `--profile` | str | Default | 浏览器配置文件 |

### 2.3 URL 列表文件格式

```text
# 这是注释，会被忽略
https://example.com/video1
https://example.com/video2

# 支持空行
https://example.com/video3
```

- 每行一个 URL
- 支持 `#` 开头的注释
- 忽略空行
- 支持行内注释（`URL # comment`）

## 3. 架构设计

### 3.1 模块结构

```
src/webvidgrab/
├── batch_downloader.py    # 批量下载主模块
├── url_dedup.py           # URL 去重模块
├── downloader.py          # 现有下载器（复用）
├── progress.py            # 现有进度显示（复用）
└── config.py              # 现有配置管理（复用）
```

### 3.2 组件关系

```
┌─────────────────────────────────────────────────────────────┐
│                    BatchDownloader                          │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │ URL 加载器   │───▶│ URL 去重器   │───▶│ 下载调度器   │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│                                            │                │
│                                            ▼                │
│                          ┌───────────────────────────┐      │
│                          │   并发下载执行器           │      │
│                          │  (复用 downloader.py)     │      │
│                          └───────────────────────────┘      │
│                                            │                │
│                          ┌─────────────────┴───────────┐    │
│                          ▼                             ▼    │
│                  ┌─────────────┐              ┌─────────────┐│
│                  │ 进度显示器   │              │ 重试管理器   ││
│                  └─────────────┘              └─────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### 3.3 类设计

#### 3.3.1 BatchDownloader（主类）

```python
class BatchDownloader:
    """批量下载器"""
    
    def __init__(
        self,
        url_file: Path,
        output_dir: Path,
        check_duplicates: bool = False,
        concurrency: int = 3,
        max_retries: int = 3,
        browser: str = "chrome",
        profile: str = "Default",
    ) -> None:
        """初始化批量下载器"""
        
    async def run(self) -> BatchDownloadResult:
        """执行批量下载"""
```

#### 3.3.2 URLLoader

```python
class URLLoader:
    """URL 加载器"""
    
    @staticmethod
    def load_from_file(path: Path) -> list[str]:
        """从文件加载 URL 列表"""
        
    @staticmethod
    def validate_url(url: str) -> bool:
        """验证 URL 格式"""
```

#### 3.3.3 URLDeduplicator（去重器）

```python
class URLDeduplicator:
    """URL 去重器"""
    
    def __init__(self, history_file: Path | None = None) -> None:
        """初始化去重器"""
        
    def find_duplicates(self, urls: list[str]) -> dict[str, list[int]]:
        """查找重复 URL"""
        
    def deduplicate(self, urls: list[str]) -> list[str]:
        """去重并返回唯一 URL 列表"""
        
    def save_to_history(self, urls: list[str]) -> None:
        """保存 URL 到历史记录"""
```

#### 3.3.4 DownloadScheduler

```python
class DownloadScheduler:
    """下载调度器"""
    
    def __init__(
        self,
        downloader: DownloadCallable,
        concurrency: int = 3,
        max_retries: int = 3,
    ) -> None:
        """初始化调度器"""
        
    async def schedule(
        self,
        urls: list[str],
        output_dir: Path,
        progress_callback: Callable | None = None,
    ) -> list[DownloadResult]:
        """调度下载任务"""
```

#### 3.3.5 BatchDownloadResult

```python
@dataclass
class BatchDownloadResult:
    """批量下载结果"""
    
    total: int                    # 总 URL 数
    succeeded: int                # 成功数
    failed: int                   # 失败数
    skipped: int                  # 跳过数（重复）
    results: list[DownloadResult] # 详细结果
    duration: float               # 总耗时（秒）
```

## 4. 数据流

### 4.1 正常流程

```
1. 读取 URL 文件
   ↓
2. 解析并验证 URL（过滤注释、空行、无效 URL）
   ↓
3. 去重检测（可选）
   ↓
4. 创建下载任务队列
   ↓
5. 并发执行下载（带进度显示）
   ↓
6. 处理失败重试
   ↓
7. 汇总结果并输出报告
```

### 4.2 错误处理流程

```
下载失败
   ↓
检查重试次数 < max_retries？
   ├─ 是 → 加入重试队列（指数退避）
   └─ 否 → 记录失败，继续下一个任务
   ↓
所有任务完成
   ↓
输出失败报告
```

## 5. 去重策略

### 5.1 去重级别

| 级别 | 说明 | 实现 |
|------|------|------|
| 会话内去重 | 当前 URL 列表内的重复 | 默认启用 |
| 历史去重 | 与历史下载记录重复 | `--check-duplicates` 启用 |

### 5.2 历史记录存储

```json
{
  "version": 1,
  "updated_at": "2026-03-15T15:00:00Z",
  "urls": [
    {
      "url": "https://example.com/video1",
      "downloaded_at": "2026-03-15T14:30:00Z",
      "output_file": "~/Downloads/video1.mp4",
      "file_hash": "sha256:abc123..."
    }
  ]
}
```

存储位置：`~/.config/psitedl/download_history.json`

### 5.3 去重算法

```python
def find_duplicates(urls: list[str]) -> dict[str, list[int]]:
    """
    返回：{ normalized_url: [index1, index2, ...] }
    """
    # 1. URL 标准化（去除 trailing slash, 统一 scheme 等）
    # 2. 构建映射表
    # 3. 返回重复项
```

## 6. 进度显示设计

### 6.1 进度信息

- 总任务数 / 当前进度
- 当前下载 URL
- 下载速度
- 预计剩余时间
- 成功/失败计数

### 6.2 Rich 进度条布局

```
批量下载 [████████░░] 80%  8/10 任务
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
当前：https://example.com/video8.mp4
速度：2.5 MB/s  ETA: 00:02:15
成功：7  失败：0  跳过：1
```

## 7. 重试机制

### 7.1 重试策略

| 重试次数 | 延迟时间 |
|----------|----------|
| 1 | 1 秒 |
| 2 | 2 秒 |
| 3 | 4 秒 |
| 4+ | 8 秒（上限） |

### 7.2 可重试错误

- 网络超时
- 连接重置
- 临时性 HTTP 错误（502, 503, 504）
- 浏览器启动失败

### 7.3 不可重试错误

- URL 无效
- 404 Not Found
- 权限拒绝
- 磁盘空间不足

## 8. 性能考虑

### 8.1 并发控制

- 默认并发数：3
- 最大并发数：10（防止带宽饱和）
- 使用信号量限制并发

### 8.2 内存优化

- URL 列表流式读取（支持大文件）
- 下载结果增量写入（避免内存累积）

### 8.3 磁盘 I/O

- 顺序写入日志
- 异步写入历史记录

## 9. 日志设计

### 9.1 日志级别

| 级别 | 用途 |
|------|------|
| INFO | 任务开始/完成、进度摘要 |
| DEBUG | 每个 URL 的处理细节 |
| WARNING | 重试、跳过 |
| ERROR | 失败详情 |

### 9.2 日志格式

```text
2026-03-15 15:30:00 [INFO] 批量下载开始：10 个 URL
2026-03-15 15:30:01 [INFO] [1/10] 开始下载：https://example.com/video1
2026-03-15 15:30:15 [INFO] [1/10] 下载完成：video1.mp4 (15.2 MB)
2026-03-15 15:30:16 [INFO] [2/10] 开始下载：https://example.com/video2
2026-03-15 15:30:20 [WARNING] [2/10] 下载失败，重试 1/3：Connection reset
2026-03-15 15:30:22 [INFO] [2/10] 重试成功：video2.mp4 (8.5 MB)
2026-03-15 15:35:00 [INFO] 批量下载完成：成功 9/10, 失败 1, 跳过 0
```

## 10. 测试策略

### 10.1 单元测试

- URLLoader: 文件解析、URL 验证
- URLDeduplicator: 去重逻辑、历史记录
- DownloadScheduler: 任务调度、重试逻辑

### 10.2 集成测试

- 完整批量下载流程
- 并发下载压力测试
- 大 URL 列表处理

### 10.3 端到端测试

- 真实网站下载
- 中断恢复测试

## 11. 扩展点

### 11.1 未来功能

- [ ] URL 列表从 stdin 读取
- [ ] 导出下载结果为 JSON/CSV
- [ ] 暂停/恢复下载
- [ ] 带宽限制
- [ ] 定时下载任务

### 11.2 插件接口

```python
class BatchDownloadPlugin(Protocol):
    """批量下载插件接口"""
    
    def on_url_loaded(self, urls: list[str]) -> list[str]:
        """URL 加载后钩子"""
        
    def on_download_start(self, url: str) -> None:
        """下载开始前钩子"""
        
    def on_download_complete(self, result: DownloadResult) -> None:
        """下载完成后钩子"""
```

## 12. 依赖关系

### 12.1 新增依赖

无（复用现有依赖）

### 12.2 现有依赖复用

- `rich`: 进度显示
- `aiohttp`: 异步 HTTP（如果需要）
- 现有 `downloader.py` 模块

## 13. 实施计划

### Phase 1: 核心功能

1. 实现 URLLoader
2. 实现 URLDeduplicator
3. 实现 BatchDownloader 骨架
4. 命令行参数解析

### Phase 2: 下载执行

1. 集成现有 downloader.py
2. 实现 DownloadScheduler
3. 进度显示集成

### Phase 3: 完善功能

1. 重试机制
2. 错误处理
3. 日志记录
4. 测试用例

### Phase 4: 优化

1. 性能优化
2. 文档完善
3. 用户测试

## 14. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 并发过高导致带宽饱和 | 中 | 限制最大并发数，添加带宽限制选项 |
| 大量 URL 导致内存溢出 | 低 | 流式读取，增量处理 |
| 历史记录文件过大 | 低 | 定期清理，限制记录数量 |
| 与现有 CLI 冲突 | 低 | 使用独立子命令 |

## 15. 验收标准

- [ ] 能够成功下载 10+ URL 列表
- [ ] 去重检测准确率 100%
- [ ] 失败重试机制正常工作
- [ ] 进度显示实时更新
- [ ] 命令行参数符合设计
- [ ] 单元测试覆盖率 > 80%
- [ ] 文档完整
