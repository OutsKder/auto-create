"""
sdet.py

正式的测试生成 Agent 入口适配层。

职责：
- 从 Pipeline context 中读取上下文并委托给 `backend.agent.codegen.sdet.SDETAgent`
- 保持与其他 Agent 一致的对外接口
- 让 `agent/agents` 继续作为统一编排入口，而把测试生成细节隔离在 `agent/codegen`

架构设计：
- 本类作为适配器模式的外层，提供统一的 Agent 接口
- 核心测试生成逻辑委托给 CoreSDETAgent 实现
- 便于未来替换或扩展测试生成策略
"""

from __future__ import annotations

from typing import Any, Dict

from ..base import BaseAgent, AgentConfig
from ..codegen.sdet import SDETAgent as CoreSDETAgent


class SDETAgent(BaseAgent):
    """测试生成 Agent 的对外入口。
    这是 SDET（Software Development Engineer in Test）Agent 的适配层，
    负责将测试生成请求委托给核心实现类。
    设计模式：适配器模式
    - 对外：提供统一的 Agent 接口（继承自 BaseAgent）
    - 对内：委托给 CoreSDETAgent 执行实际的测试生成逻辑
    """

    def __init__(self, llm_provider: Any, config: AgentConfig | None = None):
        """初始化 SDET Agent。
        Args:
            llm_provider: LLM 服务提供者，用于调用大语言模型生成测试代码
            config: Agent 配置对象，包含测试生成的相关配置参数
        """
        super().__init__(llm_provider, config)

    def get_input_keys(self):
        """获取 Agent 所需的输入键列表。
        Returns:
            输入键列表：
            - code_diff: 代码变更包，包含需要测试的代码修改
            - requirement_structured: 结构化需求，包含验收标准和测试要求
        """
        return ["code_diff", "requirement_structured"]

    def get_output_key(self):
        """获取 Agent 输出的键名。
        Returns:
            输出键名：tests（测试包）
        """
        return "tests"

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行测试生成的主入口方法。
        执行流程：
        1. 验证输入参数
        2. 创建核心SDET Agent实例
        3. 委托执行测试生成逻辑
        4. 返回测试结果
        Args:
            context: 包含输入数据的上下文字典，必须包含 code_diff 和 requirement_structured
        Returns:
            包含测试包的字典，键为 tests
        """
        # 验证输入参数是否完整
        self._validate_input(context)

        # 创建核心 SDET Agent 实例，委托实际的测试生成逻辑
        core_agent = CoreSDETAgent(llm_provider=self.llm, config=self.config)

        # 同步直接运行策略：如果外部未提供 codebase.repo_path，
        # 尝试从 agent config 中读取（若 config 中包含该字段）并补入上下文，
        # 以便 CoreSDETAgent 能直接将生成的测试文件写入并运行。
        if "codebase" not in context or not context.get("codebase", {}).get(
            "repo_path"
        ):
            cfg_repo = None
            try:
                cfg_repo = getattr(self.config, "repo_path", None)
            except Exception:
                cfg_repo = None
            if cfg_repo:
                context.setdefault("codebase", {})["repo_path"] = str(cfg_repo)

        # 执行测试生成并返回结果（CoreSDETAgent 已实现直接运行逻辑）
        return core_agent.execute(context)
