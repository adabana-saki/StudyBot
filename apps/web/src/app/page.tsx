"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { isAuthenticated } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import {
  Timer,
  Brain,
  Coffee,
  BarChart3,
  Trophy,
  Layers,
  ArrowRight,
  Sparkles,
} from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function LandingPage() {
  const router = useRouter();

  useEffect(() => {
    if (isAuthenticated()) {
      router.replace("/dashboard");
    }
  }, [router]);

  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Animated background */}
      <div className="fixed inset-0 -z-10">
        <div className="absolute inset-0 bg-gradient-to-br from-[#0a0f1e] via-[#0f1729] to-[#0a0f1e]" />
        <div className="absolute top-[-50%] left-[-50%] w-[200%] h-[200%] animate-gradient bg-gradient-to-r from-indigo-500/8 via-purple-500/5 to-cyan-500/8 bg-[length:200%_200%]" />
        {/* Floating orbs */}
        <div className="absolute top-20 left-10 w-72 h-72 rounded-full bg-indigo-600/10 blur-[100px] animate-float" />
        <div className="absolute bottom-32 right-10 w-96 h-96 rounded-full bg-purple-600/10 blur-[120px] animate-float-slow" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] rounded-full bg-cyan-600/5 blur-[150px] animate-pulse-glow" />
      </div>

      {/* Content */}
      <div className="relative flex flex-col items-center px-4 pt-16 pb-12">
        {/* Hero */}
        <div className="text-center max-w-lg animate-fade-in-up">
          {/* Logo */}
          <div className="relative inline-block mb-6">
            <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg glow-primary">
              <Sparkles className="w-10 h-10 text-white" />
            </div>
          </div>

          <h1 className="text-5xl sm:text-6xl font-extrabold mb-3 tracking-tight">
            <span className="bg-gradient-to-r from-white via-indigo-200 to-white bg-clip-text text-transparent">
              Study
            </span>
            <span className="bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
              Bot
            </span>
          </h1>

          <p className="text-lg text-indigo-200/80 mb-2 font-medium">
            学習を、もっと楽しく。
          </p>
          <p className="text-sm text-muted-foreground mb-10 leading-relaxed">
            ポモドーロ・学習記録・実績・フラッシュカード
            <br />
            ゲーミフィケーションで学習習慣を身につけよう
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-col gap-3 w-full max-w-xs mx-auto">
            <Button
              size="lg"
              className="w-full h-14 text-base rounded-2xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 shadow-lg glow-primary transition-all duration-300 hover:scale-[1.02]"
              asChild
            >
              <a href={`${API_URL}/api/auth/discord`}>
                <svg
                  className="w-5 h-5 mr-2"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                >
                  <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028 14.09 14.09 0 0 0 1.226-1.994.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z" />
                </svg>
                Discordでログイン
              </a>
            </Button>

            <Button
              variant="outline"
              size="lg"
              className="w-full h-14 text-base rounded-2xl glass border-white/10 hover:border-white/20 hover:bg-white/10 transition-all duration-300 hover:scale-[1.02]"
              onClick={() => router.push("/timer")}
            >
              <Timer className="w-5 h-5 mr-2 text-indigo-400" />
              ゲストで始める
              <ArrowRight className="w-4 h-4 ml-2 text-muted-foreground" />
            </Button>
          </div>
        </div>

        {/* Guest features */}
        <div className="w-full max-w-lg mt-16 animate-fade-in-up animate-delay-200">
          <div className="flex items-center gap-2 mb-4 justify-center">
            <div className="h-px flex-1 bg-gradient-to-r from-transparent to-white/10" />
            <span className="text-xs uppercase tracking-widest text-indigo-400/80 font-medium">
              ログイン不要
            </span>
            <div className="h-px flex-1 bg-gradient-to-l from-transparent to-white/10" />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={() => router.push("/timer")}
              className="glass rounded-2xl p-4 text-left group hover:border-indigo-500/30 transition-all duration-300 hover:scale-[1.02] active:scale-[0.98]"
            >
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 flex items-center justify-center mb-3 group-hover:from-indigo-500/30 group-hover:to-purple-500/30 transition-colors">
                <Brain className="h-5 w-5 text-indigo-400" />
              </div>
              <h3 className="font-semibold text-sm mb-1">ポモドーロ</h3>
              <p className="text-xs text-muted-foreground leading-relaxed">
                集中と休憩で効率UP
              </p>
            </button>

            <div className="glass rounded-2xl p-4 text-left opacity-50">
              <div className="w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center mb-3">
                <Coffee className="h-5 w-5 text-muted-foreground" />
              </div>
              <h3 className="font-semibold text-sm mb-1">
                フォーカス
                <span className="text-[10px] ml-1 text-indigo-400/60 font-normal">Soon</span>
              </h3>
              <p className="text-xs text-muted-foreground leading-relaxed">
                アプリブロックで集中
              </p>
            </div>
          </div>
        </div>

        {/* Login features */}
        <div className="w-full max-w-lg mt-12 animate-fade-in-up animate-delay-300">
          <div className="flex items-center gap-2 mb-4 justify-center">
            <div className="h-px flex-1 bg-gradient-to-r from-transparent to-white/10" />
            <span className="text-xs uppercase tracking-widest text-purple-400/80 font-medium">
              Discord連携
            </span>
            <div className="h-px flex-1 bg-gradient-to-l from-transparent to-white/10" />
          </div>

          <div className="grid grid-cols-3 gap-3">
            {[
              { icon: BarChart3, label: "ダッシュボード", color: "from-blue-500/20 to-cyan-500/20", iconColor: "text-blue-400" },
              { icon: Trophy, label: "実績・ランキング", color: "from-amber-500/20 to-orange-500/20", iconColor: "text-amber-400" },
              { icon: Layers, label: "フラッシュカード", color: "from-emerald-500/20 to-teal-500/20", iconColor: "text-emerald-400" },
            ].map((item) => (
              <div
                key={item.label}
                className="glass rounded-2xl p-3 text-center"
              >
                <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${item.color} flex items-center justify-center mx-auto mb-2`}>
                  <item.icon className={`h-5 w-5 ${item.iconColor}`} />
                </div>
                <p className="text-[11px] font-medium leading-tight">{item.label}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <footer className="mt-16 text-center">
          <p className="text-xs text-muted-foreground/50">StudyBot v2.0</p>
        </footer>
      </div>
    </div>
  );
}
