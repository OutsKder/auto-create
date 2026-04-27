import { Link } from "react-router-dom";
import { ArrowUpRight, Sparkles } from "lucide-react";
import WeaveMark from "../components/WeaveMark";

type Draft = {
  title: string;
  subtitle: string;
  tag: "飞书骨架" | "AI 极客风" | "融合版" | "昼夜双态";
  path: string;
  status: "进行中" | "待评审" | "已定稿" | "推荐";
  updatedAt: string;
  accent: string;
  featured?: boolean;
};

const landingDrafts: Draft[] = [
  {
    title: "v4 · Day/Night",
    subtitle: "基于 v2/v3 的昼夜双态原型，太阳与日食切换黑白工作空间",
    tag: "昼夜双态",
    path: "/drafts/landing/v4",
    status: "推荐",
    updatedAt: "Day 1 · 17:35",
    accent: "bg-gradient-to-r from-amber-300 via-weave-500 to-glow-violet",
    featured: true,
  },
  {
    title: "v3 · Hybrid",
    subtitle: "飞书骨架 + 苹果质感 + AI 调性，白底辉光，克制而惊艳",
    tag: "融合版",
    path: "/drafts/landing/v3",
    status: "待评审",
    updatedAt: "Day 1 · 16:10",
    accent: "bg-gradient-to-r from-ink-900 via-weave-600 to-glow-violet",
  },
  {
    title: "v1 · Feishu Clean",
    subtitle: "飞书极简骨架，功能先行，无任何视觉噪音",
    tag: "飞书骨架",
    path: "/drafts/landing/v1",
    status: "待评审",
    updatedAt: "Day 1 · 16:00",
    accent: "bg-ink-900",
  },
  {
    title: "v2 · Geek Glow",
    subtitle: "暗色 + 辉光粒子 + 代码感，突出 AI 原生调性",
    tag: "AI 极客风",
    path: "/drafts/landing/v2",
    status: "待评审",
    updatedAt: "Day 1 · 16:00",
    accent: "bg-gradient-to-r from-weave-600 to-glow-violet",
  },
];

export default function DraftGallery() {
  return (
    <div className="min-h-full bg-ink-50">
      {/* Top bar */}
      <header className="sticky top-0 z-10 bg-white/80 backdrop-blur border-b border-ink-200">
        <div className="mx-auto max-w-6xl px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="h-6 w-6 rounded-md bg-ink-900 flex items-center justify-center">
              <WeaveMark className="h-4 w-4" />
            </div>
            <span className="font-semibold text-ink-900 text-[15px] tracking-tight">
              织界 · Draft Gallery
            </span>
            <span className="ml-2 inline-flex items-center h-5 px-1.5 rounded text-[11px] font-medium bg-ink-100 text-ink-600">
              内部预览
            </span>
          </div>
          <div className="eyebrow">Day 1 / Phase 1 · Foundation</div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-12">
        {/* Intro */}
        <div className="mb-12 max-w-2xl animate-slide-up">
          <div className="eyebrow mb-4">
            <Sparkles className="h-3.5 w-3.5" />
            草稿陈列馆
          </div>
          <h1 className="text-3xl font-semibold tracking-tight text-ink-900 leading-tight">
            挑一版你最想推进的方向。
          </h1>
          <p className="mt-3 text-ink-600 text-[15px] leading-relaxed">
            每一张卡片都是一版独立的视觉草稿，互不污染、随时可回溯。
            点击任意卡片进入全屏预览；决定后我们再往 Story 2 推进。
          </p>
        </div>

        {/* Section · Landing */}
        <section>
          <div className="flex items-baseline justify-between mb-4">
            <h2 className="text-sm font-semibold text-ink-900">
              官网首页 · Landing Page
            </h2>
            <span className="text-xs text-ink-500">
              Story 1 · {landingDrafts.length} 个草稿
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {landingDrafts.map((d) => (
              <Link
                to={d.path}
                key={d.path}
                className={`group card-feishu p-5 relative overflow-hidden ${
                  d.featured ? "ring-1 ring-weave-500/30 shadow-glow-sm" : ""
                }`}
              >
                <div
                  className={`absolute top-0 left-0 right-0 h-[3px] ${d.accent}`}
                />
                {d.featured && (
                  <div className="absolute top-3 right-3 inline-flex items-center gap-1 text-[10px] font-medium tracking-wider uppercase text-weave-700 bg-weave-50 px-2 py-0.5 rounded-full border border-weave-100">
                    <Sparkles className="h-2.5 w-2.5" />
                    推荐
                  </div>
                )}
                <div className="flex items-start justify-between">
                  <div>
                    <div className="text-xs font-medium text-ink-500 mb-1.5">
                      {d.tag}
                    </div>
                    <div className="text-base font-semibold text-ink-900">
                      {d.title}
                    </div>
                  </div>
                  {!d.featured && (
                    <ArrowUpRight
                      className="h-4 w-4 text-ink-400 transition-transform duration-200 group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-ink-900"
                    />
                  )}
                </div>
                <p className="mt-3 text-sm text-ink-600 leading-relaxed">
                  {d.subtitle}
                </p>
                <div className="mt-5 flex items-center gap-3 text-[11px] text-ink-500">
                  <span className="inline-flex items-center gap-1.5">
                    <span
                      className={`h-1.5 w-1.5 rounded-full ${
                        d.status === "推荐"
                          ? "bg-weave-500"
                          : d.status === "已定稿"
                          ? "bg-emerald-500"
                          : "bg-amber-500"
                      }`}
                    />
                    {d.status}
                  </span>
                  <span className="text-ink-300">·</span>
                  <span>{d.updatedAt}</span>
                </div>
              </Link>
            ))}
          </div>
        </section>

        <section className="mt-14">
          <div className="flex items-baseline justify-between mb-4">
            <h2 className="text-sm font-semibold text-ink-900">
              控制台 · Console
            </h2>
            <span className="text-xs text-ink-500">Story 2 · 4 个草稿</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-5xl">
            <Link
              to="/drafts/login/v2"
              className="group card-feishu p-5 relative overflow-hidden block"
            >
              <div className="absolute top-0 left-0 right-0 h-[3px] bg-gradient-to-r from-weave-500 via-ink-900 to-glow-violet" />
              <div className="flex items-start justify-between">
                <div>
                  <div className="text-xs font-medium text-ink-500 mb-1.5">
                    登录入口
                  </div>
                  <div className="text-base font-semibold text-ink-900">
                    v2 · Login Gateway
                  </div>
                </div>
                <ArrowUpRight className="h-4 w-4 text-ink-400 transition-transform duration-200 group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-ink-900" />
              </div>
              <p className="mt-3 text-sm text-ink-600 leading-relaxed">
                从 Landing 进入系统前的轻量登录门，支持演示态一键体验。
              </p>
              <div className="mt-5 flex items-center gap-3 text-[11px] text-ink-500">
                <span className="inline-flex items-center gap-1.5">
                  <span className="h-1.5 w-1.5 rounded-full bg-weave-500" />
                  新实验
                </span>
                <span className="text-ink-300">·</span>
                <span>Day 1 · 17:20</span>
              </div>
            </Link>
            <Link
              to="/drafts/onboarding/v2"
              className="group card-feishu p-5 relative overflow-hidden block"
            >
              <div className="absolute top-0 left-0 right-0 h-[3px] bg-gradient-to-r from-ink-900 via-weave-600 to-glow-violet" />
              <div className="flex items-start justify-between">
                <div>
                  <div className="text-xs font-medium text-ink-500 mb-1.5">
                    角色感知引导
                  </div>
                  <div className="text-base font-semibold text-ink-900">
                    v2 · Role Onboarding
                  </div>
                </div>
                <ArrowUpRight className="h-4 w-4 text-ink-400 transition-transform duration-200 group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-ink-900" />
              </div>
              <p className="mt-3 text-sm text-ink-600 leading-relaxed">
                进入控制台前先选择身份，再决定默认引导和信息深度。
              </p>
              <div className="mt-5 flex items-center gap-3 text-[11px] text-ink-500">
                <span className="inline-flex items-center gap-1.5">
                  <span className="h-1.5 w-1.5 rounded-full bg-weave-500" />
                  新实验
                </span>
                <span className="text-ink-300">·</span>
                <span>Day 1 · 16:40</span>
              </div>
            </Link>
            <Link
              to="/drafts/console/v2-option-b"
              className="group card-feishu p-5 relative overflow-hidden block ring-1 ring-weave-500/30 shadow-glow-sm"
            >
              <div className="absolute top-0 left-0 right-0 h-[3px] bg-gradient-to-r from-weave-600 to-glow-violet" />
              <div className="absolute top-3 right-3 inline-flex items-center gap-1 text-[10px] font-medium tracking-wider uppercase text-weave-700 bg-weave-50 px-2 py-0.5 rounded-full border border-weave-100">
                <Sparkles className="h-2.5 w-2.5" />
                保留
              </div>
              <div className="flex items-start justify-between">
                <div>
                  <div className="text-xs font-medium text-ink-500 mb-1.5">
                    方案 B · 主舞台
                  </div>
                  <div className="text-base font-semibold text-ink-900">
                    v2 · Console Option B
                  </div>
                </div>
                <ArrowUpRight className="h-4 w-4 text-ink-400 transition-transform duration-200 group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-ink-900" />
              </div>
              <p className="mt-3 text-sm text-ink-600 leading-relaxed">
                中间 Pipeline 做主视觉，两侧启动器和操作台辅助，作为当前推荐保留草稿。
              </p>
              <div className="mt-5 flex items-center gap-3 text-[11px] text-ink-500">
                <span className="inline-flex items-center gap-1.5">
                  <span className="h-1.5 w-1.5 rounded-full bg-weave-500" />
                  推荐保留
                </span>
                <span className="text-ink-300">·</span>
                <span>Day 1 · 16:20</span>
              </div>
            </Link>
            <Link
              to="/drafts/console/v2-option-b-backup"
              className="group card-feishu p-5 relative overflow-hidden block"
            >
              <div className="absolute top-0 left-0 right-0 h-[3px] bg-gradient-to-r from-emerald-500 via-weave-500 to-glow-violet" />
              <div className="flex items-start justify-between">
                <div>
                  <div className="text-xs font-medium text-ink-500 mb-1.5">
                    备份快照
                  </div>
                  <div className="text-base font-semibold text-ink-900">
                    v2 · Option B Backup
                  </div>
                </div>
                <ArrowUpRight className="h-4 w-4 text-ink-400 transition-transform duration-200 group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-ink-900" />
              </div>
              <p className="mt-3 text-sm text-ink-600 leading-relaxed">
                当前 Option B 的独立备份，用于后续对照和回滚，不参与继续试错。
              </p>
              <div className="mt-5 flex items-center gap-3 text-[11px] text-ink-500">
                <span className="inline-flex items-center gap-1.5">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                  已备份
                </span>
                <span className="text-ink-300">·</span>
                <span>Day 1 · 20:31</span>
              </div>
            </Link>
          </div>
        </section>
      </main>

      <footer className="mx-auto max-w-6xl px-6 pb-10 pt-6 border-t border-ink-200 mt-8 flex items-center justify-between text-xs text-ink-500">
        <span>织界 Weave · Main Site · Draft Gallery</span>
        <span className="font-mono">v0.1.0-alpha</span>
      </footer>
    </div>
  );
}
