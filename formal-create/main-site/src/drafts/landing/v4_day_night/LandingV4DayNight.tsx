import { useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  CircleDot,
  Code2,
  Eclipse,
  FileText,
  GitMerge,
  Moon,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  SunMedium,
  Terminal,
  Workflow,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import WeaveMark from "../../../components/WeaveMark";

type Mode = "day" | "night";
type PipelineCode = "CREATED" | "RUNNING" | "WAITING_APPROVAL" | "FINISHED";

const pipelineStates: {
  code: PipelineCode;
  title: string;
  day: string;
  night: string;
  icon: LucideIcon;
}[] = [
  {
    code: "CREATED",
    title: "需求建档",
    day: "把一句话需求沉淀成可追踪任务",
    night: "捕获输入，生成 pipeline context",
    icon: FileText,
  },
  {
    code: "RUNNING",
    title: "AI 推进",
    day: "生成架构、代码、测试建议",
    night: "Engine synthesizing delivery flow",
    icon: Terminal,
  },
  {
    code: "WAITING_APPROVAL",
    title: "人工判断",
    day: "关键节点等待你审批或退回",
    night: "Human gate required",
    icon: ShieldCheck,
  },
  {
    code: "FINISHED",
    title: "MR 交付",
    day: "输出可审阅、可合并的结果",
    night: "Merge request prepared",
    icon: GitMerge,
  },
];

const semanticLayers: Record<Mode, { label: string; icon: LucideIcon }[]> = {
  day: [
    { label: "文档层：看清需求与约束", icon: FileText },
    { label: "审批层：知道何时该判断", icon: ShieldCheck },
    { label: "交付层：确认 MR 可以合并", icon: GitMerge },
  ],
  night: [
    { label: "日志层：看到 AI 正在推进", icon: Terminal },
    { label: "代码层：生成实现与测试", icon: Code2 },
    { label: "控制层：在审批点接管", icon: ShieldCheck },
  ],
};

const modeCopy: Record<
  Mode,
  {
    badge: string;
    titleLead: string;
    titleAccent: string;
    description: string;
    secondaryAction: string;
  }
> = {
  day: {
    badge: "Day Review Mode",
    titleLead: "让需求在可审阅的光线下",
    titleAccent: "自动流动。",
    description:
      "日间模式保留飞书式清晰骨架，把需求、审批和 MR 交付摊开给团队看。",
    secondaryAction: "切到夜间引擎",
  },
  night: {
    badge: "Night Engine Mode",
    titleLead: "把一句需求送进",
    titleAccent: "透明黑盒。",
    description:
      "夜间模式强化 AI 运行感：系统自动推进架构、代码和测试，只在 WAITING_APPROVAL 时把你叫回来。",
    secondaryAction: "切到日间审阅",
  },
};

const statusTone: Record<PipelineCode, string> = {
  CREATED: "已建档",
  RUNNING: "运行中",
  WAITING_APPROVAL: "待审批",
  FINISHED: "可交付",
};

const focusCopy: Record<
  PipelineCode,
  { status: string; title: string; description: string }
> = {
  CREATED: {
    status: "已建档",
    title: "一句需求已创建流水线",
    description:
      "用户只需要输入目标和约束，系统会把它建档为可追踪的 Pipeline，并准备进入 AI 生成阶段。",
  },
  RUNNING: {
    status: "运行中",
    title: "AI 正在推进交付流",
    description:
      "引擎正在生成架构建议、实现计划和测试思路。这个阶段自动推进，不需要用户手动拆任务。",
  },
  WAITING_APPROVAL: {
    status: "等待审批",
    title: "架构建议等待审批",
    description:
      "AI 已经完成需求解析和方案生成。现在暂停在人工判断点，等待你批准继续生成代码与 MR。",
  },
  FINISHED: {
    status: "MR 已生成",
    title: "交付结果准备完成",
    description:
      "审批通过后，流水线继续生成代码、测试建议和合并请求。你可以进入控制台查看完整产物。",
  },
};

export default function LandingV4DayNight() {
  const [mode, setMode] = useState<Mode>("night");
  const [activeCode, setActiveCode] = useState<PipelineCode>("WAITING_APPROVAL");
  const isNight = mode === "night";
  const copy = modeCopy[mode];

  return (
    <div
      className={`min-h-full relative overflow-hidden transition-colors duration-500 ${
        isNight ? "bg-ink-950 text-white" : "bg-white text-ink-900"
      }`}
    >
      <div
        className={`pointer-events-none absolute inset-0 transition-opacity duration-500 ${
          isNight ? "bg-grid-dark opacity-45" : "bg-grid-light opacity-70"
        } bg-grid-24`}
      />
      <div
        className={`pointer-events-none absolute -top-52 left-1/2 h-[680px] w-[980px] -translate-x-1/2 rounded-full blur-[150px] transition-colors duration-500 ${
          isNight ? "bg-weave-500/20" : "bg-weave-300/15"
        }`}
      />
      <div
        className={`pointer-events-none absolute bottom-0 right-0 h-[520px] w-[560px] rounded-full blur-[140px] transition-colors duration-500 ${
          isNight ? "bg-glow-violet/15" : "bg-amber-200/25"
        }`}
      />

      <div className="relative">
        <DraftBar isNight={isNight} />
        <header
          className={`sticky top-10 z-10 border-b backdrop-blur-xl transition-colors duration-500 ${
            isNight
              ? "border-white/[0.06] bg-ink-950/65"
              : "border-ink-200 bg-white/80"
          }`}
        >
          <div className="mx-auto max-w-7xl px-6 h-14 flex items-center justify-between">
            <div className="flex items-center gap-8">
              <div className="flex items-center gap-2.5">
                <div
                  className={`h-6 w-6 rounded-md flex items-center justify-center transition-colors duration-500 ${
                    isNight
                      ? "bg-gradient-to-br from-weave-500 to-glow-violet shadow-glow-sm"
                      : "bg-ink-900"
                  }`}
                >
                  <WeaveMark className="h-4 w-4" />
                </div>
                <span className="font-semibold tracking-tight text-[15px]">
                  织界{" "}
                  <span className={isNight ? "text-white/50" : "text-ink-400"}>
                    Weave
                  </span>
                </span>
              </div>
              <nav
                className={`hidden md:flex items-center gap-7 text-sm ${
                  isNight ? "text-white/55" : "text-ink-600"
                }`}
              >
                {["产品", "工作流", "审批", "架构"].map((item) => (
                  <a
                    key={item}
                    className={`cursor-pointer transition-colors ${
                      isNight ? "hover:text-white" : "hover:text-ink-900"
                    }`}
                  >
                    {item}
                  </a>
                ))}
              </nav>
            </div>
            <div className="flex items-center gap-2">
              <ThemeSwitch mode={mode} onChange={setMode} />
              <Link
                to="/drafts/login/v2"
                className={`inline-flex items-center gap-2 h-9 px-4 rounded-md text-sm font-medium transition-all ${
                  isNight
                    ? "bg-white text-ink-950 hover:bg-white/90"
                    : "bg-ink-900 text-white hover:bg-ink-800"
                }`}
              >
                进入控制台
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>
          </div>
        </header>

        <main>
          <section className="mx-auto max-w-7xl px-6 pt-16 pb-14 lg:pt-20 lg:pb-16 grid lg:grid-cols-[0.92fr_1.08fr] gap-12 items-center">
            <div className="animate-slide-up">
              <div
                className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-[11px] font-medium tracking-wider uppercase backdrop-blur ${
                  isNight
                    ? "border-white/[0.08] bg-white/[0.04] text-white/55"
                    : "border-ink-200 bg-white/70 text-ink-500"
                }`}
              >
                {isNight ? (
                  <Eclipse className="h-3.5 w-3.5 text-weave-300" />
                ) : (
                  <SunMedium className="h-3.5 w-3.5 text-amber-500" />
                )}
                Transparent Blackbox · {copy.badge}
              </div>

              <h1 className="mt-6 text-5xl md:text-7xl font-semibold tracking-tighter leading-[0.98]">
                {copy.titleLead}
                <span
                  className={`block bg-clip-text text-transparent ${
                    isNight
                      ? "bg-gradient-to-r from-weave-300 via-weave-400 to-glow-violet"
                      : "bg-gradient-to-r from-ink-900 via-weave-700 to-glow-violet"
                  }`}
                >
                  {copy.titleAccent}
                </span>
              </h1>

              <p
                className={`mt-7 max-w-xl text-lg leading-relaxed ${
                  isNight ? "text-white/60" : "text-ink-600"
                }`}
              >
                {copy.description}
              </p>

              <div className="mt-8 flex flex-wrap items-center gap-3">
                <Link
                  to="/drafts/login/v2"
                  className={`inline-flex items-center gap-2 h-11 px-6 rounded-lg text-[15px] font-medium transition-all ${
                    isNight
                      ? "bg-white text-ink-950 hover:bg-white/90 shadow-glow-sm"
                      : "bg-ink-900 text-white hover:bg-ink-800 shadow-feishu-hover"
                  }`}
                >
                  创建可审阅流水线
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <button
                  onClick={() => setMode(isNight ? "day" : "night")}
                  className={`inline-flex items-center gap-2 h-11 px-6 rounded-lg border text-[15px] font-medium backdrop-blur transition-all focus-visible:outline-none focus-visible:ring-2 ${
                    isNight
                      ? "border-white/10 bg-white/[0.03] text-white/75 hover:bg-white/[0.06] focus-visible:ring-white/20"
                      : "border-ink-200 bg-white/70 text-ink-700 hover:bg-ink-50 focus-visible:ring-ink-900/15"
                  }`}
                >
                  {isNight ? <SunMedium className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
                  {copy.secondaryAction}
                </button>
              </div>
            </div>

            <SolarEnginePanel
              mode={mode}
              activeCode={activeCode}
              onSelect={setActiveCode}
              onApprove={() => setActiveCode("FINISHED")}
              onReset={() => setActiveCode("WAITING_APPROVAL")}
            />
          </section>

          <section
            className={`border-t transition-colors duration-500 ${
              isNight ? "border-white/[0.07]" : "border-ink-200 bg-ink-50/45"
            }`}
          >
            <div className="mx-auto max-w-7xl px-6 py-12">
              <StateRail
                mode={mode}
                activeCode={activeCode}
                onSelect={setActiveCode}
              />
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}

function ThemeSwitch({
  mode,
  onChange,
}: {
  mode: Mode;
  onChange: (mode: Mode) => void;
}) {
  const isNight = mode === "night";
  return (
    <button
      onClick={() => onChange(isNight ? "day" : "night")}
      aria-label="切换昼夜模式"
      className={`group relative h-9 w-[72px] rounded-full border p-1 transition-all duration-500 focus-visible:outline-none focus-visible:ring-2 ${
        isNight
          ? "border-white/10 bg-white/[0.05] focus-visible:ring-weave-400/40"
          : "border-ink-200 bg-ink-50 focus-visible:ring-ink-900/15"
      }`}
    >
      <span
        className={`absolute top-1 h-7 w-7 rounded-full flex items-center justify-center transition-all duration-500 ${
          isNight
            ? "translate-x-9 bg-ink-950 text-weave-300 shadow-glow-sm"
            : "translate-x-0 bg-white text-amber-500 shadow-feishu-card"
        }`}
      >
        {isNight ? <Eclipse className="h-4 w-4" /> : <SunMedium className="h-4 w-4" />}
      </span>
    </button>
  );
}

function SolarEnginePanel({
  mode,
  activeCode,
  onSelect,
  onApprove,
  onReset,
}: {
  mode: Mode;
  activeCode: PipelineCode;
  onSelect: (code: PipelineCode) => void;
  onApprove: () => void;
  onReset: () => void;
}) {
  const isNight = mode === "night";
  const layers = semanticLayers[mode];
  const isFinished = activeCode === "FINISHED";
  const focus = focusCopy[activeCode];

  return (
    <div className="relative animate-slide-up">
      <div
        className={`absolute -inset-6 rounded-[2rem] blur-3xl transition-colors duration-500 ${
          isNight
            ? "bg-gradient-to-br from-weave-500/15 via-transparent to-glow-violet/15"
            : "bg-gradient-to-br from-weave-200/30 via-transparent to-amber-200/30"
        }`}
      />
      <div
        className={`relative rounded-[2rem] border backdrop-blur-xl overflow-hidden transition-all duration-500 ${
          isNight
            ? "border-white/10 bg-black/60 shadow-2xl"
            : "border-ink-200 bg-white/90 shadow-apple-modal"
        }`}
      >
        <div
          className={`flex items-center justify-between border-b px-5 py-4 ${
            isNight ? "border-white/[0.07] bg-white/[0.025]" : "border-ink-200 bg-ink-50/70"
          }`}
        >
          <div>
            <div className={isNight ? "text-xs text-white/40" : "text-xs text-ink-500"}>
              Solar Engine Panel
            </div>
            <div className="mt-1 text-sm font-semibold">评论功能交付流水线</div>
          </div>
          <span
            className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[11px] ${
              isFinished
                ? isNight
                  ? "border-emerald-400/20 bg-emerald-400/10 text-emerald-300"
                  : "border-emerald-200 bg-emerald-50 text-emerald-700"
                : isNight
                  ? "border-amber-400/20 bg-amber-400/10 text-amber-300"
                  : "border-amber-200 bg-amber-50 text-amber-700"
            }`}
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                isFinished ? "bg-emerald-400" : "bg-amber-400 animate-pulse"
              }`}
            />
            {focus.status}
          </span>
        </div>

        <div className="p-5">
          <div className="relative">
            <div
              className={`absolute left-8 right-8 top-1/2 h-px -translate-y-1/2 ${
                isNight
                  ? "bg-gradient-to-r from-weave-400/20 via-weave-300/80 to-glow-violet/20"
                  : "bg-gradient-to-r from-ink-200 via-weave-400 to-ink-200"
              }`}
            />
            <div className="relative grid grid-cols-4 gap-3">
              {pipelineStates.map(({ code, title, icon: Icon }, index) => {
                const active = code === activeCode;
                return (
                  <button
                    key={code}
                    type="button"
                    onClick={() => onSelect(code)}
                    className="group flex flex-col items-center text-center focus-visible:outline-none"
                  >
                    <span
                      className={`relative h-14 w-14 rounded-2xl border flex items-center justify-center transition-all duration-500 group-hover:-translate-y-0.5 ${
                        active
                          ? code === "FINISHED"
                            ? isNight
                              ? "border-emerald-300/45 bg-emerald-300/10 text-emerald-300 shadow-[0_0_26px_rgba(52,211,153,0.16)]"
                              : "border-emerald-300 bg-emerald-50 text-emerald-700 shadow-feishu-card"
                            : code === "WAITING_APPROVAL"
                              ? isNight
                                ? "border-amber-300/45 bg-amber-300/10 text-amber-300 shadow-[0_0_26px_rgba(251,191,36,0.18)]"
                                : "border-amber-300 bg-amber-50 text-amber-700 shadow-feishu-card"
                              : isNight
                                ? "border-weave-300/45 bg-weave-300/10 text-weave-200 shadow-glow-sm"
                                : "border-weave-200 bg-weave-50 text-weave-700 shadow-feishu-card"
                          : isNight
                            ? "border-white/[0.08] bg-white/[0.04] text-weave-300"
                            : "border-ink-200 bg-white text-weave-600 shadow-feishu-card"
                      }`}
                    >
                      {active && (
                        <span
                          className={`absolute -inset-1 rounded-[1.15rem] border animate-pulse ${
                            code === "FINISHED"
                              ? "border-emerald-300/25"
                              : code === "WAITING_APPROVAL"
                                ? "border-amber-300/25"
                                : "border-weave-300/25"
                          }`}
                        />
                      )}
                      <Icon className="h-5 w-5" />
                    </span>
                    <span
                      className={`mt-3 text-center text-[10px] font-mono ${
                        isNight ? "text-white/35" : "text-ink-400"
                      }`}
                    >
                      {index + 1}. {code}
                    </span>
                    <span className="mt-1 text-center text-xs font-semibold">
                      {title}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          <div
            className={`mt-6 rounded-2xl border p-4 ${
              isNight ? "border-white/[0.08] bg-white/[0.035]" : "border-ink-200 bg-white"
            }`}
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className={isNight ? "text-xs text-white/40" : "text-xs text-ink-500"}>
                  当前焦点
                </div>
                <div className="mt-1 text-lg font-semibold">{focus.title}</div>
                <p
                  className={`mt-2 text-sm leading-relaxed ${
                    isNight ? "text-white/55" : "text-ink-600"
                  }`}
                >
                  {focus.description}
                </p>
              </div>
              {isFinished ? (
                <CheckCircle2 className={isNight ? "h-5 w-5 text-emerald-300" : "h-5 w-5 text-emerald-600"} />
              ) : (
                <Sparkles className={isNight ? "h-5 w-5 text-weave-300" : "h-5 w-5 text-weave-600"} />
              )}
            </div>

            <div className="mt-5 grid gap-2">
              {layers.map(({ label, icon: Icon }) => (
                <div
                  key={label}
                  className={`flex items-center gap-2 rounded-xl px-3 py-2 text-sm transition-colors ${
                    isNight ? "bg-white/[0.04] text-white/65" : "bg-ink-50 text-ink-600"
                  }`}
                >
                  <Icon className={isNight ? "h-4 w-4 text-weave-300" : "h-4 w-4 text-weave-600"} />
                  {label}
                </div>
              ))}
            </div>

            <div className="mt-5 flex flex-wrap items-center gap-2">
              {activeCode === "FINISHED" ? (
                <>
                  <Link
                    to="/drafts/login/v2"
                    className={`inline-flex items-center gap-2 h-9 px-4 rounded-lg text-sm font-medium transition-colors ${
                      isNight
                        ? "bg-white text-ink-950 hover:bg-white/90"
                        : "bg-ink-900 text-white hover:bg-ink-800"
                    }`}
                  >
                    查看控制台
                    <ArrowRight className="h-3.5 w-3.5" />
                  </Link>
                  <button
                    onClick={onReset}
                    className={`inline-flex items-center gap-2 h-9 px-4 rounded-lg border text-sm font-medium transition-colors ${
                      isNight
                        ? "border-white/10 bg-white/[0.03] text-white/65 hover:bg-white/[0.06] hover:text-white"
                        : "border-ink-200 bg-white text-ink-600 hover:bg-ink-50 hover:text-ink-900"
                    }`}
                  >
                    <RotateCcw className="h-3.5 w-3.5" />
                    重新演示
                  </button>
                </>
              ) : activeCode === "WAITING_APPROVAL" ? (
                <button
                  onClick={onApprove}
                  className={`inline-flex items-center gap-2 h-9 px-4 rounded-lg text-sm font-medium transition-colors ${
                    isNight
                      ? "bg-amber-300 text-ink-950 hover:bg-amber-200"
                      : "bg-amber-500 text-white hover:bg-amber-600"
                  }`}
                >
                  批准流程
                  <ArrowRight className="h-3.5 w-3.5" />
                </button>
              ) : (
                <div
                  className={`inline-flex h-9 items-center rounded-lg px-3 text-xs ${
                    isNight ? "bg-white/[0.035] text-white/45" : "bg-ink-50 text-ink-500"
                  }`}
                >
                  点击其他节点查看说明，审批节点可推进流程。
                </div>
              )}
            </div>
          </div>

          <div className="mt-4 grid grid-cols-4 gap-2 text-xs">
            {pipelineStates.map(({ code }) => (
              <div
                key={code}
                className={`rounded-xl border px-3 py-2 ${
                  isNight
                    ? "border-white/[0.08] bg-white/[0.03]"
                    : "border-ink-200 bg-ink-50"
                }`}
              >
                <div className={isNight ? "font-mono text-white/35" : "font-mono text-ink-400"}>
                  {code}
                </div>
                <div className="mt-1 font-medium">
                  {statusTone[code as keyof typeof statusTone]}
                </div>
              </div>
            ))}
          </div>

          <div
            className={`mt-4 flex items-center gap-2 text-xs ${
              isNight ? "text-white/45" : "text-ink-500"
            }`}
          >
            <Workflow className="h-3.5 w-3.5" />
            昼夜切换只改变信息读法，不改变后端状态机。
          </div>
        </div>
      </div>
    </div>
  );
}

function StateRail({
  mode,
  activeCode,
  onSelect,
}: {
  mode: Mode;
  activeCode: PipelineCode;
  onSelect: (code: PipelineCode) => void;
}) {
  const isNight = mode === "night";

  return (
    <div
      className={`rounded-[1.5rem] border px-4 py-4 ${
        isNight
          ? "border-white/[0.08] bg-white/[0.025]"
          : "border-ink-200 bg-white shadow-feishu-card"
      }`}
    >
      <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
        {pipelineStates.map(({ code, title, day, night, icon: Icon }, index) => {
          const active = code === activeCode;
          return (
            <button
              key={code}
              type="button"
              onClick={() => onSelect(code)}
              className={`relative rounded-2xl border p-4 transition-all ${
                active
                  ? code === "FINISHED"
                    ? isNight
                      ? "border-emerald-300/30 bg-emerald-300/10"
                      : "border-emerald-200 bg-emerald-50/70"
                    : code === "WAITING_APPROVAL"
                      ? isNight
                        ? "border-amber-300/30 bg-amber-300/10"
                        : "border-amber-200 bg-amber-50/70"
                      : isNight
                        ? "border-weave-300/25 bg-weave-300/10"
                        : "border-weave-200 bg-weave-50/70"
                  : isNight
                    ? "border-white/[0.06] bg-white/[0.025]"
                    : "border-transparent bg-ink-50/70"
              } text-left hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-weave-400/30`}
            >
              <div className="flex items-center justify-between">
                <span className={isNight ? "font-mono text-[10px] text-white/30" : "font-mono text-[10px] text-ink-400"}>
                  0{index + 1} / {code}
                </span>
                <Icon
                  className={`h-4 w-4 ${
                    active
                      ? code === "FINISHED"
                        ? "text-emerald-400"
                        : code === "WAITING_APPROVAL"
                          ? "text-amber-400"
                          : isNight
                            ? "text-weave-200"
                            : "text-weave-700"
                      : isNight
                        ? "text-weave-300"
                        : "text-weave-600"
                  }`}
                />
              </div>
              <div className="mt-4 text-sm font-semibold">{title}</div>
              <p className={`mt-2 text-xs leading-relaxed ${isNight ? "text-white/45" : "text-ink-500"}`}>
                {isNight ? night : day}
              </p>
              {active && (
                <div
                  className={`mt-3 inline-flex items-center gap-1.5 text-[11px] font-medium ${
                    code === "FINISHED"
                      ? "text-emerald-500"
                      : code === "WAITING_APPROVAL"
                        ? "text-amber-500"
                        : "text-weave-500"
                  }`}
                >
                  <CircleDot className={`h-3 w-3 ${code === "FINISHED" ? "" : "animate-pulse"}`} />
                  {code === "FINISHED"
                    ? "MR 已准备完成"
                    : code === "WAITING_APPROVAL"
                      ? "等待人类确认"
                      : "正在查看此节点"}
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function DraftBar({ isNight }: { isNight: boolean }) {
  return (
    <div
      className={`sticky top-0 z-20 h-10 border-b backdrop-blur-xl ${
        isNight
          ? "border-white/[0.06] bg-black/35 text-white/45"
          : "border-ink-200 bg-white/75 text-ink-500"
      }`}
    >
      <div className="mx-auto max-w-7xl px-6 h-full flex items-center justify-between text-xs">
        <Link
          to="/"
          className={`inline-flex items-center gap-1.5 transition-colors ${
            isNight ? "hover:text-white" : "hover:text-ink-900"
          }`}
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Draft Gallery
        </Link>
        <span className="font-mono">v4 · day/night workspace</span>
      </div>
    </div>
  );
}
