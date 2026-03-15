"""配置管理模块测试 - TDD 驱动开发"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# 这些测试将在配置管理功能实现前编写 (TDD)
# 当前会失败，实现功能后应变为通过


class TestConfigLoader:
    """配置加载测试"""

    def test_load_config_from_file(self, config_file: Path, sample_config: dict) -> None:
        """从文件加载配置"""
        from webvidgrab.config import load_config

        loaded = load_config(config_file)
        assert loaded["output_dir"] == sample_config["output_dir"]
        assert loaded["browser"] == sample_config["browser"]
        assert loaded["concurrency"] == sample_config["concurrency"]

    def test_load_config_not_found(self, temp_dir: Path) -> None:
        """配置文件不存在时返回默认配置"""
        from webvidgrab.config import load_config

        non_existent = temp_dir / "non_existent.json"
        loaded = load_config(non_existent)
        assert loaded is not None
        assert "output_dir" in loaded

    def test_load_config_invalid_json(self, temp_dir: Path) -> None:
        """配置文件格式错误时抛出异常"""
        from webvidgrab.config import ConfigError, load_config

        invalid_file = temp_dir / "invalid.json"
        with open(invalid_file, "w", encoding="utf-8") as f:
            f.write("{ invalid json }")

        with pytest.raises(ConfigError):
            load_config(invalid_file)


class TestConfigValidator:
    """配置验证测试"""

    def test_validate_output_dir(self, sample_config: dict) -> None:
        """验证输出目录路径"""
        from webvidgrab.config import validate_config

        # 有效路径
        assert validate_config(sample_config) is True

        # 无效路径 (包含特殊字符)
        invalid_config = sample_config.copy()
        invalid_config["output_dir"] = "/invalid/<path>"
        with pytest.raises(ValueError):
            validate_config(invalid_config)

    def test_validate_concurrency(self, sample_config: dict) -> None:
        """验证并发数范围"""
        from webvidgrab.config import validate_config

        # 有效并发数
        sample_config["concurrency"] = 5
        assert validate_config(sample_config) is True

        # 无效并发数 (0 或负数)
        sample_config["concurrency"] = 0
        with pytest.raises(ValueError):
            validate_config(sample_config)

        # 无效并发数 (过大)
        sample_config["concurrency"] = 100
        with pytest.raises(ValueError):
            validate_config(sample_config)

    def test_validate_browser(self, sample_config: dict) -> None:
        """验证浏览器类型"""
        from webvidgrab.config import validate_config

        valid_browsers = ["chrome", "firefox", "edge", "safari"]
        for browser in valid_browsers:
            sample_config["browser"] = browser
            assert validate_config(sample_config) is True

        # 无效浏览器
        sample_config["browser"] = "invalid_browser"
        with pytest.raises(ValueError):
            validate_config(sample_config)


class TestConfigMerger:
    """配置合并测试 (CLI 参数覆盖配置文件)"""

    def test_cli_overrides_config(self, sample_config: dict) -> None:
        """CLI 参数优先级高于配置文件"""
        from webvidgrab.config import merge_configs

        base_config = sample_config
        cli_args = {"output_dir": "/cli/override", "concurrency": 1}

        merged = merge_configs(base_config, cli_args)
        assert merged["output_dir"] == "/cli/override"
        assert merged["concurrency"] == 1
        # 未覆盖的字段保持原值
        assert merged["browser"] == base_config["browser"]

    def test_merge_empty_cli(self, sample_config: dict) -> None:
        """空 CLI 参数时返回原配置"""
        from webvidgrab.config import merge_configs

        merged = merge_configs(sample_config, {})
        assert merged == sample_config


class TestConfigPersistence:
    """配置持久化测试"""

    def test_save_config(self, temp_dir: Path, sample_config: dict) -> None:
        """保存配置到文件"""
        from webvidgrab.config import save_config

        config_file = temp_dir / "saved_config.json"
        save_config(sample_config, config_file)

        assert config_file.exists()
        with open(config_file, encoding="utf-8") as f:
            saved = json.load(f)
        assert saved == sample_config

    def test_save_config_creates_dirs(self, temp_dir: Path, sample_config: dict) -> None:
        """保存配置时自动创建目录"""
        from webvidgrab.config import save_config

        nested_dir = temp_dir / "nested" / "config" / "dir"
        config_file = nested_dir / "config.json"

        save_config(sample_config, config_file)
        assert config_file.exists()


class TestDefaultConfig:
    """默认配置测试"""

    def test_get_default_config(self) -> None:
        """获取默认配置"""
        from webvidgrab.config import get_default_config

        default = get_default_config()
        assert "output_dir" in default
        assert "browser" in default
        assert "concurrency" in default
        assert default["concurrency"] >= 1
        assert default["max_retries"] >= 0

    def test_default_config_values(self) -> None:
        """验证默认配置值合理性"""
        from webvidgrab.config import get_default_config

        default = get_default_config()
        # 并发数默认值应在 1-10 之间
        assert 1 <= default["concurrency"] <= 10
        # 超时时间应为正数
        assert default["timeout"] > 0
