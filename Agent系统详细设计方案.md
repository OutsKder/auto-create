# DevFlow Agent 系统详细设计方案（执行内核）

## 一、 系统定位与架构边界

在整个 DevFlow 研发流程引擎中，Agent 系统充当**“执行内核” (Execution Kernel)** 的角色。

- **核心职责**：
  - 定义标准的 Agent 接口契约。
  - 实现 5 个核心阶段的智能 Agent（需求分析、方案设计、代码生成、测试生成、代码评审）。
  - 沉淀和管理领域 Prompt 模板。
  - 支持多 LLM Provider（模型解耦，支持自由切换）。
- **明确系统边界（不做的部分）**：
  - **不负责状态转换与调度**：流程状态的流转（如 `PENDING` -> `RUNNING` -> `DONE`）由 Pipeline Engine（如 LangGraph/状态机实现）控制。
  - **不负责中断恢复和持久化**：Agent 作为一个黑盒纯函数（或局部状态对象），每次执行基于 Pipeline 传入的 `context`，仅负责输出其负责阶段的增量数据结果。
  - **不处理 Human-in-the-Loop 的挂起**：Agent 生成结果即结束工作，流转与暂停让人类审批（Approval）由外层管道接管。

---

## 二、 交互契约与接口设计

Agent 层与 Pipeline Engine 层之间通过一个大 JSON / 字典对象 `context` 进行数据通信。所有 Agent 均实现同一个基础接口。

### 1. Agent 基础接口 (Base Agent)

```python
from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseAgent(ABC):
    def __init__(self, llm_provider: Any, config: Dict[str, Any] = None):
        """
        初始化 Agent
        :param llm_provider: 统一的大模型提供者实例 (如基于 LangChain 的 ChatModel)
        :param config: 该 Agent 特有的配置参数
        """
        self.llm = llm_provider
        self.config = config or {}

    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行阶段任务，消费上下文，产出增量上下文
        :param context: Pipeline 传入的全局全量上下文
        :return: 仅含有该阶段计算产物的一个字典，Pipeline 会负责将其 Merge 回总 context
        """
        pass
```

---

## 三、 五大核心 Agent 详细设计

### 1. 需求分析 Agent (Requirement Analyst)

- **职责扮演**：资深产品经理。
- **输入提取**：`context["requirement_raw"]`
- **处理逻辑**：
  - 运用 LLM 强大的理解能力，对自然语言输入进行拆解。
  - 识别潜在的边界条件、模糊点，转化为结构化需求。
  - 强制输出 JSON（结合 LLM Tool Calling 或 Structured Output）。
- **输出契约**（更新到 Pipeline 的键）：`requirement_structured`
- **输出结构**：包含 `goal` (核心目标), `features` (功能点列表), `constraints` (约束), `acceptance_criteria` (验收标准)。

### 2. 方案设计 Agent (Tech Architect)

- **职责扮演**：高级架构师。
- **输入提取**：`context["requirement_structured"]` + 本地代码库。
- **处理逻辑**：
  - 若代码库较大，通过语义检索引擎（提供工具链给 LLM）提取出受需求影响的代码文件，组装成 `codebase_context`。
  - 结合代码现状，设计技术方案。
  - 明确输出详细的文件变更列表 (`file_change_plan`)：哪些文件需修改、哪些需新建。
- **输出契约**：`design`
- **输出结构**：包含 `architecture`, `api_design`, `file_change_plan`, `risk_analysis`。
- _(注：此 Agent 返回后，Pipeline Engine 会暂停并等待用户审批)_。

### 3. 代码生成 Agent (Code Generator Executer)

- **职责扮演**：全栈程序员。
- **输入提取**：`requirement_structured` + `design` (特别是 file_change_plan)。
- **处理逻辑**：
  - 遍历 `file_change_plan`，针对指定文件，生成变更后的代码。
  - 结合 AST 工具或精准的语法替换手段（或者直接输出完整的 Git Diff），将模型输出映射为具体的文本变更集。
- **输出契约**：`code_diff`
- **输出结构**：包含被修改的文件列表及 `diff` 字符串。

### 4. 测试生成 Agent (Test Engineer)

- **职责扮演**：测试开发工程师 SDET。
- **输入提取**：`code_diff` + `requirement_structured` (特别是 AC)。
- **处理逻辑**：
  - 根据代码的输入输出变更，针对性编写覆盖用例（Unit Tests）。
  - 若包含集成逻辑，编写简单的集成测试脚本。
  - （可选扩展）调用沙盒环境执行测试，并解析通过率及日志。
- **输出契约**：`tests`
- **输出结构**：包含 `unit_tests`, `test_results`。

### 5. 代码评审 Agent (Senior Reviewer)

- **职责扮演**：技术委员会评审专家。
- **输入提取**：`code_diff` + `design` + `tests`。
- **处理逻辑**：
  - **规范维度**：检查代码异味、圈复杂度、规范符合度。
  - **安全维度**：检查潜在的内存泄漏、注入风险、并发死锁等。
  - **业务一致性**：判断该 Diff 是否真实响应了初始方案设计，是否有多余的无关改动。
  - 综合产出评分、修改建议，给出结论（Pass 或 Fail）。
- **输出契约**：`review`
- **输出结构**：包含 `issues`, `suggestions`, `risk_level`, `pass`。

---

## 四、 多 LLM Provider 支持机制

为了保证模型解耦并贴近实际工业使用规范，基于 LangChain 的底层逻辑实现以下扩展：

1. **统一的工厂模式**：设计 `LLMFactory` 根据配置文件动态生成不同平台的 `BaseChatModel`。
2. **支持的模型矩阵**：
   - 字节豆包模型 (Doubao-pro-32k/128k)：作为默认基础提供商。
   - 阿里通义千问 (Qwen-Max/Plus)：提供强大的代码逻辑能力。
   - 其它兼容 OpenAI 接口的模型。
3. **隔离机制**：各个 Agent 代码中不出现任何大模型厂商的专有 SDK 调用，全部依托一套 `invoke(messages)` 与 `with_structured_output()` 标准接口。

---

## 五、 Prompt 模板设计与管理

脱离 Hardcode，采用集中的模块化管理 (建议放置于 `prompts/` 目录)。采用“三个维度”构建高质量的 Prompt：

1. **System Prompt (基座人设)**
   - 设定“你是谁，你要遵守什么禁忌”。例如给评审 Agent 设定极其严格的审查标准。
2. **Context Prompt (动态上下文)**
   - 每次调用使用 Jinja2/f-string 注入当前的 `context` 数据（如目前在修改的仓库语言是 TypeScript，目前的需求是...）。
3. **Format/Instruction Prompt (格式与任务指令)**
   - 告诉模型现在该生成什么格式，如 XML tag、JSON 等，确保返回内容可被下一环节机器解析。
