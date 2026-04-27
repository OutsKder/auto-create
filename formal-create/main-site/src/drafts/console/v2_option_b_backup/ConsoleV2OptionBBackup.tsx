import { useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  Bot,
  CheckCircle2,
  Clock3,
  Code2,
  FileText,
  GitMerge,
  LogOut,
  Loader2,
  MessageSquareText,
  Plus,
  Rocket,
  Search,
  ShieldCheck,
  Sparkles,
  Terminal,
  UserCircle,
  Workflow,
} from "lucide-react";
import WeaveMark from "../../../components/WeaveMark";

type PipelineState = "CREATED" | "RUNNING" | "WAITING_APPROVAL" | "FINISHED";
type RoleKey = "first" | "product" | "tech" | "manager";
type ProjectStage = "empty" | "planned" | "running";

type AgentStatus = "done" | "current" | "waiting" | "pending";

type AgentStage = {
  title: string;
  agent: string;
  output: string;
  icon: typeof FileText;
};

type RoleLens = {
  key: RoleKey;
  label: string;
  shortLabel: string;
  eyebrow: string;
  title: string;
  description: string;
  inputTitle: string;
  inputHint: string;
  placeholder: string;
  outputHint: string;
  templates: string[];
  previewTitle: string;
  previewHint: string;
  emptyTitle: string;
  emptyText: string;
  insights: Array<{
    label: string;
    value: string;
    hint: string;
  }>;
  checkpoint: {
    title: string;
    summary: string;
    primary: string;
  };
};

const ROLE_LENS: Record<RoleKey, RoleLens> = {
  first: {
    key: "first",
    label: "第一次使用",
    shortLabel: "新手",
    eyebrow: "Guided Workspace",
    title: "跟着提示创建第一条流水线。",
    description:
      "先输入一句需求。系统会解释每个状态、每个产物，以及什么时候需要你做判断。",
    inputTitle: "告诉我你想做什么",
    inputHint: "不用写 PRD，也不用懂技术术语。",
    placeholder: "例如：我想给博客增加评论功能，需要能审核评论。",
    outputHint: "你会看到：需求解释、当前状态、审批提醒、下一步建议。",
    templates: [
      "我想给博客增加评论功能，需要能审核评论。",
      "我想做一个团队知识库搜索页，能搜索 Markdown 文档。",
      "我想给订单系统增加退款审批流程。",
    ],
    previewTitle: "新手引导预览",
    previewHint: "每个节点都会解释“发生了什么”和“你要做什么”。",
    emptyTitle: "还没有流水线",
    emptyText:
      "在左侧输入一句需求。创建后，这里会一步步解释 AI 正在做什么。",
    insights: [
      { label: "下一步", value: "输入需求", hint: "从一句话开始" },
      { label: "引导强度", value: "高", hint: "解释状态和按钮" },
      { label: "默认展开", value: "状态说明", hint: "先看懂流程" },
    ],
    checkpoint: {
      title: "这里需要你确认",
      summary:
        "AI 已经生成方案。你只需要判断方向是否正确，不需要一次看懂所有技术细节。",
      primary: "查看审批说明",
    },
  },
  product: {
    key: "product",
    label: "产品 / 业务",
    shortLabel: "产品",
    eyebrow: "Product Lens",
    title: "先判断 AI 有没有理解业务。",
    description:
      "默认突出需求理解、用户故事、边界条件和验收标准，帮助你把控交付方向。",
    inputTitle: "描述业务目标",
    inputHint: "写清用户、场景、边界和验收口径。",
    placeholder:
      "例如：给博客增加评论功能，支持登录用户评论、管理员审核、敏感词过滤。",
    outputHint: "预估会生成：用户故事、边界条件、验收标准、审批建议。",
    templates: [
      "给博客增加评论功能，支持登录用户评论、管理员审核、敏感词过滤。",
      "为订单系统增加退款审批流程，需要保留完整操作日志。",
      "做一个团队知识库搜索页，支持 Markdown 文档和语义检索。",
    ],
    previewTitle: "需求理解预览",
    previewHint: "默认先看 AI 是否正确理解业务意图。",
    emptyTitle: "等待业务需求",
    emptyText:
      "输入目标用户、使用场景和边界条件。AI 会先产出可审阅的需求拆解。",
    insights: [
      { label: "默认重点", value: "验收标准", hint: "判断需求是否完整" },
      { label: "风险提示", value: "边界缺失", hint: "提醒补充约束" },
      { label: "审批视角", value: "业务方向", hint: "先确认做对事" },
    ],
    checkpoint: {
      title: "需求与验收等待确认",
      summary:
        "重点检查用户故事、边界条件和验收标准是否符合业务目标。通过后再进入工程实现。",
      primary: "审阅需求拆解",
    },
  },
  tech: {
    key: "tech",
    label: "技术负责人",
    shortLabel: "技术",
    eyebrow: "Engineering Lens",
    title: "先看架构、接口和代码风险。",
    description:
      "默认突出模块边界、API、状态机、测试策略和 MR 信息，帮助你判断方案能不能落地。",
    inputTitle: "描述工程任务",
    inputHint: "可以补充技术约束、接口、数据模型或兼容性要求。",
    placeholder:
      "例如：为订单系统增加退款审批流程，需要保留操作日志并兼容现有状态机。",
    outputHint: "预估会生成：架构方案、接口设计、代码 Diff、测试报告、MR 链接。",
    templates: [
      "为订单系统增加退款审批流程，需要保留操作日志并兼容现有状态机。",
      "给评论功能增加敏感词过滤，要求可配置词库和单元测试。",
      "为知识库搜索增加语义检索 API，并保留关键词搜索兜底。",
    ],
    previewTitle: "工程执行预览",
    previewHint: "默认先看架构和实现风险。",
    emptyTitle: "等待工程需求",
    emptyText:
      "输入任务和约束。AI 会优先输出架构边界、接口设计和测试建议。",
    insights: [
      { label: "默认重点", value: "架构方案", hint: "模块边界是否清晰" },
      { label: "风险提示", value: "状态兼容", hint: "关注回滚和测试" },
      { label: "审批视角", value: "可合并性", hint: "先确认能落地" },
    ],
    checkpoint: {
      title: "架构方案等待审批",
      summary:
        "重点检查模块边界、API 设计、状态机影响和测试覆盖。通过后继续生成代码与 MR。",
      primary: "审阅架构方案",
    },
  },
  manager: {
    key: "manager",
    label: "管理者",
    shortLabel: "管理",
    eyebrow: "Delivery Lens",
    title: "先看进度、风险和是否需要介入。",
    description:
      "默认突出流水线状态、审批等待、风险摘要和交付结果，帮助你快速判断项目是否可控。",
    inputTitle: "创建交付事项",
    inputHint: "用业务语言描述目标即可，系统会拆成可跟踪流程。",
    placeholder: "例如：本周完成评论功能闭环，要求可审核、可测试、可交付 MR。",
    outputHint: "预估会生成：进度总览、阻塞点、风险提示、交付摘要。",
    templates: [
      "本周完成评论功能闭环，要求可审核、可测试、可交付 MR。",
      "推进退款审批流程上线，重点关注风险、阻塞和审批等待。",
      "完成知识库搜索 MVP，要求能看到进度、风险和最终交付物。",
    ],
    previewTitle: "交付状态预览",
    previewHint: "默认先看是否阻塞、是否需要审批、是否接近交付。",
    emptyTitle: "等待交付目标",
    emptyText:
      "输入一个交付目标。AI 会把它转成可跟踪流水线，并突出风险和状态。",
    insights: [
      { label: "默认重点", value: "风险状态", hint: "是否需要介入" },
      { label: "审批等待", value: "实时提示", hint: "减少流程阻塞" },
      { label: "交付摘要", value: "可追踪", hint: "看结果不看细节" },
    ],
    checkpoint: {
      title: "关键审批正在阻塞交付",
      summary:
        "当前流水线停在人工审批点。处理后即可继续生成代码、测试和 MR 交付摘要。",
      primary: "处理阻塞",
    },
  },
};

const roleOrder: RoleKey[] = ["first", "product", "tech", "manager"];

const DEMO_REQUIREMENT =
  "给博客增加评论功能：登录用户可评论，管理员可审核，敏感词自动拦截，并生成可合并 MR。";

const agentStages: AgentStage[] = [
  {
    title: "需求分析",
    agent: "Requirement Agent",
    output: "结构化需求 / 验收标准",
    icon: MessageSquareText,
  },
  {
    title: "方案设计",
    agent: "Architecture Agent",
    output: "技术方案 / 影响范围",
    icon: Workflow,
  },
  {
    title: "代码生成",
    agent: "Coding Agent",
    output: "代码变更集 / Diff",
    icon: Code2,
  },
  {
    title: "测试生成",
    agent: "Test Agent",
    output: "测试代码 / 执行结果",
    icon: CheckCircle2,
  },
  {
    title: "代码评审",
    agent: "Review Agent",
    output: "评审报告 / 修复建议",
    icon: ShieldCheck,
  },
  {
    title: "交付集成",
    agent: "Delivery Agent",
    output: "MR / 变更摘要",
    icon: GitMerge,
  },
];

export default function ConsoleV2Geek() {
  const [selectedRole, setSelectedRole] = useState<RoleKey>("first");
  const [requirement, setRequirement] = useState(DEMO_REQUIREMENT);
  const [pipelineState, setPipelineState] = useState<PipelineState>("CREATED");
  const [hasCreated, setHasCreated] = useState(false);
  const [hasPlan, setHasPlan] = useState(false);
  const [hasApproved, setHasApproved] = useState(false);
  const activeLens = ROLE_LENS[selectedRole];

  const activeRequirement = requirement.trim() || activeLens.templates[0];

  const projectStage: ProjectStage = hasCreated ? "running" : hasPlan ? "planned" : "empty";

  function generateDeliveryPlan() {
    if (!activeRequirement) return;
    setHasPlan(true);
    setHasCreated(false);
    setHasApproved(false);
    setPipelineState("CREATED");
  }

  function confirmPlanAndRun() {
    setHasPlan(true);
    setHasCreated(true);
    setHasApproved(false);
    setPipelineState("RUNNING");
    window.setTimeout(() => setPipelineState("WAITING_APPROVAL"), 900);
  }

  function approveCheckpoint() {
    setHasApproved(true);
    setPipelineState("RUNNING");
    window.setTimeout(() => setPipelineState("FINISHED"), 700);
  }

  function rejectCheckpoint() {
    setHasCreated(false);
    setHasPlan(true);
    setHasApproved(false);
    setPipelineState("CREATED");
  }

  function resetDemo() {
    setRequirement(DEMO_REQUIREMENT);
    setHasCreated(false);
    setHasPlan(false);
    setHasApproved(false);
    setPipelineState("CREATED");
  }

  function handlePrimaryAction() {
    if (projectStage === "empty") {
      generateDeliveryPlan();
    }
  }

  return (
    <div className="h-screen bg-ink-950 text-white relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0 bg-grid-dark bg-grid-24 opacity-50" />
      <div className="pointer-events-none absolute -top-32 left-1/2 h-[520px] w-[820px] -translate-x-1/2 rounded-full bg-weave-500/20 blur-[140px]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[420px] w-[520px] rounded-full bg-glow-violet/15 blur-[130px]" />

      <div className="relative flex h-screen overflow-hidden">
        <aside className="hidden w-[88px] flex-col border-r border-white/[0.06] bg-black/25 backdrop-blur-xl lg:flex">
          <div className="flex h-[76px] items-center justify-center border-b border-white/[0.06]">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-weave-500 to-glow-violet shadow-glow-sm">
              <WeaveMark className="h-4 w-4" />
            </div>
          </div>

          <nav className="flex flex-col items-center gap-2 p-3 text-xs">
            {[
              { icon: Rocket, label: "项目", active: true },
              { icon: FileText, label: "制品" },
              { icon: ShieldCheck, label: "审批" },
              { icon: Bot, label: "设置" },
            ].map((item) => (
              <button
                key={item.label}
                title={item.label}
                className={`flex h-14 w-14 flex-col items-center justify-center gap-1 rounded-2xl transition-colors ${
                  item.active
                    ? "bg-white/[0.08] text-white"
                    : "text-white/55 hover:text-white hover:bg-white/[0.04]"
                }`}
              >
                <item.icon className="h-4 w-4" />
                <span className="text-[10px] leading-none">{item.label}</span>
              </button>
            ))}
          </nav>

          <div className="mt-auto p-3">
            <div
              className="flex h-12 w-full items-center justify-center rounded-2xl border border-white/[0.08] bg-white/[0.03] text-weave-300"
              title="Alpha Workspace"
            >
              <Sparkles className="h-4 w-4" />
            </div>
          </div>
        </aside>

        <main className="flex min-h-0 flex-1 flex-col bg-ink-950/35">
          <TopStatusBar
            lens={activeLens}
            requirement={activeRequirement}
            state={pipelineState}
            selectedRole={selectedRole}
            onRoleChange={setSelectedRole}
          />

          <div className="min-h-0 flex-1 overflow-hidden p-3 md:p-4">
            <div className="grid h-full min-h-0 grid-cols-1 gap-3 overflow-y-auto lg:grid-cols-[minmax(190px,0.72fr)_minmax(300px,1.36fr)_minmax(200px,0.82fr)] lg:overflow-hidden xl:grid-cols-[240px_minmax(420px,1fr)_280px]">
              <section className="flex min-h-[520px] flex-col overflow-hidden rounded-2xl border border-white/[0.08] bg-white/[0.03] backdrop-blur-xl lg:min-h-0">
                <div className="flex-none px-5 py-4 border-b border-white/[0.06] flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] font-mono text-white/30">01</span>
                      <h2 className="text-sm font-semibold">项目启动器</h2>
                    </div>
                    <p className="mt-1 text-xs text-white/45">
                      输入目标，先生成计划，再启动执行。
                    </p>
                  </div>
                  <span className="text-[11px] font-mono text-white/35">
                    POST /pipelines
                  </span>
                </div>

                <div className="min-h-0 flex-1 overflow-y-auto p-4">
                  <textarea
                    value={requirement}
                    onChange={(event) => setRequirement(event.target.value)}
                    placeholder={activeLens.placeholder}
                    className="min-h-32 w-full resize-none rounded-xl border border-white/[0.08] bg-black/30 px-4 py-3 text-sm leading-relaxed text-white placeholder:text-white/25 outline-none transition-all focus:border-weave-400/50 focus:ring-4 focus:ring-weave-500/10"
                  />

                  <div className="mt-4 flex flex-wrap gap-2">
                    {activeLens.templates.map((template) => (
                      <button
                        key={template}
                        onClick={() => setRequirement(template)}
                        className="rounded-full border border-white/[0.08] bg-white/[0.03] px-3 py-1.5 text-xs text-white/55 hover:text-white hover:bg-white/[0.06] transition-colors"
                      >
                        {template.slice(0, 20)}...
                      </button>
                    ))}
                  </div>

                  <DemoExperienceCard
                    stage={projectStage}
                    state={pipelineState}
                    hasApproved={hasApproved}
                    onReset={resetDemo}
                  />

                  {hasPlan && !hasCreated && (
                    <DeliveryPlanCard
                      lens={activeLens}
                      requirement={activeRequirement}
                    />
                  )}

                  <div className="sticky bottom-0 -mx-4 -mb-4 mt-5 flex flex-col gap-3 border-t border-white/[0.06] bg-ink-950/90 px-4 py-4 backdrop-blur-xl">
                    <div className="text-xs text-white/40">
                      {activeLens.outputHint}
                    </div>
                    <button
                      onClick={handlePrimaryAction}
                      disabled={hasPlan || hasCreated}
                      className={`h-11 rounded-xl px-5 text-sm font-semibold transition-colors ${
                        hasPlan || hasCreated
                          ? "cursor-not-allowed border border-white/[0.08] bg-white/[0.03] text-white/35"
                          : "btn-glow"
                      }`}
                    >
                      {hasCreated ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin" />
                          已交给操作台
                        </>
                      ) : hasPlan ? (
                        <>
                          <CheckCircle2 className="h-4 w-4" />
                          计划已生成
                        </>
                      ) : (
                        <>
                          <Rocket className="h-4 w-4" />
                          生成交付计划
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </section>

              <AgentPipeline
                stage={projectStage}
                state={pipelineState}
              />

              <aside className="flex min-h-[520px] flex-col overflow-hidden rounded-2xl border border-white/[0.08] bg-black/35 backdrop-blur-xl lg:min-h-0">
                <div className="flex-none px-5 py-4 border-b border-white/[0.06] flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] font-mono text-white/30">03</span>
                      <h2 className="text-sm font-semibold">当前节点操作台</h2>
                    </div>
                    <p className="mt-1 text-xs text-white/45">
                      查看产物，处理审批，拿到交付包。
                    </p>
                  </div>
                  <StateBadge state={pipelineState} />
                </div>

                <div className="min-h-0 flex-1 overflow-y-auto p-5">
                  {hasPlan && !hasCreated ? (
                    <PlanPreview
                      lens={activeLens}
                      requirement={activeRequirement}
                      onConfirm={confirmPlanAndRun}
                    />
                  ) : !hasCreated ? (
                    <EmptyPreview lens={activeLens} />
                  ) : (
                    <PipelinePreview
                      requirement={activeRequirement}
                      state={pipelineState}
                      lens={activeLens}
                      onApprove={approveCheckpoint}
                      onReject={rejectCheckpoint}
                    />
                  )}
                </div>
              </aside>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

function StateBadge({ state }: { state: PipelineState }) {
  const map = {
    CREATED: "text-white/45 bg-white/[0.04] border-white/[0.08]",
    RUNNING: "text-weave-300 bg-weave-500/10 border-weave-400/20",
    WAITING_APPROVAL: "text-amber-300 bg-amber-500/10 border-amber-400/20",
    FINISHED: "text-emerald-300 bg-emerald-500/10 border-emerald-400/20",
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-mono ${map[state]}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {state}
    </span>
  );
}

function TopStatusBar({
  lens,
  requirement,
  state,
  selectedRole,
  onRoleChange,
}: {
  lens: RoleLens;
  requirement: string;
  state: PipelineState;
  selectedRole: RoleKey;
  onRoleChange: (role: RoleKey) => void;
}) {
  return (
    <header className="flex h-[76px] flex-none items-center justify-between gap-4 border-b border-white/[0.07] bg-ink-950/75 px-5 backdrop-blur-xl md:px-6">
      <div className="flex min-w-0 items-center gap-4">
        <Link
          to="/drafts/landing/v2"
          className="hidden h-10 w-10 flex-none items-center justify-center rounded-xl border border-white/[0.08] bg-white/[0.03] text-white/45 transition-colors hover:bg-white/[0.06] hover:text-weave-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-weave-400/35 md:flex"
          aria-label="返回官网"
        >
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1.5 text-[11px] font-mono uppercase tracking-[0.16em] text-weave-200/80">
              <Terminal className="h-3.5 w-3.5" />
              Project Cockpit
            </span>
            <StateBadge state={state} />
            <span className="rounded-full border border-white/[0.08] bg-white/[0.03] px-2.5 py-1 text-[11px] text-white/40">
              {lens.label}
            </span>
          </div>
          <div className="mt-1 flex min-w-0 items-baseline gap-3">
            <h1 className="hidden shrink-0 text-sm font-semibold text-white xl:block">
              当前项目
            </h1>
            <p className="min-w-0 truncate text-sm text-white/65">
              {requirement}
            </p>
          </div>
        </div>
      </div>
      <div className="flex flex-none items-center gap-2">
        <RoleLensSwitcher selectedRole={selectedRole} onChange={onRoleChange} />
        <ContextActions />
      </div>
    </header>
  );
}

function ContextActions() {
  return (
    <>
      <Link
        to="/drafts/landing/v2"
        className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-white/[0.08] bg-white/[0.03] px-3 text-xs font-mono text-white/45 transition-colors hover:bg-white/[0.06] hover:text-weave-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-weave-400/35"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Landing
      </Link>
      <div className="hidden h-9 items-center gap-2 rounded-lg border border-white/[0.08] bg-black/20 px-3 text-sm text-white/40 md:flex">
        <Search className="h-4 w-4" />
        搜索项目 / MR
      </div>
      <button className="inline-flex h-9 items-center gap-2 rounded-lg bg-white px-3 text-sm font-medium text-ink-950 transition-colors hover:bg-white/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/30">
        <Plus className="h-4 w-4" />
        新建
      </button>
      <button className="inline-flex h-9 items-center gap-2 rounded-lg border border-white/[0.08] bg-white/[0.03] px-3 text-sm text-white/60 transition-colors hover:bg-white/[0.06] hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/20">
        <UserCircle className="h-4 w-4" />
        Demo
        <LogOut className="h-3.5 w-3.5 text-white/35" />
      </button>
    </>
  );
}

function getAgentStatus(
  index: number,
  stage: ProjectStage,
  state: PipelineState
): AgentStatus {
  if (stage === "empty") return "pending";
  if (stage === "planned") return index === 0 ? "current" : "pending";
  if (state === "FINISHED") return "done";
  if (state === "WAITING_APPROVAL") {
    if (index === 0) return "done";
    if (index === 1) return "waiting";
    return "pending";
  }
  if (state === "RUNNING") {
    if (index === 0) return "done";
    if (index === 1) return "current";
    return "pending";
  }
  return "pending";
}

function AgentPipeline({
  stage,
  state,
}: {
  stage: ProjectStage;
  state: PipelineState;
}) {
  return (
    <section className="flex min-h-[620px] flex-col overflow-hidden rounded-[1.35rem] border border-weave-400/20 bg-gradient-to-b from-weave-500/10 via-black/30 to-black/25 shadow-[0_0_42px_rgba(96,135,255,0.10)] backdrop-blur-xl lg:min-h-0">
      <div className="flex-none border-b border-white/[0.06] px-5 py-4">
        <div className="flex items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-mono text-white/30">02</span>
              <h2 className="text-sm font-semibold">Agent Pipeline</h2>
            </div>
            <p className="mt-1 text-xs text-white/45">
              主舞台：AI 分阶段推进，人类只在关键点介入。
            </p>
          </div>
          <span className="rounded-full border border-white/[0.08] bg-white/[0.035] px-2 py-1 text-[11px] font-mono text-white/40">
            {state}
          </span>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-5">
        <div className="relative space-y-3">
          <div className="absolute bottom-6 left-[1.15rem] top-6 w-px bg-gradient-to-b from-weave-400/50 via-white/10 to-transparent" />
          {agentStages.map((agent, index) => {
            const status = getAgentStatus(index, stage, state);
            const Icon = agent.icon;
            return (
              <div
                key={agent.title}
                className={`relative rounded-2xl border p-4 transition-colors ${
                  status === "waiting"
                    ? "border-amber-400/25 bg-amber-500/10"
                    : status === "current"
                    ? "border-weave-400/25 bg-weave-500/10"
                    : status === "done"
                    ? "border-emerald-400/20 bg-emerald-500/10"
                    : "border-white/[0.07] bg-white/[0.025]"
                }`}
              >
                <div className="flex items-start gap-3">
                  <div
                    className={`relative z-10 flex h-9 w-9 flex-none items-center justify-center rounded-xl ${
                      status === "waiting"
                        ? "bg-amber-500/14 text-amber-300"
                        : status === "current"
                        ? "bg-weave-500/14 text-weave-300"
                        : status === "done"
                        ? "bg-emerald-500/14 text-emerald-300"
                        : "bg-white/[0.04] text-white/30"
                    }`}
                  >
                    {status === "done" ? (
                      <CheckCircle2 className="h-4 w-4" />
                    ) : status === "current" ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : status === "waiting" ? (
                      <ShieldCheck className="h-4 w-4" />
                    ) : (
                      <Icon className="h-4 w-4" />
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="text-sm font-semibold">{agent.title}</div>
                        <div className="mt-0.5 text-[11px] font-mono text-white/35">
                          {agent.agent}
                        </div>
                      </div>
                      <span
                        className={`rounded-full px-2 py-0.5 text-[10px] font-mono ${
                          status === "waiting"
                            ? "bg-amber-500/10 text-amber-300"
                            : status === "current"
                            ? "bg-weave-500/10 text-weave-300"
                            : status === "done"
                            ? "bg-emerald-500/10 text-emerald-300"
                            : "bg-white/[0.04] text-white/30"
                        }`}
                      >
                        {status}
                      </span>
                    </div>
                    <p className="mt-2 text-xs leading-relaxed text-white/45">
                      输出：{agent.output}
                    </p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function DemoExperienceCard({
  stage,
  state,
  hasApproved,
  onReset,
}: {
  stage: ProjectStage;
  state: PipelineState;
  hasApproved: boolean;
  onReset: () => void;
}) {
  const currentStep =
    stage === "empty"
      ? 0
      : stage === "planned"
      ? 1
      : state === "WAITING_APPROVAL"
      ? 2
      : state === "FINISHED"
      ? 4
      : hasApproved
      ? 3
      : 2;

  const steps = [
    "生成交付计划",
    "在右侧确认启动",
    "在右侧审批方案",
    "等待交付完成",
  ];

  return (
    <div className="mt-4 rounded-2xl border border-white/[0.08] bg-white/[0.025] p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="text-xs font-semibold text-white/80">示例体验路线</div>
          <p className="mt-1 text-xs leading-relaxed text-white/40">
            左侧只生成计划；所有确认、审批和交付决策都在右侧操作台完成。
          </p>
        </div>
        <button
          onClick={onReset}
          className="rounded-lg border border-white/[0.08] bg-black/20 px-2.5 py-1.5 text-[11px] text-white/50 transition-colors hover:bg-white/[0.06] hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/20"
        >
          重置
        </button>
      </div>
      <div className="mt-3 space-y-2">
        {steps.map((step, index) => {
          const done = currentStep > index;
          const active = currentStep === index;
          return (
            <div
              key={step}
              className={`flex items-center gap-2 rounded-xl px-3 py-2 text-xs ${
                done
                  ? "bg-emerald-500/10 text-emerald-200"
                  : active
                  ? "bg-weave-500/10 text-weave-200"
                  : "bg-black/20 text-white/35"
              }`}
            >
              <span className="font-mono text-[10px]">{String(index + 1).padStart(2, "0")}</span>
              <span>{step}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function DeliveryPlanCard({
  lens,
  requirement,
}: {
  lens: RoleLens;
  requirement: string;
}) {
  const planItems = [
    {
      label: "理解目标",
      text:
        lens.key === "tech"
          ? "提取技术约束、接口边界和状态影响"
          : lens.key === "manager"
          ? "提取交付目标、风险点和审批阻塞"
          : lens.key === "product"
          ? "提取用户场景、边界条件和验收标准"
          : "把一句需求翻译成可执行任务",
    },
    {
      label: "生成路径",
      text: "需求澄清 -> 架构方案 -> 代码生成 -> 测试 & MR",
    },
    {
      label: "设置闸门",
      text: "在关键节点暂停，等待你批准或退回修改",
    },
  ];

  return (
    <div className="mt-5 rounded-2xl border border-weave-400/20 bg-weave-500/10 p-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-xs font-medium text-weave-200">交付计划已生成</div>
          <p className="mt-1 line-clamp-2 text-sm leading-relaxed text-white/70">
            {requirement}
          </p>
        </div>
        <Sparkles className="h-4 w-4 flex-none text-weave-300" />
      </div>
      <div className="mt-4 grid gap-2 md:grid-cols-3">
        {planItems.map((item) => (
          <div
            key={item.label}
            className="rounded-xl border border-white/[0.08] bg-black/20 p-3"
          >
            <div className="text-[11px] font-medium text-white/45">{item.label}</div>
            <div className="mt-1 text-xs leading-relaxed text-white/65">{item.text}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function PlanPreview({
  lens,
  requirement,
  onConfirm,
}: {
  lens: RoleLens;
  requirement: string;
  onConfirm: () => void;
}) {
  return (
    <div className="min-h-[360px]">
      <div className="rounded-xl border border-white/[0.08] bg-white/[0.03] p-4">
        <div className="text-[11px] font-mono text-white/35">PLAN / PIP-DRAFT</div>
        <h3 className="mt-1 text-sm font-semibold leading-relaxed">{requirement}</h3>
      </div>

      <div className="mt-5 space-y-3">
        {[
          ["01", "确认目标", lens.outputHint],
          ["02", "生成路径", "AI 会先产出需求、架构、代码和测试的执行顺序。"],
          ["03", "等待审批", lens.checkpoint.summary],
        ].map(([index, title, desc]) => (
          <div
            key={title}
            className="rounded-xl border border-white/[0.08] bg-white/[0.025] p-4"
          >
            <div className="flex items-center justify-between">
              <span className="font-mono text-[11px] text-white/35">{index}</span>
              <CheckCircle2 className="h-4 w-4 text-weave-300" />
            </div>
            <div className="mt-3 text-sm font-semibold">{title}</div>
            <p className="mt-1 text-xs leading-relaxed text-white/45">{desc}</p>
          </div>
        ))}
      </div>

      <button
        onClick={onConfirm}
        className="mt-5 inline-flex h-9 items-center gap-2 rounded-lg bg-white px-4 text-sm font-medium text-ink-950 transition-colors hover:bg-white/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/30"
      >
        确认计划并启动
        <ArrowRight className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}

function RoleLensSwitcher({
  selectedRole,
  onChange,
}: {
  selectedRole: RoleKey;
  onChange: (role: RoleKey) => void;
}) {
  return (
    <div className="flex h-9 items-center gap-1 rounded-lg border border-white/[0.08] bg-black/20 p-1">
      <span className="hidden px-2 text-[11px] text-white/35 sm:inline">视角</span>
      <div className="flex items-center gap-1">
        {roleOrder.map((role) => {
          const lens = ROLE_LENS[role];
          const active = selectedRole === role;
          return (
            <button
              key={role}
              onClick={() => onChange(role)}
              className={`h-7 rounded-md px-2.5 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-weave-400/35 ${
                active
                  ? "bg-white text-ink-950"
                  : "text-white/55 hover:bg-white/[0.06] hover:text-white"
              }`}
            >
              {lens.shortLabel}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function EmptyPreview({ lens }: { lens: RoleLens }) {
  return (
    <div className="min-h-[360px] flex flex-col items-center justify-center text-center">
      <div className="relative">
        <div className="absolute inset-0 rounded-full bg-weave-500/20 blur-2xl" />
        <div className="relative h-14 w-14 rounded-2xl border border-white/[0.08] bg-white/[0.04] flex items-center justify-center">
          <Sparkles className="h-6 w-6 text-weave-300" />
        </div>
      </div>
      <h3 className="mt-5 text-base font-semibold">{lens.emptyTitle}</h3>
      <p className="mt-2 max-w-xs text-sm leading-relaxed text-white/45">
        {lens.emptyText}
      </p>
    </div>
  );
}

function PipelinePreview({
  requirement,
  state,
  lens,
  onApprove,
  onReject,
}: {
  requirement: string;
  state: PipelineState;
  lens: RoleLens;
  onApprove: () => void;
  onReject: () => void;
}) {
  if (state === "FINISHED") {
    return <DeliveryPackage requirement={requirement} lens={lens} />;
  }

  return (
    <div>
      <div className="rounded-xl border border-white/[0.08] bg-white/[0.03] p-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="text-[11px] font-mono text-white/35">PIP-2046</div>
            <h3 className="mt-1 text-sm font-semibold leading-relaxed">
              {requirement}
            </h3>
          </div>
          <Clock3 className="h-4 w-4 text-white/30 flex-none" />
        </div>
      </div>

      <div className="mt-5 rounded-xl border border-white/[0.08] bg-white/[0.025] p-4">
        <div className="flex items-center gap-2 text-sm font-semibold">
          {state === "WAITING_APPROVAL" ? (
            <ShieldCheck className="h-4 w-4 text-amber-300" />
          ) : (
            <Loader2 className="h-4 w-4 animate-spin text-weave-300" />
          )}
          {state === "WAITING_APPROVAL" ? "方案设计等待人工审批" : "Architecture Agent 正在生成方案"}
        </div>
        <p className="mt-2 text-xs leading-relaxed text-white/45">
          {state === "WAITING_APPROVAL"
            ? "当前节点已产出技术方案。请在下方做 Approve / Reject 决策。"
            : "AI 正在基于需求上下文生成方案、影响范围和下一步代码生成输入。"}
        </p>
      </div>

      <div className="mt-5 rounded-xl border border-white/[0.08] bg-black/45 overflow-hidden">
        <div className="px-4 py-2.5 border-b border-white/[0.06] flex items-center justify-between">
          <span className="text-xs font-medium text-white/70">Agent Log</span>
          <span className="text-[11px] font-mono text-white/30">
            GET /pipelines/PIP-2046
          </span>
        </div>
        <div className="p-4 font-mono text-[12px] leading-6">
          <p className="text-emerald-300">✓ requirement.normalized</p>
          <p className="text-emerald-300">✓ stories.generated: 3</p>
          <p className="text-weave-300">→ architecture.drafting...</p>
          {state === "WAITING_APPROVAL" && (
            <p className="text-amber-300">◆ checkpoint.required: architecture_v1</p>
          )}
        </div>
      </div>

      {state === "WAITING_APPROVAL" && (
        <div className="mt-5 rounded-xl border border-amber-400/20 bg-amber-500/10 p-4">
          <div className="flex items-center gap-2 text-sm font-semibold text-amber-200">
            <ShieldCheck className="h-4 w-4" />
            {lens.checkpoint.title}
          </div>
          <p className="mt-2 text-xs leading-relaxed text-amber-100/60">
            {lens.checkpoint.summary}
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <button
              onClick={onReject}
              className="inline-flex h-8 items-center rounded-lg border border-amber-200/20 bg-black/20 px-3 text-xs font-medium text-amber-100/75 transition-colors hover:bg-black/30 hover:text-amber-50"
            >
              退回并补充约束
            </button>
            <button
              onClick={onApprove}
              className="inline-flex h-8 items-center gap-2 rounded-lg bg-amber-300 px-3 text-xs font-semibold text-ink-950 transition-colors hover:bg-amber-200"
            >
              批准继续交付
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function DeliveryPackage({
  requirement,
  lens,
}: {
  requirement: string;
  lens: RoleLens;
}) {
  const artifacts = [
    {
      title: "需求文档",
      desc:
        lens.key === "product"
          ? "用户故事、边界条件和验收标准已整理"
          : "需求目标、约束和交付范围已沉淀",
      icon: FileText,
    },
    {
      title: "架构方案",
      desc:
        lens.key === "tech"
          ? "模块边界、API 和状态机影响已标注"
          : "关键实现路径和风险已摘要",
      icon: Workflow,
    },
    {
      title: "测试摘要",
      desc: "单元测试、边界场景和回归建议已生成",
      icon: CheckCircle2,
    },
    {
      title: "Merge Request",
      desc: "MR #2046 已准备，可进入代码审阅",
      icon: GitMerge,
    },
  ];

  return (
    <div>
      <div className="rounded-xl border border-emerald-400/20 bg-emerald-500/10 p-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="text-[11px] font-mono text-emerald-200/65">
              FINISHED / DELIVERY PACKAGE
            </div>
            <h3 className="mt-1 text-sm font-semibold leading-relaxed">
              {requirement}
            </h3>
            <p className="mt-2 text-xs leading-relaxed text-emerald-100/60">
              流水线已完成，以下产物可以进入评审、验收或合并流程。
            </p>
          </div>
          <CheckCircle2 className="h-5 w-5 flex-none text-emerald-300" />
        </div>
      </div>

      <div className="mt-5 grid gap-3">
        {artifacts.map(({ title, desc, icon: Icon }) => (
          <div
            key={title}
            className="rounded-xl border border-white/[0.08] bg-white/[0.025] p-4"
          >
            <div className="flex items-start gap-3">
              <div className="flex h-9 w-9 flex-none items-center justify-center rounded-lg bg-emerald-500/12 text-emerald-300">
                <Icon className="h-4 w-4" />
              </div>
              <div>
                <div className="text-sm font-medium">{title}</div>
                <div className="mt-1 text-xs leading-relaxed text-white/45">{desc}</div>
              </div>
            </div>
          </div>
        ))}
      </div>

      <button className="mt-5 inline-flex h-9 items-center gap-2 rounded-lg bg-white px-4 text-sm font-medium text-ink-950 transition-colors hover:bg-white/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/30">
        打开 MR
        <ArrowRight className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}
