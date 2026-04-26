# DevFlow Agent 系统 (执行内核)

本目录包含了 DevFlow 研发全流程引擎的 **AI 执行内核 (Execution Kernel)**。Agent 模块不负责流程的流转、状态机的维护和任务的调度，而是作为高度封装的黑盒任务处理器，基于外层 Pipeline 传入的上下文 (`context`) 完成单节点的专业领域任务，并输出结构化的增量数据。

---

## 一、目录结构

```
backend/agent/
├── __init__.py                    # 包导出入口
├── base.py                        # BaseAgent 抽象基类 & AgentConfig
├── callbacks.py                    # TraceCallbackHandler 链路追踪组件
├── agents/                        # 核心 Agent 实现
│   ├── __init__.py
│   ├── requirement_analyst.py     # 需求分析 Agent
│   └── ...                        # 后续扩展：tech_architect, code_generator, etc.
├── prompts/                       # Prompt 模板管理
│   ├── __init__.py
│   ├── manager.py                 # PromptManager 模板管理器
│   ├── common.py                  # 通用 Prompt (重试、纠错等)
│   ├── requirement_analyst.py     # 需求分析 Agent 专属 Prompt
│   └── templates/                 # 模板文件目录(预留)
│       └── requirement_analyst/
│           ├── system.txt
│           ├── context.txt
│           └── output_schema.json
├── llm/                           # LLM Provider 实现
│   ├── __init__.py
│   ├── base.py                    # BaseLLMProvider 抽象接口
│   ├── factory.py                 # LLMFactory 工厂类
│   └── providers/                 # 各 Provider 实现
│       ├── __init__.py
│       ├── doubao.py              # 字节豆包
│       ├── qwen.py                # 阿里通义千问
│       └── openai_compatible.py   # OpenAI 兼容
└── utils/                         # 工具函数
    ├── __init__.py
    ├── code_parser.py             # 代码解析工具
    └── output_parser.py           # 输出解析工具
```

---

## 二、核心架构设计

### 2.1 统一的接口契约 (BaseAgent)

所有 Agent 均继承自 `BaseAgent` 抽象类，对外只暴露一个标准接口：

```python
from agent import RequirementAnalyst

analyst = RequirementAnalyst(llm_provider=llm)

result = analyst.execute({
    "requirement_raw": "我要做一个类似微信的软件"
})

# result 包含:
# - requirement_structured: 结构化需求数据
# - meta_trace: 链路追踪元数据
```

### 2.2 大模型解耦与依赖注入

Agent 内部代码不绑定任何特定厂商 SDK，通过注入的 `llm_provider` 实现零代码切换：

```python
# 支持的 Provider
- Doubao (字节豆包)
- Qwen (通义千问)
- OpenAI Compatible (其他兼容模型)
```

### 2.3 确定性的结构输出

Agent 输出全部通过 Pydantic Model 定义，配合 LLM Structured Output 确保跨节点数据流转的确定性。

---

## 三、核心 Agent 详解

### 3.1 需求分析 Agent (Requirement Analyst)

**角色定位**：资深产品经理

**输入输出**：

| 阶段 | 输入 | 输出 |
|------|------|------|
| 需求分析 | `requirement_raw` | `requirement_structured` |

**输出结构 (RequirementStructured)**：

```python
{
    "is_clear": bool,                    # 需求是否清晰
    "clarifying_questions": [str],       # 澄清问题（当 is_clear=False 时）
    "goal": str,                         # 核心目标
    "features": [str],                   # 功能点列表
    "constraints": [str],                # 非功能约束
    "acceptance_criteria": [str]          # 验收标准
}
```

**执行流程**：

```
输入校验
    ↓
极端短输入拦截 (< 5 字符)
    ↓
Token 数量防爆检测 (> 10000 则拒绝)
    ↓
LLM 调用生成结构化需求
    ↓
JSON 解析
    ↓ [解析失败]
重试自愈机制
    ↓
返回增量 context + meta_trace
```

---

## 四、工业级特性

### 4.1 人机协同与专业追问 (Human-in-the-Loop)

当输入需求严重模糊时，Agent 会：
1. 判定 `is_clear=False`
2. 自动生成 1-3 个选择性启发问题
3. 挂起流程等待用户补充

### 4.2 全景可观测性链路追踪 (Trace & Token Logging)

通过 `TraceCallbackHandler` 实现：
- 流式打字机效果输出
- 精准 Token 数量统计
- 全链路耗时记录
- 出入参快照捕获

### 4.3 隔离的 Prompt 管理架构

Prompt 模板与代码完全解耦：
- `prompts/common.py` - 通用模板（重试、纠错）
- `prompts/requirement_analyst.py` - 专属模板
- `prompts/templates/` - 文件模板（可选）

### 4.4 自动纠错与重试容错 (Self-Healing)

当 JSON 解析失败时，自动触发重试流程：
1. 捕获解析异常
2. 将错误信息 + 原始输出反馈给 LLM
3. 引导模型自我修正
4. 重新解析验证

### 4.5 防提示词注入 (Prompt Injection Guardrails)

通过 XML Style 包裹用户输入，防止恶意指令注入：
```
<user_input>
{requirement_raw}
</user_input>
```

### 4.6 动态防爆限流 (Token Limits & OOM Protection)

- 使用 `tiktoken` 精确计算 Token 数量
- 超过 10000 Token 直接拒绝
- 防止天价账单和 OOM 崩溃

---

## 五、与 Pipeline 引擎对接

```python
from agent import RequirementAnalyst

analyst = RequirementAnalyst(llm_provider=llm)
context = {"requirement_raw": "我要做一个类似微信的软件"}

result = analyst.execute(context)

req_data = result.get("requirement_structured", {})
trace_data = result.get("meta_trace", {})

if not req_data.get("is_clear"):
    # 流程暂停，等待用户补充澄清问题
    pipeline.pause_and_ask_user(req_data.get("clarifying_questions"))
else:
    # 成功处理，进入下一阶段
    context.update(result)
    pipeline.next_stage("tech_architect")
```

**对接优势**：
1. 职责边界极致清晰 - Agent 纯粹作为智力单元
2. 应对不确定性的"降维打击" - LLM 输出强制转换为可编程的 dict
3. 天然拥抱工作流扩展 - 新增 Agent 只需继承 BaseAgent

---

## 六、后续扩展资产

已完成的基础工程设施可供后续 Agent 无缝复用：

| 组件 | 复用方式 |
|------|----------|
| `callbacks.py` | 所有 Agent 使用 `TraceCallbackHandler` 获得监控能力 |
| `prompts/common.py` | JSON 解析失败时复用 `JSON_RETRY_*` 模板 |
| `base.py` | 新 Agent 继承 `BaseAgent` 获得标准接口 |
| Pydantic 结构化输出 | 定义 `XxxStructured(BaseModel)` 即可复用解析逻辑 |

---

## 七、运行与测试

```bash
python -m backend.agent.agents.requirement_analyst
```

或创建测试文件：

```python
# test_requirement_analyst.py
from agent import RequirementAnalyst
from doubao_llm import llm

analyst = RequirementAnalyst(llm_provider=llm)

# 正常需求
result = analyst.execute({"requirement_raw": "我要做一个记账软件，支持收入支出分类和月度报表"})
print(result)

# 模糊需求（触发追问）
result = analyst.execute({"requirement_raw": "微信"})
print(result)
```

---

## 八、依赖项

```
langchain>=0.1.0
langchain-core>=0.1.0
pydantic>=2.0.0
tiktoken>=0.5.0  # 可选，用于精确 Token 计算
```
