# Agent 子系统开发指南

此文档面向 Agent 开发者，概述 `backend/agent` 包的结构、约定和实作须知。你负责实现具体 Agent 逻辑（输入/输出遵循 `contracts.py`）。

## 快速概览

- 位置：`backend/agent`
- 目的：构建可编排的 AI 驱动开发流水线（DevFlow）。
- 设计原则：Agent 产出结构化工件（不直接变更工作区）；副作用（apply patch、运行测试）由 pipeline 层或 `codegen/testing_workflow` 处理。

## 关键模块

- `contracts.py`：所有 Agent 间传递数据的 Pydantic 模型契约（必须遵守）。
- `base.py`：定义 `BaseAgent` 与 `AgentConfig`，Agent 的基类行为与输入/输出校验在此实现。
- `agents/`：对外暴露的 pipeline-facing Agent 适配层（子类化 `BaseAgent` 并实现 `execute(context)`）。
- `codegen/`：代码生成核心（patcher、runner、TestingWorkflow 等），负责实际文件写入与测试执行。
- `llm/`：LLM Provider 抽象与工厂（支持 `doubao`, `qwen`, `openai` 等），通过 `LLMFactory` 构造。
- `workspace/`：提供隔离工作区创建/清理工具 `WorkspaceManager`。
- `self_healing/`：故障回馈、triage 与 retry 管理。
- `callbacks.py`：观测与 tracing 回调（流式输出、token 统计等）。

## Agent 开发约定（必须遵守）

1. 位置与导出
   - 新 Agent 放在 `backend/agent/agents/<your_agent>.py`。
   - Agent 类应继承 `BaseAgent`。

2. 输入/输出契约
   - 在类属性宣言 `input_model` 为对应的 Pydantic 类型（来自 `contracts.py`）。
   - 设置 `output_key`（字符串）和 `output_model`（对应 Pydantic 类型）。
   - `execute(self, context: Dict[str, Any]) -> Dict[str, Any]` 必须返回一个只包含该阶段产物的字典，形如 `{output_key: artifact}`。
   - 在 `execute` 开头调用 `self._validate_input(context)`，返回前调用 `self._validate_output(result)`，以保证契约一致性。

3. 不做副作用（除非文档允许）
   - Agent 不应直接写文件、修改 Git、或执行系统级测试。所有副作用由 `TestingWorkflow` / `codegen` 层或 pipeline orchestration 承担。

4. 获取 repo/workspace
   - 若 Agent 需要访问代码仓（仅读取/检索），从 `context['codebase']['repo_path']` 或在构造时传入 `repo_root`。
   - 若需要在隔离目录运行（apply patch / 测试由其他组件做），使用 `workspace.WorkspaceManager`。

5. 日志与可观测性
   - 使用 `self.logger` 记录关键步骤与异常。
   - LLM 调用可绑定 `TraceCallbackHandler`（`callbacks.py`）以获得 token/耗时追踪。

6. LLM 使用
   - 通过依赖注入接收 `llm_provider`（由 `LLMFactory` 构造）。
   - 避免在 Agent 中硬编码 provider；保持 provider 可替换以便测试。

## 常见 Agent 示例与上下文键

- `RequirementAnalyst` → 输出键 `requirement_structured`（类型 `RequirementStructured`）。
- `TechArchitect` → 输出键 `design`（类型 `Design`），并可能产出 `codebase_context`。
- `CodeGeneratorAgent` → 输出键 `code_diff`（类型 `DiffBundle`）。实现范例见 `agents/code_generator.py`，它在内部复用 `codegen.code_generator.CodeGeneratorAgent`。
- `SDETAgent` → 输出键 `tests`（类型 `TestBundle`），注意 SDET 不直接运行测试。
- `SeniorReviewerAgent` → 输出键 `review`（类型 `Review`）。

这些键名即 pipeline context 中的字段名，编排器会将各阶段产物合并回全局 context。

## TestingWorkflow 配置模板

`SelfHealingCoordinator` 已接入 `context.testing_profile` 与 `context.testing_options`，会在调用 `TestingWorkflow` 时自动合并预设。

读写型测试模板（会写文件时使用，例如历史持久化测试）:

```json
{
   "testing_profile": "read_write",
   "testing_options": {
      "timeout": 300,
      "sandbox_config": {
         "network_disabled": true,
         "read_only": false,
         "cpus": "1",
         "memory": "1g",
         "pids_limit": "256",
         "tmpfs_size": "256m"
      }
   }
}
```

纯只读测试模板（不允许写入仓库挂载目录）:

```json
{
   "testing_profile": "read_only",
   "testing_options": {
      "timeout": 300,
      "sandbox_config": {
         "network_disabled": true,
         "read_only": true,
         "cpus": "1",
         "memory": "512m",
         "pids_limit": "256",
         "tmpfs_size": "256m"
      }
   }
}
```

说明:
- 预设定义在 `backend/agent/codegen/testing_options.py`。
- 若同时传 `testing_options`，会覆盖预设同名字段；`sandbox_config` 做浅层合并。

## Contracts 注意点（选要）

- `DiffBundle`：包含 `patches`（每项为 `Patch`），`patch_format` 可为 `search_replace` / `full_content` / `unified_diff`。
- `TestBundle`：包含 `test_plan`、`test_files`、`runner_commands` 与可选的 `sandbox_result`。
- `Review`：包含 `pass`（别名）、`issues`、`risk_level` 等审查结果。
- `AgentTrace` / `AgentResult`：用于记录 agent 执行元信息（耗时、tokens、重试数等），Agent 实现应在可能发生异常时填充 warnings/trace。

## 测试 Agent 的建议流程

1. 使用一个轻量的 mock LLM provider（实现 `BaseLLMProvider` 的假实现）以固定返回值，便于单元测试。
2. 构造最小 `context`，只包含 `input_model` 所需字段。
3. 在测试中调用 `agent.execute(context)`，断言：
   - 返回字典包含 `output_key`。
   - `output_model` 校验通过（或手动 model_validate）。

示例（伪代码）:

```py
from backend.agent.agents.my_agent import MyAgent
from backend.agent.llm.factory import LLMFactory

llm = LLMFactory.create("doubao", model="dummy")  # 或用 mock
agent = MyAgent(llm_provider=llm)
context = {"requirement_raw": "..."}
result = agent.execute(context)
assert "my_output_key" in result
```

## 开发与调试贴士

- 若 Agent 抛错，pipeline orchestration 层应捕获并将错误送入 `self_healing` 流程（triage + retry）。
- 使用 `TraceCallbackHandler` 打开详细 LLM 调试信息：设置环境变量 `AGENT_TRACE_COMPACT=0` 可查看流式输出与 token 信息。
- 复用 `prompts/templates/*` 中的 system/instruction/context 文件以保证 prompt 的一致性和可审计性。

## 需要扩展的地方（贡献建议）

- 增加 Agent 注册/发现机制，支持配置化 pipeline 模板。
- 提供更多 mock LLM 用于单元测试。
- 增强文档，列出每个 contracts 模型的示例 JSON（便于快速构造 context）。

---

文档已基于 `backend/agent/README.md`、`backend/agent/base.py`、`backend/agent/callbacks.py`、`backend/agent/agents/code_generator.py`、`backend/agent/llm/factory.py` 与 `backend/agent/workspace/manager.py` 汇总而成。如需我把示例测试用例、mock LLM 或 contracts 示例 JSON 一并加入，请告知。
