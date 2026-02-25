"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { isAuthenticated } from "@/lib/auth";
import { startSession, endSession, getBlockedApps, syncAppUsage, syncBreaches } from "@/lib/api";
import {
  scheduleLocalNotification,
  isNative,
  startAppMonitoring,
  stopAppMonitoring,
  getNativeUsageStats,
} from "@/lib/native";
import GuestBottomNav from "@/components/GuestBottomNav";
import {
  Play,
  Pause,
  RotateCcw,
  Coffee,
  Brain,
  LogIn,
  ChevronDown,
  ChevronUp,
  History,
  ArrowLeft,
  Flame,
  Zap,
  Settings2,
  Shield,
} from "lucide-react";

// ---------- 型定義 ----------

type TimerMode = "focus" | "break";
type TimerState = "idle" | "running" | "paused";

interface SessionLog {
  date: string;
  mode: TimerMode;
  duration: number;
  completed: boolean;
}

// ---------- プリセット ----------

const PRESETS = [
  { label: "25/5", focus: 25, break: 5 },
  { label: "50/10", focus: 50, break: 10 },
  { label: "15/3", focus: 15, break: 3 },
];

// ---------- LocalStorage ----------

function getSessions(): SessionLog[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(localStorage.getItem("studybot_timer_sessions") || "[]");
  } catch {
    return [];
  }
}

function saveSession(session: SessionLog) {
  const sessions = getSessions();
  sessions.unshift(session);
  localStorage.setItem(
    "studybot_timer_sessions",
    JSON.stringify(sessions.slice(0, 100)),
  );
}

function getTodayStats() {
  const today = new Date().toISOString().split("T")[0];
  const sessions = getSessions().filter(
    (s) => s.date.startsWith(today) && s.mode === "focus" && s.completed,
  );
  const totalMinutes = sessions.reduce((sum, s) => sum + s.duration / 60, 0);
  return { count: sessions.length, totalMinutes: Math.round(totalMinutes) };
}

// ---------- フォーマット ----------

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}

// ---------- コンポーネント ----------

export default function TimerPage() {
  const router = useRouter();
  const [mode, setMode] = useState<TimerMode>("focus");
  const [state, setState] = useState<TimerState>("idle");
  const [focusMinutes, setFocusMinutes] = useState(25);
  const [breakMinutes, setBreakMinutes] = useState(5);
  const [remaining, setRemaining] = useState(25 * 60);
  const [totalSeconds, setTotalSeconds] = useState(25 * 60);
  const [showHistory, setShowHistory] = useState(false);
  const [showCustom, setShowCustom] = useState(false);
  const [todayStats, setTodayStats] = useState({ count: 0, totalMinutes: 0 });
  const [auth, setAuth] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startTimeRef = useRef<number>(0);
  const [appGuardActive, setAppGuardActive] = useState(false);
  const sessionIdRef = useRef<number | null>(null);

  useEffect(() => {
    setAuth(isAuthenticated());
  }, []);

  useEffect(() => {
    setTodayStats(getTodayStats());
  }, [state]);

  useEffect(() => {
    if (state === "running") {
      intervalRef.current = setInterval(() => {
        setRemaining((prev) => {
          if (prev <= 1) {
            clearInterval(intervalRef.current!);
            handleComplete();
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [state]);

  const handleComplete = useCallback(async () => {
    const duration = totalSeconds;
    saveSession({
      date: new Date().toISOString(),
      mode,
      duration,
      completed: true,
    });

    // API: end session (study_logs are created server-side)
    if (auth && mode === "focus") {
      // AppGuard: 監視停止 + データ同期
      if (appGuardActive && isNative()) {
        try {
          const breachEvents = await stopAppMonitoring();
          const sid = sessionIdRef.current;

          if (sid && breachEvents.length > 0) {
            await syncBreaches(
              sid,
              breachEvents.map((b) => ({
                package_name: b.packageName,
                app_name: b.appName,
                breach_duration_ms: b.breachDurationMs,
                occurred_at: new Date(b.occurredAt).toISOString(),
              })),
            );
          }

          // 使用時間データ取得 & 同期
          const endTime = Date.now();
          const usageEntries = await getNativeUsageStats(
            startTimeRef.current,
            endTime,
          );
          if (sid && usageEntries.length > 0) {
            await syncAppUsage(
              sid,
              usageEntries.map((e) => ({
                package_name: e.packageName,
                app_name: e.appName,
                foreground_time_ms: e.foregroundTimeMs,
                period_start: new Date(e.periodStart).toISOString(),
                period_end: new Date(e.periodEnd).toISOString(),
              })),
            );
          }
        } catch (guardErr) {
          console.warn("AppGuardデータ同期失敗:", guardErr);
        }
        setAppGuardActive(false);
        sessionIdRef.current = null;
      }

      endSession().catch(() => {});
    }

    if (mode === "focus") {
      scheduleLocalNotification(
        "集中セッション完了！",
        `${Math.round(duration / 60)}分お疲れ様！休憩しましょう`,
        0,
      );
      setMode("break");
      const breakSec = breakMinutes * 60;
      setRemaining(breakSec);
      setTotalSeconds(breakSec);
    } else {
      scheduleLocalNotification(
        "休憩終了！",
        "次の集中セッションを始めましょう",
        0,
      );
      setMode("focus");
      const focusSec = focusMinutes * 60;
      setRemaining(focusSec);
      setTotalSeconds(focusSec);
    }
    setState("idle");
    setTodayStats(getTodayStats());
  }, [mode, totalSeconds, focusMinutes, breakMinutes, auth, appGuardActive]);

  const start = async () => {
    startTimeRef.current = Date.now();
    setState("running");

    // API: start session
    if (auth && mode === "focus") {
      try {
        const session = await startSession({
          session_type: "pomodoro",
          duration_minutes: focusMinutes,
          topic: "",
        });
        sessionIdRef.current = session.id;

        // AppGuard: ネイティブ環境でアプリ監視開始
        if (isNative()) {
          try {
            const blockedApps = await getBlockedApps();
            const blockedPkgs = blockedApps.map((a) => a.package_name);
            if (blockedPkgs.length > 0) {
              await startAppMonitoring(session.id, blockedPkgs);
              setAppGuardActive(true);
            }
          } catch (guardErr) {
            console.warn("AppGuard監視開始失敗:", guardErr);
          }
        }
      } catch {
        // セッション作成失敗してもタイマーは動かす
        sessionIdRef.current = null;
      }
    }
  };

  const pause = () => setState("paused");

  const reset = async () => {
    // AppGuard: リセット時も監視を停止
    if (appGuardActive && isNative()) {
      try {
        await stopAppMonitoring();
      } catch {
        // ignore
      }
      setAppGuardActive(false);
      sessionIdRef.current = null;
    }

    setState("idle");
    const sec = (mode === "focus" ? focusMinutes : breakMinutes) * 60;
    setRemaining(sec);
    setTotalSeconds(sec);
  };

  const selectPreset = (focus: number, brk: number) => {
    if (state !== "idle") return;
    setFocusMinutes(focus);
    setBreakMinutes(brk);
    setMode("focus");
    const sec = focus * 60;
    setRemaining(sec);
    setTotalSeconds(sec);
  };

  const adjustMinutes = (delta: number) => {
    if (state !== "idle") return;
    if (mode === "focus") {
      const next = Math.max(1, Math.min(120, focusMinutes + delta));
      setFocusMinutes(next);
      setRemaining(next * 60);
      setTotalSeconds(next * 60);
    } else {
      const next = Math.max(1, Math.min(30, breakMinutes + delta));
      setBreakMinutes(next);
      setRemaining(next * 60);
      setTotalSeconds(next * 60);
    }
  };

  const progress =
    totalSeconds > 0 ? ((totalSeconds - remaining) / totalSeconds) * 100 : 0;
  const circumference = 2 * Math.PI * 45;
  const isFocus = mode === "focus";
  const sessions = getSessions().slice(0, 10);

  return (
    <div className="min-h-screen relative overflow-hidden pb-24">
      {/* Animated background */}
      <div className="fixed inset-0 -z-10">
        <div className="absolute inset-0 bg-gradient-to-br from-[#0a0f1e] via-[#0f1729] to-[#0a0f1e]" />
        {state === "running" && (
          <>
            <div
              className={`absolute top-10 left-5 w-80 h-80 rounded-full blur-[120px] animate-pulse-glow ${
                isFocus ? "bg-indigo-600/15" : "bg-emerald-600/15"
              }`}
            />
            <div
              className={`absolute bottom-20 right-5 w-96 h-96 rounded-full blur-[150px] animate-float-slow ${
                isFocus ? "bg-purple-600/10" : "bg-teal-600/10"
              }`}
            />
          </>
        )}
      </div>

      {/* Content */}
      <div className="relative flex flex-col items-center px-4 pt-6 pb-8">
        {/* Header */}
        <div className="w-full max-w-md flex items-center justify-between mb-8 animate-fade-in-up">
          <button
            onClick={() => router.push("/")}
            className="p-2 -ml-2 rounded-xl hover:bg-white/5 transition-colors"
          >
            <ArrowLeft className="h-5 w-5 text-muted-foreground" />
          </button>

          {!isAuthenticated() && (
            <button
              onClick={() => router.push("/")}
              className="flex items-center gap-1.5 text-xs text-indigo-400/70 hover:text-indigo-400 transition-colors"
            >
              <LogIn className="h-3.5 w-3.5" />
              ログインで同期
            </button>
          )}
        </div>

        {/* Today stats + goal progress */}
        <div className="w-full max-w-md mb-8 animate-fade-in-up animate-delay-100">
          <div className="grid grid-cols-2 gap-3 mb-3">
            <div className="glass rounded-2xl p-4 text-center">
              <div className="flex items-center justify-center gap-1.5 mb-1">
                <Flame className="h-4 w-4 text-orange-400" />
                <span className="text-2xl font-bold">{todayStats.count}</span>
              </div>
              <p className="text-[11px] text-muted-foreground">セッション</p>
            </div>
            <div className="glass rounded-2xl p-4 text-center">
              <div className="flex items-center justify-center gap-1.5 mb-1">
                <Zap className="h-4 w-4 text-yellow-400" />
                <span className="text-2xl font-bold">{todayStats.totalMinutes}</span>
              </div>
              <p className="text-[11px] text-muted-foreground">分集中</p>
            </div>
          </div>
          {/* Daily goal bar */}
          <div className="glass rounded-xl px-4 py-2.5">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[10px] text-muted-foreground">今日の目標 120分</span>
              <span className="text-[10px] font-medium text-indigo-400">
                {Math.min(100, Math.round((todayStats.totalMinutes / 120) * 100))}%
              </span>
            </div>
            <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-purple-500 transition-all duration-700"
                style={{ width: `${Math.min(100, (todayStats.totalMinutes / 120) * 100)}%` }}
              />
            </div>
          </div>
        </div>

        {/* Mode toggle */}
        <div className="glass rounded-full p-1 flex gap-1 mb-8 animate-fade-in-up animate-delay-200">
          <button
            onClick={() => {
              if (state !== "idle") return;
              setMode("focus");
              setRemaining(focusMinutes * 60);
              setTotalSeconds(focusMinutes * 60);
            }}
            disabled={state !== "idle"}
            className={`flex items-center gap-1.5 px-5 py-2 rounded-full text-sm font-medium transition-all duration-300 ${
              isFocus
                ? "bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-lg"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <Brain className="h-4 w-4" />
            集中
          </button>
          <button
            onClick={() => {
              if (state !== "idle") return;
              setMode("break");
              setRemaining(breakMinutes * 60);
              setTotalSeconds(breakMinutes * 60);
            }}
            disabled={state !== "idle"}
            className={`flex items-center gap-1.5 px-5 py-2 rounded-full text-sm font-medium transition-all duration-300 ${
              !isFocus
                ? "bg-gradient-to-r from-emerald-600 to-teal-600 text-white shadow-lg"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <Coffee className="h-4 w-4" />
            休憩
          </button>
        </div>

        {/* AppGuard indicator */}
        {appGuardActive && state === "running" && (
          <div className="flex items-center gap-1.5 mb-4 px-3 py-1.5 rounded-full glass text-xs text-emerald-400 animate-fade-in-up">
            <Shield className="h-3.5 w-3.5" />
            AppGuard 監視中
          </div>
        )}

        {/* Timer circle */}
        <div className={`relative w-72 h-72 mb-8 animate-fade-in-up animate-delay-300 ${state === "running" ? "animate-breathe" : ""}`}>
          {/* Glow behind */}
          {state === "running" && (
            <div
              className={`absolute inset-4 rounded-full blur-2xl ${
                isFocus ? "bg-indigo-500/20" : "bg-emerald-500/20"
              } animate-pulse-glow`}
            />
          )}

          <svg className="w-full h-full -rotate-90 relative z-10" viewBox="0 0 100 100">
            {/* Background track */}
            <circle
              cx="50" cy="50" r="45"
              fill="none"
              stroke="rgba(255,255,255,0.06)"
              strokeWidth="3"
            />
            {/* Progress arc */}
            <circle
              cx="50" cy="50" r="45"
              fill="none"
              stroke={`url(#timer-gradient-${isFocus ? "focus" : "break"})`}
              strokeWidth="3.5"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={circumference * (1 - progress / 100)}
              className="transition-all duration-1000 ease-linear"
            />
            {/* Dot at the end of progress */}
            {progress > 0 && (
              <circle
                cx={50 + 45 * Math.cos(((progress / 100) * 360 - 90) * (Math.PI / 180))}
                cy={50 + 45 * Math.sin(((progress / 100) * 360 - 90) * (Math.PI / 180))}
                r="2.5"
                fill="white"
                className="drop-shadow-lg"
              />
            )}
            <defs>
              <linearGradient id="timer-gradient-focus" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stopColor="#818cf8" />
                <stop offset="100%" stopColor="#a78bfa" />
              </linearGradient>
              <linearGradient id="timer-gradient-break" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stopColor="#34d399" />
                <stop offset="100%" stopColor="#2dd4bf" />
              </linearGradient>
            </defs>
          </svg>

          {/* Center content */}
          <div className="absolute inset-0 flex flex-col items-center justify-center z-20">
            {state === "idle" ? (
              <div className="flex items-center gap-4">
                <button
                  onClick={() => adjustMinutes(-5)}
                  className="p-2 rounded-full glass hover:bg-white/10 transition-all active:scale-90"
                >
                  <ChevronDown className="h-4 w-4 text-muted-foreground" />
                </button>
                <span className="text-6xl font-bold font-mono tabular-nums tracking-tight text-glow">
                  {formatTime(remaining)}
                </span>
                <button
                  onClick={() => adjustMinutes(5)}
                  className="p-2 rounded-full glass hover:bg-white/10 transition-all active:scale-90"
                >
                  <ChevronUp className="h-4 w-4 text-muted-foreground" />
                </button>
              </div>
            ) : (
              <span
                className={`text-6xl font-bold font-mono tabular-nums tracking-tight ${
                  state === "running" ? "text-glow" : ""
                }`}
              >
                {formatTime(remaining)}
              </span>
            )}
            <span
              className={`text-xs mt-2 font-medium uppercase tracking-widest ${
                isFocus ? "text-indigo-400/70" : "text-emerald-400/70"
              }`}
            >
              {isFocus ? "Focus" : "Break"}
            </span>
          </div>
        </div>

        {/* Presets + Custom */}
        {state === "idle" && (
          <div className="w-full max-w-md mb-8 animate-fade-in-up">
            <div className="flex items-center justify-center gap-2 mb-3">
              {PRESETS.map((p) => {
                const isActive =
                  !showCustom && focusMinutes === p.focus && breakMinutes === p.break;
                return (
                  <button
                    key={p.label}
                    onClick={() => {
                      selectPreset(p.focus, p.break);
                      setShowCustom(false);
                    }}
                    className={`px-4 py-2 rounded-full text-sm font-medium transition-all duration-200 ${
                      isActive
                        ? "glass border-indigo-500/30 text-indigo-300"
                        : "text-muted-foreground hover:text-foreground hover:bg-white/5"
                    }`}
                  >
                    {p.label}
                  </button>
                );
              })}
              <button
                onClick={() => setShowCustom(!showCustom)}
                className={`p-2 rounded-full transition-all duration-200 ${
                  showCustom
                    ? "glass border-indigo-500/30 text-indigo-300"
                    : "text-muted-foreground hover:text-foreground hover:bg-white/5"
                }`}
                title="カスタム設定"
              >
                <Settings2 className="h-4 w-4" />
              </button>
            </div>

            {/* Custom time picker */}
            {showCustom && (
              <div className="glass rounded-2xl p-4 animate-fade-in-up">
                <div className="grid grid-cols-2 gap-4">
                  {/* Focus time */}
                  <div>
                    <label className="text-[10px] text-muted-foreground mb-2 block text-center">
                      集中（分）
                    </label>
                    <div className="flex items-center justify-center gap-2">
                      <button
                        onClick={() => adjustMinutes(-1)}
                        className="w-8 h-8 rounded-lg glass hover:bg-white/10 flex items-center justify-center transition-all active:scale-90"
                      >
                        <ChevronDown className="h-4 w-4" />
                      </button>
                      <input
                        type="number"
                        min={1}
                        max={180}
                        value={focusMinutes}
                        onChange={(e) => {
                          const v = Math.max(1, Math.min(180, parseInt(e.target.value) || 1));
                          setFocusMinutes(v);
                          if (mode === "focus") {
                            setRemaining(v * 60);
                            setTotalSeconds(v * 60);
                          }
                        }}
                        className="w-16 h-10 text-center text-lg font-bold rounded-xl bg-white/5 border border-white/10 focus:outline-none focus:border-indigo-500/30 [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                      />
                      <button
                        onClick={() => adjustMinutes(1)}
                        className="w-8 h-8 rounded-lg glass hover:bg-white/10 flex items-center justify-center transition-all active:scale-90"
                      >
                        <ChevronUp className="h-4 w-4" />
                      </button>
                    </div>
                  </div>

                  {/* Break time */}
                  <div>
                    <label className="text-[10px] text-muted-foreground mb-2 block text-center">
                      休憩（分）
                    </label>
                    <div className="flex items-center justify-center gap-2">
                      <button
                        onClick={() => {
                          const next = Math.max(1, breakMinutes - 1);
                          setBreakMinutes(next);
                          if (mode === "break") {
                            setRemaining(next * 60);
                            setTotalSeconds(next * 60);
                          }
                        }}
                        className="w-8 h-8 rounded-lg glass hover:bg-white/10 flex items-center justify-center transition-all active:scale-90"
                      >
                        <ChevronDown className="h-4 w-4" />
                      </button>
                      <input
                        type="number"
                        min={1}
                        max={60}
                        value={breakMinutes}
                        onChange={(e) => {
                          const v = Math.max(1, Math.min(60, parseInt(e.target.value) || 1));
                          setBreakMinutes(v);
                          if (mode === "break") {
                            setRemaining(v * 60);
                            setTotalSeconds(v * 60);
                          }
                        }}
                        className="w-16 h-10 text-center text-lg font-bold rounded-xl bg-white/5 border border-white/10 focus:outline-none focus:border-indigo-500/30 [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                      />
                      <button
                        onClick={() => {
                          const next = Math.min(60, breakMinutes + 1);
                          setBreakMinutes(next);
                          if (mode === "break") {
                            setRemaining(next * 60);
                            setTotalSeconds(next * 60);
                          }
                        }}
                        className="w-8 h-8 rounded-lg glass hover:bg-white/10 flex items-center justify-center transition-all active:scale-90"
                      >
                        <ChevronUp className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </div>

                {/* Quick custom buttons */}
                <div className="flex flex-wrap justify-center gap-1.5 mt-3 pt-3 border-t border-white/5">
                  {[10, 20, 30, 40, 45, 60, 90, 120].map((m) => (
                    <button
                      key={m}
                      onClick={() => {
                        setFocusMinutes(m);
                        setMode("focus");
                        setRemaining(m * 60);
                        setTotalSeconds(m * 60);
                      }}
                      className={`px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all ${
                        focusMinutes === m && mode === "focus"
                          ? "bg-indigo-500/20 text-indigo-300"
                          : "bg-white/5 text-muted-foreground hover:bg-white/10"
                      }`}
                    >
                      {m}分
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Control buttons */}
        <div className="flex gap-3 mb-10">
          {state === "idle" && (
            <button
              onClick={start}
              className={`flex items-center gap-2 px-10 py-4 rounded-2xl text-base font-semibold transition-all duration-300 hover:scale-[1.03] active:scale-[0.97] shadow-lg ${
                isFocus
                  ? "bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 glow-primary"
                  : "bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 glow-green"
              }`}
            >
              <Play className="h-5 w-5" fill="currentColor" />
              スタート
            </button>
          )}
          {state === "running" && (
            <>
              <button
                onClick={pause}
                className="flex items-center gap-2 px-8 py-4 rounded-2xl text-base font-semibold glass hover:bg-white/10 transition-all duration-200 active:scale-[0.97]"
              >
                <Pause className="h-5 w-5" />
                一時停止
              </button>
              <button
                onClick={reset}
                className="p-4 rounded-2xl glass hover:bg-white/10 transition-all duration-200 active:scale-[0.97]"
              >
                <RotateCcw className="h-5 w-5 text-muted-foreground" />
              </button>
            </>
          )}
          {state === "paused" && (
            <>
              <button
                onClick={start}
                className={`flex items-center gap-2 px-8 py-4 rounded-2xl text-base font-semibold transition-all duration-300 hover:scale-[1.03] active:scale-[0.97] shadow-lg ${
                  isFocus
                    ? "bg-gradient-to-r from-indigo-600 to-purple-600 glow-primary"
                    : "bg-gradient-to-r from-emerald-600 to-teal-600 glow-green"
                }`}
              >
                <Play className="h-5 w-5" fill="currentColor" />
                再開
              </button>
              <button
                onClick={reset}
                className="p-4 rounded-2xl glass hover:bg-white/10 transition-all duration-200 active:scale-[0.97]"
              >
                <RotateCcw className="h-5 w-5 text-muted-foreground" />
              </button>
            </>
          )}
        </div>

        {/* History */}
        <div className="w-full max-w-md">
          <button
            onClick={() => setShowHistory(!showHistory)}
            className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors mb-3 mx-auto"
          >
            <History className="h-4 w-4" />
            セッション履歴
            {showHistory ? (
              <ChevronUp className="h-3.5 w-3.5" />
            ) : (
              <ChevronDown className="h-3.5 w-3.5" />
            )}
          </button>

          {showHistory && (
            <div className="space-y-2 animate-fade-in-up">
              {sessions.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-6">
                  まだセッションがありません
                </p>
              ) : (
                sessions.map((s, i) => (
                  <div
                    key={i}
                    className="glass rounded-xl px-4 py-3 flex items-center justify-between"
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                          s.mode === "focus"
                            ? "bg-indigo-500/20"
                            : "bg-emerald-500/20"
                        }`}
                      >
                        {s.mode === "focus" ? (
                          <Brain className="h-4 w-4 text-indigo-400" />
                        ) : (
                          <Coffee className="h-4 w-4 text-emerald-400" />
                        )}
                      </div>
                      <div>
                        <p className="text-sm font-medium">
                          {Math.round(s.duration / 60)}分
                          {s.mode === "focus" ? "集中" : "休憩"}
                        </p>
                        <p className="text-[11px] text-muted-foreground">
                          {new Date(s.date).toLocaleTimeString("ja-JP", {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </p>
                      </div>
                    </div>
                    {s.completed && (
                      <span className="text-xs font-medium text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full">
                        完了
                      </span>
                    )}
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </div>

      <GuestBottomNav />
    </div>
  );
}
