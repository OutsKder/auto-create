# Step2 精确检索规范草案

## 1. 目标与原则

### 1.1 目标

在已有 Step1 Repo-Map（全局骨架）基础上，构建 Step2 精确检索能力，输出“尽可能小但尽可能全”的需求相关代码上下文，支撑后续方案设计与代码修改。

### 1.2 核心原则

- 全面性优先：宁可多召回后裁剪，不可漏掉关键修改点。
- 可解释性：每个命中文件必须有“命中证据”。
- 可复现性：同一输入在相同索引版本下结果稳定。
- 增量更新：索引随代码变化快速更新，避免全量重建。

---

## 2. Step2 输入与输出协议

### 2.1 输入

````json
```jsonc
{
  // 来源：用户原始需求文本（或 requirement_structured 反向生成的检索主查询）
  "query": "为现有系统新增邮箱登录与用户管理",

  // 来源：运行时上下文 context.codebase.repo_path（由上层调用方传入）
  "repo_path": "/path/to/repo",

  // 来源：Step1 Repo-Map 输出结果（由 Step2 在执行前读取/注入）
  "repo_skeleton": "...Step1 输出...",

  // 来源：需求结构化模块（产品需求解析器/NLP 预处理）输出
  "requirement_structured": {
    // 来源：需求总目标提炼（如 PRD 标题/一句话目标）
    "goal": "",
    // 来源：功能点拆解（如 登录、用户管理、权限控制）
    "features": [],
    // 来源：技术与业务约束（性能、兼容性、安全、合规）
    "constraints": [],
    // 来源：验收标准（测试条件、完成定义 DoD）
    "acceptance_criteria": []
  },

  // 来源：Step2 检索配置默认值（可由调用方覆盖）
  "top_k": 30,

  // 来源：Step2 依赖闭包扩展策略默认值（规范建议 1-hop）
  "expand_hops": 1,

  // 来源：仓库语言探测结果 + 调用方提示（用于选择解析器与索引通道）
  "language_hints": ["python", "javascript", "typescript"]
}
````

````

### 2.2 输出（codebase_context）

```json
{
  "codebase_context": {
    "query": "",
    "repo_skeleton": "",
    "hot_files": [
      {
        "path": "backend/auth/service.py",
        "content": "...full file content...",
        "score": 0.91,
        "evidence": ["semantic", "keyword:email", "import-neighbor"]
      }
    ],
    "dependency_signatures": [
      "backend/models/user.py: class User(Base)",
      "backend/auth/service.py: def login_with_email(email, password)"
    ],
    "coverage_report": {
      "requirement_points": [
        {
          "point": "邮箱登录",
          "matched_files": 6,
          "status": "covered"
        },
        {
          "point": "用户管理",
          "matched_files": 9,
          "status": "covered"
        }
      ],
      "uncovered_points": [],
      "risk_level": "low"
    }
  }
}
````

---

## 3. 分层索引设计（离线基座）

### 3.1 目录级摘要索引（Dir Summary Index）

每一级目录维护一个 `summary.json`：

- 目录职责
- 关键模块
- 对外接口
- 与其他目录的依赖关系

建议字段：

```json
{
  "dir": "backend/auth",
  "purpose": "认证与授权",
  "key_files": ["service.py", "router.py", "schemas.py"],
  "exports": ["login", "refresh_token"],
  "depends_on": ["backend/models", "backend/utils"]
}
```

### 3.2 文件级摘要索引（File Summary Index）

每个文件维护一个 `file_summary.json`：

- 文件职责
- 主符号（类/函数/路由/配置键）
- 关键业务关键词
- 上下游依赖

### 3.3 符号索引（Symbol Index）

按语言抽取：

- Python：class/def/import/decorator
- TS/JS：class/function/export/import/route handler
- 配置：env key、yaml/json key、feature flag

### 3.4 向量索引（Semantic Index）

向量化粒度：

- 文件摘要向量
- 代码块向量（函数级）
- 文档片段向量（README、设计文档）

---

## 4. 在线检索流水线（Step2 主流程）

### 4.1 Query 解析

从 `requirement_structured` 生成检索子查询：

- 业务实体：用户、邮箱、权限
- 行为动词：新增、校验、绑定、发送
- 技术约束：性能、精度、兼容性

### 4.2 多通道并行召回（并集）

至少启用四路：

1. 关键词召回（BM25/倒排）
2. 语义召回（向量 TopK）
3. 符号召回（函数名/类名/路由名）
4. 规则召回（领域规则）

规则召回示例：

- 命中“用户管理”时，强制扩展到 `model + service + router + dto/schema + permission`。
- 命中“邮箱”时，强制扩展到 `auth + notification + config(env)`。

### 4.3 依赖闭包扩展（防漏）

对初始命中集进行 `N-hop` 扩展（建议默认 1 hop）：

- import 邻居
- 调用链邻居
- 路由上下游
- 同模块核心文件

### 4.4 重排与裁剪

重排分数建议：

- `FinalScore = 0.45*Semantic + 0.25*Keyword + 0.20*Dependency + 0.10*RuleBoost`
- 先取高分文件，再按覆盖报告补足遗漏需求点。

### 4.5 结果打包

输出：

- `hot_files`：全量代码（可设单文件上限，如 30k 字符）
- `dependency_signatures`：只放关键签名
- `coverage_report`：覆盖与漏项说明

---

## 5. OpenCode Skill 的定位（流程约束层）

OpenCode Skill 不替代索引，而用于“强约束执行顺序”和“标准化产出格式”。

建议 Skill 固定步骤：

1. 读取 Step1 repo_skeleton
2. 按 query 生成检索子任务
3. 调用检索工具拿候选集
4. 生成候选证据与覆盖报告
5. 输出最终 `codebase_context`

这样可兼顾：

- 可控流程（Skill）
- 检索质量（索引 + RAG）
- 结果稳定（固定协议）

---

## 6. 质量门禁（必须满足）

### 6.1 覆盖门禁

- 每个 requirement point 至少命中 `>=1` 关键文件。
- 若有未覆盖 point，必须在 `uncovered_points` 明示并提升风险等级。

### 6.2 证据门禁

- 每个 hot_file 至少具备 2 类证据（如 semantic + dependency）。

### 6.3 变更前审计门禁

- 在进入“代码生成”前输出“预计修改文件清单 vs 检索命中清单”差异。
- 差异过大时要求回到 Step2 补检索。

---

## 7. 落地实施顺序（建议）

### Phase A（本周可落地）

- 建立目录/文件摘要索引（先 Python）
- 接入多通道召回中的关键词 + 规则 + 依赖扩展
- 输出标准 `coverage_report`

### Phase B

- 接入向量召回与重排
- 增加函数级 chunk 检索
- 引入缓存与增量更新

### Phase C

- 引入 OpenCode Skill 编排
- 加入离线评测集（历史需求回放）
- 建立召回率/精确率仪表盘

---

## 8. 与当前项目接口建议

在 `backend/agent/tools` 增加：

- `context_retrieval_step2.py`
  - `retrieve_precise_context(input) -> codebase_context`

由 `TechArchitect.execute(context)` 调用：

1. 读取 `context.requirement_structured`
2. 读取 `context.codebase.repo_path`
3. 调用 Step1（已实现）得到 `repo_skeleton`
4. 调用 Step2（本规范）得到 `hot_files + dependency_signatures + coverage_report`
5. 将 `requirement_structured + codebase_context` 一并输入 LLM 生成 `design`

---

## 9. 风险与对策

- 风险：全量摘要维护成本高。
  - 对策：git diff 增量更新，只更新变更文件及受影响目录。
- 风险：召回结果过多导致 prompt 膨胀。
  - 对策：先证据重排，再按需求点分桶抽样。
- 风险：跨语言仓库解析不一致。
  - 对策：先落地 Python/TS 两种主语言，其他语言走保底关键词+路径规则。

---

## 10. 结论

若目标是“最小化且全面”地找到需求相关代码片段，最佳实践是：

- Step1：毫秒级 Repo-Map（已完成）
- Step2：分层摘要索引 + 多通道并集召回 + 依赖闭包扩展 + 覆盖报告
- Skill：用于固定执行流程与输出协议，不直接承担核心检索。

该方案可在保证召回全面性的同时，将误召回控制在可裁剪范围内，适合作为后续自动改码链路的稳定输入层。
