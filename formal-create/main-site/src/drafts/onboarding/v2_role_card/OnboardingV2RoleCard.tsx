import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  BriefcaseBusiness,
  CheckCircle2,
  Code2,
  Sparkles,
  UserRound,
  UsersRound,
} from "lucide-react";
import WeaveMark from "../../../components/WeaveMark";

type RoleKey = "first" | "product" | "tech" | "manager";

const roles: Array<{
  key: RoleKey;
  title: string;
  desc: string;
  focus: string;
  code: string;
  label: string;
  icon: typeof UserRound;
  rotate: number;
}> = [
  {
    key: "first",
    title: "第一次使用",
    desc: "一步一步告诉我该做什么。",
    focus: "少术语、强引导、大按钮",
    code: "A",
    label: "GUIDE",
    icon: UserRound,
    rotate: -5,
  },
  {
    key: "product",
    title: "产品 / 业务",
    desc: "重点看 AI 有没有理解需求。",
    focus: "用户故事、边界条件、验收标准",
    code: "P",
    label: "STORY",
    icon: BriefcaseBusiness,
    rotate: -1.5,
  },
  {
    key: "tech",
    title: "技术负责人",
    desc: "重点看架构、接口和代码可靠性。",
    focus: "API、状态机、Diff、测试报告",
    code: "T",
    label: "STACK",
    icon: Code2,
    rotate: 1.5,
  },
  {
    key: "manager",
    title: "管理者",
    desc: "重点看进度、风险和最终结果。",
    focus: "进度总览、风险提示、交付摘要",
    code: "M",
    label: "SIGNAL",
    icon: UsersRound,
    rotate: 5,
  },
];

export default function OnboardingV2RoleCard() {
  const [selectedRole, setSelectedRole] = useState<RoleKey>("first");
  const [deckOpen, setDeckOpen] = useState(false);
  const [viewport, setViewport] = useState(() => ({
    width: typeof window === "undefined" ? 1280 : window.innerWidth,
    height: typeof window === "undefined" ? 820 : window.innerHeight,
  }));
  const selected = roles.find((role) => role.key === selectedRole)!;

  const isShort = viewport.height < 760;
  const isNarrow = viewport.width < 1080;
  const isCompact = isShort || isNarrow;
  const availableDeckWidth = Math.min(viewport.width - 96, 980);
  const cardGap = isCompact ? 24 : 42;
  const targetCardWidth = isCompact ? 148 : 168;
  const fittedCardWidth = Math.floor((availableDeckWidth - cardGap * 3) / 4);
  const cardWidth = Math.max(118, Math.min(targetCardWidth, fittedCardWidth));
  const cardHeight = Math.round(cardWidth * 1.55);
  const cardSlot = cardWidth + cardGap;
  const deckOffsets = [-1.5, -0.5, 0.5, 1.5].map((slot) =>
    Math.round(slot * cardSlot)
  );

  useEffect(() => {
    const timer = window.setTimeout(() => setDeckOpen(true), 280);
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    function handleResize() {
      setViewport({
        width: window.innerWidth,
        height: window.innerHeight,
      });
    }

    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  return (
    <div className="min-h-full bg-ink-950 text-white relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0 bg-grid-dark bg-grid-24 opacity-45" />
      <div className="pointer-events-none absolute -top-48 left-1/2 h-[640px] w-[880px] -translate-x-1/2 rounded-full bg-weave-500/24 blur-[150px]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[480px] w-[560px] rounded-full bg-glow-violet/16 blur-[140px]" />

      <div className="relative min-h-screen flex flex-col">
        <header className="h-14 border-b border-white/[0.06] bg-black/25 backdrop-blur-xl">
          <div className="mx-auto max-w-6xl px-6 h-full flex items-center justify-between">
            <Link
              to="/drafts/landing/v2"
              className="inline-flex items-center gap-1.5 text-xs font-mono text-white/45 hover:text-weave-300 transition-colors"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              返回 Landing
            </Link>
            <div className="flex items-center gap-2">
              <div className="h-6 w-6 rounded-md bg-gradient-to-br from-weave-500 to-glow-violet flex items-center justify-center shadow-glow-sm">
                <WeaveMark className="h-4 w-4" />
              </div>
              <span className="text-sm font-semibold tracking-tight">
                织界 <span className="text-white/45 font-normal">Weave</span>
              </span>
            </div>
          </div>
        </header>

        <main className="relative flex-1 overflow-hidden px-6 py-4">
          <section className="relative mx-auto grid min-h-[calc(100vh-5.5rem)] w-full max-w-6xl grid-rows-[auto_1fr_auto]">
            <div className="relative z-10 text-center pb-4">
              <div className="inline-flex items-center gap-2 rounded-full border border-white/[0.08] bg-white/[0.035] px-3 py-1 text-[11px] font-medium tracking-wider uppercase text-white/45 backdrop-blur">
                <Sparkles className="h-3.5 w-3.5 text-weave-300" />
                Role-aware onboarding
              </div>
              <h1 className="mt-3 text-3xl md:text-4xl font-semibold tracking-tight">
                选择你的工作台身份牌。
              </h1>
              <p className="mx-auto mt-2 max-w-2xl text-sm leading-relaxed text-white/48">
                底层流程不变，只改变默认引导和信息深度。
              </p>
            </div>

            <div className="relative min-h-[290px]">
              <div className="pointer-events-none absolute inset-x-0 top-1/2 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />
              <div className="pointer-events-none absolute left-1/2 top-1/2 h-[340px] w-[720px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-weave-400/9 blur-[100px]" />
              <div className="pointer-events-none absolute left-1/2 top-1/2 h-40 w-40 -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/[0.035]" />

                  {roles.map((role, index) => (
                    <button
                      key={role.key}
                      onClick={() => setSelectedRole(role.key)}
                      style={{
                        left: "50%",
                        top: "50%",
                        width: `${cardWidth}px`,
                        height: `${cardHeight}px`,
                        zIndex: selectedRole === role.key ? 20 : 10 + index,
                        transitionDelay: deckOpen ? `${index * 80}ms` : "0ms",
                        transform: deckOpen
                          ? `translateX(calc(-50% + ${deckOffsets[index]}px)) translateY(calc(-50% + ${
                              selectedRole === role.key ? "-18px" : "0px"
                            })) rotate(${role.rotate}deg) rotateY(0deg)`
                          : `translateX(-50%) translateY(calc(-50% + ${
                              index * 4
                            }px)) rotate(${-4 + index * 2.5}deg) rotateY(-10deg) scale(0.92)`,
                      }}
                      className={`group absolute text-left rounded-[1.4rem] border p-4 overflow-hidden transition-[transform,box-shadow,border-color,background-color,opacity] duration-700 ease-[cubic-bezier(0.22,1,0.36,1)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-weave-300/40 ${
                        selectedRole === role.key
                          ? "border-weave-300/45 bg-weave-400/12 shadow-glow-md"
                          : "border-white/[0.08] bg-black/35 opacity-70 hover:opacity-100 hover:bg-white/[0.055] hover:border-white/[0.16]"
                      }`}
                    >
                      {/* 卡背微光：展开后淡出，保留“翻开”的感觉 */}
                      <div
                        className={`pointer-events-none absolute inset-0 rounded-[1.4rem] bg-[radial-gradient(circle_at_50%_20%,rgba(96,135,255,0.22),transparent_32%),linear-gradient(135deg,rgba(255,255,255,0.08),rgba(255,255,255,0.015))] transition-opacity duration-500 ${
                          deckOpen ? "opacity-0" : "opacity-100"
                        }`}
                      />
                      <div
                        className={`pointer-events-none absolute inset-4 rounded-[1rem] border border-white/[0.08] transition-opacity duration-500 ${
                          deckOpen ? "opacity-0" : "opacity-100"
                        }`}
                      />
                      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/35 to-transparent opacity-0 transition-opacity group-hover:opacity-100" />
                      {selectedRole === role.key && (
                        <div className="absolute -right-10 -top-10 h-32 w-32 rounded-full bg-weave-400/20 blur-3xl" />
                      )}

                      <div
                        className={`relative flex h-full flex-col transition-opacity duration-500 ${
                          deckOpen ? "opacity-100" : "opacity-0"
                        }`}
                      >
                        <div className="flex items-start justify-between">
                          <div>
                            <div className="font-mono text-2xl font-semibold tracking-tight text-white">
                              {role.code}
                            </div>
                            <div className="mt-0.5 text-[10px] font-mono tracking-[0.24em] text-white/28">
                              {role.label}
                            </div>
                          </div>
                          {selectedRole === role.key ? (
                            <CheckCircle2 className="h-4 w-4 text-weave-300" />
                          ) : (
                            <span className="h-4 w-4 rounded-full border border-white/15" />
                          )}
                        </div>

                        <div className={`my-auto flex justify-center ${isCompact ? "py-4" : "py-7"}`}>
                          <div
                            className={`${isCompact ? "h-12 w-12" : "h-16 w-16"} rounded-2xl flex items-center justify-center border transition-colors ${
                              selectedRole === role.key
                                ? "border-weave-300/30 bg-weave-400/14 text-weave-200"
                                : "border-white/[0.08] bg-white/[0.04] text-white/42 group-hover:text-white/70"
                            }`}
                          >
                            <role.icon className={isCompact ? "h-5 w-5" : "h-7 w-7"} />
                          </div>
                        </div>

                        <div>
                          <div className={`${isCompact ? "text-sm" : "text-base"} font-semibold tracking-tight`}>
                            {role.title}
                          </div>
                          <p className="mt-1.5 text-xs leading-relaxed text-white/48">
                            {role.desc}
                          </p>
                          <div className={`${isCompact ? "mt-2" : "mt-4"} rounded-xl border border-white/[0.06] bg-black/25 px-3 py-2 text-[11px] leading-relaxed text-white/38`}>
                            {role.focus}
                          </div>
                        </div>
                      </div>
                    </button>
                  ))}
            </div>

                <aside className="relative z-30 mx-auto w-full max-w-2xl rounded-2xl border border-white/[0.07] bg-black/32 p-3 backdrop-blur-xl shadow-apple-glass md:p-4">
                  <div className="grid gap-4 md:grid-cols-[1fr_auto] md:items-center">
                    <div>
                      <div className="text-[11px] font-medium tracking-wider uppercase text-white/32">
                        Selected role
                      </div>
                      <h2 className="mt-1 text-lg font-semibold tracking-tight">
                        {selected.title}
                      </h2>
                      <p className="mt-1 max-w-xl text-sm leading-relaxed text-white/48">
                        {selected.desc} 进入后仍可切换视角。
                      </p>
                      <div className={`${isShort ? "hidden" : "mt-3 flex"} flex-wrap gap-2`}>
                        {["解释方式", "模块排序", "审批文案"].map((item) => (
                          <span
                            key={item}
                            className="inline-flex items-center gap-1.5 rounded-full border border-white/[0.06] bg-white/[0.03] px-2.5 py-1 text-[11px] text-white/42"
                          >
                            <CheckCircle2 className="h-3 w-3 text-weave-300" />
                            {item}
                          </span>
                        ))}
                      </div>
                    </div>
                    <Link
                      to={`/drafts/console/v2?role=${selectedRole}`}
                      className="btn-glow h-11 px-5 whitespace-nowrap"
                    >
                      进入我的工作台
                      <ArrowRight className="h-4 w-4" />
                    </Link>
                  </div>
                </aside>
          </section>
        </main>
      </div>
    </div>
  );
}
