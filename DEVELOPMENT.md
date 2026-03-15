# PSiteDL 开发指南

## 📋 目录

- [架构概览](#架构概览)
- [开发环境设置](#开发环境设置)
- [代码结构](#代码结构)
- [测试驱动开发](#测试驱动开发)
- [代码规范](#代码规范)
- [调试技巧](#调试技巧)
- [发布流程](#发布流程)

## 架构概览

### 核心模块

```
src/webvidgrab/
├── site_cli.py       # 命令行入口
├── site_gui.py       # 图形界面入口
├── config.py         # 配置管理 (TODO)
├── logging.py        # 日志系统 (TODO)
├── errors.py         # 错误处理 (TODO)
├── progress.py       # 进度显示 (TODO)
├── downloader.py     # 并发下载 (TODO)
└── probe.py          # 视频探测
```

### 数据流

```
用户输入 → 配置加载 → URL 解析 → 视频探测 → Cookie 导出 → 下载 → 进度显示 → 完成
                ↓           ↓          ↓          ↓          ↓
            配置验证   错误处理   候选评分   重试机制   日志记录
```

## 开发环境设置

### 1. 克隆项目

```bash
git clone https://github.com/xinyuebaba-git/PSiteDL.git
cd PSiteDL
```

### 2. 创建虚拟环境

```bash
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate  # Windows
```

### 3. 安装依赖

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 验证安装
pytest --version
black --version
ruff --version
```

### 4. 安装 Playwright 浏览器

```bash
playwright install chrome
```

### 5. 预提交钩子 (可选)

```bash
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
echo "Running code quality checks..."
black src/ tests/
ruff check src/ tests/
mypy src/
echo "Running tests..."
pytest tests/ -q
EOF
chmod +x .git/hooks/pre-commit
```

## 代码结构

### 模块职责

#### `config.py` - 配置管理
- `load_config(path)` - 加载配置文件
- `save_config(config, path)` - 保存配置
- `validate_config(config)` - 验证配置
- `merge_configs(base, override)` - 合并配置
- `get_default_config()` - 获取默认配置

#### `logging.py` - 日志系统
- `create_logger(name, level, log_file, json_format)` - 创建日志器
- `create_logger_with_rotation(...)` - 带轮转的日志器
- `create_audit_logger(path)` - 审计日志器
- `log_context(logger, operation)` - 日志上下文管理器
- `log_execution_time(logger, name)` - 执行时间装饰器

#### `errors.py` - 错误处理
- `retry_on_error(max_retries, exceptions)` - 重试装饰器
- `handle_network_error(timeout)` - 网络错误上下文
- `safe_extract_videos(html, base_url)` - 安全提取视频
- `safe_export_cookies(browser, profile, log)` - 安全导出 Cookie
- `ErrorHandler` - 错误处理器类

#### `progress.py` - 进度显示
- `DownloadProgress` - 下载进度类
- `MultiProgressTracker` - 多文件进度跟踪
- `render_progress_bar(current, total, width)` - 渲染进度条
- `RichProgressDisplay` - Rich 库进度显示

#### `downloader.py` - 并发下载
- `ConcurrentDownloader` - 并发下载器
- `DownloadQueue` - 下载队列
- `RetryQueue` - 重试队列
- `BandwidthLimiter` - 带宽限制器
- `ResultAggregator` - 结果汇总

## 测试驱动开发

### TDD 流程

```
1. 红 → 写一个失败的测试
2. 绿 → 写最小代码使测试通过
3. 重构 → 改进代码结构，保持测试通过
```

### 测试示例

**步骤 1: 写测试** (`tests/test_config.py`)
```python
def test_load_config_from_file(config_file, sample_config):
    from webvidgrab.config import load_config
    
    loaded = load_config(config_file)
    assert loaded["output_dir"] == sample_config["output_dir"]
```

**步骤 2: 运行测试 (失败)**
```bash
$ pytest tests/test_config.py -v
FAILED - ModuleNotFoundError: No module named 'webvidgrab.config'
```

**步骤 3: 实现功能** (`src/webvidgrab/config.py`)
```python
import json
from pathlib import Path

def load_config(path: Path) -> dict:
    if not path.exists():
        return get_default_config()
    
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def get_default_config() -> dict:
    return {
        "output_dir": str(Path.home() / "Downloads"),
        "browser": "chrome",
        "concurrency": 3,
        # ...
    }
```

**步骤 4: 运行测试 (通过)**
```bash
$ pytest tests/test_config.py -v
PASSED ✓
```

### 测试最佳实践

1. **使用 fixtures**: 在 `conftest.py` 定义共享测试数据
2. **测试隔离**: 每个测试独立，不依赖其他测试
3. **测试命名**: `test_<function>_<scenario>_<expected>`
4. **断言明确**: 一个测试一个断言 (或少量相关断言)
5. **Mock 外部依赖**: 使用 `unittest.mock` 隔离网络/文件系统

## 代码规范

### 类型注解

所有公共函数必须有类型注解：

```python
from pathlib import Path
from typing import Any, Optional

def load_config(path: Path) -> dict[str, Any]:
    """加载配置文件"""
    ...

def find_video_url(html: str, base_url: str) -> Optional[str]:
    """查找视频 URL"""
    ...
```

### 文档字符串

使用 Google 风格文档字符串：

```python
def download_video(url: str, output_dir: Path) -> DownloadResult:
    """下载单个视频文件
    
    Args:
        url: 视频页面 URL
        output_dir: 输出目录
        
    Returns:
        DownloadResult 包含下载结果
        
    Raises:
        DownloadError: 下载失败时抛出
    """
    ...
```

### 代码格式化

使用 Black 和 Ruff 自动格式化：

```bash
# 格式化代码
black src/ tests/

# 检查代码质量
ruff check src/ tests/

# 自动修复问题
ruff check --fix src/ tests/
```

### 命名规范

- **模块**: 小写，下划线分隔 (`site_cli.py`)
- **函数**: 小写，下划线分隔 (`load_config`)
- **类**: 大驼峰 (`DownloadProgress`)
- **常量**: 全大写，下划线分隔 (`DEFAULT_TIMEOUT`)
- **私有**: 单下划线前缀 (`_internal_helper`)

## 调试技巧

### 日志调试

```python
from webvidgrab.logging import create_logger

logger = create_logger(__name__, level="DEBUG")

def debug_function():
    logger.debug("Entering function", extra={"params": locals()})
    try:
        # ... 代码
        logger.info("Operation completed")
    except Exception as e:
        logger.error("Operation failed", exc_info=True)
        raise
```

### 断点调试

```bash
# 安装 ipdb
pip install ipdb

# 代码中插入断点
import ipdb; ipdb.set_trace()

# 运行测试时调试
pytest tests/test_feature.py -s --pdb
```

### 性能分析

```bash
# 使用 cProfile
python -m cProfile -o profile.stats src/webvidgrab/site_cli.py

# 可视化分析
snakeviz profile.stats
```

## 发布流程

### 1. 更新版本号

编辑 `pyproject.toml`:
```toml
[project]
version = "0.2.0"  # 语义化版本
```

### 2. 更新变更日志

编辑 `CHANGELOG.md`:
```markdown
## [0.2.0] - 2026-03-15

### Added
- 配置管理系统
- 结构化日志
- 并发下载支持

### Changed
- 改进错误处理逻辑

### Fixed
- 修复 Cookie 导出失败问题
```

### 3. 运行测试

```bash
pytest --cov=src/webvidgrab --cov-report=term-missing
# 确保覆盖率 >= 80%
```

### 4. 构建分发包

```bash
python3 scripts/build_psitedl_bundle.py
```

### 5. 创建 Git 标签

```bash
git add .
git commit -m "Release version 0.2.0"
git tag -a v0.2.0 -m "Version 0.2.0"
git push origin main --tags
```

---

**最后更新**: 2026-03-15  
**维护者**: PSiteDL 开发团队
