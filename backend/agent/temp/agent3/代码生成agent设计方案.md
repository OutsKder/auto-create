# 代码生成 Agent 设计方案

本方案面向两个核心阶段：

1. 代码生成 / 修改 Agent（Code Executor）
2. 测试生成 Agent（SDET）

目标不是“生成一大坨代码”，而是把技术方案精确落到逐文件变更，并通过沙盒测试形成闭环自愈，最终输出可合并的代码变更集（Diff）。

---

## 一、设计目标

### 1.1 核心目标

- 输入技术方案 `design` + 代码库 `codebase`
- 按 `file_change_plan` 逐文件生成或修改代码
- 输出机器可处理的代码变更集 `code_diff`
- 将 `code_diff` 直接衔接到测试生成与沙盒执行
- 通过有限次数迭代完成“生成-验证-修复”闭环，避免死循环

### 1.2 设计原则

- 精确修改，不做无关重写
- 文件级最小变更，优先局部补丁而不是整文件覆盖
- 所有变更都能回放、追踪、审计
- 测试先于合并，失败必须返回可诊断的错误信息
- 重试次数有限，超过上限后必须熔断并交给人工确认

---

## 二、Agent边界与职责拆分

### 2.1 代码生成 Agent（Code Executor）负责什么

- 读取 `design.file_change_plan`
- 只加载计划中涉及的文件及其必要邻近上下文
- 生成逐文件补丁或差异指令
- 交给执行器应用到工作区
- 产出标准化 `code_diff`

### 2.2 测试生成 Agent（SDET）负责什么

- 读取 `code_diff` + `requirement_structured.acceptance_criteria`
- 把验收标准映射为测试点清单
- 生成 pytest / unittest / 集成测试建议或测试文件
- 给出测试执行命令和依赖隔离策略

### 2.3 运行器（Runner）负责什么

- 不在宿主机直接跑代码
- 在沙盒容器中执行测试命令
- 捕获 `stdout`、`stderr`、`exit_code`
- 将失败日志回传给修复循环

---

## 三、代码生成 Agent 的技术方案

### 3.1 输入契约

代码生成 Agent 的最小输入应包含：

- `requirement_structured`
- `design`
- `codebase_context`
- `repo_path`
- `file_change_plan`

其中真正决定修改范围的是 `file_change_plan`，Agent 不得超范围改动其他文件。

### 3.2 代码生成技术栈

建议使用以下技术组合：

- **文件级上下文组装**：只喂给模型计划中相关文件、调用链邻居文件、必要摘要信息
- **Search / Replace 补丁协议**：让模型输出精确替换块，减少整文件漂移
- **统一 Diff 标准化**：最终输出转为 `git diff` 风格，便于审计和应用
- **AST / 语法辅助校验**：针对 Python、JS/TS 做结构检查，减少补丁打坏语法
- **静态验证**：格式化、lint、类型检查、最小单测或语法检查
- **执行器隔离**：文件修改与命令执行由 OpenCode 或等价沙盒执行器完成

### 3.3 推荐的补丁策略

内部生成阶段优先使用 Search / Replace Blocks，原因是：

- 约束模型只改动局部区域
- Token 成本低于全文件重写
- 更容易和 `file_change_plan` 对齐
- 适合后续做自动补丁应用与冲突重试

建议模型输出的补丁结构保持如下语义：

```text
FILE: path/to/file.py
<<<<<<< SEARCH
旧代码块
=======
新代码块
>>>>>>> REPLACE
```

对外输出时，再把这些补丁标准化成统一的 `code_diff`。

### 3.4 `code_diff` 的标准输出形式

建议不要只返回一个裸 `diff` 字符串，而是返回结构化 Diff Bundle：

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
      "patch": "...",
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
```

其中：

- `files_changed` 用于审计和权限控制
- `patches` 用于机器应用与回放
- `diff` 用于人工 review 和后续 review agent 输入
- `validation` 用于记录当前轮次已经做过哪些检查

### 3.5 代码生成执行流程

1. 读取 `design.file_change_plan`
2. 按文件拉取最小必要上下文
3. 要求模型按文件输出补丁，而不是输出整仓库代码
4. 由执行器应用补丁
5. 立即做静态检查：语法 / 格式 / 类型 / targeted lint
6. 如果补丁冲突或语法失败，只重试当前文件，不扩大修改面

### 3.6 精确性控制

为了保证“微创手术”式修改，代码生成 Agent 必须遵守：

- 只允许修改 `file_change_plan` 中列出的文件
- 除非是新文件创建，不允许生成整文件替换方案
- 不得为了“顺手优化”而改无关模块
- 发现重复逻辑时优先复用已有工具函数，再考虑局部重构
- 若同一补丁连续失败，应先回看目标文件的真实内容，而不是盲目扩大上下文

---

## 四、测试生成 Agent（SDET）设计

### 4.1 输入契约

测试生成 Agent 的最小输入应包含：

- `code_diff`
- `requirement_structured.acceptance_criteria`
- `design`
- 必要时补充 `codebase_context`

### 4.2 测试生成策略

测试 Agent 不负责改业务代码，它只负责把验收标准变成可执行测试：

- 每个 AC 转成一个或多个测试点
- 每个测试点生成独立测试函数
- 对外部依赖必须使用 mock / stub / fake
- 对数据库、网络、文件系统等副作用做隔离
- 明确区分 unit / integration / e2e 三层

### 4.3 测试文件输出形式

建议 `tests` 输出同样结构化，而不是只给一段测试字符串：

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
```

### 4.4 测试生成原则

- 每个新增 API 至少包含正向测试
- 关键路径至少包含一个失败态或边界态测试
- 优先测试行为，而不是测试实现细节
- 如果测试依赖网络或第三方服务，必须 mock，不允许直连真实外部系统
- 测试代码要和项目现有测试栈保持一致，不能随意切换框架

---

## 五、运行环境与沙盒执行

### 5.1 运行环境来源

代码和测试不能在宿主机直接执行，应当由沙盒环境统一运行。优先级建议如下：

1. 项目根目录已有 `Dockerfile.dev` / `docker-compose` / 项目指定开发镜像
2. 如果没有，则使用默认基础镜像，例如 `python:3.10-slim` 或项目配置中的默认镜像
3. 所有命令通过 OpenCode Bash Executor 或同类沙盒执行器发起

### 5.2 执行方式

- 将当前工作目录挂载到容器 `/workspace`
- 在容器内部执行测试命令
- 捕获标准输出、标准错误和退出码
- 将失败日志原样传给修复循环

### 5.3 推荐运行命令

根据项目技术栈动态选择：

- Python 项目：`pytest`
- Node 项目：`npm test` / `pnpm test`
- 前后端混合项目：只跑受影响的最小测试集合，再在必要时跑全量测试

### 5.4 为什么必须沙盒化

- 避免污染宿主机环境
- 保证 CI 和本地行为尽量一致
- 便于复现和回放失败
- 降低“我本地能跑”的不确定性

---

## 六、代码生成与测试的闭环自愈

### 6.1 流转顺序

推荐的最小闭环如下：

```text
CodeGen -> TestGen -> Runner -> Triage -> CodeGen
```

### 6.2 反馈环节点职责

- **CodeGen**：按 `file_change_plan` 生成或修改代码
- **TestGen**：把 AC 转成测试，并给出运行命令
- **Runner**：在沙盒中执行测试，输出真实日志
- **Triage**：把失败分成语法、依赖、断言、环境、性能等类别
- **CodeGen**：只针对本轮失败做最小修复

### 6.3 重试上限

建议最大重试次数为 3 次：

- 第 1 次：原始实现
- 第 2 次：根据报错做定点修复
- 第 3 次：再次最小修复并收敛
- 第 4 次仍失败：熔断，进入 `WAITING_APPROVAL`

这样可以兼顾成本和效果，避免无限循环。

### 6.4 错误分诊规则

建议将错误日志分成几类再回灌给模型：

- `SyntaxError`：优先检查补丁协议和局部替换是否破坏语法
- `ImportError` / `ModuleNotFoundError`：优先检查依赖、路径、导入顺序
- `AssertionError`：优先检查业务逻辑是否偏离 AC
- `ConnectionError` / `TimeoutError`：优先检查 mock、沙盒配置和超时
- `Lint` / `TypeError`：优先修局部规范问题，不扩大修改范围

### 6.5 何时停止重试

遇到以下情况必须停止自动修复：

- 同一类错误连续出现，且修复后无实质变化
- 补丁开始触及非计划文件
- 失败原因明显是环境问题而不是代码问题
- 需要人类确认设计方向或业务取舍

---

## 七、技能化的行为控制：可以借鉴什么

这一部分可以直接借鉴前一问提到的 skill 思路，用“规则文件 + 行为约束”控制 Agent。

### 7.1 推荐的控制载体

- `AGENTS.md`：主合同，定义阶段规则、修改边界和验证要求
- `agent_docs/code_patterns.md`：代码风格、架构模式、文件命名、变更纪律
- `agent_docs/testing.md`：测试策略、mock 策略、运行命令、失败处理
- `MEMORY.md`：记录当前阶段、已完成工作、已知风险
- 如需更细粒度控制，可为代码生成与测试生成各自增加独立规则文件

### 7.2 可直接注入的行为规则

适合放进代码生成 / 测试生成的规则包括：

- 只允许修改 `file_change_plan` 中列出的文件
- 不要重写整个文件，优先做局部替换
- 不要删除文件，除非方案里明确允许并经过确认
- 不要修改无关模块
- 不要绕过失败测试
- 不要为了通过测试而弱化断言或跳过 mock
- 新增公共函数必须配套测试
- 外部依赖必须隔离，不允许直接访问真实服务
- 遇到重复失败时先缩小修改面，而不是扩大重构面

### 7.3 适合做成“Skill 风格”的规则包

如果后续要把这套能力做成可复用规范，可以拆成：

- `codegen-sop.md`：代码生成标准作业程序
- `sdet-sop.md`：测试生成和自愈规则
- `review-checklist.md`：交付前审查清单

它们不一定非要是 VS Code Skill，也可以是仓库内通用的 Markdown 规范包。

---

## 八、与后续测试生成的衔接

代码生成和测试生成之间不要靠自然语言“顺嘴交接”，而要靠结构化上下文：

1. CodeGen 输出 `code_diff`
2. `code_diff` 作为测试生成 Agent 的主输入
3. 测试生成 Agent 根据 `code_diff` + AC 生成测试点
4. Runner 执行测试命令并回传日志
5. 日志进入 Triage，再决定是否回到 CodeGen

这条链路的核心是：**Diff 先于测试，测试先于修复，修复必须可追踪**。

---

## 九、建议的最终接口

### 9.1 Code Executor 输入 / 输出

输入：

- `requirement_structured`
- `design`
- `codebase_context`

输出：

- `code_diff`

### 9.2 SDET 输入 / 输出

输入：

- `code_diff`
- `requirement_structured`

输出：

- `tests`

### 9.3 Runner 输入 / 输出

输入：

- `tests.runner_commands`
- `repo_path`
- `sandbox_config`

输出：

- `tests.sandbox_result`

---

## 十、落地优先级

建议按下面顺序实现：

1. 先把 `code_diff` 定义成结构化 Diff Bundle
2. 再接上沙盒 Runner
3. 再实现 SDET 的 AC-to-Test 映射
4. 最后加自愈循环和熔断机制

这样可以先跑通单次生成，再逐步增强闭环能力，风险更低。
