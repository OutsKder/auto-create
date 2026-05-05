import { useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  Bot,
  CheckCircle2,
  Clock3,
  FileText,
  GitMerge,
  LogOut,
  Loader2,
  MessageSquareText,
  Rocket,
  ShieldCheck,
  Sparkles,
  Terminal,
  UserCircle,
  Workflow,
} from "lucide-react";
import { pipelineApi } from "../../../api/pipelineApi";
import type { PipelineState } from "../../../api/pipelineApi";
import WeaveMark from "../../../components/WeaveMark";

type RoleKey = "first" | "product" | "tech" | "manager";
type ProjectStage = "empty" | "planned" | "running";

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

export default function ConsoleV3CalmCockpit() {
  const [selectedRole, setSelectedRole] = useState<RoleKey>("first");
  const [requirement, setRequirement] = useState(DEMO_REQUIREMENT);
  const [pipelineState, setPipelineState] = useState<PipelineState>("CREATED");
  const [hasCreated, setHasCreated] = useState(false);
  const [hasPlan, setHasPlan] = useState(false);
  const [hasApproved, setHasApproved] = useState(false);
  const [pipelineId, setPipelineId] = useState<string | null>(null);
  const [checkpointId, setCheckpointId] = useState<string | null>(null);
  const [isApiBusy, setIsApiBusy] = useState(false);
  const activeLens = ROLE_LENS[selectedRole];

  const activeRequirement = requirement.trim() || activeLens.templates[0];

  const projectStage: ProjectStage = hasCreated ? "running" : hasPlan ? "planned" : "empty";

  async function refreshPipeline(id: string) {
    const pipeline = await pipelineApi.getPipeline(id);
    setPipelineState(pipeline.state);
    setCheckpointId(pipeline.checkpoint?.id ?? null);
  }

  async function generateDeliveryPlan() {
    if (!activeRequirement) return;
    setIsApiBusy(true);
    try {
      const pipeline = await pipelineApi.createPipeline({ requirement: activeRequirement });
      setPipelineId(pipeline.id);
      setCheckpointId(pipeline.checkpoint?.id ?? null);
      setHasPlan(true);
      setHasCreated(false);
      setHasApproved(false);
      setPipelineState(pipeline.state);
    } finally {
      setIsApiBusy(false);
    }
  }

  async function confirmPlanAndRun() {
    if (!pipelineId) return;
    setIsApiBusy(true);
    try {
      const pipeline = await pipelineApi.runPipeline(pipelineId);
      setCheckpointId(pipeline.checkpoint?.id ?? null);
      setHasPlan(true);
      setHasCreated(true);
      setHasApproved(false);
      setPipelineState(pipeline.state);
      window.setTimeout(() => {
        void refreshPipeline(pipelineId);
      }, 950);
    } finally {
      setIsApiBusy(false);
    }
  }

  async function approveCheckpoint() {
    if (!checkpointId || !pipelineId) return;
    setIsApiBusy(true);
    try {
      const pipeline = await pipelineApi.approveCheckpoint(checkpointId);
      setHasApproved(true);
      setPipelineState(pipeline.state);
      setCheckpointId(pipeline.checkpoint?.id ?? checkpointId);
      window.setTimeout(() => {
        void refreshPipeline(pipelineId);
      }, 760);
    } finally {
      setIsApiBusy(false);
    }
  }

  async function rejectCheckpoint() {
    if (!checkpointId) return;
    setIsApiBusy(true);
    try {
      const pipeline = await pipelineApi.rejectCheckpoint(checkpointId, {
        reason: "需要补充接口约束后重新确认计划。",
      });
      setCheckpointId(pipeline.checkpoint?.id ?? null);
      setHasCreated(false);
      setHasPlan(true);
      setHasApproved(false);
      setPipelineState(pipeline.state);
    } finally {
      setIsApiBusy(false);
    }
  }

  function resetDemo() {
    setRequirement(DEMO_REQUIREMENT);
    setHasCreated(false);
    setHasPlan(false);
    setHasApproved(false);
    setPipelineId(null);
    setCheckpointId(null);
    setPipelineState("CREATED");
  }

  return (
    <div className="relative h-screen overflow-hidden bg-[#0b0b12] text-white">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_42%_-18%,rgba(139,92,246,0.16),transparent_34%),radial-gradient(circle_at_88%_18%,rgba(236,72,153,0.12),transparent_30%),linear-gradient(135deg,#0b0b12_0%,#11111a_52%,#0b0810_100%)]" />
      <div className="stellar-field pointer-events-none" />
      <div className="pointer-events-none absolute -top-40 left-[18%] h-[520px] w-[620px] rounded-full bg-weave-500/16 blur-[150px] animate-float" />
      <div className="pointer-events-none absolute right-[-10%] top-24 h-[520px] w-[620px] rounded-full bg-glow-pink/10 blur-[150px]" />
      <div className="pointer-events-none absolute inset-0 bg-grid-dark bg-grid-24 opacity-[0.12]" />

      <div className="relative flex h-screen overflow-hidden">
        <aside className="hidden w-[72px] flex-col border-r border-white/[0.07] bg-[#0d0d16]/45 shadow-[inset_-1px_0_0_rgba(255,255,255,0.03)] backdrop-blur-2xl lg:flex">
          <div className="flex h-16 items-center justify-center border-b border-white/[0.06]">
            <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br from-weave-400 via-glow-violet to-glow-pink shadow-[0_0_24px_rgba(139,92,246,0.28)]">
              <WeaveMark className="h-4 w-4" />
            </div>
          </div>

          <nav className="flex flex-col items-center gap-2 p-2 text-xs">
            {[
              { icon: Rocket, label: "项目", active: true },
              { icon: FileText, label: "制品" },
              { icon: ShieldCheck, label: "审批" },
            ].map((item) => (
              <button
                key={item.label}
                title={item.label}
                className={`flex h-12 w-12 flex-col items-center justify-center gap-1 rounded-2xl transition-colors ${
                  item.active
                    ? "border border-white/[0.10] bg-white/[0.08] text-white shadow-[0_0_20px_rgba(139,92,246,0.14)]"
                    : "text-white/50 hover:text-white hover:bg-white/[0.05]"
                }`}
              >
                <item.icon className="h-4 w-4" />
                <span className="text-[10px] leading-none">{item.label}</span>
              </button>
            ))}
          </nav>

          <div className="mt-auto p-2">
            <div
              className="flex h-12 w-full items-center justify-center rounded-2xl border border-white/[0.08] bg-white/[0.035] text-glow-pink shadow-[0_0_16px_rgba(236,72,153,0.10)]"
              title="Calm Cockpit Draft"
            >
              <Sparkles className="h-4 w-4" />
            </div>
          </div>
        </aside>

        <main className="flex min-h-0 flex-1 flex-col bg-transparent">
          <TopStatusBar
            lens={activeLens}
            requirement={activeRequirement}
            state={pipelineState}
            selectedRole={selectedRole}
            onRoleChange={setSelectedRole}
          />

          <div className="min-h-0 flex-1 overflow-hidden p-4 md:p-5">
            <div className="mx-auto grid h-full max-w-[1480px] min-h-0 grid-cols-1 gap-4 overflow-y-auto lg:grid-cols-[248px_minmax(0,1fr)] lg:overflow-hidden">
              <ProjectFlowPanel
                stage={projectStage}
                state={pipelineState}
                hasApproved={hasApproved}
                onReset={resetDemo}
              />

              <CurrentStepWorkspace
                lens={activeLens}
                requirement={requirement}
                activeRequirement={activeRequirement}
                stage={projectStage}
                state={pipelineState}
                hasPlan={hasPlan}
                hasCreated={hasCreated}
                hasApproved={hasApproved}
                isApiBusy={isApiBusy}
                onRequirementChange={setRequirement}
                onGeneratePlan={generateDeliveryPlan}
                onConfirmPlan={confirmPlanAndRun}
                onApprove={approveCheckpoint}
                onReject={rejectCheckpoint}
              />
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

function ProjectFlowPanel({
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
  const currentIndex =
    stage === "empty"
      ? 0
      : stage === "planned"
      ? 1
      : state === "WAITING_APPROVAL"
      ? 3
      : state === "FINISHED"
      ? 4
      : hasApproved
      ? 2
      : 2;

  const flow = [
    {
      title: "输入需求",
      desc: "描述目标和约束",
      icon: MessageSquareText,
    },
    {
      title: "确认计划",
      desc: "接受 AI 的交付路径",
      icon: FileText,
    },
    {
      title: "AI 执行",
      desc: "需求、方案、代码、测试",
      icon: Bot,
    },
    {
      title: "人工审批",
      desc: "Approve 或 Reject",
      icon: ShieldCheck,
    },
    {
      title: "交付结果",
      desc: "文档、测试摘要、MR",
      icon: GitMerge,
    },
  ];

  return (
    <aside className="flex min-h-[500px] flex-col overflow-hidden rounded-[1.5rem] border border-white/[0.09] bg-[#11111a]/50 shadow-[0_20px_70px_rgba(0,0,0,0.20),inset_0_1px_0_rgba(255,255,255,0.04)] backdrop-blur-2xl lg:min-h-0">
      <div className="flex-none border-b border-white/[0.06] px-4 py-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold">项目完成路径</h2>
            <p className="mt-1 text-xs text-white/42">只保留路线和当前位置。</p>
          </div>
          <button
            onClick={onReset}
            className="rounded-lg border border-white/[0.10] bg-white/[0.04] px-2.5 py-1.5 text-[11px] text-white/50 transition-colors hover:border-glow-violet/30 hover:bg-white/[0.07] hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-glow-violet/30"
          >
            重置
          </button>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        <div className="space-y-2">
          {flow.map((item, index) => {
            const done = currentIndex > index;
            const active = currentIndex === index;
            const Icon = item.icon;
            return (
              <div
                key={item.title}
                className={`rounded-2xl border p-3.5 transition-all duration-300 ${
                  active
                    ? "border-glow-pink/35 bg-gradient-to-br from-weave-500/15 via-glow-violet/10 to-glow-pink/10 shadow-[0_0_28px_rgba(139,92,246,0.14)]"
                    : done
                    ? "border-emerald-400/20 bg-emerald-500/10"
                    : "border-white/[0.07] bg-black/20"
                }`}
              >
                <div className="flex items-start gap-3">
                  <div
                    className={`flex h-8 w-8 flex-none items-center justify-center rounded-xl ${
                      active
                        ? "bg-gradient-to-br from-weave-400/25 to-glow-pink/20 text-glow-pink"
                        : done
                        ? "bg-emerald-500/15 text-emerald-300"
                        : "bg-white/[0.04] text-white/30"
                    }`}
                  >
                    {done ? <CheckCircle2 className="h-3.5 w-3.5" /> : <Icon className="h-3.5 w-3.5" />}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[10px] text-white/30">
                        {String(index + 1).padStart(2, "0")}
                      </span>
                      <div className="text-[13px] font-semibold">{item.title}</div>
                    </div>
                    <p className="mt-1 text-xs leading-relaxed text-white/45">{item.desc}</p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </aside>
  );
}

function CurrentStepWorkspace({
  lens,
  requirement,
  activeRequirement,
  stage,
  state,
  hasPlan,
  hasCreated,
  hasApproved,
  isApiBusy,
  onRequirementChange,
  onGeneratePlan,
  onConfirmPlan,
  onApprove,
  onReject,
}: {
  lens: RoleLens;
  requirement: string;
  activeRequirement: string;
  stage: ProjectStage;
  state: PipelineState;
  hasPlan: boolean;
  hasCreated: boolean;
  hasApproved: boolean;
  isApiBusy: boolean;
  onRequirementChange: (value: string) => void;
  onGeneratePlan: () => Promise<void>;
  onConfirmPlan: () => Promise<void>;
  onApprove: () => Promise<void>;
  onReject: () => Promise<void>;
}) {
  const title =
    stage === "empty"
      ? "输入项目目标"
      : stage === "planned"
      ? "确认交付计划"
      : state === "FINISHED"
      ? "查看交付结果"
      : state === "WAITING_APPROVAL"
      ? "审批当前方案"
      : "AI 正在执行";

  const description =
    stage === "empty"
      ? "先用自然语言描述你要完成的项目，系统会生成可审阅的交付计划。"
      : stage === "planned"
      ? "只在这里做确认。接受后，AI 才会进入执行流水线。"
      : state === "FINISHED"
      ? "交付包已生成，可以查看产物并进入 MR。"
      : state === "WAITING_APPROVAL"
      ? "当前节点需要你判断是否接受方案，所有决策集中在这里。"
      : hasApproved
      ? "审批已通过，AI 正在完成后续交付。"
      : "AI 正在生成方案，完成后会停在人工审批点。";

  return (
    <section className="flex min-h-[620px] flex-col overflow-hidden rounded-[1.5rem] border border-white/[0.09] bg-[#101019]/56 shadow-[0_22px_80px_rgba(0,0,0,0.24),inset_0_1px_0_rgba(255,255,255,0.04)] backdrop-blur-2xl lg:min-h-0">
      <div className="flex-none border-b border-white/[0.06] bg-white/[0.012] px-6 py-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 bg-gradient-to-r from-weave-200 via-glow-violet to-glow-pink bg-clip-text text-[11px] font-mono uppercase tracking-[0.16em] text-transparent">
              Current Step
            </div>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight">{title}</h2>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-white/45">
              {description}
            </p>
          </div>
          <StateBadge state={state} />
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-5 md:p-6">
        {stage === "empty" && (
          <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_300px]">
            <div>
              <textarea
                value={requirement}
                onChange={(event) => onRequirementChange(event.target.value)}
                placeholder={lens.placeholder}
                className="min-h-56 w-full resize-none rounded-[1.25rem] border border-white/[0.10] bg-black/24 px-4 py-3 text-sm leading-relaxed text-white placeholder:text-white/25 outline-none transition-all focus:border-glow-violet/50 focus:ring-4 focus:ring-glow-violet/10"
              />
              <div className="mt-4 flex flex-wrap gap-2">
                {lens.templates.map((template) => (
                  <button
                    key={template}
                    onClick={() => onRequirementChange(template)}
                    className="rounded-full border border-white/[0.10] bg-white/[0.035] px-3 py-1.5 text-xs text-white/55 transition-colors hover:border-glow-violet/30 hover:bg-white/[0.07] hover:text-white"
                  >
                    {template.slice(0, 24)}...
                  </button>
                ))}
              </div>
              <button
                onClick={onGeneratePlan}
                disabled={hasPlan || hasCreated || isApiBusy}
                className="mt-5 inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-weave-400 via-glow-violet to-glow-pink px-5 text-sm font-semibold text-white shadow-[0_0_26px_rgba(236,72,153,0.20)] transition-all hover:scale-[1.01] hover:shadow-[0_0_34px_rgba(236,72,153,0.30)] disabled:cursor-not-allowed disabled:opacity-55 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-glow-pink/40"
              >
                {isApiBusy ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Rocket className="h-4 w-4" />
                )}
                {isApiBusy ? "正在创建流水线" : "生成交付计划"}
              </button>
            </div>
            <RequirementBrief requirement={activeRequirement} resolved={false} />
          </div>
        )}

        {stage === "planned" && (
          <div className="grid gap-5 xl:grid-cols-[300px_minmax(0,1fr)]">
            <RequirementBrief requirement={activeRequirement} resolved />
            <PlanPreview
              lens={lens}
              requirement={activeRequirement}
              onConfirm={onConfirmPlan}
              isBusy={isApiBusy}
            />
          </div>
        )}

        {stage === "running" && (
          <div className="grid gap-5 xl:grid-cols-[300px_minmax(0,1fr)]">
            <RequirementBrief requirement={activeRequirement} resolved />
            <PipelinePreview
              requirement={activeRequirement}
              state={state}
              lens={lens}
              onApprove={onApprove}
              onReject={onReject}
              isBusy={isApiBusy}
            />
          </div>
        )}
      </div>
    </section>
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
    <header className="flex h-16 flex-none items-center justify-between gap-4 border-b border-white/[0.08] bg-[#0d0d16]/58 px-5 shadow-[0_10px_34px_rgba(0,0,0,0.20)] backdrop-blur-2xl md:px-6">
      <div className="flex min-w-0 items-center gap-4">
        <Link
          to="/drafts/landing/v2"
          className="hidden h-9 w-9 flex-none items-center justify-center rounded-xl border border-white/[0.10] bg-white/[0.035] text-white/45 transition-colors hover:border-glow-violet/35 hover:bg-white/[0.07] hover:text-glow-pink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-glow-violet/35 md:flex"
          aria-label="返回官网"
        >
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1.5 bg-gradient-to-r from-weave-200 via-glow-violet to-glow-pink bg-clip-text text-[11px] font-mono uppercase tracking-[0.16em] text-transparent">
              <Terminal className="h-3.5 w-3.5" />
              Calm Cockpit
            </span>
            <StateBadge state={state} />
            <span className="rounded-full border border-white/[0.10] bg-white/[0.04] px-2.5 py-1 text-[11px] text-white/45">
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
        to="/drafts/landing/v5"
        className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-white/[0.10] bg-white/[0.04] px-3 text-xs font-mono text-white/45 transition-colors hover:border-glow-violet/30 hover:bg-white/[0.07] hover:text-glow-pink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-glow-violet/35"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        v5
      </Link>
      <button className="inline-flex h-9 items-center gap-2 rounded-lg border border-white/[0.10] bg-white/[0.04] px-3 text-sm text-white/60 transition-colors hover:bg-white/[0.07] hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/20">
        <UserCircle className="h-4 w-4" />
        Demo
        <LogOut className="h-3.5 w-3.5 text-white/35" />
      </button>
    </>
  );
}

function RequirementBrief({
  requirement,
  resolved,
}: {
  requirement: string;
  resolved: boolean;
}) {
  const briefItems = [
    { label: "目标", value: "上线博客评论能力" },
    { label: "用户", value: "登录用户 / 管理员" },
    { label: "约束", value: "审核、敏感词拦截、生成 MR" },
    { label: "验收", value: "可评论、可审核、违规内容被拦截" },
  ];

  return (
    <div className="mb-4 rounded-2xl border border-white/[0.10] bg-white/[0.04] p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.03)]">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                resolved ? "bg-emerald-400" : "bg-white/25"
              }`}
            />
            <div className="text-xs font-semibold text-white/80">
              需求理解
            </div>
          </div>
          <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-white/45">
            {requirement}
          </p>
        </div>
        <span
          className={`flex-none rounded-full border px-2 py-1 text-[10px] font-mono ${
            resolved
              ? "border-glow-violet/25 bg-gradient-to-r from-weave-500/15 to-glow-pink/10 text-glow-pink"
              : "border-white/[0.10] bg-white/[0.035] text-white/35"
          }`}
        >
          {resolved ? "PARSED" : "WAITING"}
        </span>
      </div>

      <div className="mt-3 grid gap-2 sm:grid-cols-2">
        {briefItems.map((item) => (
          <div
            key={item.label}
            className={`rounded-xl border px-3 py-2 ${
              resolved
                ? "border-white/[0.10] bg-black/25"
                : "border-white/[0.06] bg-black/10 opacity-55"
            }`}
          >
            <div className="text-[10px] font-medium text-white/35">{item.label}</div>
            <div className="mt-1 text-xs leading-relaxed text-white/70">
              {resolved ? item.value : "等待 AI 解析"}
            </div>
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
  isBusy,
}: {
  lens: RoleLens;
  requirement: string;
  onConfirm: () => Promise<void>;
  isBusy: boolean;
}) {
  return (
    <div className="min-h-[360px]">
      <div className="rounded-xl border border-white/[0.10] bg-white/[0.04] p-4">
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
            className="rounded-xl border border-white/[0.10] bg-white/[0.035] p-4"
          >
            <div className="flex items-center justify-between">
              <span className="font-mono text-[11px] text-white/35">{index}</span>
              <CheckCircle2 className="h-4 w-4 text-glow-pink" />
            </div>
            <div className="mt-3 text-sm font-semibold">{title}</div>
            <p className="mt-1 text-xs leading-relaxed text-white/45">{desc}</p>
          </div>
        ))}
      </div>

      <button
        onClick={onConfirm}
        disabled={isBusy}
        className="mt-5 inline-flex h-9 items-center gap-2 rounded-lg bg-gradient-to-r from-weave-400 via-glow-violet to-glow-pink px-4 text-sm font-semibold text-white shadow-[0_0_26px_rgba(236,72,153,0.22)] transition-all hover:scale-[1.01] hover:shadow-[0_0_34px_rgba(236,72,153,0.32)] disabled:cursor-not-allowed disabled:opacity-55 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-glow-pink/40"
      >
        {isBusy ? "正在启动" : "确认计划并启动"}
        {isBusy ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          <ArrowRight className="h-3.5 w-3.5" />
        )}
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
    <div className="flex h-9 items-center gap-1 rounded-lg border border-white/[0.10] bg-black/25 p-1">
      <span className="hidden px-2 text-[11px] text-white/35 sm:inline">视角</span>
      <div className="flex items-center gap-1">
        {roleOrder.map((role) => {
          const lens = ROLE_LENS[role];
          const active = selectedRole === role;
          return (
            <button
              key={role}
              onClick={() => onChange(role)}
              className={`h-7 rounded-md px-2.5 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-glow-violet/35 ${
                active
                  ? "bg-gradient-to-r from-weave-300 to-glow-pink text-white shadow-[0_0_18px_rgba(236,72,153,0.18)]"
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

function PipelinePreview({
  requirement,
  state,
  lens,
  onApprove,
  onReject,
  isBusy,
}: {
  requirement: string;
  state: PipelineState;
  lens: RoleLens;
  onApprove: () => Promise<void>;
  onReject: () => Promise<void>;
  isBusy: boolean;
}) {
  if (state === "FINISHED") {
    return <DeliveryPackage requirement={requirement} lens={lens} />;
  }

  return (
    <div>
      <div className="rounded-xl border border-white/[0.10] bg-white/[0.04] p-4">
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

      <div className="mt-5 rounded-xl border border-white/[0.10] bg-white/[0.035] p-4">
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

      <div className="mt-5 overflow-hidden rounded-xl border border-white/[0.10] bg-black/45">
        <div className="flex items-center justify-between border-b border-white/[0.07] px-4 py-2.5">
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
              disabled={isBusy}
              className="inline-flex h-8 items-center rounded-lg border border-amber-200/20 bg-black/20 px-3 text-xs font-medium text-amber-100/75 transition-colors hover:bg-black/30 hover:text-amber-50 disabled:cursor-not-allowed disabled:opacity-55"
            >
              退回并补充约束
            </button>
            <button
              onClick={onApprove}
              disabled={isBusy}
              className="inline-flex h-8 items-center gap-2 rounded-lg bg-gradient-to-r from-amber-300 via-glow-pink to-glow-violet px-3 text-xs font-semibold text-white shadow-[0_0_24px_rgba(236,72,153,0.24)] transition-all hover:scale-[1.01] disabled:cursor-not-allowed disabled:opacity-55"
            >
              {isBusy ? "正在提交" : "批准继续交付"}
              {isBusy ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <ArrowRight className="h-3.5 w-3.5" />
              )}
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
