import { Link } from "react-router-dom";
import {
  ArrowRight,
  ArrowLeft,
  Sparkles,
  Terminal,
  GitMerge,
  Cpu,
  Binary,
  CheckCircle2,
  CircleDot,
  FileText,
  Workflow,
  ShieldCheck,
  ChevronRight,
} from "lucide-react";
import WeaveMark from "../../../components/WeaveMark";

/**
 * Landing Page · v3 Hybrid
 * ------------------------------------------------------------------
 * 融合策略：
 *  - 骨架 = v1 (白底、细边、飞书信息密度)
 *  - 调性 = v2 (居中大字 Hero + <idea/> 极客标签 + 终端日志)
 *  - 质感 = Apple (只在关键 CTA 与 Hero 底注入辉光与玻璃态)
 *  - 品牌色 = ink-900 黑 为主 + weave 蓝 只出现在 "关键动作"
 *
 * Rams 原则：
 *  - 去掉 v2 的深色网格（视觉噪音）
 *  - 动效仅保留 slide-up + 日志光标闪烁
 *  - 按钮只用一种主按钮样式（黑底白字）
 * ------------------------------------------------------------------
 */
export default function LandingV3Hybrid() {
  return (
    <div className="min-h-full bg-white text-ink-900 relative overflow-hidden">
      {/* 极轻的 Hero 背景辉光——白底上的"一层温度" */}
      <div className="pointer-events-none absolute top-0 left-1/2 -translate-x-1/2 h-[520px] w-[1100px] rounded-full bg-weave-400/10 blur-[120px]" />
      <div className="pointer-events-none absolute top-32 right-1/4 h-[320px] w-[420px] rounded-full bg-glow-violet/10 blur-[100px]" />

      <div className="relative">
        <DraftBar />

        {/* Nav */}
        <header className="border-b border-ink-200 bg-white/85 backdrop-blur-xl sticky top-10 z-10">
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

        {/* Hero —— 居中大字，白底辉光 */}
        <section>
          <div className="mx-auto max-w-5xl px-6 pt-24 pb-16 text-center">
            <div className="inline-flex items-center gap-2 mb-6 animate-fade-in">
              <span className="inline-flex items-center gap-1.5 text-[11px] font-medium tracking-wider uppercase text-ink-500 px-2.5 py-1 rounded-full border border-ink-200 bg-white/70 backdrop-blur">
                <Sparkles className="h-3 w-3 text-weave-600" />
                AI-Native Delivery · Alpha
              </span>
            </div>

            <h1 className="text-5xl md:text-[64px] font-semibold tracking-tighter leading-[1.02] animate-slide-up">
              把
              <span className="inline-block mx-2 px-2.5 py-0.5 rounded-lg bg-ink-50 border border-ink-200 font-mono text-[0.82em] align-[0.08em] text-ink-700">
                &lt;idea/&gt;
              </span>
              <br className="hidden md:inline" />
              编译成
              <span className="ml-3 bg-gradient-to-r from-weave-700 via-weave-500 to-glow-violet bg-clip-text text-transparent">
                可合并的 MR。
              </span>
            </h1>

            <p className="mt-7 text-ink-600 text-lg leading-relaxed max-w-2xl mx-auto animate-slide-up">
              织界是一台透明的黑盒：需求 → 架构 → 代码 → 测试，
              每一步都可审阅、可回退、可信任。
            </p>

            <div className="mt-9 flex flex-wrap items-center justify-center gap-3 animate-slide-up">
              <button className="btn-primary h-11 px-5 text-[15px]">
                创建第一条流水线
                <ArrowRight className="h-4 w-4" />
              </button>
              <button className="btn-outline h-11 px-5 text-[15px]">
                <Terminal className="h-4 w-4" />
                查看 CLI 示例
              </button>
            </div>

            <div className="mt-7 flex items-center justify-center gap-5 text-xs text-ink-500">
              <span className="inline-flex items-center gap-1.5">
                <ShieldCheck className="h-3.5 w-3.5" />
                每一步都可审阅
              </span>
              <span className="text-ink-300">·</span>
              <span className="inline-flex items-center gap-1.5">
                <Workflow className="h-3.5 w-3.5" />
                状态机严格闭环
              </span>
              <span className="text-ink-300">·</span>
              <span className="inline-flex items-center gap-1.5">
                <GitMerge className="h-3.5 w-3.5" />
                自动 MR 交付
              </span>
            </div>

            {/* Hero 底部的"终端预览" —— 白底浅色版 */}
            <div className="mt-16 max-w-3xl mx-auto animate-slide-up">
              <TerminalPreviewLight />
            </div>
          </div>
        </section>

        {/* 四步流程 —— 飞书无缝栅格 + 连线箭头 */}
        <section className="border-t border-ink-200 bg-ink-50/40">
          <div className="mx-auto max-w-6xl px-6 py-20">
            <div className="max-w-2xl">
              <div className="eyebrow mb-4">
                <Cpu className="h-3.5 w-3.5" />
                Pipeline
              </div>
              <h2 className="text-3xl md:text-4xl font-semibold tracking-tight">
                四个节点，全链路可干预。
              </h2>
              <p className="mt-3 text-ink-600">
                每个节点产出都可展开审阅，拒绝即回退，通过即前进——
                没有黑盒，没有失控的幻觉。
              </p>
            </div>

            <div className="mt-12 relative">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-px bg-ink-200 border border-ink-200 rounded-lg overflow-hidden">
                {STEPS.map((s, i) => (
                  <div
                    key={s.title}
                    className="relative bg-white p-6 hover:bg-white transition-all group"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-mono text-ink-400">
                        0{i + 1}
                      </span>
                      <s.icon
                        className="h-4 w-4 text-ink-900 opacity-70 group-hover:opacity-100 group-hover:text-weave-600 transition-all"
                        strokeWidth={2}
                      />
                    </div>
                    <h3 className="mt-5 text-[15px] font-semibold">
                      {s.title}
                    </h3>
                    <p className="mt-2 text-[13px] text-ink-600 leading-relaxed">
                      {s.desc}
                    </p>
                    {i < STEPS.length - 1 && (
                      <ChevronRight className="hidden md:block absolute top-1/2 -right-[7px] -translate-y-1/2 h-3 w-3 text-ink-300 bg-white rounded-full z-10" />
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* Live Preview · 飞书卡片 + 流水线可视化 */}
        <section className="border-t border-ink-200">
          <div className="mx-auto max-w-6xl px-6 py-20 grid md:grid-cols-12 gap-10 items-center">
            <div className="md:col-span-5">
              <div className="eyebrow mb-4">Live Pipeline</div>
              <h2 className="text-3xl md:text-4xl font-semibold tracking-tight leading-tight">
                一眼看懂
                <br />
                AI 现在在做什么。
              </h2>
              <p className="mt-4 text-ink-600 leading-relaxed">
                控制台把每条流水线拆成清晰的节点。
                正在跑的一步会有柔和的光脉动；
                需要你审批的那一步，会主动把你叫回来。
              </p>
              <div className="mt-6 flex items-center gap-3">
                <button className="btn-primary h-10 px-5">
                  体验控制台
                  <ArrowRight className="h-4 w-4" />
                </button>
                <button className="btn-ghost h-10 px-5">
                  查看演示视频
                </button>
              </div>
            </div>
            <div className="md:col-span-7">
              <PipelineCard />
            </div>
          </div>
        </section>

        {/* Principles */}
        <section className="border-t border-ink-200 bg-ink-50/40">
          <div className="mx-auto max-w-6xl px-6 py-20 grid md:grid-cols-2 gap-16">
            <div>
              <div className="eyebrow mb-4">Principles</div>
              <h2 className="text-3xl md:text-4xl font-semibold tracking-tight leading-tight">
                不做
                <span className="text-ink-400 line-through mx-2 font-normal">
                  一键生成
                </span>
                <br />
                只做<span className="text-weave-700">可被信任的交付</span>。
              </h2>
            </div>
            <div className="space-y-4">
              {PRINCIPLES.map((p) => (
                <div key={p.title} className="card-feishu p-5">
                  <div className="flex items-center gap-2.5">
                    <div className="h-5 w-5 rounded-full bg-ink-900 flex items-center justify-center">
                      <CheckCircle2
                        className="h-3 w-3 text-white"
                        strokeWidth={3}
                      />
                    </div>
                    <h3 className="text-[15px] font-semibold">{p.title}</h3>
                  </div>
                  <p className="mt-2 text-sm text-ink-600 leading-relaxed pl-[30px]">
                    {p.desc}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* CTA · 苹果玻璃 + 微辉光 */}
        <section className="border-t border-ink-200">
          <div className="mx-auto max-w-5xl px-6 py-24">
            <div className="relative rounded-3xl border border-ink-200 bg-white shadow-apple-glass p-12 md:p-16 overflow-hidden">
              {/* 内辉光 */}
              <div className="absolute -top-24 -right-24 h-64 w-64 rounded-full bg-weave-400/20 blur-3xl" />
              <div className="absolute -bottom-20 -left-10 h-56 w-56 rounded-full bg-glow-violet/15 blur-3xl" />
              <div className="relative text-center">
                <h2 className="text-3xl md:text-5xl font-semibold tracking-tight">
                  准备好把下一个需求
                  <br />
                  交给流水线了吗？
                </h2>
                <p className="mt-4 text-ink-600 text-lg">
                  3 分钟创建，其余的事——我们接管。
                </p>
                <div className="mt-8 inline-flex items-center gap-3">
                  <button className="btn-primary h-11 px-6 text-[15px]">
                    立即开始
                    <ArrowRight className="h-4 w-4" />
                  </button>
                  <button className="btn-ghost h-11 px-6 text-[15px]">
                    阅读架构文档
                  </button>
                </div>
              </div>
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
    </div>
  );
}

/* ------------------ 小组件 ------------------ */

function DraftBar() {
  return (
    <div className="h-10 bg-ink-950 text-white flex items-center justify-between px-6 text-[11px] font-mono">
      <Link
        to="/drafts/landing/v2"
        className="flex items-center gap-1.5 hover:text-weave-300 transition-colors"
      >
        <ArrowLeft className="h-3 w-3" />
        上一版 v2
      </Link>
      <span className="text-white/60">
        drafts/landing/
        <span className="text-white">v3_hybrid</span>
        <span className="ml-2 inline-flex items-center px-1.5 py-px rounded bg-weave-500/20 text-weave-300 text-[10px]">
          NEW
        </span>
      </span>
      <Link
        to="/"
        className="flex items-center gap-1.5 hover:text-weave-300 transition-colors"
      >
        Draft Gallery
        <ArrowRight className="h-3 w-3" />
      </Link>
    </div>
  );
}

/**
 * 浅色版终端预览 —— 把 v2 最帅的部分翻译到白底
 * 关键：用 ink-50 底 + ink-200 边，保留 mono 字体和图标色；
 * 让"代码感"不靠暗色，而靠字体 + 留白。
 */
function TerminalPreviewLight() {
  return (
    <div className="rounded-xl border border-ink-200 bg-white shadow-apple-glass overflow-hidden text-left">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-ink-200 bg-ink-50/60">
        <div className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-red-400/80" />
          <span className="h-2.5 w-2.5 rounded-full bg-amber-400/80" />
          <span className="h-2.5 w-2.5 rounded-full bg-emerald-400/80" />
        </div>
        <span className="text-[11px] font-mono text-ink-500">
          weave · pipeline PIP-2046
        </span>
        <span className="text-[11px] font-mono text-amber-600 inline-flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-amber-500 animate-pulse" />
          WAITING_APPROVAL
        </span>
      </div>
      <div className="px-5 py-4 font-mono text-[13px] leading-7 space-y-1 bg-white">
        <div className="flex items-center gap-2 text-ink-700">
          <Binary className="h-3 w-3 text-weave-600" />
          <span className="text-ink-400">$</span>
          <span>weave create &quot;给博客加个评论功能&quot;</span>
        </div>
        <div className="flex items-center gap-2 text-emerald-600">
          <span className="inline-block w-3">✓</span>
          <span>需求澄清 · 3 条用户故事已生成</span>
        </div>
        <div className="flex items-center gap-2 text-emerald-600">
          <span className="inline-block w-3">✓</span>
          <span>架构设计 · 接口清单 &amp; 模块边界 · v1</span>
        </div>
        <div className="flex items-center gap-2 text-amber-600 animate-pulse">
          <span className="inline-block w-3">◆</span>
          <span>等待审批 · 你的一次点击，决定流水线往哪走</span>
        </div>
        <div className="flex items-center gap-2 text-ink-400">
          <span className="inline-block w-3">·</span>
          <span>代码生成 · 待触发</span>
        </div>
        <div className="flex items-center gap-2 text-ink-400">
          <span className="inline-block w-3">·</span>
          <span>测试 &amp; MR · 待触发</span>
        </div>
        <div className="flex items-center gap-2 pt-3 mt-2 border-t border-ink-100 text-xs">
          <button className="inline-flex items-center gap-1.5 h-7 px-3 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100 transition-colors">
            <CheckCircle2 className="h-3 w-3" />
            Approve
          </button>
          <button className="inline-flex items-center gap-1.5 h-7 px-3 rounded bg-white text-ink-600 border border-ink-200 hover:bg-ink-50 transition-colors">
            Reject &amp; 反馈
          </button>
          <span className="ml-auto text-ink-400 hidden sm:inline">
            ↑↓ 浏览制品 · ⏎ 确认
          </span>
        </div>
      </div>
    </div>
  );
}

function PipelineCard() {
  return (
    <div className="card-feishu overflow-hidden shadow-apple-glass">
      <div className="px-5 py-3 border-b border-ink-200 flex items-center justify-between bg-white">
        <div className="flex items-center gap-2.5">
          <span className="h-1.5 w-1.5 rounded-full bg-amber-500 animate-pulse" />
          <span className="text-[13px] font-semibold tracking-tight">
            PIP-2046
          </span>
          <span className="text-xs text-ink-500">· 给博客增加评论功能</span>
        </div>
        <span className="text-[11px] font-mono text-amber-600 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded">
          WAITING_APPROVAL
        </span>
      </div>
      <ul className="divide-y divide-ink-100">
        {PIPE_STEPS.map((s) => (
          <li
            key={s.name}
            className="px-5 py-3.5 flex items-center justify-between text-sm hover:bg-ink-50/50 transition-colors"
          >
            <div className="flex items-center gap-3">
              {s.state === "done" && (
                <CheckCircle2 className="h-4 w-4 text-emerald-500" />
              )}
              {s.state === "current" && (
                <div className="relative">
                  <CircleDot className="h-4 w-4 text-amber-500" />
                  <span className="absolute inset-0 rounded-full bg-amber-400/40 animate-ping" />
                </div>
              )}
              {s.state === "pending" && (
                <div className="h-4 w-4 rounded-full border border-ink-300" />
              )}
              <span
                className={
                  s.state === "pending"
                    ? "text-ink-400"
                    : "text-ink-800 font-medium"
                }
              >
                {s.name}
              </span>
              {s.state === "current" && (
                <span className="text-[11px] px-1.5 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-200">
                  需要你
                </span>
              )}
            </div>
            <span className="text-[11px] font-mono text-ink-400">{s.meta}</span>
          </li>
        ))}
      </ul>
      <div className="px-5 py-3 bg-gradient-to-r from-ink-50 to-white border-t border-ink-200 flex items-center justify-between">
        <span className="text-xs text-ink-600 inline-flex items-center gap-1.5">
          <FileText className="h-3.5 w-3.5" />
          架构方案 v1 · 待你审批 · 预计 3 分钟
        </span>
        <button className="btn-primary h-7 px-3 text-xs">查看详情</button>
      </div>
    </div>
  );
}

/* ------------------ 数据 ------------------ */

const STEPS = [
  { title: "需求理解", desc: "模糊的一句话 → 结构化用户故事。", icon: Sparkles },
  { title: "架构设计", desc: "可审阅的技术方案与接口约定。", icon: Cpu },
  { title: "代码生成", desc: "按方案落盘分支，改动可追溯。", icon: Terminal },
  { title: "测试 & MR", desc: "自动跑测试，通过即提交 MR。", icon: GitMerge },
];

const PRINCIPLES = [
  {
    title: "每一步都有人把关",
    desc: "需求、架构、代码、测试——任一节点你都可以 Approve 或 Reject 并留下反馈。",
  },
  {
    title: "状态机严格闭环",
    desc: "CREATED → RUNNING → WAITING_APPROVAL → FINISHED，不跳步、不丢状态。",
  },
  {
    title: "产物即文档",
    desc: "每个节点的输出沉淀为可检索制品，Markdown 与 Diff 视图原生支持。",
  },
];

const PIPE_STEPS = [
  { name: "需求澄清", state: "done", meta: "2.1s" },
  { name: "架构设计", state: "current", meta: "等你审批" },
  { name: "代码生成", state: "pending", meta: "—" },
  { name: "测试 & MR", state: "pending", meta: "—" },
] as const;
