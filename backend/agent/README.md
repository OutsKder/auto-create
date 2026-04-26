# DevFlow Agent 系统 (执行内核)

本目录包含了 DevFlow 研发全流程引擎的 **AI 执行内核 (Execution Kernel)**。Agent 模块不负责流程的流转、状态机的维护和任务的调度，而是作为高度封装的黑盒任务处理器，基于外层 Pipeline 传入的上下文 (`context`) 完成单节点的专业领域任务，并输出结构化的增量数据。

## 一、技术架构设计

1. **统一的接口契约 (`BaseAgent`)**
   所有维度的 Agent（如需求分析、方案设计、代码生成、测试开发、代码评审）均继承自 `BaseAgent` 抽象类，对外只暴露一个标准且一致的接口：`execute(context: Dict) -> Dict`。
2. **大模型解耦与依赖注入 (LLM Provider Injection)**
   Agent 内部代码绝对不绑定抖音、阿里、OpenAI 等特定厂商的特有 SDK。而是依赖注入遵循 LangChain 标准协议的 `BaseChatModel`。只需在外层改变 `llm_provider` 的实例，即可实现千问、豆包等模型的零代码改造切换。
3. **确定性的结构输出 (Structured Output via Pydantic)**
   传统的 LLM 具有高度不确定性。为了在工程流水线中做到 100% 数据接住，Agent 的输出契约全部通过 `pydantic.BaseModel` 定义。配合强指令（Format Instructions）保证模型输出跨节点数据流转时的极其确定性。

## 二、系统核心技术亮点

目前的 Agent 模块（以 `RequirementAnalyst` 为例）引入了极具工业级竞争力的强悍特性：

- **人机协同与专业追问 (Human-in-the-Loop & Clarification)**
  不仅把自然语言“翻译”成需求，更引入了一套宽容但有底线的评估体系。当输入的需求严重模糊或缺失业务闭环时，Agent 会将其判定为不可用 (`is_clear=False`)并自动挂起流程，提出 1-3 个选择性启发问题（`clarifying_questions`）向用户索取信息。在此过程中，Agent 会基于同理心和行业常识，尽可能为缺少细则的小白用户补全业务闭环。
- **全景可观测性链路追踪 (Trace & Token Logging)**
  在底层大模型交互中，我们通过自定义 `TraceCallbackHandler` 实现了极致的可观测性。不仅支持了打字机般的流式输出体验，还隐式构建了全链路数据埋点。每次调用所消耗的时间、精准的 Token 数量（包括 Prompt 和 Completion，并附带针对流式调用的“三重跌落兜底”计算机制）以及出入参快照（`prompts_snapshot`、`completion_snapshot`）均被完整捕获并打包在 `meta_trace` 中，供上层流水线溯源、核算成本或在前端仪表盘展示。
- **隔离的 Prompt 管理架构 (Prompt Decoupling)**
  将以往硬编码在 Python 逻辑中的长篇系统设定与提示词彻底剥离，统一收敛至 `backend/agent/prompt/` 目录下（如 `requirement_analyst_prompt.py`、`common_prompt.py`）。这种高内聚低耦合的模型隔离感，使得团队中的 Prompt Engineer 能够安全、独立地进行提示词调优，而无需担忧破坏核心业务逻辑。
- **自动纠错与重试容错 (Self-Healing / Retry Parsing)**
  大模型偶尔会输出非法的 JSON（例如漏掉括号或添加了 Markdown 标识），这在传统的流水线中会导致灾难性崩溃。我们在底层实现了一套原生的**重试自愈机制**。当 Pydantic 解析异常时，自动触发重试流程：将【格式要求】、【出错的字符串】与【错误异常栈】反哺给 LLM 勒令其自行修复，极大地提升了系统的存活率与鲁棒性。
- **防提示词注入隔离 (Prompt Injection Guardrails)**
  面对不可信的外部输入信息，在底层架构引入 XML Style 或显式区间的包裹(`<user_input>`)，结合强硬的系统级隔离声明，抵御针对后续 DevOps 和代码层面的恶意 Prompt Attack。
- **动态防爆限流体系 (Token Limits & OOM Protection)**
  借助 `tiktoken`（或降级字数计算）在真正发入 LLM 前进行 Tokens 预估测算。当输入字符串超出安全阈值（如 `10000` Tokens）时，直接从业务层阻断请求并抛出清晰的错误提示，彻底防止天价账单和 OOM 崩溃。

## 三、与 Pipeline 引擎的对接方式及优势

在外层使用 StateMachine (状态机) 或 LangGraph 等 Pipeline 引擎时，与当前 Agent 的交互极其简单，呈现出极强的数据流式处理能力：

```python
from agent.requirement_analyst import RequirementAnalyst
# 假设 llm 是一个全局或工厂创建的 LangChain ChatModel 实例，开启了 streaming=True
from doubao_llm import llm

# 1. 在 Pipeline 的某个 Stage 处实例化对应的执行 Agent
analyst = RequirementAnalyst(llm_provider=llm)

# 2. Pipeline 提供并组织当前时刻的全局参数
current_context = {
    "requirement_raw": "我要做一个类似微信的软件"
}

# 3. 将上下文传入 Agent 执行
# 这里 Agent 内部会触发 Trace 回调，实现流式输出并捕获元数据
result = analyst.execute(current_context)

# 4. Pipeline 根据 Agent 的标准契约决定系统流转状态
req_data = result.get("requirement_structured", {})
trace_data = result.get("meta_trace", {})

# 可以将 trace_data 落库，用于在前端面板展示该节点的 Token 消耗和耗时
save_to_db(trace_data)

if not req_data.get("is_clear"):
    # 【高光时刻：多次追问挂起】Pipeline 将状态设为 WAITING_INPUT / PENDING_USER
    # 并将澄清问题推送给前端，等待用户补充后再重新执行本阶段
    pipeline.pause_and_ask_user(req_data.get("clarifying_questions"))
else:
    # 成功处理，将此阶段的结构化高价值增量更新汇入主数据总线，放行进入下一 Stage
    current_context.update(result)
    pipeline.next_stage("tech_architect")
```

**这种对接方式的设计优势：**

1. **职责边界极致清晰**：Agent 层纯粹作为算力与智力单元（接收信息 -> 施加 Prompt 智能加工 -> 产出标准化积木块），绝不关心流程流到了哪一步，保证了单元的可替换性和极简的单元测试。
2. **应对不确定性的“降维打击”**：把大语言模型的“自由发散”强制压缩成可编程的 `dict/JSON` 和 `is_clear` 状态标。外部 Pipeline 看 LLM 不再是一个黑盒的对话框，而是一个有着明确布尔出口和预构体接口的**微服务模块**。
3. **天然拥抱工作流扩展**：当产研工作流需要增加 `UI Designer` 节点时，只需新建继承 `BaseAgent` 的类，配置相应的输入输出 Schema，然后插入 Pipeline 的列表数组中即可，核心架构无需伤筋动骨。

## 四、后续 Agent 可继承的沉淀资产

这套 `RequirementAnalyst` 所跑通的基础工程设施，将成为后续所有研发节点 Agent（如 `Tech Architect`, `Coder Agent`, `Reviewer`）可直接无缝继承的庞大资产池：

1. **`callbacks.py` -> 链路追踪组件**：所有后续 Agent 在使用 `invoke` 时挂载 `TraceCallbackHandler`，免费获得流式打印、耗时记录和精准 Tokens 结算的监控面板，保证整个流水线全程透明可见。
2. **`common_prompt.py` -> 纠错自愈兜底基石**：Tech Architect 生产表结构 JSON、Coder 生成文件层级 JSON 时，如果发生解析撕裂，直接引用 `JSON_RETRY_SYSTEM_PROMPT` 唤起自愈程序。
3. **Pydantic 结构化卡口范式**：后续 Agent 只需撰写自身的 `XxxStructured(BaseModel)`，并复用底层 `try-except` 包裹的 `self.parser.parse()` 逻辑，就能像工厂流水线模具一样，把模糊的响应压断并强转成字典对象装车推给下一环。
4. **统一的大模型实例桥接方案**：基于 LangChain `ChatOpenAI` 桥接统一封装的模型实例入口，后续所有的 Agent 都不用再重新实现发包逻辑或对接各类国产/开源大模型的 HTTP 请求协议。

## 四、运行与测试

通过以下指令执行专门针对“需求分析 Agent”构建的测试用例：
测试包含了正常复杂需求的【高分拆解能力】与垃圾模糊需求的【追问拦截与格式自愈能力】。

```bash
python backend/test_requirement_analyst.py
```

_(运行前请确保当前 Python 环境变量中已安装 `langchain`, `langchain-core` 以及 `pydantic`，且通过 `doubao_llm.py` 配置好了可用的大模型秘钥 / API endpoint)。_
