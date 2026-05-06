import { useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  CircleDashed,
  Download,
  ExternalLink,
  FileText,
  Loader2,
  Play,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Terminal,
} from "lucide-react";
import { pipelineApi } from "../../../api/pipelineApi";
import type { Pipeline, PipelineStage, PipelineState } from "../../../api/pipelineApi";
import WeaveMark from "../../../components/WeaveMark";

const DEFAULT_REQUIREMENT = "生成一个绚丽美观的网页，上面只有六个字“南京邮电大学”。";

const STAGE_GUIDANCE: Record<string, { title: string; running: string; done: string; userCheck: string }> = {
  analysis: {
    title: "需求理解",
    running: "AI 正在把你的一句话拆成目标、边界和验收标准。",
    done: "AI 已经整理出它对需求的理解。",
    userCheck: "检查 AI 有没有误解你真正想要的结果。",
  },
  design: {
    title: "方案设计",
    running: "AI 正在决定页面结构、文件方案和实现路径。",
    done: "AI 已经给出可执行方案。",
    userCheck: "确认方向是否正确，尤其是页面目标和交付形式。",
  },
  coding: {
    title: "代码生成",
    running: "AI 正在生成完整文件。若格式不合格，系统会自动打回重写。",
    done: "AI 已经返回代码变更。",
    userCheck: "重点看是否生成了完整文件，而不是说明或占位内容。",
  },
  testing: {
    title: "测试验证",
    running: "AI 和系统正在检查生成文件是否可用、是否符合需求。",
    done: "测试结果已生成。",
    userCheck: "确认关键验收点是否通过。",
  },
  review: {
    title: "质量评审",
    running: "AI 正在做最后的正确性、风险和交付质量检查。",
    done: "评审结论已生成。",
    userCheck: "查看是否存在阻塞交付的问题。",
  },
  delivery: {
    title: "交付整理",
    running: "AI 正在整理最终交付物和验收摘要。",
    done: "交付包已经准备完成。",
    userCheck: "打开结果，确认是否可以验收。",
  },
};

const FALLBACK_STAGES = [
  { id: "analysis", name: "需求理解" },
  { id: "design", name: "方案设计" },
  { id: "coding", name: "代码生成" },
  { id: "testing", name: "测试验证" },
  { id: "review", name: "质量评审" },
  { id: "delivery", name: "交付整理" },
];

const STAGE_CONTEXT_KEY: Record<string, string> = {
  analysis: "requirement_structured",
  design: "design_doc",
  coding: "code_diff",
  testing: "test_report",
  review: "review_result",
  delivery: "delivery",
};

const DECISION_COPY: Record<
  string,
  {
    object: string;
    criteria: string[];
    passLabel: string;
    editLabel: string;
    rejectLabel: string;
    editHint: string;
  }
> = {
  analysis: {
    object: "审批 AI 对需求的理解：目标、边界、验收标准是否正确。",
    criteria: ["目标是否被误解", "必须出现的文字/功能是否正确", "验收标准是否能判断成败"],
    passLabel: "理解正确，进入方案设计",
    editLabel: "保存修改，进入方案设计",
    rejectLabel: "退回，让 AI 重新理解",
    editHint: "你可以直接修改 goal、constraints、acceptance_criteria。修改后的内容会作为方案设计输入。",
  },
  design: {
    object: "审批 AI 的实现方案：页面结构、文件计划、风险是否合理。",
    criteria: ["实现方向是否符合目标", "文件计划是否完整", "有没有遗漏约束或风险"],
    passLabel: "方案可行，开始生成代码",
    editLabel: "保存方案修改，开始生成代码",
    rejectLabel: "退回，让 AI 重做方案",
    editHint: "你可以修改 architecture、file_change_plan、risk_analysis。修改后的方案会驱动代码生成。",
  },
  coding: {
    object: "审批 AI 生成的代码变更：是否是完整文件，是否满足需求。",
    criteria: ["是否生成完整文件", "是否没有 fallback/TODO 占位", "文件路径和内容是否符合预期"],
    passLabel: "代码可接受，开始测试",
    editLabel: "保存代码修改，开始测试",
    rejectLabel: "退回，让 AI 重新生成代码",
    editHint: "高级用法：可修改 code_diff.patches。保存后会把你改过的代码变更交给测试阶段。",
  },
  testing: {
    object: "审批测试结论：是否足以说明结果可继续交付。",
    criteria: ["核心验收点是否通过", "失败信息是否清楚", "是否需要补充检查"],
    passLabel: "测试结论可信，进入质量评审",
    editLabel: "保存测试修正，进入质量评审",
    rejectLabel: "退回，让 AI 重新测试",
    editHint: "你可以修正测试结论或补充需要验证的验收点。",
  },
  review: {
    object: "审批质量评审：是否存在阻塞交付的问题。",
    criteria: ["是否有高风险问题", "结论是否明确", "是否需要返工"],
    passLabel: "无阻塞问题，整理交付",
    editLabel: "保存评审修正，整理交付",
    rejectLabel: "退回，让 AI 重新评审",
    editHint: "你可以修正评审结论或补充阻塞项。",
  },
  delivery: {
    object: "审批最终交付：是否可以验收。",
    criteria: ["结果是否满足需求", "交付说明是否清楚", "是否可以打开/测试"],
    passLabel: "确认验收完成",
    editLabel: "保存交付说明，确认完成",
    rejectLabel: "退回，让 AI 重新整理交付",
    editHint: "你可以修正交付摘要和验收说明。",
  },
};

export default function ConsoleV5GuidedCockpit() {
  const [requirement, setRequirement] = useState(DEFAULT_REQUIREMENT);
  const [pipeline, setPipeline] = useState<Pipeline | null>(null);
  const [pipelineId, setPipelineId] = useState<string | null>(null);
  const [checkpointId, setCheckpointId] = useState<string | null>(null);
  const [isBusy, setIsBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [editableDraft, setEditableDraft] = useState("");
  const [regenerateFeedback, setRegenerateFeedback] = useState("");

  const state: PipelineState = pipeline?.state || "CREATED";
  const context = pipeline?.context || {};
  const lastError = asString(context.last_error);
  const currentStageId = pipeline?.currentStage?.id || pipeline?.checkpoint?.stageId || "analysis";
  const currentStage = pipeline?.currentStage;

  function syncPipeline(next: Pipeline) {
    setPipeline(next);
    setPipelineId(next.id);
    setCheckpointId(next.checkpoint?.id ?? null);
    if (next.state === "WAITING_APPROVAL") {
      setEditableDraft(formatEditableStageDraft(next));
      setRegenerateFeedback("");
    }
  }

  function pollPipelineUntilSettled(id: string, attempts = 90) {
    window.setTimeout(async () => {
      try {
        const next = await pipelineApi.getPipeline(id);
        syncPipeline(next);
        if (next.state === "RUNNING" && attempts > 1) {
          pollPipelineUntilSettled(id, attempts - 1);
        }
      } catch (error) {
        setNotice(error instanceof Error ? error.message : "暂时无法同步 AI 进度。");
      }
    }, 2000);
  }

  async function runCurrentStage(id: string) {
    const next = await pipelineApi.runPipeline(id);
    syncPipeline(next);
    if (next.state === "RUNNING") {
      pollPipelineUntilSettled(id);
    }
    return next;
  }

  async function startPipeline() {
    const activeRequirement = requirement.trim();
    if (!activeRequirement) return;

    setIsBusy(true);
    setNotice("");
    try {
      const created = await pipelineApi.createPipeline({ requirement: activeRequirement });
      syncPipeline(created);
      const running = await runCurrentStage(created.id);
      if (running.state === "WAITING_APPROVAL") {
        setNotice("第一阶段已经完成，请先审阅 AI 的理解。");
      }
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "创建流水线失败。");
    } finally {
      setIsBusy(false);
    }
  }

  async function approveAndContinue() {
    if (!checkpointId || !pipelineId) return;

    setIsBusy(true);
    setNotice("");
    try {
      const approved = await pipelineApi.approveCheckpoint(checkpointId, {
        note: "用户认可当前 AI 产物，直接进入下一阶段。",
      });
      syncPipeline(approved);
      if (approved.state === "RUNNING") {
        await runCurrentStage(approved.id);
      }
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "提交审批失败。");
    } finally {
      setIsBusy(false);
    }
  }

  async function editAndContinue() {
    if (!checkpointId || !pipelineId || !pipeline) return;

    setIsBusy(true);
    setNotice("");
    try {
      const contextPatch = buildContextPatchFromDraft(pipeline, editableDraft);
      const approved = await pipelineApi.approveCheckpoint(checkpointId, {
        note: "用户人工修改 AI 草稿后继续下一阶段。",
        contextPatch,
      });
      syncPipeline(approved);
      if (approved.state === "RUNNING") {
        await runCurrentStage(approved.id);
      }
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "修改后继续失败。");
    } finally {
      setIsBusy(false);
    }
  }

  async function rejectAndRevise() {
    if (!checkpointId) return;

    setIsBusy(true);
    setNotice("");
    try {
      const next = await pipelineApi.rejectCheckpoint(checkpointId, {
        reason: regenerateFeedback.trim() || "用户认为当前阶段产物需要补充约束后重新生成。",
      });
      syncPipeline(next);
      if (next.state === "RUNNING") {
        await runCurrentStage(next.id);
      }
      setNotice("已退回当前阶段，AI 会基于你的反馈重新生成。");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "退回失败。");
    } finally {
      setIsBusy(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#f7f8fb] text-zinc-950">
      <div className="mx-auto flex min-h-screen w-full max-w-7xl flex-col px-4 py-5 sm:px-6 lg:px-8">
        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-zinc-200 pb-4">
          <div className="flex items-center gap-3">
            <Link
              to="/"
              className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-zinc-200 bg-white text-zinc-500 shadow-sm transition-colors hover:bg-zinc-50 hover:text-zinc-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-950"
            >
              <ArrowLeft className="h-4 w-4" />
            </Link>
            <WeaveMark className="h-8 w-8" />
            <div>
              <div className="text-sm font-semibold text-zinc-950">v5 · Guided Cockpit</div>
              <div className="text-xs text-zinc-500">用户引导优先，开发者信息默认折叠</div>
            </div>
          </div>
          <div className="inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            Real AI Pipeline
          </div>
        </header>

        <section className="grid flex-1 gap-5 py-5 lg:grid-cols-[380px_minmax(0,1fr)]">
          <aside className="space-y-4">
            <div className="rounded-3xl border border-zinc-200 bg-white p-5 shadow-sm">
              <div className="inline-flex items-center gap-2 rounded-full bg-zinc-100 px-3 py-1 text-xs font-medium text-zinc-600">
                <Sparkles className="h-3.5 w-3.5" />
                从一句需求开始
              </div>
              <h1 className="mt-4 text-2xl font-semibold tracking-tight text-zinc-950">
                不展示服务器细节，只引导你完成交付。
              </h1>
              <p className="mt-2 text-sm leading-6 text-zinc-500">
                你只需要判断 AI 是否理解正确、方案是否可接受、最终结果是否可验收。
              </p>

              <label className="mt-5 block text-sm font-medium text-zinc-800">你的目标</label>
              <textarea
                value={requirement}
                onChange={(event) => setRequirement(event.target.value)}
                className="mt-2 min-h-32 w-full resize-none rounded-2xl border border-zinc-200 bg-zinc-50 px-4 py-3 text-sm leading-6 text-zinc-900 outline-none transition-colors placeholder:text-zinc-400 focus:border-zinc-400 focus:bg-white focus:ring-4 focus:ring-zinc-100"
                placeholder="例如：生成一个绚丽美观的网页，上面只有六个字“南京邮电大学”。"
              />

              <div className="mt-4 grid gap-2">
                {[
                  "生成一个绚丽美观的网页，上面只有六个字“南京邮电大学”。",
                  "生成一个可打开的产品介绍页，突出 AI 交付流程。",
                  "生成一个单页作品集网站，包含姓名、介绍和联系方式。",
                ].map((template) => (
                  <button
                    key={template}
                    type="button"
                    onClick={() => setRequirement(template)}
                    className="rounded-xl border border-zinc-200 bg-white px-3 py-2 text-left text-xs leading-5 text-zinc-600 transition-colors hover:border-zinc-300 hover:bg-zinc-50 hover:text-zinc-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-950"
                  >
                    {template}
                  </button>
                ))}
              </div>

              <button
                type="button"
                onClick={startPipeline}
                disabled={isBusy}
                className="mt-5 inline-flex h-11 w-full items-center justify-center gap-2 rounded-2xl bg-zinc-950 px-4 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-950 focus-visible:ring-offset-2"
              >
                {isBusy ? "AI 正在启动" : pipeline ? "重新生成" : "开始 AI 交付"}
                {isBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              </button>
            </div>

            <StageDecisionGate
              state={state}
              checkpointTitle={pipeline?.checkpoint?.title}
              currentStageId={currentStageId}
              isBusy={isBusy}
              editableDraft={editableDraft}
              regenerateFeedback={regenerateFeedback}
              onDraftChange={setEditableDraft}
              onFeedbackChange={setRegenerateFeedback}
              onApprove={approveAndContinue}
              onEditAndContinue={editAndContinue}
              onReject={rejectAndRevise}
            />
          </aside>

          <section className="space-y-4">
            <GuidedProgressCard
              state={state}
              isBusy={isBusy}
              currentStageId={currentStageId}
              currentStage={currentStage}
              lastError={lastError}
            />

            {notice && (
              <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm leading-6 text-amber-800">
                {notice}
              </div>
            )}

            <StageTimeline stages={pipeline?.stages} currentStageId={currentStageId} state={state} />

            <AiResultSummary pipeline={pipeline} />

            <DeliveryActions pipeline={pipeline} />

            <DeveloperDetails pipeline={pipeline} />
          </section>
        </section>
      </div>
    </main>
  );
}

function GuidedProgressCard({
  state,
  isBusy,
  currentStageId,
  currentStage,
  lastError,
}: {
  state: PipelineState;
  isBusy: boolean;
  currentStageId: string;
  currentStage?: PipelineStage;
  lastError: string;
}) {
  const guidance = STAGE_GUIDANCE[currentStageId] || STAGE_GUIDANCE.analysis;
  const friendlyError = toFriendlyError(lastError);

  const title =
    state === "FINISHED"
      ? "交付已完成"
      : friendlyError
      ? "AI 生成遇到格式问题，正在按规则处理"
      : state === "WAITING_APPROVAL"
      ? `${guidance.title}等待你确认`
      : state === "RUNNING" || isBusy
      ? guidance.running
      : "准备创建第一条 AI 交付流水线";

  const body =
    state === "FINISHED"
      ? "你可以查看最终结果摘要，并在开发者详情中打开本地入口文件。"
      : friendlyError
      ? friendlyError
      : state === "WAITING_APPROVAL"
      ? guidance.userCheck
      : state === "RUNNING" || isBusy
      ? "你暂时不需要操作。完成后系统会停在审批点，让你判断是否继续。"
      : "输入需求后，AI 会先做需求理解，然后一步步生成方案、代码、测试和交付摘要。";

  return (
    <div className="overflow-hidden rounded-3xl border border-zinc-200 bg-white shadow-sm">
      <div className="border-b border-zinc-100 p-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="text-xs font-medium uppercase tracking-[0.16em] text-zinc-400">Current Guidance</div>
            <h2 className="mt-2 text-xl font-semibold tracking-tight text-zinc-950">{title}</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-zinc-500">{body}</p>
          </div>
          <StatusBadge state={state} hasError={Boolean(friendlyError)} />
        </div>
      </div>

      <div className="grid gap-3 p-5 md:grid-cols-3">
        <GuidanceMetric label="当前阶段" value={currentStage?.name || guidance.title} />
        <GuidanceMetric
          label="你需要做什么"
          value={state === "WAITING_APPROVAL" ? "审阅后批准或退回" : state === "RUNNING" ? "等待 AI 完成" : "输入目标并启动"}
        />
        <GuidanceMetric
          label="系统会做什么"
          value={currentStageId === "coding" ? "失败自动打回重写" : "生成可审阅结果"}
        />
      </div>
    </div>
  );
}

function StatusBadge({ state, hasError }: { state: PipelineState; hasError: boolean }) {
  if (hasError) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-medium text-amber-700">
        <RefreshCw className="h-3.5 w-3.5" />
        自动重试中
      </span>
    );
  }
  if (state === "WAITING_APPROVAL") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700">
        <ShieldCheck className="h-3.5 w-3.5" />
        等待确认
      </span>
    );
  }
  if (state === "FINISHED") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700">
        <CheckCircle2 className="h-3.5 w-3.5" />
        已完成
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-zinc-200 bg-zinc-50 px-3 py-1 text-xs font-medium text-zinc-600">
      {state === "RUNNING" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CircleDashed className="h-3.5 w-3.5" />}
      {state === "RUNNING" ? "运行中" : "未开始"}
    </span>
  );
}

function GuidanceMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-zinc-200 bg-zinc-50 p-4">
      <div className="text-xs font-medium text-zinc-400">{label}</div>
      <div className="mt-1 text-sm font-medium leading-6 text-zinc-900">{value}</div>
    </div>
  );
}

function StageTimeline({
  stages,
  currentStageId,
  state,
}: {
  stages?: PipelineStage[];
  currentStageId: string;
  state: PipelineState;
}) {
  const displayStages = stages?.length ? stages : FALLBACK_STAGES;

  return (
    <div className="rounded-3xl border border-zinc-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-xs font-medium uppercase tracking-[0.16em] text-zinc-400">Flow</div>
          <h3 className="mt-1 text-base font-semibold text-zinc-950">AI 交付路径</h3>
        </div>
        <div className="text-xs text-zinc-400">6 steps</div>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-6">
        {displayStages.map((stage, index) => {
          const status = "status" in stage ? stage.status : "PENDING";
          const active = stage.id === currentStageId && state !== "FINISHED";
          const done = status === "DONE" || state === "FINISHED";
          return (
            <div
              key={stage.id}
              className={`rounded-2xl border p-3 transition-colors ${
                active
                  ? "border-zinc-950 bg-zinc-950 text-white"
                  : done
                  ? "border-emerald-200 bg-emerald-50 text-emerald-900"
                  : "border-zinc-200 bg-zinc-50 text-zinc-500"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold">{String(index + 1).padStart(2, "0")}</span>
                {done ? <CheckCircle2 className="h-3.5 w-3.5" /> : active ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CircleDashed className="h-3.5 w-3.5" />}
              </div>
              <div className="mt-3 text-sm font-medium">{stage.name}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function AiResultSummary({ pipeline }: { pipeline: Pipeline | null }) {
  const context = pipeline?.context || {};
  const stageId = pipeline?.checkpoint?.stageId || pipeline?.currentStage?.id || "analysis";
  const summary = buildHumanSummary(stageId, context, pipeline?.state);

  return (
    <div className="rounded-3xl border border-zinc-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-xs font-medium uppercase tracking-[0.16em] text-zinc-400">AI Result</div>
          <h3 className="mt-1 text-base font-semibold text-zinc-950">{summary.title}</h3>
          <p className="mt-2 text-sm leading-6 text-zinc-500">{summary.description}</p>
        </div>
        <FileText className="h-5 w-5 flex-none text-zinc-400" />
      </div>

      <div className="mt-5 grid gap-3">
        {summary.items.map((item) => (
          <div key={item.label} className="rounded-2xl border border-zinc-200 bg-zinc-50 p-4">
            <div className="text-xs font-medium text-zinc-400">{item.label}</div>
            <div className="mt-1 text-sm leading-6 text-zinc-800">{item.value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function DeliveryActions({ pipeline }: { pipeline: Pipeline | null }) {
  if (!pipeline) return null;

  const context = pipeline.context || {};
  const delivery = asRecord(context.delivery);
  const deliveryPackage = asRecord(delivery.delivery_package || context.delivery_package);
  if (!Object.keys(deliveryPackage).length && pipeline.state !== "FINISHED") {
    return null;
  }

  const projectTitle = asString(delivery.project_title) || asString(deliveryPackage.project_title) || "AI 生成项目";
  const version = asString(delivery.version) || asString(deliveryPackage.version) || "v1";
  const files = asArray(deliveryPackage.files).map((item) => asRecord(item));
  const canDownload = Boolean(asString(delivery.download_url) || asString(deliveryPackage.download_url));
  const canPreview = Boolean(asString(delivery.preview_url) || asString(deliveryPackage.preview_url));

  return (
    <div className="rounded-3xl border border-emerald-200 bg-emerald-50 p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-xs font-medium uppercase tracking-[0.16em] text-emerald-700/60">Delivery Package</div>
          <h3 className="mt-1 text-lg font-semibold text-emerald-950">{projectTitle}</h3>
          <p className="mt-1 text-sm leading-6 text-emerald-900/65">
            {version} · 已生成可交付项目包。你可以打开预览，也可以下载完整文件。
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <a
            href={pipelineApi.deliveryPreviewUrl(pipeline.id)}
            target="_blank"
            rel="noreferrer"
            aria-disabled={!canPreview}
            className={`inline-flex h-10 items-center gap-2 rounded-2xl px-4 text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-700 ${
              canPreview
                ? "bg-white text-emerald-900 hover:bg-emerald-100"
                : "pointer-events-none bg-white/60 text-emerald-900/35"
            }`}
          >
            打开预览
            <ExternalLink className="h-4 w-4" />
          </a>
          <a
            href={pipelineApi.deliveryDownloadUrl(pipeline.id)}
            aria-disabled={!canDownload}
            className={`inline-flex h-10 items-center gap-2 rounded-2xl px-4 text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-700 ${
              canDownload
                ? "bg-emerald-700 text-white hover:bg-emerald-800"
                : "pointer-events-none bg-emerald-700/40 text-white/70"
            }`}
          >
            下载项目 ZIP
            <Download className="h-4 w-4" />
          </a>
        </div>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-2">
        <div className="rounded-2xl border border-emerald-200 bg-white p-4">
          <div className="text-xs font-semibold text-emerald-900">验收状态</div>
          <p className="mt-1 text-sm leading-6 text-emerald-900/70">
            {delivery.test_passed === true
              ? "测试已通过，可以人工验收。"
              : delivery.test_passed === false
              ? "测试未完全通过，请先查看问题再交付。"
              : "等待测试结果。"}
          </p>
        </div>
        <div className="rounded-2xl border border-emerald-200 bg-white p-4">
          <div className="text-xs font-semibold text-emerald-900">包含文件</div>
          <p className="mt-1 text-sm leading-6 text-emerald-900/70">
            {files.length
              ? files.slice(0, 5).map((file) => asString(file.path)).filter(Boolean).join("、")
              : "等待交付文件清单。"}
          </p>
        </div>
      </div>
    </div>
  );
}

function StageDecisionGate({
  state,
  checkpointTitle,
  currentStageId,
  isBusy,
  editableDraft,
  regenerateFeedback,
  onDraftChange,
  onFeedbackChange,
  onApprove,
  onEditAndContinue,
  onReject,
}: {
  state: PipelineState;
  checkpointTitle?: string;
  currentStageId: string;
  isBusy: boolean;
  editableDraft: string;
  regenerateFeedback: string;
  onDraftChange: (value: string) => void;
  onFeedbackChange: (value: string) => void;
  onApprove: () => Promise<void>;
  onEditAndContinue: () => Promise<void>;
  onReject: () => Promise<void>;
}) {
  const decision = DECISION_COPY[currentStageId] || DECISION_COPY.analysis;
  const canApprove = state === "WAITING_APPROVAL";

  return (
    <div className="rounded-3xl border border-zinc-200 bg-white p-5 shadow-sm">
      <div className="flex items-center gap-2">
        <ShieldCheck className={`h-4 w-4 ${canApprove ? "text-blue-600" : "text-zinc-400"}`} />
        <h2 className="text-sm font-semibold text-zinc-950">人工决策闸门</h2>
      </div>
      <p className="mt-3 text-sm leading-6 text-zinc-500">
        {canApprove
          ? checkpointTitle || decision.object
          : state === "RUNNING"
          ? "AI 正在工作，你可以等待它停在下一个确认点。"
          : state === "FINISHED"
          ? "流程已完成，请查看结果并打开交付文件验收。"
          : "先输入目标并启动 AI 交付流程。"}
      </p>

      {canApprove && (
        <div className="mt-4 space-y-4">
          <div className="rounded-2xl border border-blue-200 bg-blue-50 p-4">
            <div className="text-xs font-semibold text-blue-900">你正在审批什么</div>
            <p className="mt-1 text-sm leading-6 text-blue-900/75">{decision.object}</p>
            <div className="mt-3 text-xs font-semibold text-blue-900">重点看</div>
            <div className="mt-2 flex flex-wrap gap-2">
              {decision.criteria.map((item) => (
                <span key={item} className="rounded-full border border-blue-200 bg-white px-2 py-1 text-[11px] text-blue-800">
                  {item}
                </span>
              ))}
            </div>
          </div>

          <button
            type="button"
            onClick={onApprove}
            disabled={isBusy}
            className="inline-flex h-10 items-center justify-center gap-2 rounded-2xl bg-zinc-950 px-4 text-sm font-semibold text-white transition-colors hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-950"
          >
            {decision.passLabel}
            {isBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}
          </button>

          <details className="group rounded-2xl border border-zinc-200 bg-zinc-50 p-4">
            <summary className="flex cursor-pointer list-none items-center justify-between gap-3">
              <div>
                <div className="text-sm font-semibold text-zinc-950">修改后继续</div>
                <div className="mt-1 text-xs leading-5 text-zinc-500">{decision.editHint}</div>
              </div>
              <ChevronDown className="h-4 w-4 text-zinc-400 transition-transform group-open:rotate-180" />
            </summary>
            <StageEditableForm
              stageId={currentStageId}
              draft={editableDraft}
              onDraftChange={onDraftChange}
            />
            <button
              type="button"
              onClick={onEditAndContinue}
              disabled={isBusy}
              className="mt-3 inline-flex h-10 w-full items-center justify-center gap-2 rounded-2xl border border-zinc-300 bg-white px-4 text-sm font-semibold text-zinc-900 transition-colors hover:bg-zinc-100 disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-950"
            >
              {decision.editLabel}
              {isBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
            </button>
          </details>

          <details className="group rounded-2xl border border-amber-200 bg-amber-50 p-4">
            <summary className="flex cursor-pointer list-none items-center justify-between gap-3">
              <div>
                <div className="text-sm font-semibold text-amber-950">退回重新生成</div>
                <div className="mt-1 text-xs leading-5 text-amber-800/70">
                  写清楚哪里不对，AI 会基于你的反馈重新生成当前阶段。
                </div>
              </div>
              <ChevronDown className="h-4 w-4 text-amber-700 transition-transform group-open:rotate-180" />
            </summary>
            <textarea
              value={regenerateFeedback}
              onChange={(event) => onFeedbackChange(event.target.value)}
              className="mt-4 min-h-24 w-full resize-y rounded-2xl border border-amber-200 bg-white px-3 py-2 text-sm leading-6 text-amber-950 outline-none transition-colors placeholder:text-amber-800/35 focus:border-amber-300 focus:ring-4 focus:ring-amber-100"
              placeholder="例如：不要做成官网首页，只要一个艺术化静态页，页面主体只保留“南京邮电大学”六个字。"
            />
            <button
              type="button"
              onClick={onReject}
              disabled={isBusy}
              className="mt-3 inline-flex h-10 w-full items-center justify-center gap-2 rounded-2xl border border-amber-300 bg-white px-4 text-sm font-semibold text-amber-900 transition-colors hover:bg-amber-100 disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400"
            >
              {decision.rejectLabel}
              {isBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            </button>
          </details>
        </div>
      )}
    </div>
  );
}

function StageEditableForm({
  stageId,
  draft,
  onDraftChange,
}: {
  stageId: string;
  draft: string;
  onDraftChange: (value: string) => void;
}) {
  const parsed = parseDraftObject(draft);
  if (!parsed) {
    return (
      <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 p-4">
        <div className="text-sm font-semibold text-red-900">草稿格式需要修正</div>
        <p className="mt-1 text-xs leading-5 text-red-800/70">
          当前草稿不是合法 JSON。你可以先在这里修正，或退回让 AI 重新生成。
        </p>
        <textarea
          value={draft}
          onChange={(event) => onDraftChange(event.target.value)}
          className="mt-3 min-h-44 w-full resize-y rounded-2xl border border-red-200 bg-white px-3 py-2 font-mono text-xs leading-5 text-red-950 outline-none focus:border-red-300 focus:ring-4 focus:ring-red-100"
        />
      </div>
    );
  }

  const updateDraft = (recipe: (next: Record<string, unknown>) => void) => {
    const next = { ...parsed };
    recipe(next);
    onDraftChange(JSON.stringify(next, null, 2));
  };

  return (
    <div className="mt-4 space-y-3">
      {stageId === "analysis" ? (
        <RequirementEditForm draft={parsed} onChange={updateDraft} />
      ) : stageId === "design" ? (
        <DesignEditForm draft={parsed} onChange={updateDraft} />
      ) : stageId === "coding" ? (
        <CodingEditForm draft={parsed} onChange={updateDraft} />
      ) : stageId === "testing" ? (
        <TestingEditForm draft={parsed} onChange={updateDraft} />
      ) : stageId === "review" ? (
        <ReviewEditForm draft={parsed} onChange={updateDraft} />
      ) : (
        <DeliveryEditForm draft={parsed} onChange={updateDraft} />
      )}

      <details className="group rounded-2xl border border-zinc-200 bg-white p-3">
        <summary className="flex cursor-pointer list-none items-center justify-between gap-3">
          <div>
            <div className="text-xs font-semibold text-zinc-800">高级编辑：原始 JSON</div>
            <div className="mt-0.5 text-[11px] text-zinc-500">仅在表单无法表达时使用。</div>
          </div>
          <ChevronDown className="h-4 w-4 text-zinc-400 transition-transform group-open:rotate-180" />
        </summary>
        <textarea
          value={draft}
          onChange={(event) => onDraftChange(event.target.value)}
          className="mt-3 min-h-48 w-full resize-y rounded-2xl border border-zinc-200 bg-zinc-50 px-3 py-2 font-mono text-xs leading-5 text-zinc-800 outline-none transition-colors focus:border-zinc-400 focus:ring-4 focus:ring-zinc-100"
        />
      </details>
    </div>
  );
}

function RequirementEditForm({
  draft,
  onChange,
}: {
  draft: Record<string, unknown>;
  onChange: (recipe: (next: Record<string, unknown>) => void) => void;
}) {
  return (
    <>
      <FormField
        label="目标"
        hint="AI 接下来会以这个目标设计方案。"
        value={asString(draft.goal)}
        onChange={(value) => onChange((next) => setField(next, "goal", value))}
      />
      <FormArea
        label="功能/必须体现"
        hint="一行一条，例如：只展示“南京邮电大学”六个字。"
        value={arrayToLines(draft.features)}
        onChange={(value) => onChange((next) => setField(next, "features", linesToArray(value)))}
      />
      <FormArea
        label="边界/约束"
        hint="一行一条，写清不要做什么、必须满足什么。"
        value={arrayToLines(draft.constraints)}
        onChange={(value) => onChange((next) => setField(next, "constraints", linesToArray(value)))}
      />
      <FormArea
        label="验收标准"
        hint="一行一条，后续测试会围绕这些标准判断。"
        value={arrayToLines(draft.acceptance_criteria)}
        onChange={(value) => onChange((next) => setField(next, "acceptance_criteria", linesToArray(value)))}
      />
      <FormArea
        label="不做什么"
        hint="可选。比如不要导航、不要多页面、不要外部资源。"
        value={arrayToLines(draft.out_of_scope)}
        onChange={(value) => onChange((next) => setField(next, "out_of_scope", linesToArray(value)))}
      />
    </>
  );
}

function DesignEditForm({
  draft,
  onChange,
}: {
  draft: Record<string, unknown>;
  onChange: (recipe: (next: Record<string, unknown>) => void) => void;
}) {
  return (
    <>
      <FormArea
        label="实现思路"
        hint="描述页面结构、视觉策略和主要技术做法。"
        value={asString(draft.architecture)}
        onChange={(value) => onChange((next) => setField(next, "architecture", value))}
      />
      <FormArea
        label="文件计划"
        hint="一行一个文件。格式建议：/index.html - 生成完整单页。"
        value={filePlanToLines(draft.file_change_plan)}
        onChange={(value) => onChange((next) => setField(next, "file_change_plan", linesToFilePlan(value)))}
      />
      <FormArea
        label="视觉/体验要求"
        hint="补充风格要求，会进入下一阶段代码生成。"
        value={asString(draft.visual_direction)}
        onChange={(value) => onChange((next) => setField(next, "visual_direction", value))}
      />
      <FormArea
        label="风险和注意事项"
        hint="例如：不要依赖外部 CDN；必须本地可打开。"
        value={asString(draft.risk_analysis)}
        onChange={(value) => onChange((next) => setField(next, "risk_analysis", value))}
      />
    </>
  );
}

function CodingEditForm({
  draft,
  onChange,
}: {
  draft: Record<string, unknown>;
  onChange: (recipe: (next: Record<string, unknown>) => void) => void;
}) {
  const patches = asArray(draft.patches).map((item) => asRecord(item));
  return (
    <>
      <div className="rounded-2xl border border-zinc-200 bg-white p-3">
        <div className="text-xs font-semibold text-zinc-800">生成文件</div>
        <div className="mt-2 space-y-1">
          {patches.length ? (
            patches.map((patch, index) => (
              <div key={`${asString(patch.file_path)}-${index}`} className="rounded-xl bg-zinc-50 px-3 py-2 font-mono text-xs text-zinc-700">
                {asString(patch.file_path) || "未命名文件"}
              </div>
            ))
          ) : (
            <div className="text-xs text-zinc-500">等待 AI 返回文件列表。</div>
          )}
        </div>
      </div>
      <FormArea
        label="人工校准说明"
        hint="普通用户不需要改代码。写清你对代码结果的要求，后续测试/评审会读取。"
        value={asString(draft.human_review_notes)}
        onChange={(value) => onChange((next) => setField(next, "human_review_notes", value))}
      />
    </>
  );
}

function TestingEditForm({
  draft,
  onChange,
}: {
  draft: Record<string, unknown>;
  onChange: (recipe: (next: Record<string, unknown>) => void) => void;
}) {
  return (
    <>
      <FormField
        label="测试结论"
        hint="例如：通过 / 不通过 / 需要补充验证。"
        value={asString(draft.summary) || (draft.passed === true ? "通过" : draft.passed === false ? "不通过" : "")}
        onChange={(value) => onChange((next) => setField(next, "summary", value))}
      />
      <FormArea
        label="补充测试点"
        hint="一行一条，会作为质量评审参考。"
        value={arrayToLines(draft.human_test_points)}
        onChange={(value) => onChange((next) => setField(next, "human_test_points", linesToArray(value)))}
      />
    </>
  );
}

function ReviewEditForm({
  draft,
  onChange,
}: {
  draft: Record<string, unknown>;
  onChange: (recipe: (next: Record<string, unknown>) => void) => void;
}) {
  return (
    <>
      <FormArea
        label="评审结论"
        hint="说明是否存在阻塞交付的问题。"
        value={asString(draft.summary) || asString(draft.result) || JSON.stringify(draft, null, 2)}
        onChange={(value) => onChange((next) => setField(next, "summary", value))}
      />
      <FormArea
        label="阻塞问题"
        hint="一行一条；没有就留空。"
        value={arrayToLines(draft.blockers)}
        onChange={(value) => onChange((next) => setField(next, "blockers", linesToArray(value)))}
      />
    </>
  );
}

function DeliveryEditForm({
  draft,
  onChange,
}: {
  draft: Record<string, unknown>;
  onChange: (recipe: (next: Record<string, unknown>) => void) => void;
}) {
  return (
    <>
      <FormArea
        label="交付说明"
        hint="给验收人看的最终说明。"
        value={asString(draft.summary)}
        onChange={(value) => onChange((next) => setField(next, "summary", value))}
      />
      <FormArea
        label="验收备注"
        hint="写清如何打开、如何判断成功。"
        value={asString(draft.acceptance_notes)}
        onChange={(value) => onChange((next) => setField(next, "acceptance_notes", value))}
      />
    </>
  );
}

function FormField({
  label,
  hint,
  value,
  onChange,
}: {
  label: string;
  hint: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block rounded-2xl border border-zinc-200 bg-white p-3">
      <span className="text-xs font-semibold text-zinc-800">{label}</span>
      <span className="mt-0.5 block text-[11px] leading-5 text-zinc-500">{hint}</span>
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-2 h-10 w-full rounded-xl border border-zinc-200 bg-zinc-50 px-3 text-sm text-zinc-900 outline-none transition-colors focus:border-zinc-400 focus:bg-white focus:ring-4 focus:ring-zinc-100"
      />
    </label>
  );
}

function FormArea({
  label,
  hint,
  value,
  onChange,
}: {
  label: string;
  hint: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block rounded-2xl border border-zinc-200 bg-white p-3">
      <span className="text-xs font-semibold text-zinc-800">{label}</span>
      <span className="mt-0.5 block text-[11px] leading-5 text-zinc-500">{hint}</span>
      <textarea
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-2 min-h-24 w-full resize-y rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm leading-6 text-zinc-900 outline-none transition-colors focus:border-zinc-400 focus:bg-white focus:ring-4 focus:ring-zinc-100"
      />
    </label>
  );
}

function DeveloperDetails({ pipeline }: { pipeline: Pipeline | null }) {
  if (!pipeline) return null;

  const context = pipeline.context || {};
  const delivery = asRecord(context.delivery);
  const workspace = asRecord(context.workspace);
  const rows = [
    ["Pipeline ID", pipeline.id],
    ["后端状态", `${pipeline.state} / ${pipeline.currentStage?.id || "none"}`],
    ["workspace_dir", asString(context.workspace_dir) || asString(delivery.workspace_dir) || asString(workspace.root)],
    ["entry_file", asString(context.entry_file) || asString(delivery.entry_file) || asString(workspace.entry_file)],
    ["artifact_dir", asString(context.artifact_dir)],
    ["last_error", asString(context.last_error)],
  ].filter(([, value]) => value);

  return (
    <details className="group rounded-3xl border border-zinc-200 bg-white p-5 shadow-sm">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <Terminal className="h-4 w-4 text-zinc-400" />
          <div>
            <div className="text-sm font-semibold text-zinc-950">开发者详情</div>
            <div className="text-xs text-zinc-500">默认隐藏，演示或排错时再打开</div>
          </div>
        </div>
        <ChevronDown className="h-4 w-4 text-zinc-400 transition-transform group-open:rotate-180" />
      </summary>

      <div className="mt-4 grid gap-2">
        {rows.map(([label, value]) => (
          <div key={label} className="grid gap-2 rounded-2xl border border-zinc-200 bg-zinc-50 px-3 py-2 md:grid-cols-[120px_minmax(0,1fr)]">
            <div className="text-xs font-medium text-zinc-400">{label}</div>
            <div className="break-all font-mono text-xs leading-5 text-zinc-700">{value}</div>
          </div>
        ))}
      </div>
    </details>
  );
}

function buildHumanSummary(stageId: string, context: Record<string, unknown>, state?: PipelineState) {
  const requirement = asRecord(context.requirement_structured);
  const design = asRecord(context.design_doc);
  const codeDiff = asRecord(context.code_diff);
  const testReport = asRecord(context.test_report);
  const delivery = asRecord(context.delivery);
  const patches = asArray(codeDiff.patches).map((item) => asRecord(item));

  if (!context || Object.keys(context).length === 0) {
    return {
      title: "等待 AI 返回第一份结果",
      description: "这里不会展示原始 JSON，而是把 AI 的结果翻译成你能判断的摘要。",
      items: [
        { label: "你会看到", value: "AI 理解、方案摘要、生成文件、测试结论和下一步建议。" },
      ],
    };
  }

  if (state === "FINISHED") {
    return {
      title: "交付完成",
      description: "最终结果已经整理好。路径信息仍放在开发者详情中，主界面只显示验收口径。",
      items: [
        { label: "验收状态", value: testPassedText(testReport, delivery) },
        { label: "交付说明", value: asString(delivery.summary) || "交付包已准备，可以打开结果进行人工验收。" },
      ],
    };
  }

  if (stageId === "analysis" || requirement.goal) {
    return {
      title: "AI 对需求的理解",
      description: "先确认 AI 是否做对事，再进入方案和代码生成。",
      items: [
        { label: "目标", value: asString(requirement.goal) || asString(context.requirement_raw) || "等待 AI 整理目标。" },
        { label: "验收标准", value: listText(requirement.acceptance_criteria) || "等待 AI 给出可判断的验收标准。" },
        { label: "边界/约束", value: listText(requirement.constraints) || "暂无明确约束，必要时可以补充。" },
      ],
    };
  }

  if (stageId === "design" || design.architecture) {
    return {
      title: "AI 给出的实现方案",
      description: "这里关注方向是否合理，不要求你阅读底层数据结构。",
      items: [
        { label: "实现思路", value: asString(design.architecture) || "等待方案生成。" },
        { label: "计划改动", value: filePlanText(design.file_change_plan) || "等待 AI 列出文件计划。" },
        { label: "风险", value: asString(design.risk_analysis) || "暂未发现明确风险。" },
      ],
    };
  }

  if (stageId === "coding" || patches.length > 0) {
    return {
      title: "AI 正在生成完整文件",
      description: "系统会严格检查返回格式；不合格会打回重写，不再生成占位文件。",
      items: [
        { label: "文件", value: patches.map((patch) => asString(patch.file_path)).filter(Boolean).join("、") || "等待豆包返回完整文件。" },
        { label: "规则", value: "必须返回完整文件内容，不能返回 fallback、TODO 或只有说明文字。" },
      ],
    };
  }

  if (stageId === "testing" || Object.keys(testReport).length > 0) {
    return {
      title: "测试与验收检查",
      description: "把技术测试结果翻译成是否可以继续交付。",
      items: [
        { label: "测试结论", value: testPassedText(testReport, delivery) },
        { label: "建议", value: "如果测试失败，系统会保留错误并停止交付，避免把坏结果交给你。" },
      ],
    };
  }

  return {
    title: "AI 阶段产物摘要",
    description: "阶段完成后，这里会用自然语言解释 AI 返回了什么。",
    items: [{ label: "当前状态", value: "AI 正在生成，请稍等。" }],
  };
}

function formatEditableStageDraft(pipeline: Pipeline) {
  const stageId = pipeline.checkpoint?.stageId || pipeline.currentStage?.id || "analysis";
  const contextKey = STAGE_CONTEXT_KEY[stageId] || "requirement_structured";
  const value = pipeline.context?.[contextKey] || {};
  return JSON.stringify(value, null, 2);
}

function buildContextPatchFromDraft(pipeline: Pipeline, draftText: string) {
  const stageId = pipeline.checkpoint?.stageId || pipeline.currentStage?.id || "analysis";
  const contextKey = STAGE_CONTEXT_KEY[stageId] || "requirement_structured";
  let parsed: unknown;

  try {
    parsed = JSON.parse(draftText);
  } catch {
    throw new Error("修改后的草稿必须是合法 JSON。请检查引号、逗号和括号。");
  }

  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error("修改后的草稿必须是一个 JSON 对象。");
  }

  return {
    [contextKey]: parsed,
    human_revision: {
      stage_id: stageId,
      context_key: contextKey,
      edited_at: new Date().toISOString(),
    },
  };
}

function parseDraftObject(draftText: string) {
  try {
    const parsed: unknown = JSON.parse(draftText || "{}");
    return parsed && typeof parsed === "object" && !Array.isArray(parsed)
      ? (parsed as Record<string, unknown>)
      : null;
  } catch {
    return null;
  }
}

function setField(target: Record<string, unknown>, key: string, value: unknown) {
  target[key] = value;
}

function arrayToLines(value: unknown) {
  return asArray(value).map(String).join("\n");
}

function linesToArray(value: string) {
  return value
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

function filePlanToLines(value: unknown) {
  return asArray(value)
    .map((item) => {
      const record = asRecord(item);
      const filePath = asString(record.file_path);
      const description = asString(record.description) || asString(record.reason);
      return [filePath, description].filter(Boolean).join(" - ");
    })
    .filter(Boolean)
    .join("\n");
}

function linesToFilePlan(value: string) {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [filePath, ...descriptionParts] = line.split(/\s+-\s+/);
      return {
        file_path: filePath.trim(),
        change_type: "create",
        description: descriptionParts.join(" - ").trim() || "用户修改后的文件计划",
        reason: "用户在方案审批阶段调整",
        risk_level: "low",
        acceptance_links: [],
      };
    });
}

function toFriendlyError(error: string) {
  if (!error) return "";
  if (error.includes("Diff Bundle") || error.includes("strict")) {
    const retryMatch = error.match(/after\s+(\d+)\s+attempts/i);
    return retryMatch
      ? `豆包连续 ${retryMatch[1]} 次没有按完整文件格式返回。系统已停止交付，避免生成错误项目。`
      : "豆包返回的代码格式没有通过检查。系统会把错误反馈给豆包并要求重新生成。";
  }
  if (error.includes("api_key")) {
    return "模型调用缺少 API Key，请先检查后端模型配置。";
  }
  return "AI 执行遇到问题。你可以打开开发者详情查看原始错误。";
}

function testPassedText(testReport: Record<string, unknown>, delivery: Record<string, unknown>) {
  const passed =
    typeof testReport.passed === "boolean"
      ? testReport.passed
      : typeof delivery.test_passed === "boolean"
      ? delivery.test_passed
      : undefined;
  if (passed === undefined) return "等待测试结果。";
  return passed ? "已通过，可以进入人工验收。" : "未通过，系统不会继续伪装成交付成功。";
}

function filePlanText(value: unknown) {
  return asArray(value)
    .map((item) => {
      const record = asRecord(item);
      return asString(record.file_path) || asString(record.description);
    })
    .filter(Boolean)
    .join("、");
}

function listText(value: unknown) {
  return asArray(value).map(String).filter(Boolean).join("；");
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function asString(value: unknown) {
  return typeof value === "string" && value.trim() ? value.trim() : "";
}
