import { Link } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  Bot,
  CheckCircle2,
  CircleDot,
  Code2,
  Cpu,
  FileText,
  GitBranch,
  GitMerge,
  MessageSquareText,
  ShieldCheck,
  Sparkles,
  Terminal,
  Workflow,
} from "lucide-react";
import WeaveMark from "../../../components/WeaveMark";

/**
 * Landing Page · v2 Geek Glow
 * ------------------------------------------------------------------
 * Product direction:
 * - Keep the v2 dark AI-native personality.
 * - Make the first screen explain the product, not just decorate it.
 * - Surface the competition requirements: Pipeline, HITL checkpoint,
 *   backend state machine, artifact review, and MR delivery.
 *
 * Design filter:
 * - v0: crisp hierarchy, strong interaction states, lucid panels.
 * - Dieter Rams: glow only where it explains active AI work.
 * - UX copy: action-first, no vague "submit" language.
 * ------------------------------------------------------------------
 */
export default function LandingV2Geek() {
  return (
    <div className="min-h-full bg-ink-950 text-white relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0 bg-grid-dark bg-grid-24 opacity-45" />
      <div className="pointer-events-none absolute -top-56 left-1/2 h-[720px] w-[980px] -translate-x-1/2 rounded-full bg-weave-500/20 blur-[150px]" />
      <div className="pointer-events-none absolute top-[22rem] -right-20 h-[520px] w-[580px] rounded-full bg-glow-violet/15 blur-[140px]" />
      <div className="pointer-events-none absolute bottom-0 left-0 h-[420px] w-[520px] rounded-full bg-cyan-400/10 blur-[140px]" />

      <div className="relative">
        <DraftBar />
        <SiteHeader />

        <main>
          <HeroSection />
          <TrustStrip />
          <PipelineSection />
          <FinalCta />
        </main>

        <Footer />
      </div>
    </div>
  );
}

function SiteHeader() {
  return (
    <header className="sticky top-10 z-10 border-b border-white/[0.06] bg-ink-950/65 backdrop-blur-xl">
      <div className="mx-auto max-w-7xl px-6 h-14 flex items-center justify-between">
        <div className="flex items-center gap-8">
          <div className="flex items-center gap-2.5">
            <div className="h-6 w-6 rounded-md bg-gradient-to-br from-weave-500 to-glow-violet flex items-center justify-center shadow-glow-sm">
              <WeaveMark className="h-4 w-4" />
            </div>
            <span className="font-semibold tracking-tight text-[15px]">
              织界 <span className="text-white/50 font-normal">Weave</span>
            </span>
          </div>
          <nav className="hidden md:flex items-center gap-7 text-sm text-white/58">
            {["产品", "工作流", "审批", "架构"].map((item) => (
              <a
                key={item}
                className="hover:text-white transition-colors cursor-pointer"
              >
                {item}
              </a>
            ))}
          </nav>
        </div>
        <div className="flex items-center gap-2">
          <button className="inline-flex items-center h-9 px-4 rounded-md text-sm text-white/65 hover:text-white hover:bg-white/[0.05] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-weave-400/40">
            登录
          </button>
          <Link to="/drafts/login/v2" className="btn-glow">
            进入控制台
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      </div>
    </header>
  );
}

function HeroSection() {
  return (
    <section className="relative">
      <div className="mx-auto max-w-7xl px-6 pt-16 pb-14 lg:pt-20 lg:pb-16 grid lg:grid-cols-[0.92fr_1.08fr] gap-12 items-center">
        <div className="animate-slide-up">
          <div className="inline-flex items-center gap-2 rounded-full border border-white/[0.08] bg-white/[0.04] px-3 py-1 text-[11px] font-medium tracking-wider uppercase text-white/58 backdrop-blur">
            <Sparkles className="h-3.5 w-3.5 text-weave-300" />
            AI-Native Delivery Engine
            <span className="h-1 w-1 rounded-full bg-white/25" />
            Alpha
          </div>

          <h1 className="mt-6 text-5xl md:text-7xl font-semibold tracking-tighter leading-[0.98]">
            输入一句需求。
            <br />
            让 AI 跑完一条
            <span className="block bg-gradient-to-r from-weave-300 via-weave-400 to-glow-violet bg-clip-text text-transparent">
              可审阅的交付流水线。
            </span>
          </h1>

          <p className="mt-7 max-w-xl text-lg leading-relaxed text-white/60">
            从一句需求到架构、代码、测试和 MR。AI 推进流程，你只在关键节点做判断。
          </p>

          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Link
              to="/drafts/login/v2"
              className="btn-glow h-11 px-6 text-[15px]"
            >
              打开控制台创建流水线
              <ArrowRight className="h-4 w-4" />
            </Link>
            <button className="inline-flex items-center gap-2 h-11 px-6 rounded-lg border border-white/10 bg-white/[0.03] text-white/78 text-[15px] font-medium backdrop-blur hover:bg-white/[0.06] hover:border-white/20 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/20">
              <Terminal className="h-4 w-4" />
              先看运行过程
            </button>
          </div>

        </div>

        <div className="animate-slide-up">
          <EnginePanel />
        </div>
      </div>
    </section>
  );
}

function EnginePanel() {
  return (
    <div className="relative">
      <div className="absolute -inset-8 rounded-[2rem] bg-gradient-to-br from-weave-500/20 via-transparent to-glow-violet/20 blur-3xl" />
      <div className="relative rounded-3xl border border-white/10 bg-black/55 backdrop-blur-xl shadow-2xl overflow-hidden">
        <div className="flex items-center justify-between border-b border-white/[0.07] bg-white/[0.025] px-4 py-3">
          <div className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full bg-red-500/70" />
            <span className="h-2.5 w-2.5 rounded-full bg-amber-500/70" />
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-500/70" />
          </div>
          <span className="text-[11px] font-mono text-white/38">
            示例：创建评论功能流水线
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-400/20 bg-amber-400/10 px-2 py-0.5 text-[11px] font-mono text-amber-300">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-300 animate-pulse" />
            等待你审批
          </span>
        </div>

        <div className="grid md:grid-cols-[1fr_0.92fr]">
          <div className="p-5 border-b md:border-b-0 md:border-r border-white/[0.07]">
            <div className="rounded-xl border border-white/[0.08] bg-white/[0.035] p-4">
              <div className="flex items-center gap-2 text-xs text-white/45">
                <MessageSquareText className="h-3.5 w-3.5 text-weave-300" />
                第 1 步：用户输入需求
              </div>
              <p className="mt-3 text-sm leading-relaxed text-white/80">
                “给博客增加评论功能，支持登录用户评论、管理员审核、敏感词过滤。”
              </p>
              <Link
                to="/drafts/console/v2"
                className="mt-4 inline-flex items-center gap-2 h-8 px-3 rounded-lg bg-white/[0.06] text-xs text-white/72 hover:bg-white/[0.1] hover:text-white transition-colors"
              >
                用这个例子试一遍
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>

            <div className="mt-4 space-y-3">
              {ENGINE_STEPS.map((step) => (
                <div
                  key={step.title}
                  className="group flex items-center gap-3 rounded-xl border border-white/[0.08] bg-white/[0.025] p-3 transition-all hover:bg-white/[0.045] hover:border-white/[0.14]"
                >
                  <div
                    className={`h-9 w-9 rounded-lg flex items-center justify-center ${
                      step.state === "done"
                        ? "bg-emerald-400/10 text-emerald-300"
                        : step.state === "current"
                        ? "bg-weave-500/12 text-weave-300 shadow-glow-sm"
                        : "bg-white/[0.04] text-white/30"
                    }`}
                  >
                    {step.state === "done" ? (
                      <CheckCircle2 className="h-4 w-4" />
                    ) : step.state === "current" ? (
                      <CircleDot className="h-4 w-4 animate-pulse" />
                    ) : (
                      <step.icon className="h-4 w-4" />
                    )}
                  </div>
                  <div className="min-w-0">
                    <div className="text-sm font-medium">{step.title}</div>
                    <div className="mt-0.5 text-xs text-white/42">{step.desc}</div>
                  </div>
                  <div className="ml-auto whitespace-nowrap text-[11px] text-white/35">
                    {step.api}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-xs text-white/38">第 3 步：需要你审批</div>
                <h3 className="mt-1 text-sm font-semibold">
                  架构方案 v1 等待确认
                </h3>
              </div>
              <ShieldCheck className="h-4 w-4 text-amber-300" />
            </div>

            <div className="mt-4 rounded-xl border border-amber-300/18 bg-amber-300/[0.08] p-4">
              <div className="text-xs font-mono text-amber-200">
                当前要做什么？
              </div>
              <p className="mt-2 text-sm leading-relaxed text-amber-50/70">
                先读方案。觉得方向对，就批准进入代码生成；觉得不对，就驳回并写反馈。
              </p>
              <div className="mt-4 flex gap-2">
                <button className="inline-flex items-center gap-1.5 h-8 px-3 rounded-lg bg-emerald-400 text-ink-950 text-xs font-semibold hover:bg-emerald-300 transition-colors">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  批准并继续
                </button>
                <button className="inline-flex items-center h-8 px-3 rounded-lg border border-white/10 bg-white/[0.04] text-xs text-white/65 hover:bg-white/[0.08] hover:text-white transition-colors">
                  驳回并反馈
                </button>
              </div>
            </div>

            <div className="mt-4 rounded-xl border border-white/[0.08] bg-black/45 p-4 font-mono text-[12px] leading-6">
              <p className="mb-2 text-white/38">
                你不用操作这些接口，前端会自动调用：
              </p>
              <p className="text-emerald-300">✓ POST /pipelines</p>
              <p className="text-emerald-300">✓ POST /pipelines/PIP-2046/run</p>
              <p className="text-weave-300">→ GET /pipelines/PIP-2046</p>
              <p className="text-amber-300">◆ checkpoint: architecture_v1</p>
              <p className="text-white/28">· POST /checkpoints/:id/approve</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function TrustStrip() {
  return (
    <section className="border-y border-white/[0.06] bg-white/[0.018]">
      <div className="mx-auto max-w-7xl px-6 py-5 grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
        {[
          ["你输入", "一句自然语言需求，不需要会写代码。"],
          ["AI 执行", "自动拆需求、写方案、生成代码和测试。"],
          ["你审批", "关键节点确认方向，最后得到 MR。"],
        ].map(([title, desc]) => (
          <div key={title} className="flex items-center gap-3 text-white/55">
            <span className="h-1.5 w-1.5 rounded-full bg-weave-300" />
            <span className="font-medium text-white/80">{title}</span>
            <span className="hidden sm:inline text-white/30">/</span>
            <span>{desc}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function PipelineSection() {
  return (
    <section className="border-b border-white/[0.06]">
      <div className="mx-auto max-w-7xl px-6 py-14">
        <SectionHeader
          eyebrow="Pipeline"
          title="打开控制台后，流程自动推进。"
          desc="你输入需求，AI 运行流水线；需要判断时，系统再把你叫回来。"
        />

        <div className="mt-8 grid grid-cols-1 md:grid-cols-4 gap-3">
          {STEPS.map((step, index) => (
            <div
              key={step.title}
              className="group relative rounded-2xl border border-white/[0.08] bg-white/[0.025] p-4 transition-all duration-300 hover:-translate-y-1 hover:bg-white/[0.045] hover:border-white/[0.15]"
            >
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-mono text-white/35">
                  0{index + 1}
                </span>
                <step.icon className="h-4 w-4 text-weave-300 opacity-80 group-hover:opacity-100" />
              </div>
              <h3 className="mt-5 text-[15px] font-semibold">{step.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-white/52">
                {step.desc}
              </p>
              <div className="mt-4 rounded-lg border border-white/[0.06] bg-black/30 px-3 py-2">
                <div className="text-[11px] text-white/38">页面会显示</div>
                <div className="mt-1 text-xs font-medium text-white/70">
                  {step.state}
                </div>
              </div>
              {index < STEPS.length - 1 && (
                <div className="hidden md:block absolute top-1/2 -right-2 h-px w-4 bg-gradient-to-r from-weave-300/40 to-transparent" />
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function FinalCta() {
  return (
    <section>
      <div className="mx-auto max-w-6xl px-6 py-28">
        <div className="relative overflow-hidden rounded-[2rem] border border-white/10 bg-gradient-to-br from-white/[0.065] to-white/[0.022] px-8 py-14 md:px-16 md:py-20 backdrop-blur-xl shadow-apple-modal">
          <div className="absolute -right-28 -top-28 h-80 w-80 rounded-full bg-weave-500/24 blur-3xl" />
          <div className="absolute -bottom-28 -left-24 h-72 w-72 rounded-full bg-glow-violet/18 blur-3xl" />
          <div className="relative mx-auto max-w-3xl text-center">
            <div className="inline-flex items-center justify-center gap-2 text-[11px] font-medium tracking-wider uppercase text-white/45">
                <Bot className="h-3.5 w-3.5 text-weave-300" />
                Start with one sentence
            </div>
            <h2 className="mt-5 text-3xl md:text-[44px] font-semibold tracking-tight leading-tight">
                把下一个需求，交给一条可审阅的流水线。
            </h2>
            <p className="mx-auto mt-5 max-w-xl text-sm md:text-base leading-relaxed text-white/56">
                进入控制台，体验从创建 Pipeline 到等待审批的完整前端闭环。
            </p>
            <div className="mt-8 flex flex-wrap justify-center gap-3">
              <Link to="/drafts/login/v2" className="btn-glow h-11 px-6">
                打开控制台
                <ArrowRight className="h-4 w-4" />
              </Link>
              <button className="inline-flex items-center h-11 px-6 rounded-lg border border-white/10 bg-white/[0.035] text-sm text-white/75 hover:bg-white/[0.07] hover:text-white transition-colors">
                阅读接口契约
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="border-t border-white/[0.06]">
      <div className="mx-auto max-w-7xl px-6 py-10 flex flex-col md:flex-row items-center justify-between gap-4 text-xs text-white/40">
        <div className="flex items-center gap-2">
          <div className="h-5 w-5 rounded bg-gradient-to-br from-weave-500 to-glow-violet flex items-center justify-center">
            <WeaveMark className="h-3.5 w-3.5" />
          </div>
          <span>织界 Weave · 透明的黑盒</span>
        </div>
        <div className="flex items-center gap-5">
          <a className="hover:text-white transition-colors cursor-pointer">GitHub</a>
          <a className="hover:text-white transition-colors cursor-pointer">架构共识</a>
          <a className="hover:text-white transition-colors cursor-pointer">隐私</a>
        </div>
      </div>
    </footer>
  );
}

function DraftBar() {
  return (
    <div className="h-10 bg-black text-white/80 border-b border-white/[0.06] flex items-center justify-between px-6 text-[11px] font-mono">
      <Link
        to="/drafts/landing/v1"
        className="flex items-center gap-1.5 hover:text-weave-300 transition-colors"
      >
        <ArrowLeft className="h-3 w-3" />
        上一版 v1
      </Link>
      <span className="text-white/40">
        drafts/landing/<span className="text-white">v2_geek_glow</span>
        <span className="ml-2 text-weave-300">optimized</span>
      </span>
      <Link
        to="/drafts/landing/v3"
        className="flex items-center gap-1.5 hover:text-weave-300 transition-colors"
      >
        下一版 v3 · Hybrid
        <ArrowRight className="h-3 w-3" />
      </Link>
    </div>
  );
}

function SectionHeader({
  eyebrow,
  title,
  desc,
}: {
  eyebrow: string;
  title: string;
  desc: string;
}) {
  return (
    <div className="max-w-2xl">
      <div className="eyebrow !text-white/55 mb-4">{eyebrow}</div>
      <h2 className="text-3xl md:text-4xl font-semibold tracking-tight">
        {title}
      </h2>
      <p className="mt-3 text-white/58 leading-relaxed">{desc}</p>
    </div>
  );
}

const ENGINE_STEPS = [
  {
    title: "需求澄清",
    desc: "生成用户故事与边界条件",
    api: "已完成",
    icon: MessageSquareText,
    state: "done",
  },
  {
    title: "架构设计",
    desc: "等待 Tech Lead 审批",
    api: "需要你确认",
    icon: Workflow,
    state: "current",
  },
  {
    title: "代码生成",
    desc: "按方案写入分支",
    api: "审批后开始",
    icon: Code2,
    state: "pending",
  },
  {
    title: "测试 & MR",
    desc: "生成测试报告与 MR",
    api: "最后交付",
    icon: GitMerge,
    state: "pending",
  },
] as const;

const STEPS = [
  {
    title: "输入需求",
    desc: "在控制台写一句话，例如：给博客增加评论功能。",
    icon: FileText,
    state: "创建流水线",
  },
  {
    title: "点击创建并运行",
    desc: "系统创建 Pipeline 并启动 Agent，页面开始展示进度。",
    icon: Cpu,
    state: "正在执行",
  },
  {
    title: "审批关键产物",
    desc: "看到架构方案后，选择批准继续或驳回修改。",
    icon: ShieldCheck,
    state: "等待你审批",
  },
  {
    title: "拿到 MR",
    desc: "通过测试后生成 MR，把结果交给工程流程。",
    icon: GitBranch,
    state: "交付完成",
  },
];

