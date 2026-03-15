# PSiteDL Phase 2 架构设计文档

## 概述

Phase 2 目标：实现配置管理 + 日志系统，通过 23 个测试用例

**设计原则：**
- 遵循 TDD（测试驱动开发）
- 类型注解完整
- 配置与代码分离
- 结构化日志支持审计

---

## 1. 配置管理模块 (config.py)

### 1.1 配置文件格式

采用 JSON 格式，原因：
- 人类可读
- 跨语言兼容
- Python 原生支持
- 易于版本控制

**配置文件示例：**
```json
{
  "output_dir": "./downloads",
  "browser": "chrome",
  "profile": "Default",
  "concurrency": 3,
  "max_retries": 3,
  "timeout": 30,
  "log_level": "INFO",
  "log_file": "./logs/psitedl.log"
}
```

### 1.2 配置项设计

| 配置项 | 类型 | 默认值 | 验证规则 | 说明 |
|--------|------|--------|----------|------|
| `output_dir` | str | `"./downloads"` | 有效路径，不含特殊字符 | 视频下载目录 |
| `browser` | str | `"chrome"` | `chrome\|firefox\|edge\|safari` | 浏览器类型 |
| `profile` | str | `"Default"` | 非空字符串 | 浏览器配置文件名 |
| `concurrency` | int | `3` | 1 ≤ n ≤ 10 | 并发下载数 |
| `max_retries` | int | `3` | n ≥ 0 | 失败重试次数 |
| `timeout` | int | `30` | n > 0 | 请求超时 (秒) |
| `log_level` | str | `"INFO"` | `DEBUG\|INFO\|WARNING\|ERROR\|CRITICAL` | 日志级别 |
| `log_file` | str | `"./logs/psitedl.log"` | 有效路径 | 日志文件路径 |

### 1.3 验证规则

```python
# 路径验证
- 不能包含：< > : " | ? * 等特殊字符
- 必须是合法的 Unix/Windows 路径格式

# 数值验证
- concurrency: 1-10 (避免资源耗尽)
- max_retries: ≥ 0
- timeout: > 0

# 枚举验证
- browser: chrome, firefox, edge, safari
- log_level: DEBUG, INFO, WARNING, ERROR, CRITICAL
```

### 1.4 默认配置

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

### 1.5 类图

```
┌─────────────────────────────────────────────────────────┐
│                      config.py                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────┐    ┌──────────────────────┐       │
│  │  ConfigError    │    │  ConfigLoader        │       │
│  │  (Exception)    │    │                      │       │
│  └─────────────────┘    │  - config_path: Path │       │
│                         │                      │       │
│                         │  + load() -> dict    │       │
│                         │  + save() -> None    │       │
│                         └──────────────────────┘       │
│                                                         │
│  ┌──────────────────────┐    ┌──────────────────────┐  │
│  │  ConfigValidator     │    │  ConfigMerger        │  │
│  │                      │    │                      │  │
│  │  + validate() -> bool│    │  + merge() -> dict   │  │
│  │  + _validate_path()  │    │                      │  │
│  │  + _validate_range() │    │                      │  │
│  │  + _validate_enum()  │    │                      │  │
│  └──────────────────────┘    └──────────────────────┘  │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │              Public API                          │  │
│  │                                                  │  │
│  │  get_default_config() -> dict                    │  │
│  │  load_config(path: Path) -> dict                 │  │
│  │  save_config(config: dict, path: Path) -> None   │  │
│  │  validate_config(config: dict) -> bool           │  │
│  │  merge_configs(base: dict, override: dict) -> dict│ │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 1.6 API 设计

```python
from pathlib import Path
from typing import Any


def get_default_config() -> dict[str, Any]:
    """获取默认配置"""
    ...


def load_config(config_path: Path) -> dict[str, Any]:
    """
    从文件加载配置
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        配置字典
        
    Raises:
        ConfigError: JSON 解析失败或文件权限问题
    """
    ...


def save_config(config: dict[str, Any], config_path: Path) -> None:
    """
    保存配置到文件
    
    Args:
        config: 配置字典
        config_path: 目标文件路径
        
    Raises:
        ConfigError: 文件写入失败
    """
    ...


def validate_config(config: dict[str, Any]) -> bool:
    """
    验证配置有效性
    
    Args:
        config: 待验证的配置字典
        
    Returns:
        True 如果配置有效
        
    Raises:
        ValueError: 配置项验证失败
    """
    ...


def merge_configs(
    base_config: dict[str, Any],
    override_config: dict[str, Any]
) -> dict[str, Any]:
    """
    合并配置 (CLI 参数覆盖配置文件)
    
    Args:
        base_config: 基础配置 (来自文件)
        override_config: 覆盖配置 (来自 CLI)
        
    Returns:
        合并后的配置
    """
    ...
```

### 1.7 数据流

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  配置文件    │────▶│  ConfigLoader │────▶│  配置字典    │
│  (JSON)      │     │               │     │              │
└──────────────┘     └──────────────┘     └──────────────┘
                                                 │
                                                 ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  CLI 参数     │────▶│ ConfigMerger  │◀────│  验证器      │
│              │     │               │     │              │
└──────────────┘     └──────────────┘     └──────────────┘
                                                 │
                                                 ▼
                                          ┌──────────────┐
                                          │  最终配置     │
                                          │  (应用运行)   │
                                          └──────────────┘
```

---

## 2. 日志系统模块 (logging.py)

### 2.1 日志级别

采用 Python 标准日志级别：

| 级别 | 数值 | 使用场景 |
|------|------|----------|
| DEBUG | 10 | 调试信息，详细执行过程 |
| INFO | 20 | 正常操作信息 |
| WARNING | 30 | 警告，不影响运行 |
| ERROR | 40 | 错误，操作失败 |
| CRITICAL | 50 | 严重错误，程序终止 |

### 2.2 日志格式

**结构化日志 (JSON 格式)：**
```json
{
  "timestamp": "2026-03-15T10:30:45.123Z",
  "level": "INFO",
  "logger": "webvidgrab.downloader",
  "message": "Download started",
  "context": {
    "url": "https://example.com/video",
    "user": "admin",
    "operation": "download"
  }
}
```

**传统格式 (人类可读)：**
```
2026-03-15 10:30:45.123 | INFO     | webvidgrab.downloader | Download started
```

### 2.3 轮转策略

**按大小轮转 (Size-based Rotation)：**
- 单文件最大：10MB
- 备份数量：5 个
- 文件命名：`psitedl.log.1`, `psitedl.log.2`, ...

**按日期轮转 (Time-based Rotation)：**
- 轮转周期：每天
- 文件命名：`psitedl.2026-03-15.log`
- 保留天数：30 天

### 2.4 审计日志

**关键操作审计：**
- 下载开始/结束
- 配置变更
- 认证操作
- 错误异常

**审计日志特点：**
- 只追加写入 (immutable)
- 独立文件 (`audit.log`)
- JSON 格式便于分析
- 包含操作者、时间、操作类型

### 2.5 类图

```
┌─────────────────────────────────────────────────────────┐
│                     logging.py                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │              Logger Factory                      │  │
│  │                                                  │  │
│  │  create_logger() -> logging.Logger               │  │
│  │  create_logger_with_rotation() -> logging.Logger │  │
│  │  create_date_logger() -> logging.Logger          │  │
│  │  create_audit_logger() -> AuditLogger            │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
│  ┌─────────────────────────┐    ┌────────────────────┐ │
│  │  StructuredFormatter    │    │  AuditLogger       │ │
│  │  (logging.Formatter)    │    │                    │ │
│  │                         │    │  - file: Path      │ │
│  │  + format() -> str      │    │                    │ │
│  │  + format_json() -> str │    │  + audit()         │ │
│  └─────────────────────────┘    └────────────────────┘ │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │              Context Manager                     │  │
│  │                                                  │  │
│  │  log_context() -> ContextManager                 │  │
│  │  log_execution_time() -> Decorator               │  │
│  │  log_if_slow() -> Decorator                      │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 2.6 API 设计

```python
import logging
from pathlib import Path
from contextlib import contextmanager
from typing import Callable, Any


def create_logger(
    name: str,
    level: str = "INFO",
    log_file: str | None = None,
    json_format: bool = False,
) -> logging.Logger:
    """
    创建日志记录器
    
    Args:
        name: 日志器名称
        level: 日志级别
        log_file: 日志文件路径 (可选)
        json_format: 是否使用 JSON 格式
        
    Returns:
        配置好的 Logger 实例
    """
    ...


def create_logger_with_rotation(
    name: str,
    log_file: str,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    level: str = "INFO",
) -> logging.Logger:
    """
    创建带轮转的日志记录器
    
    Args:
        name: 日志器名称
        log_file: 日志文件路径
        max_bytes: 单文件最大字节数
        backup_count: 备份文件数量
        level: 日志级别
        
    Returns:
        配置好的 Logger 实例
    """
    ...


def create_date_logger(
    name: str,
    log_dir: str,
    format: str = "%Y-%m-%d",
    level: str = "INFO",
) -> logging.Logger:
    """
    创建按日期轮转的日志记录器
    
    Args:
        name: 日志器名称
        log_dir: 日志目录
        format: 日期格式
        level: 日志级别
        
    Returns:
        配置好的 Logger 实例
    """
    ...


class AuditLogger:
    """审计日志记录器"""
    
    def __init__(self, audit_file: str) -> None:
        """初始化审计日志"""
        ...
    
    def audit(
        self,
        operation: str,
        **context: Any
    ) -> None:
        """
        记录审计日志
        
        Args:
            operation: 操作类型 (如 download_started)
            **context: 额外上下文信息
        """
        ...


@contextmanager
def log_context(
    logger: logging.Logger,
    operation: str,
    **context: Any
):
    """
    日志上下文管理器 (自动记录开始/结束)
    
    Args:
        logger: 日志记录器
        operation: 操作名称
        **context: 上下文信息
        
    Yields:
        None
        
    Example:
        with log_context(logger, "download", url=url):
            download_video(url)
    """
    ...


def log_execution_time(
    logger: logging.Logger,
    operation: str
) -> Callable:
    """
    记录函数执行时间的装饰器
    
    Args:
        logger: 日志记录器
        operation: 操作名称
        
    Returns:
        装饰器函数
    """
    ...


def log_if_slow(
    logger: logging.Logger,
    threshold: float = 1.0
) -> Callable:
    """
    记录慢操作的装饰器
    
    Args:
        logger: 日志记录器
        threshold: 慢操作阈值 (秒)
        
    Returns:
        装饰器函数
    """
    ...
```

### 2.7 数据流

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  应用代码     │────▶│ Logger       │────▶│  Formatter   │
│  (logger.info)│    │              │     │              │
└──────────────┘     └──────────────┘     └──────────────┘
                                                 │
                    ┌────────────────────────────┤
                    │                            │
                    ▼                            ▼
           ┌──────────────┐            ┌──────────────┐
           │  Console     │            │  File Handler│
           │  Handler     │            │  (Rotation)  │
           └──────────────┘            └──────────────┘
                                              │
                                              ▼
                                       ┌──────────────┐
                                       │  日志文件     │
                                       │  psitedl.log │
                                       └──────────────┘


┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  关键操作     │────▶│ AuditLogger  │────▶│  audit.log   │
│  (审计点)    │     │              │     │  (只追加)    │
└──────────────┘     └──────────────┘     └──────────────┘
```

---

## 3. 模块依赖关系

```
PSiteDL
├── src/
│   └── webvidgrab/
│       ├── __init__.py
│       ├── config.py          # 配置管理
│       ├── logging.py         # 日志系统
│       ├── downloader.py      # 下载器 (Phase 3)
│       ├── extractor.py       # 视频提取 (Phase 3)
│       └── cli.py             # 命令行界面 (Phase 4)
├── tests/
│   ├── test_config.py         # 配置测试 (23 个用例中的一部分)
│   ├── test_logging.py        # 日志测试 (23 个用例中的一部分)
│   └── ...
└── config/
    └── default.json           # 默认配置文件
```

---

## 4. 测试覆盖要求

### 4.1 配置模块测试 (12 个用例)

- [x] `test_load_config_from_file` - 从文件加载配置
- [x] `test_load_config_not_found` - 文件不存在返回默认
- [x] `test_load_config_invalid_json` - JSON 错误抛出异常
- [x] `test_validate_output_dir` - 验证输出目录
- [x] `test_validate_concurrency` - 验证并发数
- [x] `test_validate_browser` - 验证浏览器类型
- [x] `test_cli_overrides_config` - CLI 参数覆盖
- [x] `test_merge_empty_cli` - 空 CLI 合并
- [x] `test_save_config` - 保存配置
- [x] `test_save_config_creates_dirs` - 自动创建目录
- [x] `test_get_default_config` - 获取默认配置
- [x] `test_default_config_values` - 默认值合理性

### 4.2 日志模块测试 (11 个用例)

- [x] `test_create_logger` - 创建日志器
- [x] `test_logger_levels` - 日志级别
- [x] `test_json_log_format` - JSON 格式
- [x] `test_rotate_by_size` - 按大小轮转
- [x] `test_rotate_by_date` - 按日期轮转
- [x] `test_audit_critical_operations` - 审计关键操作
- [x] `test_audit_log_immutable` - 审计日志只追加
- [x] `test_context_manager` - 上下文管理器
- [x] `test_context_with_error` - 错误上下文
- [x] `test_log_execution_time` - 执行时间装饰器
- [x] `test_log_slow_operations` - 慢操作装饰器

---

## 5. 实现计划

### 5.1 第一阶段：配置模块 (2 天)

1. **Day 1**: 实现 `ConfigLoader` 和 `ConfigValidator`
   - `get_default_config()`
   - `load_config()`
   - `validate_config()`
   - 运行测试，修复问题

2. **Day 2**: 实现 `ConfigMerger` 和持久化
   - `merge_configs()`
   - `save_config()`
   - 完整测试通过

### 5.2 第二阶段：日志模块 (3 天)

1. **Day 3**: 基础日志器
   - `create_logger()`
   - `StructuredFormatter`
   - 日志级别支持

2. **Day 4**: 轮转和审计
   - `create_logger_with_rotation()`
   - `create_date_logger()`
   - `AuditLogger`

3. **Day 5**: 上下文和装饰器
   - `log_context()`
   - `log_execution_time()`
   - `log_if_slow()`
   - 完整测试通过

### 5.3 第三阶段：集成测试 (1 天)

- 配置 + 日志联调
- 端到端测试
- 文档完善

---

## 6. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| JSON 配置解析失败 | 中 | 提供默认配置降级 |
| 日志文件权限问题 | 低 | 启动时检查并提示 |
| 轮转逻辑复杂 | 低 | 使用 Python 标准库 `logging.handlers` |
| 并发配置验证遗漏 | 中 | 边界测试覆盖 0, 1, 10, 11, -1 |

---

## 7. 验收标准

- [ ] 23 个测试用例全部通过
- [ ] 代码覆盖率 ≥ 90%
- [ ] 类型注解完整 (mypy 无错误)
- [ ] 文档完整 (docstring + 设计文档)
- [ ] 代码审查通过

---

*文档版本：1.0*
*创建日期：2026-03-15*
*作者：PSiteDL 架构团队*
