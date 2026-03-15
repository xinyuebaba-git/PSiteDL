"""配置管理模块 - 负责加载、验证、保存和合并配置。

本模块提供完整的配置管理功能，支持：
- 从 JSON 文件加载配置
- 配置项验证 (路径、范围、枚举)
- 默认配置提供
- CLI 参数与配置文件合并
- 配置持久化保存

典型用法:
    >>> from webvidgrab.config import load_config, validate_config, get_default_config
    >>> from pathlib import Path
    >>>
    >>> # 加载配置
    >>> config = load_config(Path("config.json"))
    >>>
    >>> # 验证配置
    >>> validate_config(config)
    True
    >>>
    >>> # 获取默认配置
    >>> default = get_default_config()
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, cast

__all__ = [
    "ConfigError",
    "get_default_config",
    "load_config",
    "save_config",
    "validate_config",
    "merge_configs",
]


# =============================================================================
# 常量定义
# =============================================================================

#: 默认配置字典
DEFAULT_CONFIG: dict[str, Any] = {
    "output_dir": "./downloads",
    "browser": "chrome",
    "profile": "Default",
    "concurrency": 3,
    "max_retries": 3,
    "timeout": 30,
    "log_level": "INFO",
    "log_file": "./logs/psitedl.log",
}

#: 有效的浏览器类型
VALID_BROWSERS: frozenset[str] = frozenset({"chrome", "firefox", "edge", "safari"})

#: 有效的日志级别
VALID_LOG_LEVELS: frozenset[str] = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})

#: 路径中不允许的特殊字符模式
INVALID_PATH_PATTERN: re.Pattern[str] = re.compile(r'[<>:"|?*]')


# =============================================================================
# 异常类
# =============================================================================


class ConfigError(Exception):
    """配置相关异常。

    在配置文件加载、解析或保存失败时抛出。

    Attributes:
        message: 错误描述信息
        path: 相关的文件路径 (可选)
    """

    def __init__(self, message: str, path: Path | None = None) -> None:
        """初始化 ConfigError。

        Args:
            message: 错误描述信息
            path: 相关的文件路径 (可选)
        """
        self.message = message
        self.path = path
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """格式化错误消息。

        Returns:
            包含路径信息的完整错误消息
        """
        if self.path:
            return f"{self.message}: {self.path}"
        return self.message


# =============================================================================
# 公共 API - 配置加载与保存
# =============================================================================


def get_default_config() -> dict[str, Any]:
    """获取默认配置字典。

    返回一个包含所有必需配置项的默认值字典。
    默认配置经过验证，保证可以直接使用。

    Returns:
        默认配置字典，包含以下键:
            - output_dir (str): 下载目录
            - browser (str): 浏览器类型
            - profile (str): 浏览器配置文件
            - concurrency (int): 并发数
            - max_retries (int): 最大重试次数
            - timeout (int): 超时时间 (秒)
            - log_level (str): 日志级别
            - log_file (str): 日志文件路径

    Example:
        >>> config = get_default_config()
        >>> config["concurrency"]
        3
    """
    return DEFAULT_CONFIG.copy()


def load_config(config_path: Path) -> dict[str, Any]:
    """从 JSON 文件加载配置。

    读取指定路径的配置文件并解析为字典。
    如果文件不存在，返回默认配置。
    如果文件格式错误，抛出 ConfigError。

    Args:
        config_path: 配置文件路径

    Returns:
        加载的配置字典

    Raises:
        ConfigError: JSON 解析失败或文件权限问题

    Example:
        >>> from pathlib import Path
        >>> config = load_config(Path("config.json"))
    """
    if not config_path.exists():
        return get_default_config()

    try:
        with open(config_path, encoding="utf-8") as f:
            config = cast(dict[str, Any], json.load(f))
    except json.JSONDecodeError as e:
        raise ConfigError("JSON 解析失败", config_path) from e
    except OSError as e:
        raise ConfigError("文件读取失败", config_path) from e

    return config


def save_config(config: dict[str, Any], config_path: Path) -> None:
    """保存配置到 JSON 文件。

    将配置字典写入指定路径。
    如果目录不存在，自动创建。
    使用缩进格式使文件人类可读。

    Args:
        config: 要保存的配置字典
        config_path: 目标文件路径

    Raises:
        ConfigError: 文件写入失败

    Example:
        >>> config = {"output_dir": "./videos", "concurrency": 5}
        >>> save_config(config, Path("config.json"))
    """
    try:
        # 自动创建目录
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except OSError as e:
        raise ConfigError("配置保存失败", config_path) from e


# =============================================================================
# 公共 API - 配置验证
# =============================================================================


def validate_config(config: dict[str, Any]) -> bool:
    """验证配置字典的有效性。

    检查所有配置项是否符合验证规则：
    - 路径格式正确
    - 数值在有效范围内
    - 枚举值在允许列表中

    Args:
        config: 待验证的配置字典

    Returns:
        True 如果所有配置项有效

    Raises:
        ValueError: 某个配置项验证失败

    Example:
        >>> config = get_default_config()
        >>> validate_config(config)
        True
    """
    # 验证输出目录
    _validate_output_dir(config.get("output_dir", ""))

    # 验证并发数
    _validate_concurrency(config.get("concurrency", 0))

    # 验证浏览器类型
    _validate_browser(config.get("browser", ""))

    # 验证日志级别
    _validate_log_level(config.get("log_level", ""))

    # 验证重试次数
    _validate_max_retries(config.get("max_retries", 0))

    # 验证超时时间
    _validate_timeout(config.get("timeout", 0))

    return True


def _validate_output_dir(output_dir: str) -> None:
    """验证输出目录路径。

    Args:
        output_dir: 输出目录路径

    Raises:
        ValueError: 路径包含特殊字符或格式无效
    """
    if not output_dir:
        raise ValueError("输出目录不能为空")

    if INVALID_PATH_PATTERN.search(output_dir):
        raise ValueError(f"输出目录包含非法字符：{output_dir}")


def _validate_concurrency(concurrency: Any) -> None:
    """验证并发数范围。

    并发数必须在 1-10 之间。

    Args:
        concurrency: 并发数值

    Raises:
        ValueError: 并发数不在有效范围内
    """
    if not isinstance(concurrency, int):
        raise ValueError(f"并发数必须是整数：{concurrency}")

    if concurrency < 1:
        raise ValueError(f"并发数不能小于 1: {concurrency}")

    if concurrency > 10:
        raise ValueError(f"并发数不能大于 10: {concurrency}")


def _validate_browser(browser: str) -> None:
    """验证浏览器类型。

    Args:
        browser: 浏览器类型字符串

    Raises:
        ValueError: 浏览器类型不在允许列表中
    """
    if not browser:
        raise ValueError("浏览器类型不能为空")

    if browser not in VALID_BROWSERS:
        raise ValueError(f"无效的浏览器类型：{browser}。允许的值：{', '.join(VALID_BROWSERS)}")


def _validate_log_level(log_level: str) -> None:
    """验证日志级别。

    Args:
        log_level: 日志级别字符串

    Raises:
        ValueError: 日志级别不在允许列表中
    """
    if not log_level:
        raise ValueError("日志级别不能为空")

    if log_level not in VALID_LOG_LEVELS:
        raise ValueError(f"无效的日志级别：{log_level}。允许的值：{', '.join(VALID_LOG_LEVELS)}")


def _validate_max_retries(max_retries: Any) -> None:
    """验证最大重试次数。

    Args:
        max_retries: 重试次数

    Raises:
        ValueError: 重试次数为负数
    """
    if not isinstance(max_retries, int):
        raise ValueError(f"最大重试次数必须是整数：{max_retries}")

    if max_retries < 0:
        raise ValueError(f"最大重试次数不能为负数：{max_retries}")


def _validate_timeout(timeout: Any) -> None:
    """验证超时时间。

    Args:
        timeout: 超时时间 (秒)

    Raises:
        ValueError: 超时时间为非正数
    """
    if not isinstance(timeout, int):
        raise ValueError(f"超时时间必须是整数：{timeout}")

    if timeout <= 0:
        raise ValueError(f"超时时间必须为正数：{timeout}")


# =============================================================================
# 公共 API - 配置合并
# =============================================================================


def merge_configs(base_config: dict[str, Any], override_config: dict[str, Any]) -> dict[str, Any]:
    """合并两个配置字典。

    将 override_config 中的值覆盖到 base_config。
    仅覆盖 override_config 中存在的键，其他键保持不变。
    返回新字典，不修改原始输入。

    Args:
        base_config: 基础配置 (通常来自配置文件)
        override_config: 覆盖配置 (通常来自 CLI 参数)

    Returns:
        合并后的新配置字典

    Example:
        >>> base = {"output_dir": "./downloads", "concurrency": 3}
        >>> override = {"concurrency": 5}
        >>> merged = merge_configs(base, override)
        >>> merged["concurrency"]
        5
        >>> merged["output_dir"]
        './downloads'
    """
    # 创建基础配置的深拷贝
    merged = base_config.copy()

    # 用覆盖配置更新
    for key, value in override_config.items():
        if value is not None:  # 只覆盖非 None 值
            merged[key] = value

    return merged
