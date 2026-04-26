"""
Prompt 模板管理器

负责加载和渲染各类 Agent 的 Prompt 模板
"""
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional


class PromptManager:
    """Prompt 模板管理器"""

    def __init__(self, templates_dir: Optional[str] = None):
        if templates_dir is None:
            templates_dir = Path(__file__).parent / "templates"
        self.templates_dir = Path(templates_dir)
        self._cache: Dict[str, str] = {}

    def get_template(
        self,
        agent_name: str,
        template_type: str
    ) -> str:
        """
        获取 Prompt 模板

        :param agent_name: Agent 名称 (requirement_analyst, tech_architect, etc.)
        :param template_type: 模板类型 (system/context/instruction)
        :return: 模板内容
        """
        cache_key = f"{agent_name}_{template_type}"

        if cache_key not in self._cache:
            template_path = self.templates_dir / agent_name / f"{template_type}.txt"
            if template_path.exists():
                with open(template_path, "r", encoding="utf-8") as f:
                    self._cache[cache_key] = f.read()
            else:
                return ""

        return self._cache.get(cache_key, "")

    def render_template(
        self,
        agent_name: str,
        template_type: str,
        variables: Dict[str, Any]
    ) -> str:
        """
        渲染模板，替换变量

        :param agent_name: Agent 名称
        :param template_type: 模板类型
        :param variables: 变量字典
        :return: 渲染后的内容
        """
        template = self.get_template(agent_name, template_type)

        if not template:
            return json.dumps(variables, ensure_ascii=False, indent=2)

        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            if placeholder in template:
                if isinstance(value, (dict, list)):
                    value_str = json.dumps(value, ensure_ascii=False, indent=2)
                else:
                    value_str = str(value)
                template = template.replace(placeholder, value_str)

        return template

    def get_output_schema(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """获取输出 schema"""
        schema_path = self.templates_dir / agent_name / "output_schema.json"
        if schema_path.exists():
            with open(schema_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None
