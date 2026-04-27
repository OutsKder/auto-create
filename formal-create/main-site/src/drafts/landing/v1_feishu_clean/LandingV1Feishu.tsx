import { Link } from "react-router-dom";
import {
  ArrowRight,
  ArrowLeft,
  GitBranch,
  CheckCircle2,
  CircleDot,
  FileText,
  ShieldCheck,
  Users,
  Workflow,
  Zap,
} from "lucide-react";
import WeaveMark from "../../../components/WeaveMark";

/**
 * Landing Page · v1 Feishu Clean
 * ------------------------------------------------------------------
 * 设计目标：最克制的飞书骨架。
 *  - 白底 / 薄边 / 无阴影或极浅阴影
 *  - 强栅格感、信息密度高
 *  - 只有一个品牌色（ink-900 黑），不炫技、不渐变
 *  - 字体层级严谨，标题用 tracking-tight，正文宽松行距
 * ------------------------------------------------------------------
 */
export default function LandingV1Feishu() {
  return (
    <div className="min-h-full bg-white text-ink-900">
      <DraftBar />

      {/* Nav */}
      <header className="border-b border-ink-200 bg-white/90 backdrop-blur sticky top-10 z-10">
        <div className="mx-auto max-w-6xl px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-8">
            <div className="flex items-center gap-2">
              <div className="h-6 w-6 rounded-md bg-ink-900 flex items-center justify-center">
                <WeaveMark className="h-4 w-4" />
              </div>
              <span className="font-semibold tracking-tight text-[15px]">
                织界 <span className="text-ink-400 font-normal">Weave</span>
              </span>
            </div>
            <nav className="hidden md:flex items-center gap-7 text-sm text-ink-600">
              <a className="hover:text-ink-900 transition-colors">产品</a>
              <a className="hover:text-ink-900 transition-colors">工作流</a>
              <a className="hover:text-ink-900 transition-colors">文档</a>
              <a className="hover:text-ink-900 transition-colors">更新日志</a>
            </nav>
          </div>
          <div className="flex items-center gap-2">
            <button className="btn-ghost">登录</button>
            <button className="btn-primary">
              进入控制台
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="border-b border-ink-200">
        <div className="mx-auto max-w-6xl px-6 py-20 md:py-28 grid md:grid-cols-12 gap-10 items-center">
          <div className="md:col-span-7 animate-slide-up">
            <div className="eyebrow mb-5">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
              Alpha · 面向工程师的需求交付引擎
            </div>
            <h1 className="text-4xl md:text-[52px] font-semibold tracking-tight leading-[1.08]">
              把「一句需求」
              <br />
              变成「可合并的 MR」。
            </h1>
            <p className="mt-6 text-ink-600 text-lg leading-relaxed max-w-xl">
              织界是一台透明的黑盒。
              你只负责在关键节点做决定，其余的事——
              需求、架构、代码、测试——交给流水线。
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <button className="btn-primary h-10 px-5">
                创建第一条流水线
                <ArrowRight className="h-4 w-4" />
              </button>
              <button className="btn-outline h-10 px-5">
                <GitBranch className="h-4 w-4" />
                查看样例 PR
              </button>
            </div>
            <div className="mt-10 flex items-center gap-6 text-xs text-ink-500">
              <span className="inline-flex items-center gap-2">
                <ShieldCheck className="h-3.5 w-3.5" />
                每一步都可审阅
              </span>
              <span className="inline-flex items-center gap-2">
                <Users className="h-3.5 w-3.5" />
                支持多角色审批
              </span>
              <span className="inline-flex items-center gap-2">
                <Workflow className="h-3.5 w-3.5" />
                状态机严格闭环
              </span>
            </div>
          </div>

          {/* Hero visual: 飞书风流水线卡 */}
          <div className="md:col-span-5">
            <PipelineCard />
          </div>
        </div>
      </section>

      {/* 四步流程 */}
      <section className="border-b border-ink-200">
        <div className="mx-auto max-w-6xl px-6 py-20">
          <div className="max-w-2xl">
            <div className="eyebrow mb-4">How it works</div>
            <h2 className="text-3xl font-semibold tracking-tight">
              四个节点，看得见、可干预。
            </h2>
            <p className="mt-3 text-ink-600">
              每个节点产出都可展开审阅，拒绝即回退，通过即前进——
              没有黑盒，没有幻觉的失控。
            </p>
          </div>

          <div className="mt-12 grid grid-cols-1 md:grid-cols-4 gap-px bg-ink-200 border border-ink-200 rounded-lg overflow-hidden">
            {STEPS.map((s, i) => (
              <div key={s.title} className="bg-white p-6 hover:bg-ink-50 transition-colors">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono text-ink-400">
                    0{i + 1}
                  </span>
                  <s.icon className="h-4 w-4 text-ink-900" strokeWidth={2} />
                </div>
                <h3 className="mt-5 text-[15px] font-semibold">{s.title}</h3>
                <p className="mt-2 text-[13px] text-ink-600 leading-relaxed">
                  {s.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Why / Principles */}
      <section className="border-b border-ink-200">
        <div className="mx-auto max-w-6xl px-6 py-20 grid md:grid-cols-2 gap-16">
          <div>
            <div className="eyebrow mb-4">Why Weave</div>
            <h2 className="text-3xl font-semibold tracking-tight">
              不做「一键生成」，
              <br />
              只做「可被信任的交付」。
            </h2>
          </div>
          <div className="space-y-6">
            {PRINCIPLES.map((p) => (
              <div key={p.title} className="flex gap-4">
                <div className="flex-none mt-0.5">
                  <div className="h-5 w-5 rounded-full border border-ink-900 flex items-center justify-center">
                    <CheckCircle2 className="h-3 w-3 text-ink-900" />
                  </div>
                </div>
                <div>
                  <h3 className="text-[15px] font-semibold">{p.title}</h3>
                  <p className="mt-1.5 text-sm text-ink-600 leading-relaxed">
                    {p.desc}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="bg-ink-50">
        <div className="mx-auto max-w-6xl px-6 py-20 text-center">
          <h2 className="text-3xl md:text-4xl font-semibold tracking-tight">
            准备好把下一个需求，交给流水线了吗？
          </h2>
          <p className="mt-4 text-ink-600">从创建第一条流水线开始，3 分钟完成。</p>
          <div className="mt-8 inline-flex items-center gap-3">
            <button className="btn-primary h-11 px-6">
              <Zap className="h-4 w-4" />
              立即开始
            </button>
            <button className="btn-ghost h-11 px-6">
              阅读架构文档
              <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-ink-200">
        <div className="mx-auto max-w-6xl px-6 py-10 flex flex-col md:flex-row items-center justify-between gap-4 text-xs text-ink-500">
          <div className="flex items-center gap-2">
            <div className="h-5 w-5 rounded bg-ink-900 flex items-center justify-center">
              <WeaveMark className="h-3.5 w-3.5" />
            </div>
            <span>织界 Weave · 透明的黑盒</span>
          </div>
          <div className="flex items-center gap-5">
            <a className="hover:text-ink-900">GitHub</a>
            <a className="hover:text-ink-900">架构共识</a>
            <a className="hover:text-ink-900">隐私</a>
          </div>
        </div>
      </footer>
    </div>
  );
}

/* ------------------ 小组件 ------------------ */

function DraftBar() {
  return (
    <div className="h-10 bg-ink-950 text-white flex items-center justify-between px-6 text-[11px] font-mono">
      <Link to="/" className="flex items-center gap-1.5 hover:text-weave-300 transition-colors">
        <ArrowLeft className="h-3 w-3" />
        Draft Gallery
      </Link>
      <span className="text-white/60">
        drafts/landing/<span className="text-white">v1_feishu_clean</span>
      </span>
      <Link to="/drafts/landing/v2" className="flex items-center gap-1.5 hover:text-weave-300 transition-colors">
        下一版 v2
        <ArrowRight className="h-3 w-3" />
      </Link>
    </div>
  );
}

function PipelineCard() {
  return (
    <div className="card-feishu overflow-hidden">
      <div className="px-4 py-3 border-b border-ink-200 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="h-1.5 w-1.5 rounded-full bg-amber-500 animate-pulse-slow" />
          <span className="text-[13px] font-medium">PIP-2046</span>
          <span className="text-xs text-ink-400">· 给博客增加评论功能</span>
        </div>
        <span className="text-[11px] font-mono text-ink-400">
          WAITING_APPROVAL
        </span>
      </div>
      <ul className="divide-y divide-ink-100">
        {PIPE_STEPS.map((s) => (
          <li
            key={s.name}
            className="px-4 py-3 flex items-center justify-between text-sm"
          >
            <div className="flex items-center gap-2.5">
              {s.state === "done" && (
                <CheckCircle2 className="h-4 w-4 text-emerald-500" />
              )}
              {s.state === "current" && (
                <CircleDot className="h-4 w-4 text-amber-500 animate-pulse" />
              )}
              {s.state === "pending" && (
                <div className="h-4 w-4 rounded-full border border-ink-300" />
              )}
              <span className={s.state === "pending" ? "text-ink-400" : ""}>
                {s.name}
              </span>
            </div>
            <span className="text-[11px] font-mono text-ink-400">
              {s.meta}
            </span>
          </li>
        ))}
      </ul>
      <div className="px-4 py-3 bg-ink-50 border-t border-ink-200 flex items-center justify-between">
        <span className="text-xs text-ink-600 inline-flex items-center gap-1.5">
          <FileText className="h-3.5 w-3.5" />
          架构方案 · v1 已生成，等待你的审批
        </span>
        <button className="btn-primary h-7 px-3 text-xs">查看详情</button>
      </div>
    </div>
  );
}

/* ------------------ 数据 ------------------ */

const STEPS = [
  { title: "需求理解", desc: "把模糊的一句话，转成结构化的用户故事。", icon: FileText },
  { title: "架构设计", desc: "产出可审阅的技术方案与接口约定。", icon: Workflow },
  { title: "代码生成", desc: "按方案落盘分支，每一次改动都可追溯。", icon: GitBranch },
  { title: "测试与 MR", desc: "自动跑测试，通过后提交 Merge Request。", icon: ShieldCheck },
];

const PRINCIPLES = [
  {
    title: "每一个节点都有人把关。",
    desc: "需求、架构、代码、测试——在任何一步，你都可以 Approve 或 Reject 并留下反馈。",
  },
  {
    title: "状态机严格闭环。",
    desc: "CREATED → RUNNING → WAITING_APPROVAL → FINISHED，不跳步、不丢状态，后端完全受控。",
  },
  {
    title: "产物即文档。",
    desc: "每个节点的输出都沉淀为可检索的制品，Markdown 与 Diff 视图原生支持。",
  },
];

const PIPE_STEPS = [
  { name: "需求澄清", state: "done", meta: "2s" },
  { name: "架构设计", state: "current", meta: "等你审批" },
  { name: "代码生成", state: "pending", meta: "—" },
  { name: "测试 & MR", state: "pending", meta: "—" },
] as const;
