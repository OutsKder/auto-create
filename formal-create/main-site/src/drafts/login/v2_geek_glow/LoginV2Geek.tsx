import { useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Mail,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import WeaveMark from "../../../components/WeaveMark";

export default function LoginV2Geek() {
  const [showPassword, setShowPassword] = useState(false);

  return (
    <div className="min-h-full bg-ink-950 text-white relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0 bg-grid-dark bg-grid-24 opacity-45" />
      <div className="pointer-events-none absolute -top-48 left-1/2 h-[640px] w-[880px] -translate-x-1/2 rounded-full bg-weave-500/22 blur-[150px]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[480px] w-[560px] rounded-full bg-glow-violet/15 blur-[140px]" />

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

        <main className="flex-1 flex items-center justify-center px-6 py-12">
          <section className="w-full max-w-5xl grid lg:grid-cols-[0.9fr_1.1fr] gap-10 items-center">
            <div className="hidden lg:block">
              <div className="inline-flex items-center gap-2 rounded-full border border-white/[0.08] bg-white/[0.04] px-3 py-1 text-[11px] font-medium tracking-wider uppercase text-white/50 backdrop-blur">
                <Sparkles className="h-3.5 w-3.5 text-weave-300" />
                Secure workspace
              </div>
              <h1 className="mt-5 text-4xl font-semibold tracking-tight leading-tight">
                进入你的
                <span className="block bg-gradient-to-r from-weave-300 via-weave-400 to-glow-violet bg-clip-text text-transparent">
                  AI 交付工作台。
                </span>
              </h1>
              <p className="mt-4 max-w-md text-sm leading-relaxed text-white/55">
                登录后，我们会先询问你的使用身份，再为你配置合适的信息深度和引导方式。
              </p>

              <div className="mt-8 space-y-3">
                {[
                  "身份选择只影响引导方式，不改变底层流程",
                  "演示版支持一键进入，不需要真实账号",
                  "后续可无缝接入真实认证与用户配置",
                ].map((item) => (
                  <div key={item} className="flex items-start gap-2 text-sm text-white/55">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 text-weave-300 flex-none" />
                    <span>{item}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="relative">
              <div className="absolute -inset-8 rounded-[2rem] bg-gradient-to-br from-weave-500/20 via-transparent to-glow-violet/20 blur-3xl" />
              <div className="relative mx-auto max-w-md rounded-[2rem] border border-white/10 bg-gradient-to-br from-white/[0.08] to-white/[0.025] p-6 md:p-7 backdrop-blur-xl shadow-apple-modal">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-xs text-white/40">Welcome back</div>
                    <h2 className="mt-1 text-2xl font-semibold tracking-tight">
                      登录织界
                    </h2>
                  </div>
                  <button
                    type="button"
                    onClick={() => setShowPassword((current) => !current)}
                    aria-label={showPassword ? "隐藏密码" : "显示密码"}
                    className="h-11 w-11 rounded-2xl border border-white/[0.08] bg-white/[0.04] flex items-center justify-center text-weave-300 hover:bg-white/[0.07] hover:text-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-weave-400/40"
                  >
                    <MoonPhaseIcon visible={showPassword} />
                  </button>
                </div>

                <div className="mt-7 space-y-4">
                  <label className="block">
                    <span className="text-xs font-medium text-white/50">
                      邮箱
                    </span>
                    <div className="mt-2 flex items-center gap-2 rounded-xl border border-white/[0.08] bg-black/30 px-3 h-11 focus-within:border-weave-400/50 focus-within:ring-4 focus-within:ring-weave-500/10 transition-all">
                      <Mail className="h-4 w-4 text-white/35" />
                      <input
                        defaultValue="demo@weave.ai"
                        className="w-full bg-transparent text-sm text-white outline-none placeholder:text-white/25"
                        placeholder="you@example.com"
                      />
                    </div>
                  </label>

                  <label className="block">
                    <span className="text-xs font-medium text-white/50">
                      密码
                    </span>
                    <div className="mt-2 flex items-center gap-2 rounded-xl border border-white/[0.08] bg-black/30 px-3 h-11 focus-within:border-weave-400/50 focus-within:ring-4 focus-within:ring-weave-500/10 transition-all">
                      <ShieldCheck className="h-4 w-4 text-white/35" />
                      <input
                        type={showPassword ? "text" : "password"}
                        defaultValue="weave-demo"
                        className="w-full bg-transparent text-sm text-white outline-none placeholder:text-white/25"
                        placeholder="password"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword((current) => !current)}
                        aria-label={showPassword ? "隐藏密码" : "显示密码"}
                        className="flex h-7 w-7 items-center justify-center rounded-md text-white/35 transition-colors hover:bg-white/[0.06] hover:text-weave-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-weave-400/40"
                      >
                        <MoonPhaseIcon visible={showPassword} compact />
                      </button>
                    </div>
                  </label>
                </div>

                <Link
                  to="/drafts/onboarding/v2"
                  className="btn-glow mt-6 h-11 w-full px-5"
                >
                  继续，选择使用方式
                  <ArrowRight className="h-4 w-4" />
                </Link>

                <div className="mt-4 grid grid-cols-2 gap-3">
                  <Link
                    to="/drafts/onboarding/v2"
                    className="inline-flex items-center justify-center h-10 rounded-lg border border-white/[0.08] bg-white/[0.035] text-sm text-white/65 hover:bg-white/[0.07] hover:text-white transition-colors"
                  >
                    一键体验
                  </Link>
                  <button className="inline-flex items-center justify-center h-10 rounded-lg border border-white/[0.08] bg-white/[0.02] text-sm text-white/45 hover:bg-white/[0.05] hover:text-white/70 transition-colors">
                    忘记密码
                  </button>
                </div>

                <p className="mt-5 text-center text-[11px] leading-relaxed text-white/32">
                  当前为前端演示登录。真实版本会在这里接入团队账号、SSO 或 OAuth。
                </p>
              </div>
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}

function MoonPhaseIcon({
  visible,
  compact = false,
}: {
  visible: boolean;
  compact?: boolean;
}) {
  return (
    <span
      className={`relative block rounded-full transition-all duration-500 ${
        compact ? "h-4 w-4" : "h-7 w-7"
      } ${
        visible
          ? "bg-[radial-gradient(circle_at_25%_48%,#f08a65_0%,#b43b42_34%,#53111f_62%,#120711_100%)] shadow-[0_0_18px_rgba(236,72,153,0.42),0_0_30px_rgba(96,135,255,0.22),inset_-7px_-5px_12px_rgba(0,0,0,0.55),inset_4px_2px_6px_rgba(255,183,134,0.42)]"
          : "bg-[radial-gradient(circle_at_35%_28%,#fff9dc_0%,#f4e7b3_42%,#d8bf74_100%)] shadow-[0_0_18px_rgba(147,178,255,0.38),0_0_28px_rgba(34,211,238,0.16),inset_-7px_-8px_13px_rgba(112,83,25,0.22),inset_4px_4px_8px_rgba(255,255,255,0.65)]"
      }`}
    >
      <span
        className={`absolute rounded-full transition-all duration-500 ${
          visible
            ? "inset-[-5px] bg-[radial-gradient(circle,#ec4899_0%,rgba(96,135,255,0.34)_34%,transparent_70%)] opacity-70 blur-[3px]"
            : "inset-[-5px] bg-[radial-gradient(circle,rgba(147,178,255,0.46)_0%,rgba(34,211,238,0.22)_38%,transparent_72%)] blur-[4px]"
        }`}
      />
      <span
        className={`absolute rounded-full transition-all duration-500 z-10 ${
          visible
            ? "inset-[-1px] translate-x-[19%] bg-[radial-gradient(circle_at_35%_42%,#1f2937_0%,#080611_48%,#020204_100%)] shadow-[-6px_0_10px_rgba(255,117,85,0.38),inset_3px_2px_5px_rgba(255,255,255,0.06)]"
            : "hidden"
        }`}
      />
      <span
        className={`absolute rounded-full transition-opacity duration-500 ${
          visible
            ? "left-[67%] top-[26%] z-20 h-1 w-1 bg-white/10 opacity-60 blur-[0.5px]"
            : "left-[23%] top-[26%] h-[24%] w-[24%] bg-[#c7b887]/55 opacity-100"
        }`}
      />
      {!visible && (
        <>
          <span className="absolute left-[60%] top-[31%] h-[13%] w-[13%] rounded-full bg-[#c7b887]/42" />
          <span className="absolute left-[47%] top-[58%] h-[18%] w-[18%] rounded-full bg-[#c7b887]/45" />
        </>
      )}
    </span>
  );
}
