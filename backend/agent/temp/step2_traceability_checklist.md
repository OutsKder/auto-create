你这个判断完全正确，而且是关键拐点。现在这版 Step2 只是可运行原型，不是工程级系统。下一步应该从“可跑”转向“可扩展、可评估、可演进”。

结论

现在最缺的不是再加几个规则，而是检索架构分层。
expand_terms 和 rule_recall 必须从硬编码改成可配置、可插拔、可多语言。
Skill（编排层）和 RAG（检索层）要解耦：Skill 负责流程，RAG 负责召回质量。
接下来按优先级做什么

先做检索架构重构（P0，1-2天）
目标：把单文件逻辑拆成可插拔检索器接口。
要做：
定义 Retriever 接口（keyword、rule、semantic、symbol、dependency）。
定义统一 Candidate 数据结构（path、score、evidence、source）。
在 context_retrieval_step2.py 保留编排主流程，具体召回下沉到各 Retriever。
完成定义：
能按配置启停各召回通道。
不改主流程也能增加新通道。
把规则硬编码外置配置（P0，1天）
目标：摆脱测试仓库特化逻辑。
要做：
新增规则配置目录，例如 backend/agent/retrieval/rules。
把目前 term_map、zh_map、synonym_map 从代码迁移到 yaml/json。
支持“领域包”加载：web、backend、frontend、data、auth 等。
完成定义：
不改代码即可新增一个业务领域规则包。
同一代码能跑不同仓库（只换配置）。
接入真正 RAG 通道（P0/P1，2-3天）
目标：不是关键词拼凑，而是语义召回。
要做：
基于现有向量能力接入 semantic_recall（文件级先行）。
建立 chunk 策略（函数级切块），输出 chunk 命中证据。
与 keyword/rule 做融合重排。
完成定义：
查询“用户邮箱权限”能命中非显式同名文件。
evidence 中出现 semantic:chunk_id 之类证据。
做多语言符号与依赖图（P1，2-4天）
目标：扩展到多样代码库。
要做：
Python、TS/JS、Java、Go 先实现最小符号抽取器。
统一产出 symbol index（class/function/route/config key）。
依赖扩展从 import-only 升级为 import+call+route。
完成定义：
至少 3 种主流语言仓库可跑通。
dependency_signatures 不再偏 Python。
Skill 编排层落地（P1，1-2天）
目标：可控流程、可解释输出。
要做：
固化五步编排：读骨架 -> 拆 query -> 多通道召回 -> 覆盖门禁 -> 输出上下文。
Skill 只编排，不承担检索算法本体。
完成定义：
每次执行有固定阶段日志和中间产物。
失败可定位到具体阶段。
建评测与门禁（P0/P1，并行）
目标：从“感觉好”变成“指标好”。
要做：
构建 20-50 条需求-命中文件基准集。
指标：Recall@K、Coverage Pass Rate、平均候选量、延迟。
在门禁里增加“证据门禁”和“差异审计门禁”。
完成定义：
每次迭代都有可比较指标，不再拍脑袋调参。
对你现有代码最先改哪里

主编排保留在 context_retrieval_step2.py，先把函数拆成模块。
在 codebase_context.py 增加 Step2 配置透传（retriever 开关、规则包、语言 hint）。
在 tech_architect.py 保留覆盖门禁，但把错误信息结构化（错误码+未覆盖点+建议动作）。
建议你现在就执行的下一步（最务实）

先做“规则外置 + Retriever 接口化”，这是把原型变工程系统的分水岭。
然后接 semantic_recall，马上解决“只适配测试仓库”的核心问题。
再做多语言符号抽取与评测，进入可规模化阶段。
如果你同意，我下一条就可以直接开始落代码：先把 Retriever 接口层和规则配置层搭出来（不破坏你当前可运行链路）。