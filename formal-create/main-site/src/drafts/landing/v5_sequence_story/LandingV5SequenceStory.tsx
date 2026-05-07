import { useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  CheckCircle2,
  CircleDot,
  Code2,
  Eclipse,
  FileText,
  GitMerge,
  ShieldCheck,
  Sparkles,
  SunMedium,
  Workflow,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import WeaveMark from "../../../components/WeaveMark";

type SequenceStep = {
  id: string;
  title: string;
  agent: string;
  desc: string;
  artifact: string;
  icon: LucideIcon;
  status: "done" | "active" | "next";
};

type Mode = "night" | "day";

const sequenceSteps: SequenceStep[] = [
  {
    id: "01",
    title: "需求建档",
    agent: "Requirement Agent",
    desc: "把一句自然语言需求拆成目标、角色、约束和验收标准。",
    artifact: "Requirement Brief",
    icon: FileText,
    status: "done",
  },
  {
    id: "02",
    title: "生成计划",
    agent: "Planning Agent",
    desc: "先生成可审阅的交付计划，而不是直接让 AI 写代码。",
    artifact: "Delivery Plan",
    icon: Workflow,
    status: "done",
  },
  {
    id: "03",
    title: "人工确认",
    agent: "Human Checkpoint",
    desc: "在关键节点暂停，由你判断是否接受方案并继续执行。",
    artifact: "WAITING_APPROVAL",
    icon: ShieldCheck,
    status: "active",
  },
  {
    id: "04",
    title: "代码与测试",
    agent: "Coding Agent",
    desc: "确认后再进入实现、测试建议和变更摘要生成。",
    artifact: "Diff + Tests",
    icon: Code2,
    status: "next",
  },
  {
    id: "05",
    title: "交付合并",
    agent: "Delivery Agent",
    desc: "输出需求文档、架构方案、测试摘要和可合并 MR。",
    artifact: "Merge Request",
    icon: GitMerge,
    status: "next",
  },
];

const painPoints = [
  {
    title: "需求写完就散了",
    desc: "自然语言、群聊、文档散落各处，很难沉淀成可追踪交付流。",
    old: "靠人整理",
    now: "自动建档",
  },
  {
    title: "AI 直接写代码不可控",
    desc: "没有计划和审批点，越自动越容易偏离业务目标。",
    old: "抽卡生成",
    now: "先审计划",
  },
  {
    title: "交付结果难验收",
    desc: "需求、方案、测试和 MR 分散，评审时缺少同一条线索。",
    old: "人工对齐",
    now: "闭环交付",
  },
];

const metrics = [
  { value: "1", label: "句话创建 Pipeline" },
  { value: "4", label: "个状态可追踪" },
  { value: "1", label: "个关键人工闸门" },
];

export default function LandingV5SequenceStory() {
  const [mode, setMode] = useState<Mode>("night");
  const isNight = mode === "night";

  return (
    <div
      className={`relative min-h-full overflow-hidden transition-colors duration-500 ${
        isNight ? "bg-[#090910] text-white" : "bg-[#f7f8fb] text-ink-900"
      }`}
    >
      <div
        className={`pointer-events-none absolute inset-0 transition-opacity duration-500 ${
          isNight
            ? "bg-[radial-gradient(circle_at_50%_-20%,rgba(139,92,246,0.22),transparent_36%),linear-gradient(135deg,#0a0a0f_0%,#111118_48%,#0b0712_100%)]"
            : "bg-[radial-gradient(circle_at_50%_-20%,rgba(96,135,255,0.14),transparent_36%),linear-gradient(135deg,#ffffff_0%,#f6f8ff_50%,#f7f0ff_100%)]"
        }`}
      />
      {isNight && <div className="stellar-field pointer-events-none" />}
      <div
        className={`pointer-events-none absolute -top-48 left-[14%] h-[620px] w-[720px] rounded-full blur-[160px] ${
          isNight ? "bg-weave-500/20" : "bg-weave-300/20"
        }`}
      />
      <div
        className={`pointer-events-none absolute right-[-12%] top-40 h-[560px] w-[680px] rounded-full blur-[150px] ${
          isNight ? "bg-glow-pink/15" : "bg-pink-200/30"
        }`}
      />
      <div
        className={`pointer-events-none absolute bottom-[-20%] left-[35%] h-[520px] w-[720px] rounded-full blur-[170px] ${
          isNight ? "bg-glow-violet/20" : "bg-violet-200/30"
        }`}
      />
      <div
        className={`pointer-events-none absolute inset-0 bg-grid-24 ${
          isNight ? "bg-grid-dark opacity-[0.16]" : "bg-grid-light opacity-70"
        }`}
      />

      <div className="relative">
        <header
          className={`sticky top-0 z-20 border-b backdrop-blur-2xl transition-colors duration-500 ${
            isNight
              ? "border-white/[0.08] bg-[#0d0d16]/65"
              : "border-ink-200 bg-white/80 shadow-feishu-card"
          }`}
        >
          <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-6">
            <div className="flex items-center gap-8">
              <div className="flex items-center gap-2.5">
                <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-weave-400 via-glow-violet to-glow-pink shadow-[0_0_24px_rgba(139,92,246,0.34)]">
                  <WeaveMark className="h-4 w-4" />
                </div>
                <span className="text-[15px] font-semibold tracking-tight">
                  织界{" "}
                  <span className={isNight ? "text-white/45" : "text-ink-400"}>
                    Weave
                  </span>
                </span>
              </div>
              <nav
                className={`hidden items-center gap-7 text-sm md:flex ${
                  isNight ? "text-white/50" : "text-ink-500"
                }`}
              >
                {["问题", "流水线", "角色", "交付"].map((item) => (
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
                className={`inline-flex h-9 items-center gap-2 rounded-lg px-4 text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 ${
                  isNight
                    ? "bg-white text-ink-950 hover:bg-white/90 focus-visible:ring-white/30"
                    : "bg-ink-900 text-white hover:bg-ink-800 focus-visible:ring-ink-900/20"
                }`}
              >
                进入控制台
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>
          </div>
        </header>

        <main>
          <section className="mx-auto grid max-w-7xl items-center gap-12 px-6 pb-16 pt-16 lg:grid-cols-[0.9fr_1.1fr] lg:pb-20 lg:pt-20">
            <div className="animate-slide-up">
              <div
                className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-[11px] font-medium uppercase tracking-wider backdrop-blur ${
                  isNight
                    ? "border-white/[0.10] bg-white/[0.04] text-white/55"
                    : "border-ink-200 bg-white/80 text-ink-500"
                }`}
              >
                <Sparkles className="h-3.5 w-3.5 text-glow-pink" />
                Sequential AI Delivery Engine
              </div>

              <h1 className="mt-6 text-5xl font-semibold leading-[0.96] tracking-tighter md:text-7xl">
                把一句需求，
                <span className="block bg-gradient-to-r from-weave-200 via-glow-violet to-glow-pink bg-clip-text text-transparent">
                  变成可审批的交付流。
                </span>
              </h1>

              <p
                className={`mt-6 max-w-2xl text-[15px] leading-8 ${
                  isNight ? "text-white/58" : "text-ink-600"
                }`}
              >
                织界不会让 AI 一上来就写代码。它先理解需求，生成计划，在关键节点等待人工确认，
                再继续推进代码、测试和 MR 交付。
              </p>

              <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                <Link
                  to="/drafts/login/v2"
                  className="inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-weave-400 via-glow-violet to-glow-pink px-5 text-sm font-semibold text-white shadow-[0_0_30px_rgba(236,72,153,0.24)] transition-all hover:scale-[1.01] hover:shadow-[0_0_38px_rgba(236,72,153,0.34)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-glow-pink/40"
                >
                  创建第一条需求流水线
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <Link
                  to="/drafts/login/v2"
                  className={`inline-flex h-11 items-center justify-center gap-2 rounded-xl border px-5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 ${
                    isNight
                      ? "border-white/[0.10] bg-white/[0.04] text-white/70 hover:bg-white/[0.08] hover:text-white focus-visible:ring-white/20"
                      : "border-ink-200 bg-white text-ink-700 hover:border-ink-300 hover:bg-ink-50 focus-visible:ring-ink-300"
                  }`}
                >
                  体验审批工作台
                </Link>
              </div>

              <div className="mt-10 grid max-w-xl grid-cols-3 gap-3">
                {metrics.map((item) => (
                  <div
                    key={item.label}
                    className={`rounded-2xl border p-4 backdrop-blur-xl ${
                      isNight
                        ? "border-white/[0.08] bg-white/[0.035]"
                        : "border-ink-200 bg-white/80 shadow-feishu-card"
                    }`}
                  >
                    <div className="text-2xl font-semibold tracking-tight">{item.value}</div>
                    <div
                      className={`mt-1 text-xs leading-relaxed ${
                        isNight ? "text-white/40" : "text-ink-500"
                      }`}
                    >
                      {item.label}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <SequenceStudio isNight={isNight} />
          </section>

          <PainSection isNight={isNight} />
          <FlowSection isNight={isNight} />
          <RoleSection isNight={isNight} />
          <FinalCta isNight={isNight} />
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
      type="button"
      onClick={() => onChange(isNight ? "day" : "night")}
      className={`hidden h-9 items-center gap-2 rounded-lg border px-3 text-xs font-medium transition-all sm:inline-flex ${
        isNight
          ? "border-white/[0.10] bg-white/[0.04] text-white/60 hover:bg-white/[0.08] hover:text-white"
          : "border-ink-200 bg-white text-ink-600 shadow-feishu-card hover:text-ink-900"
      }`}
      aria-label={isNight ? "切换到日间飞书审阅风格" : "切换到夜间 AI 引擎风格"}
    >
      {isNight ? <Eclipse className="h-3.5 w-3.5" /> : <SunMedium className="h-3.5 w-3.5" />}
      {isNight ? "Night" : "Day"}
    </button>
  );
}

function SequenceStudio({ isNight }: { isNight: boolean }) {
  return (
    <div className="relative animate-slide-up">
      <div
        className={`absolute inset-0 rounded-[2rem] blur-3xl ${
          isNight ? "bg-gradient-to-r from-weave-500/20 to-glow-pink/20" : "bg-weave-300/20"
        }`}
      />
      <div
        className={`relative overflow-hidden rounded-[2rem] border backdrop-blur-2xl ${
          isNight
            ? "border-white/[0.10] bg-[#10101a]/72 shadow-[0_30px_100px_rgba(0,0,0,0.35),inset_0_1px_0_rgba(255,255,255,0.05)]"
            : "border-ink-200 bg-white/90 shadow-apple-glass"
        }`}
      >
        <div
          className={`flex items-center justify-between border-b px-5 py-4 ${
            isNight ? "border-white/[0.07]" : "border-ink-200"
          }`}
        >
          <div>
            <div
              className={`text-[11px] font-mono uppercase tracking-[0.16em] ${
                isNight ? "text-white/35" : "text-ink-400"
              }`}
            >
              Requirement Studio
            </div>
            <div className="mt-1 text-sm font-semibold">博客评论功能 · 交付计划</div>
          </div>
          <span className="rounded-full border border-amber-300/25 bg-amber-500/10 px-3 py-1 text-[11px] font-mono text-amber-200">
            WAITING_APPROVAL
          </span>
        </div>

        <div className="p-5">
          <div
            className={`rounded-2xl border p-4 ${
              isNight ? "border-white/[0.08] bg-black/25" : "border-ink-200 bg-ink-50"
            }`}
          >
            <div className={`text-xs font-semibold ${isNight ? "text-white/80" : "text-ink-800"}`}>
              需求理解
            </div>
            <p className={`mt-2 text-sm leading-7 ${isNight ? "text-white/55" : "text-ink-600"}`}>
              给博客增加评论功能：登录用户可评论，管理员可审核，敏感词自动拦截，并生成可合并 MR。
            </p>
          </div>

          <div className="mt-4 space-y-3">
            {sequenceSteps.map((step) => (
              <SequenceRow key={step.id} step={step} isNight={isNight} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function SequenceRow({ step, isNight }: { step: SequenceStep; isNight: boolean }) {
  const Icon = step.icon;
  const done = step.status === "done";
  const active = step.status === "active";

  return (
    <div
      className={`rounded-2xl border p-4 transition-all ${
        active
          ? "border-glow-pink/35 bg-gradient-to-br from-weave-500/15 via-glow-violet/10 to-glow-pink/10 shadow-[0_0_32px_rgba(236,72,153,0.14)]"
          : done
          ? "border-emerald-400/20 bg-emerald-500/10"
          : isNight
          ? "border-white/[0.07] bg-white/[0.025]"
          : "border-ink-200 bg-white"
      }`}
    >
      <div className="flex items-start gap-3">
        <div
          className={`flex h-10 w-10 flex-none items-center justify-center rounded-xl ${
            active
              ? "bg-gradient-to-br from-weave-400/25 to-glow-pink/20 text-glow-pink"
              : done
              ? "bg-emerald-500/15 text-emerald-300"
              : "bg-white/[0.04] text-white/30"
          }`}
        >
          {done ? <CheckCircle2 className="h-4 w-4" /> : active ? <CircleDot className="h-4 w-4 animate-pulse" /> : <Icon className="h-4 w-4" />}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <div className="flex items-center gap-2">
                <span className={`font-mono text-[10px] ${isNight ? "text-white/30" : "text-ink-400"}`}>
                  {step.id}
                </span>
                <div className="text-sm font-semibold">{step.title}</div>
              </div>
              <div className={`mt-0.5 text-[11px] font-mono ${isNight ? "text-white/35" : "text-ink-400"}`}>
                {step.agent}
              </div>
            </div>
            <span
              className={`rounded-full border px-2 py-1 text-[10px] font-mono ${
                active
                  ? "border-amber-300/25 bg-amber-500/10 text-amber-200"
                  : done
                  ? "border-emerald-300/20 bg-emerald-500/10 text-emerald-300"
                  : isNight
                  ? "border-white/[0.08] bg-white/[0.03] text-white/35"
                  : "border-ink-200 bg-ink-50 text-ink-500"
              }`}
            >
              {step.artifact}
            </span>
          </div>
          <p className={`mt-2 text-xs leading-relaxed ${isNight ? "text-white/45" : "text-ink-500"}`}>
            {step.desc}
          </p>
        </div>
      </div>
    </div>
  );
}

function PainSection({ isNight }: { isNight: boolean }) {
  return (
    <section className="mx-auto max-w-7xl px-6 py-16">
      <SectionHeader
        isNight={isNight}
        eyebrow="你正在经历的"
        title="需求交付不是缺 AI，而是缺一条可控的顺序。"
        desc="比起让模型直接生成结果，团队真正需要的是：先理解、再计划、可暂停、可审批、可交付。"
      />
      <div className="mt-8 grid gap-4 md:grid-cols-3">
        {painPoints.map((item, index) => (
          <div
            key={item.title}
            className={`flex h-full flex-col rounded-[1.5rem] border p-5 backdrop-blur-xl transition-all hover:-translate-y-1 ${
              isNight
                ? "border-white/[0.08] bg-white/[0.035] hover:border-glow-violet/25 hover:bg-white/[0.055]"
                : "border-ink-200 bg-white/85 shadow-feishu-card hover:border-weave-200 hover:shadow-feishu-hover"
            }`}
          >
            <div className={`font-mono text-xs ${isNight ? "text-white/30" : "text-ink-400"}`}>
              0{index + 1}
            </div>
            <h3 className="mt-4 text-lg font-semibold tracking-tight">{item.title}</h3>
            <p className={`mt-3 text-sm leading-7 ${isNight ? "text-white/48" : "text-ink-600"}`}>
              {item.desc}
            </p>
            <div className="mt-auto grid grid-cols-2 gap-2 pt-5 text-xs">
              <div
                className={`rounded-xl border p-3 ${
                  isNight
                    ? "border-white/[0.06] bg-black/20 text-white/38"
                    : "border-ink-200 bg-ink-50 text-ink-500"
                }`}
              >
                以前：{item.old}
              </div>
              <div className="rounded-xl border border-glow-pink/20 bg-glow-pink/10 p-3 text-glow-pink">
                现在：{item.now}
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function FlowSection({ isNight }: { isNight: boolean }) {
  return (
    <section className="mx-auto max-w-7xl px-6 py-16">
      <SectionHeader
        isNight={isNight}
        eyebrow="顺序流水线"
        title="不是并行进度条，而是一条会暂停等待你的交付路径。"
        desc="每一步都有明确输入、产物和下一步条件。关键节点不自动越过，而是交给人判断。"
      />
      <div className="mt-8 grid gap-3 lg:grid-cols-5">
        {sequenceSteps.map((step, index) => {
          const Icon = step.icon;
          return (
            <div
              key={step.id}
              className={`relative rounded-[1.35rem] border p-5 backdrop-blur-xl ${
                isNight ? "border-white/[0.08] bg-white/[0.035]" : "border-ink-200 bg-white/85 shadow-feishu-card"
              }`}
            >
              {index < sequenceSteps.length - 1 && (
                <div className="absolute right-[-14px] top-9 hidden h-px w-7 bg-gradient-to-r from-white/20 to-transparent lg:block" />
              )}
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/[0.05] text-weave-200">
                <Icon className="h-4 w-4" />
              </div>
              <div className={`mt-5 font-mono text-[10px] ${isNight ? "text-white/30" : "text-ink-400"}`}>
                {step.id}
              </div>
              <h3 className="mt-1 text-sm font-semibold">{step.title}</h3>
              <p className={`mt-2 text-xs leading-6 ${isNight ? "text-white/42" : "text-ink-500"}`}>
                {step.desc}
              </p>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function RoleSection({ isNight }: { isNight: boolean }) {
  const roles = [
    ["新手", "解释每一步发生了什么，告诉你下一步点哪里。"],
    ["产品", "优先看需求目标、边界条件和验收标准。"],
    ["技术", "优先看架构影响、接口、状态机和测试。"],
    ["管理", "优先看进度、风险、阻塞和最终交付。"],
  ];

  return (
    <section className="mx-auto max-w-7xl px-6 py-16">
      <div
        className={`rounded-[2rem] border p-6 backdrop-blur-2xl md:p-8 ${
          isNight
            ? "border-white/[0.10] bg-[#10101a]/70"
            : "border-ink-200 bg-white/85 shadow-apple-glass"
        }`}
      >
        <div className="grid gap-8 lg:grid-cols-[0.85fr_1.15fr] lg:items-center">
          <div>
            <div className="text-[11px] font-mono uppercase tracking-[0.16em] text-glow-pink">
              Role Lens
            </div>
            <h2 className="mt-4 text-3xl font-semibold tracking-tight md:text-4xl">
              同一条流水线，四种读法。
            </h2>
            <p className={`mt-4 text-sm leading-7 ${isNight ? "text-white/50" : "text-ink-600"}`}>
              角色不会改变后端接口，也不会生成四个控制台。它只改变默认展开内容、文案密度和审批关注点。
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {roles.map(([name, desc]) => (
              <div
                key={name}
                className={`rounded-2xl border p-4 ${
                  isNight ? "border-white/[0.08] bg-white/[0.035]" : "border-ink-200 bg-ink-50"
                }`}
              >
                <div className="text-sm font-semibold">{name}</div>
                <p className={`mt-2 text-xs leading-6 ${isNight ? "text-white/45" : "text-ink-500"}`}>
                  {desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function FinalCta({ isNight }: { isNight: boolean }) {
  return (
    <section className="mx-auto max-w-7xl px-6 pb-20 pt-12">
      <div
        className={`relative overflow-hidden rounded-[2rem] border p-8 text-center backdrop-blur-2xl ${
          isNight ? "border-white/[0.10] bg-white/[0.04]" : "border-ink-200 bg-white/85 shadow-apple-glass"
        }`}
      >
        <div className="pointer-events-none absolute inset-x-20 top-0 h-32 rounded-full bg-glow-pink/15 blur-3xl" />
        <div className="relative">
          <div className={`text-[11px] font-mono uppercase tracking-[0.16em] ${isNight ? "text-white/35" : "text-ink-400"}`}>
            Ready to deliver?
          </div>
          <h2 className="mt-4 text-3xl font-semibold tracking-tight md:text-5xl">
            今天的一句需求，今晚变成可审阅交付包。
          </h2>
          <p className={`mx-auto mt-4 max-w-2xl text-sm leading-7 ${isNight ? "text-white/50" : "text-ink-600"}`}>
            从需求理解、计划确认到人工审批和 MR 交付，织界把 AI 的黑盒过程变成一条可控路径。
          </p>
          <Link
            to="/drafts/login/v2"
            className="mt-7 inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-white px-5 text-sm font-semibold text-ink-950 transition-all hover:bg-white/90"
          >
            开始体验
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </div>
    </section>
  );
}

function SectionHeader({
  isNight,
  eyebrow,
  title,
  desc,
}: {
  isNight: boolean;
  eyebrow: string;
  title: string;
  desc: string;
}) {
  return (
    <div className="max-w-3xl">
      <div className="text-[11px] font-mono uppercase tracking-[0.16em] text-glow-pink">
        {eyebrow}
      </div>
      <h2 className="mt-4 text-3xl font-semibold tracking-tight md:text-5xl">{title}</h2>
      <p className={`mt-4 text-sm leading-7 ${isNight ? "text-white/50" : "text-ink-600"}`}>
        {desc}
      </p>
    </div>
  );
}
