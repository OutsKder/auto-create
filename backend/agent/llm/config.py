"""
LLM 配置文件管理

支持从配置文件和环境变量两种方式加载 LLM 配置

使用方式：
```python
from agent.llm.config import load_config, save_config

# 从环境变量加载配置
config = load_config("doubao")

# 从配置文件加载
config = load_config("qwen", config_file="config/llm.yaml")

# 保存配置到文件
save_config("doubao", config, config_file="config/llm.yaml")
```
"""

import os
import json
import re
import yaml
from typing import Dict, Any, Optional
from pathlib import Path

from .base import LLMConfig

DEFAULT_CONFIG_DIR = Path(__file__).parent.parent.parent.parent / "config"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "llm.yaml"


def ensure_config_dir():
    """确保配置目录存在"""
    DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config_from_env(provider: str) -> Dict[str, Any]:
    """
    从环境变量加载 LLM 配置

    Args:
        provider: Provider 类型

    Returns:
        配置字典
    """
    config = {
        "provider": provider,
    }

    if provider == "doubao":
        config["model"] = os.environ.get("DOUBAO_MODEL", "doubao-pro-32k")
        config["api_key"] = os.environ.get("DOUBAO_API_KEY")
        config["base_url"] = os.environ.get(
            "DOUBAO_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3"
        )

    elif provider == "qwen":
        config["model"] = os.environ.get("QWEN_MODEL", "qwen-max")
        config["api_key"] = os.environ.get("DASHSCOPE_API_KEY")
        config["base_url"] = os.environ.get(
            "QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
        )

    elif provider == "openai":
        config["model"] = os.environ.get("OPENAI_MODEL", "gpt-4")
        config["api_key"] = os.environ.get("OPENAI_API_KEY")
        config["base_url"] = os.environ.get(
            "OPENAI_BASE_URL", "https://api.openai.com/v1"
        )

    return {k: v for k, v in config.items() if v is not None}


_ENV_PLACEHOLDER_PATTERN = re.compile(r"^\$\{([A-Z0-9_]+)\}$")


def _resolve_placeholder(value: Any) -> Any:
    """把 ${VAR} 形式的占位符替换为环境变量值。"""

    if not isinstance(value, str):
        return value

    match = _ENV_PLACEHOLDER_PATTERN.match(value.strip())
    if not match:
        return value

    return os.environ.get(match.group(1))


def load_config(provider: str, config_file: Optional[str] = None) -> LLMConfig:
    """
    加载 LLM 配置

    优先级：配置文件 > 环境变量 > 默认值

    Args:
        provider: Provider 类型
        config_file: 配置文件路径

    Returns:
        LLMConfig 实例
    """
    config_path = Path(config_file) if config_file else DEFAULT_CONFIG_FILE

    # 如果有配置文件，合并配置
    config_dict: Dict[str, Any] = {"provider": provider}
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            if config_path.suffix in [".yaml", ".yml"]:
                file_configs = yaml.safe_load(f) or {}
            elif config_path.suffix == ".json":
                file_configs = json.load(f) or {}
            else:
                file_configs = {}

            if provider in file_configs:
                provider_config = file_configs[provider]
                for key, value in provider_config.items():
                    value = _resolve_placeholder(value)
                    if value is not None:
                        config_dict[key] = value

    # 再用环境变量补齐配置文件没有提供的字段
    env_config = load_config_from_env(provider)
    for key, value in env_config.items():
        if key not in config_dict or config_dict[key] is None:
            config_dict[key] = value

    return LLMConfig(**config_dict)


def save_config(
    provider: str, config: LLMConfig, config_file: Optional[str] = None
) -> None:
    """
    保存 LLM 配置到文件

    Args:
        provider: Provider 类型
        config: LLMConfig 实例
        config_file: 配置文件路径
    """
    config_path = Path(config_file) if config_file else DEFAULT_CONFIG_FILE
    ensure_config_dir()

    # 读取现有配置
    existing_config = {}
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            if config_path.suffix in [".yaml", ".yml"]:
                existing_config = yaml.safe_load(f) or {}
            elif config_path.suffix == ".json":
                existing_config = json.load(f) or {}

    # 更新配置
    existing_config[provider] = config.dict(exclude_none=True)

    # 写回文件
    with open(config_path, "w", encoding="utf-8") as f:
        if config_path.suffix in [".yaml", ".yml"]:
            yaml.dump(existing_config, f, allow_unicode=True, default_flow_style=False)
        elif config_path.suffix == ".json":
            json.dump(existing_config, f, ensure_ascii=False, indent=2)


def get_default_config_dict() -> Dict[str, Dict[str, Any]]:
    """
    获取默认配置字典（用于生成配置文件模板）

    Returns:
        默认配置字典
    """
    return {
        "doubao": {
            "provider": "doubao",
            "model": "doubao-pro-32k",
            "api_key": "your-doubao-api-key",
            "base_url": "https://ark.cn-beijing.volces.com/api/v3",
            "temperature": 0.7,
            "max_tokens": 4096,
            "timeout": 120,
            "streaming": True,
        },
        "qwen": {
            "provider": "qwen",
            "model": "qwen-max",
            "api_key": "your-dashscope-api-key",
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "temperature": 0.7,
            "max_tokens": 4096,
            "timeout": 120,
            "streaming": True,
        },
        "openai": {
            "provider": "openai",
            "model": "gpt-4",
            "api_key": "your-openai-api-key",
            "base_url": "https://api.openai.com/v1",
            "temperature": 0.7,
            "max_tokens": 4096,
            "timeout": 120,
            "streaming": True,
        },
    }
