这是一个基于 **LangGraph + LangChain + OpenCode** 的工业级 AI 研发流程引擎（DevFlow Engine）详细方案设计。

------



# DevFlow Engine 详细方案设计

## 一、 系统架构总览

系统采用“**中枢调度-执行内核-数据总线**”的三层架构：

1. **中枢调度 (Orchestrator)**：使用 **LangGraph**。负责定义研发流程的拓扑结构、节点跳转逻辑及有状态的上下文管理。
2. **执行内核 (Execution Kernel)**：集成 **OpenCode**。负责真实环境的代码索引、文件读写、Bash 执行及测试运行。
3. **数据总线 (Data Bus)**：基于 **context 契约**。作为 Single Source of Truth，所有 Agent 均通过标准 Schema 对其进行增量更新。

------



## 二、 核心 Agent 详细设计

### 1. 需求分析 Agent (Requirement Analyst)

- **输入**：requirement_raw (用户原始描述)
- **逻辑**：
  - 利用 LLM 的推理能力，识别用户需求中的隐含逻辑。
  - 将非结构化文本拆解为：核心目标 (Goal)、功能点 (Features)、非功能约束 (Constraints) 和 验收标准 (AC)。
- **输出**：requirement_structured
- **LangChain 实现**：使用 ChatPromptTemplate 配合 with_structured_output 强制要求 LLM 返回符合 Pydantic 定义的对象。

### 2. 方案设计 Agent (Tech Architect)

- **输入**：requirement_structured + codebase 路径
- **逻辑**：
  - **Context 检索**：通过 OpenCode SDK 调用语义搜索，获取与需求相关的核心文件列表。
  - **影响评估**：分析现有代码逻辑，判断修改 A 模块是否会影响 B 模块。
  - **制定计划**：产出 file_change_plan，明确哪些文件需要修改（Modify），哪些需要新增（Create）。
- **输出**：design (包含架构说明、API 设计、修改清单)
- **OpenCode 角色**：作为“导航员”，提供仓库索引支持。

### 3. 代码生成 Agent (OpenCode Executor)

- **输入**：design + requirement_structured
- **逻辑**：
  - **驱动执行**：调用 OpenCode 的 build 模式。
  - **指令下达**：将 file_change_plan 转化为 OpenCode 可执行的自然语言指令。
  - **物理操作**：OpenCode 自动在工作目录下应用 Patch，处理代码缩进、语法规范。
- **输出**：code_diff (Git Diff 格式及受影响文件列表)
- **OpenCode 角色**：作为“主驾驶”，直接操作本地文件系统。

### 4. 测试验证 Agent (Test & Healing Engineer)

- **输入**：code_diff + design
- **逻辑**：
  - **测试编写**：针对修改点，编写对应的单元测试或集成测试。
  - **执行与修复 (Self-healing)**：驱动 OpenCode 在本地运行 pytest 或 npm test。
  - **反馈循环**：若测试失败，将错误日志传回给 OpenCode，要求其自动修复代码，直至测试通过。
- **输出**：tests (测试代码、运行日志、Pass 状态)
- **OpenCode 角色**：提供 Bash 执行环境，实现“生成-验证-修复”的闭环。

### 5. 代码评审 Agent (Senior Reviewer)

- **输入**：code_diff + design + tests
- **逻辑**：
  - **多维审查**：检查代码是否存在安全隐患、性能瓶颈、是否符合设计方案。
  - **打分与建议**：产出结构化的评审报告，给出 pass 或 fail 的建议。
- **输出**：review (评审意见、风险等级)

------



## 三、 LangGraph 状态机编排逻辑

在 LangGraph 中，流程被定义为一个有向无环图 (DAG)：

1. **节点定义 (Nodes)**：上述 5 个 Agent 分别对应图中的 5 个 Node。
2. **状态流转 (State Edges)**：
   - START -> Requirement Analyst -> Tech Architect。
   - 在 Tech Architect 节点完成后，由于需要“人工审批”，Graph 会输出当前状态并进入 **WAITING** 状态（利用 LangGraph 的 checkpoint 机制实现）。
   - **Approve**：触发外部信号，Graph 继续流向 OpenCode Executor。
   - **Reject**：携带理由返回 Tech Architect 节点重做。
3. **循环处理 (Conditional Edges)**：
   - 若 Review Agent 判定代码质量极差，可配置条件边回退至 OpenCode Executor。

------



## 四、 技术亮点 (体现核心竞争力)

### 1. 从“生成”到“执行”的跨越

传统 Agent 只能写出代码片段，本方案通过 **OpenCode SDK** 实现了对真实磁盘文件的修改和 Bash 环境的驱动，真正做到了“端到端交付”。

### 2. 带有自愈能力的流水线

在测试阶段，通过 OpenCode 捕获运行报错并自动反哺给 AI 进行二次修正，极大提高了 Pipeline 的一次通过率，减少了人工介入频率。

### 3. 精准的 Context 注入

利用 OpenCode 的代码索引能力，解决了大项目下 LLM 上下文溢出的问题。Agent 只读取“最相关”的代码片段，既节省 Token 又提高了方案设计的准确性。

### 4. 工业级状态管理

使用 LangGraph 维护 context。即便 Pipeline 在“写代码”阶段因意外中断，系统也能通过持久化的 checkpoint 从断点处恢复，具备企业级容错能力。

------



## 五、 交付物与集成点 (与队友对齐)

1. **API 接口**：Python 端提供 /run_stage 接口，接收 Pipeline ID 和当前 context，返回 Agent 处理后的增量 context。
2. **数据格式**：统一使用 Pydantic Model 校验，确保 Go 后端拿到的 JSON 永远不会出现字段缺失。
3. **OpenCode 部署**：后端需预装 OpenCode CLI 并配置好 LSP 支持，确保 Agent 能正确索引代码库。