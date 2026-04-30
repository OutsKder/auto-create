# DevFlow Agent 系统详细设计方案

## 一、系统定位与架构边界

### 1.1 核心定位

在整个 DevFlow 研发流程引擎中，Agent 系统充当**「执行内核」(Execution Kernel)** 的角色。Pipeline Engine 负责流程编排与状态流转，Agent 系统专注于各阶段的具体执行任务。

### 1.2 核心职责

- 定义标准的 Agent 接口契约
- 实现 5 个核心阶段的智能 Agent（需求分析、方案设计、代码生成、测试生成、代码评审）
- 沉淀和管理领域 Prompt 模板
- 支持多 LLM Provider（模型解耦，支持自由切换）

### 1.3 明确系统边界

| 职责                   | 负责方          |
| ---------------------- | --------------- |
| 状态转换与调度         | Pipeline Engine |
| Agent 执行与决策       | Agent 系统      |
| 中断恢复和持久化       | Pipeline Engine |
| Human-in-the-Loop 挂起 | Pipeline Engine |

**Agent 定位**：作为纯函数或局部状态对象，每次执行基于 Pipeline 传入的 `context`，仅负责输出其负责阶段的增量数据结果。

---

## 二、目录结构

```
backend/
├── agent/
│   ├── __init__.py
│   ├── base.py                 # BaseAgent 抽象基类
│   ├── factory.py              # AgentFactory 工厂类
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── base.py             # LLM Provider 接口定义
│   │   ├── factory.py          # LLMFactory 工厂
│   │   └── providers/
│   │       ├── __init__.py
│   │       ├── doubao.py       # 字节豆包 provider
│   │       ├── qwen.py         # 阿里通义千问 provider
│   │       └── openai_compatible.py  # OpenAI 兼容 provider
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── requirement_analyst.py   # 需求分析 Agent
│   │   ├── tech_architect.py        # 方案设计 Agent
│   │   ├── code_generator.py        # 代码生成 Agent
│   │   ├── test_engineer.py         # 测试生成 Agent
│   │   └── senior_reviewer.py       # 代码评审 Agent
│   ├── prompts/
│   │   ├── __init__.py
│   │   ├── manager.py           # Prompt 模板管理器
│   │   └── templates/
│   │       ├── requirement_analyst/
│   │       │   ├── system.txt
│   │       │   ├── context.json
│   │       │   └── output_schema.json
│   │       ├── tech_architect/
│   │       ├── code_generator/
│   │       ├── test_engineer/
│   │       └── senior_reviewer/
│   └── utils/
│       ├── __init__.py
│       ├── code_parser.py      # 代码解析工具
│       └── output_parser.py    # 输出解析工具
├── pipeline/
│   ├── __init__.py
│   ├── engine.py               # Pipeline Engine
│   └── context.py              # Context 定义
└── config/
    ├── __init__.py
    └── agent_config.yaml       # Agent 配置文件
```

---

## 三、交互契约与接口设计

### 3.1 Context 数据结构

```python
# context = {
#     # ======================
#     # 1️⃣ 原始需求
#     # ======================
#     "requirement_raw": "",
#     "codebase": {
#         "repo_id": "",
#         "repo_name": "",
#         "repo_path": "",
#         "branch": "main"
#     },
#
#     # ======================
#     # 2️⃣ 需求分析产物
#     # ======================
#     "requirement_structured": {
#         "goal": "",
#         "features": [],
#         "constraints": [],
#         "acceptance_criteria": []
#     },
#
#     # ======================
#     # 3️⃣ 代码库上下文
#     # ======================
#     "codebase_context": {
#         "query": "",
#         "files": [{"path": "", "content": ""}]
#     },
#
#     # ======================
#     # 4️⃣ 方案设计
#     # ======================
#     "design": {
#         "architecture": "",
#         "modules": [],
#         "api_design": [],
#         "file_change_plan": [],
#         "risk_analysis": ""
#     },
#
#     # ======================
#     # 5️⃣ 代码生成
#     # ======================
#     "code_diff": {
#         "files_changed": [],
#         "diff": ""
#     },
#
#     # ======================
#     # 6️⃣ 测试
#     # ======================
#     "tests": {
#         "unit_tests": "",
#         "integration_tests": "",
#         "test_results": {"passed": False, "logs": ""}
#     },
#
#     # ======================
#     # 7️⃣ 评审
#     # ======================
#     "review": {
#         "issues": [],
#         "suggestions": [],
#         "risk_level": "low",
#         "pass": False
#     },
#
#     # ======================
#     # 8️⃣ 交付
#     # ======================
#     "delivery": {
#         "final_diff": "",
#         "summary": "",
#         "mr_url": ""
#     }
# }
```

### 3.2 BaseAgent 抽象基类

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel

class AgentConfig(BaseModel):
    """Agent 配置模型"""
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 120
    retry_count: int = 3

class BaseAgent(ABC):
    """Agent 基类，定义标准接口"""

    def __init__(
        self,
        llm_provider: Any,
        config: Optional[AgentConfig] = None,
        prompt_manager: Any = None
    ):
        self.llm = llm_provider
        self.config = config or AgentConfig()
        self.prompt_manager = prompt_manager

    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行阶段任务，消费上下文，产出增量上下文

        :param context: Pipeline 传入的全局上下文
        :return: 仅含有该阶段计算产物的一个字典
        """
        pass

    @abstractmethod
    def get_input_keys(self) -> list[str]:
        """返回该 Agent 需要的输入键列表"""
        pass

    @abstractmethod
    def get_output_key(self) -> str:
        """返回该 Agent 输出的键名"""
        pass

    def _validate_input(self, context: Dict[str, Any]) -> None:
        """验证输入是否包含必要的键"""
        required_keys = self.get_input_keys()
        missing_keys = [k for k in required_keys if k not in context]
        if missing_keys:
            raise ValueError(
                f"Agent {self.__class__.__name__} missing required keys: {missing_keys}"
            )

    def _invoke_llm(
        self,
        messages: list[Dict[str, str]],
        output_schema: Optional[BaseModel] = None
    ) -> Any:
        """
        统一的 LLM 调用方法

        :param messages: 对话消息列表
        :param output_schema: 结构化输出 schema（可选）
        :return: LLM 响应
        """
        if output_schema:
            return self.llm.with_structured_output(output_schema).invoke(messages)
        return self.llm.invoke(messages)
```

---

## 四、五大核心 Agent 详细设计

### 4.1 需求分析 Agent (Requirement Analyst)

```python
class RequirementAnalystAgent(BaseAgent):
    """需求分析 Agent - 扮演资深产品经理"""

    def get_input_keys(self) -> list[str]:
        return ["requirement_raw", "codebase"]

    def get_output_key(self) -> str:
        return "requirement_structured"

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        self._validate_input(context)

        system_prompt = self.prompt_manager.get_template(
            "requirement_analyst",
            "system"
        )
        context_prompt = self.prompt_manager.render_template(
            "requirement_analyst",
            "context",
            {
                "requirement_raw": context["requirement_raw"],
                "repo_name": context["codebase"].get("repo_name", ""),
            }
        )
        instruction_prompt = self.prompt_manager.get_template(
            "requirement_analyst",
            "instruction"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{context_prompt}\n\n{instruction_prompt}"}
        ]

        output_schema = self.prompt_manager.get_output_schema(
            "requirement_analyst"
        )

        result = self._invoke_llm(messages, output_schema)

        return {"requirement_structured": result.model_dump()}
```

**Prompt 模板设计**：

- **System**: 设定 Agent 角色为资深产品经理，强调需求分析的逻辑性和结构性
- **Context**: 注入原始需求和代码库信息
- **Output Schema**: 定义结构化需求输出格式

**输出结构**：

```python
{
    "goal": str,                    # 核心目标
    "features": [                  # 功能点列表
        {
            "name": str,
            "description": str,
            "priority": str,       # high/medium/low
            "acceptance_criteria": [str]
        }
    ],
    "constraints": [str],           # 约束条件
    "acceptance_criteria": [str],   # 验收标准
    "assumptions": [str],           # 假设条件
    "risks": [str]                 # 潜在风险
}
```

---

### 4.2 方案设计 Agent (Tech Architect)

```python
class TechArchitectAgent(BaseAgent):
    """方案设计 Agent - 扮演高级架构师"""

    def __init__(self, *args, code_retriever: Any = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.code_retriever = code_retriever  # 代码检索器

    def get_input_keys(self) -> list[str]:
        return ["requirement_structured", "codebase", "codebase_context"]

    def get_output_key(self) -> str:
        return "design"

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        self._validate_input(context)

        # 如果没有代码库上下文，先检索
        if "codebase_context" not in context or not context["codebase_context"]["files"]:
            context["codebase_context"] = self._retrieve_codebase_context(context)

        system_prompt = self.prompt_manager.get_template("tech_architect", "system")
        context_prompt = self.prompt_manager.render_template(
            "tech_architect",
            "context",
            {
                "requirement_structured": context["requirement_structured"],
                "codebase_context": context["codebase_context"],
            }
        )
        instruction_prompt = self.prompt_manager.get_template(
            "tech_architect",
            "instruction"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{context_prompt}\n\n{instruction_prompt}"}
        ]

        output_schema = self.prompt_manager.get_output_schema("tech_architect")
        result = self._invoke_llm(messages, output_schema)

        return {"design": result.model_dump()}

    def _retrieve_codebase_context(
        self,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """检索代码库上下文"""
        if not self.code_retriever:
            return {"query": "", "files": []}

        requirement = context["requirement_structured"]
        query = f"{requirement.get('goal', '')} {' '.join(requirement.get('features', []))}"

        files = self.code_retriever.retrieve(
            query=query,
            repo_path=context["codebase"].get("repo_path", ""),
            top_k=10
        )

        return {"query": query, "files": files}
```

**输出结构**：

```python
{
    "architecture": str,           # 架构描述
    "modules": [                   # 模块设计
        {
            "name": str,
            "responsibility": str,
            "dependencies": [str]
        }
    ],
    "api_design": [               # API 设计
        {
            "endpoint": str,
            "method": str,
            "request_schema": dict,
            "response_schema": dict
        }
    ],
    "file_change_plan": [          # 文件变更计划
        {
            "file_path": str,
            "action": str,         # create/update/delete
            "description": str,
            "priority": str
        }
    ],
    "risk_analysis": str,          # 风险分析
    "estimated_complexity": str    # 预估复杂度
}
```

---

### 4.3 代码生成 Agent (Code Generator)

```python
class CodeGeneratorAgent(BaseAgent):
    """代码生成 Agent - 扮演全栈程序员"""

    def get_input_keys(self) -> list[str]:
        return ["requirement_structured", "design", "codebase_context"]

    def get_output_key(self) -> str:
        return "code_diff"

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        self._validate_input(context)

        design = context["design"]
        file_change_plan = design.get("file_change_plan", [])

        generated_files = []
        all_diffs = []

        for file_plan in file_change_plan:
            result = self._generate_single_file(context, file_plan)
            generated_files.append(result["file_path"])
            all_diffs.append(result["diff"])

        return {
            "code_diff": {
                "files_changed": generated_files,
                "diff": "\n".join(all_diffs),
                "details": [
                    {"file_path": fp["file_path"], "action": fp["action"]}
                    for fp in file_change_plan
                ]
            }
        }

    def _generate_single_file(
        self,
        context: Dict[str, Any],
        file_plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成单个文件"""
        system_prompt = self.prompt_manager.get_template(
            "code_generator",
            "system"
        )
        context_prompt = self.prompt_manager.render_template(
            "code_generator",
            "context",
            {
                "requirement_structured": context["requirement_structured"],
                "file_plan": file_plan,
                "codebase_context": context.get("codebase_context", {}),
            }
        )
        instruction_prompt = self.prompt_manager.get_template(
            "code_generator",
            "instruction"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{context_prompt}\n\n{instruction_prompt}"}
        ]

        output_schema = self.prompt_manager.get_output_schema("code_generator")
        result = self._invoke_llm(messages, output_schema)

        return result.model_dump()
```

**输出结构**：

```python
{
    "code_diff": {
        "files_changed": [str],    # 文件路径列表
        "diff": str,               # Git diff 格式字符串
        "details": [               # 详细变更
            {
                "file_path": str,
                "action": str,     # create/update/delete
                "old_content": str,
                "new_content": str,
                "language": str
            }
        ]
    }
}

---

更新说明（与 Diff/Test 契约同步）:

- 输出必须遵循结构化 Diff Bundle，便于机器应用、审计与测试回放。
- 推荐模型输出采用局部 Search/Replace 补丁协议（见下），并在外层封装为 `patches` 数组。

Search / Replace 补丁协议示例：

```

FILE: path/to/file.py
<<<<<<< SEARCH
旧代码块
=======
新代码块

> > > > > > > REPLACE

````

结构化 `code_diff` 建议格式（Diff Bundle）：

```json
{
    "stage": "coding",
    "mode": "diff_bundle",
    "files_changed": ["backend/app/service.py"],
    "patches": [
        {
            "file_path": "backend/app/service.py",
            "change_type": "modify",
            "patch_format": "search_replace",
            "patch": "FILE: backend/app/service.py\n<<<<<<< SEARCH\n...\n=======\n...\n>>>>>>> REPLACE",
            "reason": "实现技术方案中的新增校验逻辑",
            "risk_level": "low"
        }
    ],
    "diff": "git diff --no-index style text",
    "validation": {
        "static_checks": ["syntax", "format", "targeted_lint"],
        "runtime_checks": []
    }
}
````

要点：

- `files_changed` 用于权限与审计控制；Agent 不得超出这些文件的修改范围（由 Pipeline / 工厂层强制）。
- `patches` 是机器可回放的单元；执行器应逐个应用并校验回退能力。
- `diff` 便于人工 Review 与 Review Agent 输入。
- `validation` 记录本轮已做的静态/运行检查，便于 Triage。

````

---

### 4.4 测试生成 Agent (Test Engineer)

```python
class TestEngineerAgent(BaseAgent):
    """测试生成 Agent - 扮演测试开发工程师 SDET"""

    def get_input_keys(self) -> list[str]:
        return ["code_diff", "requirement_structured"]

    def get_output_key(self) -> str:
        return "tests"

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        self._validate_input(context)

        system_prompt = self.prompt_manager.get_template("test_engineer", "system")
        context_prompt = self.prompt_manager.render_template(
            "test_engineer",
            "context",
            {
                "code_diff": context["code_diff"],
                "acceptance_criteria": context["requirement_structured"].get(
                    "acceptance_criteria", []
                ),
            }
        )
        instruction_prompt = self.prompt_manager.get_template(
            "test_engineer",
            "instruction"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{context_prompt}\n\n{instruction_prompt}"}
        ]

        output_schema = self.prompt_manager.get_output_schema("test_engineer")
        result = self._invoke_llm(messages, output_schema)

        return {"tests": result.model_dump()}
````

**输出结构**：

````python
{
    "tests": {
        "unit_tests": str,          # 单元测试代码
        "integration_tests": str,   # 集成测试代码
        "test_files": [             # 测试文件列表
            {
                "file_path": str,
                "test_type": str,   # unit/integration
                "coverage": [str]  # 覆盖的函数/方法
            }
        ],
        "test_results": {
            "passed": bool,
            "total_cases": int,
            "passed_cases": int,
            "failed_cases": int,
            "logs": str
        }
    }
}

---

更新说明（与 Diff/Test 契约同步）:

- `tests` 输出应为结构化 Test Bundle，包含 `test_plan`、`test_files`、`test_code`、`runner_commands` 与 `sandbox_result`。
- `runner_commands` 是 Runner 的直接输入；Runner 在沙盒中执行后必须返回 `sandbox_result`，包含 `passed`、`exit_code` 与详细 `logs`。

推荐 `tests` 结构示例：

```json
{
    "stage": "testing",
    "test_plan": [
        {
            "acceptance_criterion": "用户可以成功创建任务",
            "test_type": "unit",
            "coverage_target": ["create_task", "validate_input"]
        }
    ],
    "test_files": [
        {
            "file_path": "tests/test_task_service.py",
            "test_type": "unit",
            "covers": ["create_task"]
        }
    ],
    "test_code": "...",
    "runner_commands": ["pytest tests/test_task_service.py -q"],
    "sandbox_result": {
        "passed": false,
        "exit_code": 1,
        "logs": "..."
    }
}
````

要点：

- 测试 Agent 不改业务代码，仅输出测试资产；若测试暴露问题，回路由 CodeGen Agent 最小修复。
- 所有外部依赖必须 mock；Runner 必须在隔离容器中执行。
- `sandbox_result` 是 Triage 的主要输入，必须尽可能保留原始 stdout/stderr 与 exit_code 以便分类错误类型。

---

以上修改将 4.3 与 4.4 节的接口说明与 `backend/agent/temp/agent3/代码生成agent设计方案.md` 中定义的 Diff/Test 契约保持一致，后续如果需要我可以继续把文档末尾的接口清单（第9节）与此契约合并成最终对照表。

````

---

### 4.5 代码评审 Agent (Senior Reviewer)

```python
class SeniorReviewerAgent(BaseAgent):
    """代码评审 Agent - 扮演技术委员会评审专家"""

    def get_input_keys(self) -> list[str]:
        return ["code_diff", "design", "tests"]

    def get_output_key(self) -> str:
        return "review"

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        self._validate_input(context)

        system_prompt = self.prompt_manager.get_template("senior_reviewer", "system")
        context_prompt = self.prompt_manager.render_template(
            "senior_reviewer",
            "context",
            {
                "code_diff": context["code_diff"],
                "design": context["design"],
                "tests": context["tests"],
            }
        )
        instruction_prompt = self.prompt_manager.get_template(
            "senior_reviewer",
            "instruction"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{context_prompt}\n\n{instruction_prompt}"}
        ]

        output_schema = self.prompt_manager.get_output_schema("senior_reviewer")
        result = self._invoke_llm(messages, output_schema)

        return {"review": result.model_dump()}
````

**输出结构**：

```python
{
    "review": {
        "issues": [                 # 发现的问题
            {
                "severity": str,    # critical/major/minor
                "category": str,   # correctness/security/style/performance
                "description": str,
                "location": str,   # 文件:行号
                "suggestion": str   # 修复建议
            }
        ],
        "suggestions": [str],       # 优化建议
        "risk_level": str,          # low/medium/high/critical
        "pass": bool,              # 是否通过评审
        "summary": str,             # 评审总结
        "score": float              # 综合评分 0-10
    }
}
```

---

## 五、多 LLM Provider 支持机制

### 5.1 LLM Provider 接口定义

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class LLMResponse(BaseModel):
    """LLM 响应模型"""
    content: str
    usage: Dict[str, int]
    model: str

class BaseLLMProvider(ABC):
    """LLM Provider 基类"""

    def __init__(self, model_name: str, api_key: str, **kwargs):
        self.model_name = model_name
        self.api_key = api_key
        self.extra_params = kwargs

    @abstractmethod
    def invoke(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> LLMResponse:
        """同步调用"""
        pass

    @abstractmethod
    async def ainvoke(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> LLMResponse:
        """异步调用"""
        pass

    def with_structured_output(self, schema: BaseModel):
        """返回支持结构化输出的包装器"""
        return StructuredOutputWrapper(self, schema)


class StructuredOutputWrapper:
    """结构化输出包装器"""

    def __init__(self, provider: BaseLLMProvider, schema: BaseModel):
        self.provider = provider
        self.schema = schema

    def invoke(self, messages: List[Dict[str, str]], **kwargs) -> BaseModel:
        response = self.provider.invoke(messages, **kwargs)
        return self.schema.model_validate_json(response.content)

    async def ainvoke(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> BaseModel:
        response = await self.provider.ainvoke(messages, **kwargs)
        return self.schema.model_validate_json(response.content)
```

### 5.2 豆包 Provider 实现

```python
class DoubaoProvider(BaseLLMProvider):
    """字节豆包大模型 Provider"""

    BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"

    def __init__(self, model_name: str = "doubao-pro-32k", api_key: str = "", **kwargs):
        super().__init__(model_name, api_key, **kwargs)
        self.endpoint = kwargs.get("endpoint", self.BASE_URL)

    def invoke(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> LLMResponse:
        import requests

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model_name,
            "messages": messages,
            **self.extra_params,
            **kwargs
        }

        response = requests.post(
            f"{self.endpoint}/chat/completions",
            headers=headers,
            json=payload,
            timeout=kwargs.get("timeout", 120)
        )
        response.raise_for_status()
        data = response.json()

        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            usage=data.get("usage", {}),
            model=self.model_name
        )

    async def ainvoke(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> LLMResponse:
        import aiohttp

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model_name,
            "messages": messages,
            **self.extra_params,
            **kwargs
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.endpoint}/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=kwargs.get("timeout", 120))
            ) as response:
                data = await response.json()

        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            usage=data.get("usage", {}),
            model=self.model_name
        )
```

### 5.3 通义千问 Provider 实现

```python
class QwenProvider(BaseLLMProvider):
    """阿里通义千问大模型 Provider"""

    BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    def __init__(self, model_name: str = "qwen-plus", api_key: str = "", **kwargs):
        super().__init__(model_name, api_key, **kwargs)
        self.endpoint = kwargs.get("endpoint", self.BASE_URL)

    def invoke(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> LLMResponse:
        import requests

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model_name,
            "messages": messages,
            **self.extra_params,
            **kwargs
        }

        response = requests.post(
            f"{self.endpoint}/chat/completions",
            headers=headers,
            json=payload,
            timeout=kwargs.get("timeout", 120)
        )
        response.raise_for_status()
        data = response.json()

        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            usage=data.get("usage", {}),
            model=self.model_name
        )

    async def ainvoke(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> LLMResponse:
        import aiohttp

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model_name,
            "messages": messages,
            **self.extra_params,
            **kwargs
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.endpoint}/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=kwargs.get("timeout", 120))
            ) as response:
                data = await response.json()

        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            usage=data.get("usage", {}),
            model=self.model_name
        )
```

### 5.4 LLM Factory

```python
class LLMFactory:
    """LLM Provider 工厂类"""

    _providers = {
        "doubao": DoubaoProvider,
        "qwen": QwenProvider,
        "openai_compatible": OpenAICompatibleProvider,
    }

    @classmethod
    def create(
        cls,
        provider_name: str,
        model_name: str,
        api_key: str,
        **kwargs
    ) -> BaseLLMProvider:
        """
        创建 LLM Provider 实例

        :param provider_name: provider 名称 (doubao/qwen/openai_compatible)
        :param model_name: 模型名称
        :param api_key: API Key
        :return: LLM Provider 实例
        """
        if provider_name not in cls._providers:
            raise ValueError(
                f"Unknown provider: {provider_name}. "
                f"Available: {list(cls._providers.keys())}"
            )

        provider_class = cls._providers[provider_name]
        return provider_class(model_name=model_name, api_key=api_key, **kwargs)

    @classmethod
    def register_provider(
        cls,
        name: str,
        provider_class: Type[BaseLLMProvider]
    ) -> None:
        """注册新的 Provider"""
        cls._providers[name] = provider_class

    @classmethod
    def list_providers(cls) -> list[str]:
        """列出所有可用的 Provider"""
        return list(cls._providers.keys())
```

---

## 六、Prompt 模板设计与管理

### 6.1 Prompt 管理器

```python
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
import yaml


class PromptManager:
    """Prompt 模板管理器"""

    def __init__(self, templates_dir: Optional[str] = None):
        if templates_dir is None:
            templates_dir = Path(__file__).parent / "templates"
        self.templates_dir = Path(templates_dir)
        self._cache: Dict[str, Dict[str, Any]] = {}

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
                    self._cache[cache_key] = {"type": "text", "content": f.read()}
            else:
                return ""

        return self._cache[cache_key].get("content", "")

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

    def get_output_schema(self, agent_name: str) -> Optional[type]:
        """获取输出 schema"""
        schema_path = self.templates_dir / agent_name / "output_schema.json"
        if schema_path.exists():
            with open(schema_path, "r", encoding="utf-8") as f:
                schema_dict = json.load(f)
            return self._json_schema_to_pydantic(schema_dict)
        return None

    @staticmethod
    def _json_schema_to_pydantic(schema: Dict[str, Any]) -> type:
        """将 JSON Schema 转换为 Pydantic 模型"""
        from pydantic import create_model

        properties = schema.get("properties", {})
        required = schema.get("required", [])

        field_definitions = {}
        for field_name, field_spec in properties.items():
            field_type = PromptManager._map_json_type(field_spec.get("type"))
            if field_name in required:
                field_definitions[field_name] = (field_type, ...)
            else:
                field_definitions[field_name] = (field_type, None)

        return create_model(
            f"{schema.get('title', 'Output')}Schema",
            **field_definitions
        )

    @staticmethod
    def _map_json_type(json_type: str) -> type:
        """映射 JSON 类型到 Python 类型"""
        type_map = {
            "string": str,
            "number": float,
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict
        }
        return type_map.get(json_type, str)
```

### 6.2 Prompt 模板示例

#### 需求分析 Agent - System Prompt

```
你是一位资深产品经理，拥有10年以上需求分析和产品设计经验。
你的职责是帮助用户将模糊的自然语言需求转化为清晰、可执行的结构化需求文档。

分析原则：
1. 需求必须明确、无歧义
2. 每个功能点必须有可验证的验收标准
3. 识别并记录潜在的风险和约束
4. 保持需求的简洁性和可实现性

输出格式：
必须返回有效的 JSON 对象，包含所有必需字段。
```

#### 需求分析 Agent - Context Template

```
## 原始需求
{{requirement_raw}}

## 代码库信息
- 仓库名称：{{repo_name}}
- 仓库路径：{{repo_path}}

请分析上述需求，识别：
1. 核心目标和期望结果
2. 具体的功能点（Feature）
3. 技术约束和业务约束
4. 可验证的验收标准
5. 潜在的假设条件和风险
```

#### 需求分析 Agent - Output Schema

```json
{
  "title": "StructuredRequirement",
  "type": "object",
  "required": ["goal", "features", "acceptance_criteria"],
  "properties": {
    "goal": {
      "type": "string",
      "description": "需求的核心目标，一句话描述"
    },
    "features": {
      "type": "array",
      "description": "功能点列表",
      "items": {
        "type": "object",
        "required": ["name", "description", "acceptance_criteria"],
        "properties": {
          "name": { "type": "string" },
          "description": { "type": "string" },
          "priority": { "type": "string", "enum": ["high", "medium", "low"] },
          "acceptance_criteria": {
            "type": "array",
            "items": { "type": "string" }
          }
        }
      }
    },
    "constraints": {
      "type": "array",
      "items": { "type": "string" },
      "description": "约束条件列表"
    },
    "acceptance_criteria": {
      "type": "array",
      "items": { "type": "string" },
      "description": "整体验收标准"
    },
    "assumptions": {
      "type": "array",
      "items": { "type": "string" }
    },
    "risks": {
      "type": "array",
      "items": { "type": "string" }
    }
  }
}
```

---

## 七、Agent 工厂与注册机制

### 7.1 AgentFactory

```python
from typing import Dict, Type, Optional


class AgentFactory:
    """Agent 工厂类，负责创建和管理 Agent 实例"""

    _agents: Dict[str, Type[BaseAgent]] = {}

    @classmethod
    def register(
        cls,
        name: str,
        agent_class: Type[BaseAgent]
    ) -> None:
        """注册 Agent 类"""
        cls._agents[name] = agent_class

    @classmethod
    def create(
        cls,
        name: str,
        llm_provider: BaseLLMProvider,
        config: Optional[AgentConfig] = None,
        **kwargs
    ) -> BaseAgent:
        """
        创建 Agent 实例

        :param name: Agent 名称
        :param llm_provider: LLM Provider
        :param config: Agent 配置
        :return: Agent 实例
        """
        if name not in cls._agents:
            raise ValueError(
                f"Unknown agent: {name}. "
                f"Available: {list(cls._agents.keys())}"
            )

        agent_class = cls._agents[name]
        return agent_class(
            llm_provider=llm_provider,
            config=config,
            **kwargs
        )

    @classmethod
    def list_agents(cls) -> list[str]:
        """列出所有注册的 Agent"""
        return list(cls._agents.keys())


# 注册内置 Agent
AgentFactory.register("requirement_analyst", RequirementAnalystAgent)
AgentFactory.register("tech_architect", TechArchitectAgent)
AgentFactory.register("code_generator", CodeGeneratorAgent)
AgentFactory.register("test_engineer", TestEngineerAgent)
AgentFactory.register("senior_reviewer", SeniorReviewerAgent)
```

---

## 八、与 Pipeline Engine 的接口对接

### 8.1 接口契约

| 阶段     | Agent 输入                                         | Agent 输出             | Pipeline 处理  |
| -------- | -------------------------------------------------- | ---------------------- | -------------- |
| 需求分析 | requirement_raw, codebase                          | requirement_structured | 存储到 context |
| 方案设计 | requirement_structured, codebase, codebase_context | design                 | 暂停等待审批   |
| 代码生成 | requirement_structured, design, codebase_context   | code_diff              | 存储到 context |
| 测试生成 | code_diff, requirement_structured                  | tests                  | 存储到 context |
| 代码评审 | code_diff, design, tests                           | review                 | 存储到 context |

### 8.2 Pipeline 调用示例

```python
from agent.factory import AgentFactory
from agent.llm.factory import LLMFactory


class PipelineEngine:
    """Pipeline Engine 示例"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.llm_provider = LLMFactory.create(
            provider_name=config["llm"]["provider"],
            model_name=config["llm"]["model"],
            api_key=config["llm"]["api_key"]
        )
        self.prompt_manager = PromptManager()

    def _execute_stage(
        self,
        stage_name: str,
        agent_name: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行单个阶段"""
        agent = AgentFactory.create(
            name=agent_name,
            llm_provider=self.llm_provider,
            prompt_manager=self.prompt_manager
        )

        result = agent.execute(context)

        context.update(result)
        return context

    def run_pipeline(self, pipeline_id: str) -> Dict[str, Any]:
        """运行 Pipeline"""
        pipeline = self.get_pipeline(pipeline_id)
        context = pipeline.get("context", {})

        stage_mapping = {
            "requirement_analysis": "requirement_analyst",
            "tech_design": "tech_architect",
            "code_generation": "code_generator",
            "test_generation": "test_engineer",
            "code_review": "senior_reviewer",
        }

        for stage_name, agent_name in stage_mapping.items():
            context = self._execute_stage(stage_name, agent_name, context)

            if stage_name == "tech_design":
                # 方案设计后需要审批
                pipeline["status"] = "WAITING_APPROVAL"
                self.save_pipeline(pipeline)
                return pipeline

        pipeline["status"] = "FINISHED"
        pipeline["context"] = context
        self.save_pipeline(pipeline)
        return pipeline
```

---

## 九、配置管理

### 9.1 Agent 配置文件

```yaml
# backend/config/agent_config.yaml

llm:
  default_provider: "doubao"
  default_model: "doubao-pro-32k"
  providers:
    doubao:
      api_key: "${DOUBAO_API_KEY}"
      endpoint: "https://ark.cn-beijing.volces.com/api/v3"
      timeout: 120
    qwen:
      api_key: "${QWEN_API_KEY}"
      endpoint: "https://dashscope.aliyuncs.com/compatible-mode/v1"
      timeout: 120

agents:
  requirement_analyst:
    temperature: 0.7
    max_tokens: 4096
    retry_count: 3
  tech_architect:
    temperature: 0.5
    max_tokens: 8192
    retry_count: 3
  code_generator:
    temperature: 0.3
    max_tokens: 8192
    retry_count: 3
  test_engineer:
    temperature: 0.5
    max_tokens: 4096
    retry_count: 3
  senior_reviewer:
    temperature: 0.3
    max_tokens: 4096
    retry_count: 2

prompts:
  templates_dir: "backend/agent/prompts/templates"
  cache_enabled: true
```

### 9.2 配置加载器

```python
import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigLoader:
    """配置加载器"""

    _instance: Optional["ConfigLoader"] = None

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self._config: Dict[str, Any] = {}

    @classmethod
    def get_instance(cls, config_path: Optional[str] = None) -> "ConfigLoader":
        if cls._instance is None:
            cls._instance = cls(config_path)
        return cls._instance

    def load(self) -> Dict[str, Any]:
        if not self._config:
            self._load_config()
        return self._config

    def _load_config(self) -> None:
        """加载配置文件"""
        if self.config_path is None:
            self.config_path = Path(__file__).parent.parent.parent / "config" / "agent_config.yaml"

        with open(self.config_path, "r", encoding="utf-8") as f:
            self._config = yaml.safe_load(f)

        self._resolve_env_vars(self._config)

    def _resolve_env_vars(self, config: Dict[str, Any]) -> None:
        """解析环境变量"""
        for key, value in config.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]
                config[key] = os.environ.get(env_var, "")
            elif isinstance(value, dict):
                self._resolve_env_vars(value)
```

---

## 十、扩展性设计

### 10.1 自定义 Agent 注册

```python
# 用户可自定义 Agent 并注册
class CustomAgent(BaseAgent):
    def get_input_keys(self) -> list[str]:
        return ["requirement_raw"]

    def get_output_key(self) -> str:
        return "custom_output"

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        # 自定义逻辑
        return {"custom_output": {...}}

# 注册自定义 Agent
AgentFactory.register("custom", CustomAgent)
```

### 10.2 自定义 LLM Provider 注册

```python
# 用户可注册新的 LLM Provider
class CustomProvider(BaseLLMProvider):
    def invoke(self, messages, **kwargs) -> LLMResponse:
        # 自定义逻辑
        pass

    async def ainvoke(self, messages, **kwargs) -> LLMResponse:
        pass

LLMFactory.register_provider("custom", CustomProvider)
```

---

## 十一、错误处理与重试机制

### 11.1 Agent 执行错误处理

```python
from functools import wraps
import logging

logger = logging.getLogger(__name__)


def with_retry(max_attempts: int = 3, backoff_factor: float = 1.5):
    """重试装饰器"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        wait_time = backoff_factor ** attempt
                        logger.warning(
                            f"Attempt {attempt + 1} failed: {e}. "
                            f"Retrying in {wait_time}s..."
                        )
                        import time
                        time.sleep(wait_time)
                    else:
                        logger.error(f"All {max_attempts} attempts failed")

            raise last_exception

        return wrapper
    return decorator


class BaseAgent(ABC):
    # ... 原有代码 ...

    @with_retry(max_attempts=3)
    def execute_with_retry(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """带重试的执行方法"""
        return self.execute(context)
```

---

## 十二、依赖项

```
# backend/requirements.txt
pydantic>=2.0.0
langchain>=0.1.0
pyyaml>=6.0
requests>=2.31.0
aiohttp>=3.9.0
jinja2>=3.1.0
```

---

## 十三、实现 Checklist

- [ ] 定义 BaseAgent 抽象基类
- [ ] 实现 AgentConfig 配置模型
- [ ] 实现 BaseLLMProvider 接口
- [ ] 实现 DoubaoProvider
- [ ] 实现 QwenProvider
- [ ] 实现 OpenAICompatibleProvider
- [ ] 实现 LLMFactory
- [ ] 实现 PromptManager
- [ ] 编写所有 Prompt 模板
- [ ] 实现 RequirementAnalystAgent
- [ ] 实现 TechArchitectAgent
- [ ] 实现 CodeGeneratorAgent
- [ ] 实现 TestEngineerAgent
- [ ] 实现 SeniorReviewerAgent
- [ ] 实现 AgentFactory
- [ ] 编写 agent_config.yaml
- [ ] 实现 ConfigLoader
- [ ] 单元测试覆盖
- [ ] 与 Pipeline Engine 集成测试
