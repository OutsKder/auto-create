在方案设计（Design）阶段，如何精准且最小化地提供**代码库上下文（Codebase Context）**是决定 AI 产出质量的核心。

虽然豆包 2.0（Doubao-pro-128k/Pro-32k）拥有巨大的上下文窗口，但**盲目塞入全部代码会导致：1. 关键信息被稀释（Lost in the middle）；2. Token 成本飙升；3. 推理速度变慢。**

以下是结合目前 AI 原生工具（如 Aider, Cursor, OpenCode）最前沿技术，针对本项目设计的**"结构化上下文压缩提取方案"**：

### 1. 技术核心：从"代码全文"转向"知识图谱 + 局部细节"

我们需要通过三层过滤机制，为豆包 2.0 准备一份"高含金量"的上下文：

#### 第一层：Repo-Map（全景图谱）—— 解决"在哪改"

**技术实现：** 利用 **Python 内置 AST (Abstract Syntax Tree)** 进行代码解析，其他文件类型使用轻量级正则提取。

- **做法：** 不提取代码逻辑，只提取每个文件的：**类名、函数签名、核心变量定义、及其位置**。
  - **Python 文件**：使用 `ast.parse()` 精确提取函数签名和类定义
  - **JS/TS 文件**：使用正则表达式提取 class 和 function
  - **其他文件**：只显示文件路径
- **价值：** 给 AI 提供一张"代码地图"。即使不看具体代码，AI 也能通过 auth.py 里的 `def verify_token(token):` 知道这是处理登录逻辑的地方。
- **豆包优势：** 128k 窗口可以轻松容纳一个中大型项目的完整 Repo-Map。
- **过滤策略**：自动过滤 `.git`, `__pycache__`, `node_modules`, `venv`, `env`, `.opencode` 等目录，减少噪音。

#### 第二层：语义索引 + LSP 引用分析 —— 解决"改什么"

**技术实现：** 结合 **向量检索 (RAG)** 和 **语言服务器协议 (LSP)**。

- **做法：**
  1. **语义搜索：** 根据结构化需求（Requirement Structured），在向量数据库中检索相关性最高的前 5-10 个代码片段。
  2. **引用追踪：** 既然修改了 user_model.py，利用 LSP 自动找出谁引用了这个模型（如 user_service.py）。
- **价值：** 自动补全"影响范围"。AI 不仅看到要改的地方，还能看到改动后会波及哪里。

#### 第三层：Hot-File 完整上下文 —— 解决"怎么改"

**技术实现：** 动态 Token 配额管理。

- **做法：** 对于语义相关度 > 0.8 或被手动标记的文件，提供**全量代码**。
- **价值：** 保证核心逻辑不丢失。

---

### 2. 在 DevFlow 中的具体执行流程 (Agent 逻辑)

在"方案设计"Agent 中，我们需要增加一个**预处理子节点 (Context Pre-processor)**：

#### Step 1: 生成 Repo-Map (Skeleton)

调用 `CodebaseContextTool` 工具类，生成项目的骨架。

- **输入：** 整个 Repo 路径 (`workspace_root`)。
- **输出：** 一个 Markdown 格式的代码库全景图谱，包含：
  - 文件路径列表（按目录结构组织）
  - Python 文件的类名和函数签名（通过 AST 解析）
  - JS/TS 文件的类名和函数名（通过正则提取）

#### Step 2: 关联性推理 (LLM Selecting)

将 Requirement Structured 和 Repo-Map 投喂给豆包 2.0。

- **Prompt：** "作为架构师，为了实现上述需求，请从以下地图中挑选出：1. 必须修改的文件；2. 需要参考逻辑的文件。"
- **输出：** 一个精简的文件路径列表（如 [auth.py, db/session.py]）。

#### Step 3: 构建最小上下文 (Context Synthesis)

根据 Step 2 的列表，构造最终的 codebase_context 结构：

```codeJSON
"codebase_context": {
    "query": "用户需求目标",
    "repo_skeleton": "代码库全景图谱...", // 整个项目的 Repomap
    "hot_files": [
        { "path": "auth.py", "content": "..." }, // 全量代码
        { "path": "db/session.py", "content": "..." } // 全量代码
    ],
    "dependency_signatures": [
         "models.py: class User(Base): ...", // 仅提供相关的函数签名
    ]
}
```

---

### 3. 结合豆包 2.0 的优化策略

豆包 2.0 的 **Pro-128k** 模型允许我们做一些更"奢侈"但在研发场景极其有效的事情：

1. **Long-Context Ranking (长上下文排序)：**
   我们可以先粗略提取 50 个相关代码块（约 5-10 万 Token），利用豆包强大的长文本理解能力，在 Prompt 中要求它："从以下 50 个代码块中，剔除与本次修改无关的代码，保留核心逻辑"。这比传统的 Embedding 过滤精准得多。
2. **多视角上下文：**
   除了代码，利用豆包的窗口把相关的 **API 文档 (Swagger)** 和 **之前的 MR 摘要** 也塞进去。这能让方案设计更符合历史规范。

---

### 4. 核心竞争力体现（针对答辩）

在演示和答辩中，你可以重点强调以下"**Context-Native**"的设计：

- **不仅仅是 RAG：** 强调你不仅用了向量检索，还结合了 **静态分析 (AST Repo-Map)** 和 **LSP (Dependency Tracking)**，这解决了传统 RAG 无法处理跨文件逻辑调用的痛点。
- **动态 Token 控制：** 强调你的 Agent 会根据需求复杂度自动调整上下文深度——简单修改只给 Repomap，复杂重构才给全量代码。
- **低噪音上下文：** 展示你如何将 10 万行的代码库，精准压缩到 5000 Token 的核心上下文，从而让豆包 2.0 的方案设计产出"零幻觉"。

### 推荐工具集成：

- 使用 **Python 内置 AST** 进行代码解析（无需额外依赖）。
- 使用 **OpenCode 的 @plan 模式** 的中间产物，它内部已经实现了类似的代码定位逻辑。
- 调用豆包 2.0 的 **character 或 json_mode** 确保 Context 提取节点返回的是严格的 JSON 路径列表。

### 已实现的代码结构

```python
class CodebaseContextTool:
    """
    提供结构化的代码库上下文提取工具。
    输入目标代码库地址，返回格式化的 codebase_context 字典。
    """
    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root

    def extract_context(self, query: str = "") -> Dict[str, Any]:
        # 返回格式化的代码库上下文
        return {
            "query": query,
            "repo_skeleton": self._generate_repo_map(),
            "hot_files": [],  # Step 2: 待实现的热点文件全量代码
            "dependency_signatures": [],  # Step 3: 待实现的依赖签名提取
        }

    def _generate_repo_map(self) -> str:
        # Step 1: 生成项目全景图谱 (Fast AST Repo-Map)
        # - Python 文件：使用 ast.parse() 精确解析
        # - JS/TS 文件：使用正则表达式提取
        # - 其他文件：只显示路径
        # - 自动过滤噪音目录
```
