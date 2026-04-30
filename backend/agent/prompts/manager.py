"""
Prompt 模板管理器

负责加载和渲染各类 Agent 的 Prompt 模板。

核心功能：
1. 从文件系统加载 Prompt 模板
2. 使用缓存机制避免重复读取
3. 支持模板变量替换（渲染）
4. 提供输出 schema 获取能力

模板文件结构约定：
├── templates/
│   ├── agent_name/
│   │   ├── system.txt          # 系统提示词模板
│   │   ├── context.txt         # 上下文提示词模板
│   │   ├── instruction.txt     # 指令提示词模板
│   │   └── output_schema.json  # 输出格式定义（可选）
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional


class PromptManager:
    """Prompt 模板管理器
    负责管理和渲染各类 Agent 的 Prompt 模板，支持缓存机制以提高性能。
    """

    def __init__(self, templates_dir: Optional[str] = None):
        """初始化 Prompt 管理器。
        Args:
            templates_dir: 模板目录路径。如果为 None，默认使用当前文件所在目录的templates子目录
        """
        # 设置模板目录，默认使用相对路径
        if templates_dir is None:
            templates_dir = Path(__file__).parent / "templates"
        self.templates_dir = Path(templates_dir)
        # 模板缓存，避免重复读取文件
        self._cache: Dict[str, str] = {}

    def get_template(self, agent_name: str, template_type: str) -> str:
        """获取指定 Agent 的 Prompt 模板。
        从文件系统加载模板，支持缓存机制。
        Args:
            agent_name: Agent 名称，如 requirement_analyst、tech_architect、code_generator 等
            template_type: 模板类型，可选值：system（系统提示词）、context（上下文提示词）、instruction（指令提示词）
        Returns:
            模板内容字符串。如果模板文件不存在，返回空字符串
        """
        # 构建缓存键
        cache_key = f"{agent_name}_{template_type}"

        # 如果缓存中不存在，则从文件加载
        if cache_key not in self._cache:
            # 构建模板文件路径：templates/{agent_name}/{template_type}.txt
            template_path = self.templates_dir / agent_name / f"{template_type}.txt"

            if template_path.exists():
                # 读取模板内容并缓存
                with open(template_path, "r", encoding="utf-8") as f:
                    self._cache[cache_key] = f.read()
            else:
                # 文件不存在，返回空字符串
                return ""

        # 返回缓存的模板内容
        return self._cache.get(cache_key, "")

    def render_template(
        self, agent_name: str, template_type: str, variables: Dict[str, Any]
    ) -> str:
        """渲染模板，将变量替换到模板占位符中。
        如果模板文件不存在，直接返回变量的 JSON 序列化结果作为降级策略。
        Args:
            agent_name: Agent 名称
            template_type: 模板类型
            variables: 变量字典，键为占位符名称，值为要替换的内容
        Returns:
            渲染后的提示词字符串
        """
        # 获取原始模板
        template = self.get_template(agent_name, template_type)
        # 如果模板不存在，降级为直接输出变量的 JSON 格式
        if not template:
            return json.dumps(variables, ensure_ascii=False, indent=2)

        # 遍历变量，替换模板中的占位符
        for key, value in variables.items():
            # 占位符格式为 {{variable_name}}
            placeholder = f"{{{{{key}}}}}"

            if placeholder in template:
                # 根据变量类型进行序列化
                if isinstance(value, (dict, list)):
                    value_str = json.dumps(value, ensure_ascii=False, indent=2)
                else:
                    value_str = str(value)

                # 替换占位符
                template = template.replace(placeholder, value_str)

        return template

    def get_output_schema(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """获取指定 Agent 的输出 schema 定义。
        Args:
            agent_name: Agent 名称
        Returns:
            输出 schema 的字典表示，如果文件不存在则返回 None
        """
        # 构建 schema 文件路径：templates/{agent_name}/output_schema.json
        schema_path = self.templates_dir / agent_name / "output_schema.json"

        if schema_path.exists():
            with open(schema_path, "r", encoding="utf-8") as f:
                return json.load(f)

        return None
