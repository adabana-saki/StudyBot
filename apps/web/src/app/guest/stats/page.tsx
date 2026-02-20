"use client";

import { useState, useEffect, useMemo } from "react";
import GuestBottomNav from "@/components/GuestBottomNav";
import { isAuthenticated } from "@/lib/auth";
import {
  getProfile,
  getStudyStats,
  getDailyStudy,
  getStudyLogs as apiGetLogs,
} from "@/lib/api";
import {
  Flame,
  Zap,
  Target,
  TrendingUp,
  Calendar,
  Award,
  Clock,
  BarChart2,
  Cloud,
  CloudOff,
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";

// ---------- localStorage ----------

interface SessionLog {
  date: string;
  mode: string;
  duration: number;
  completed: boolean;
}

interface StudyLog {
  id: string;
  subject: string;
  minutes: number;
  note: string;
  date: string;
}

function getTimerSessions(): SessionLog[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(localStorage.getItem("studybot_timer_sessions") || "[]");
  } catch {
    return [];
  }
}

function getStudyLogs(): StudyLog[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(localStorage.getItem("studybot_logs") || "[]");
  } catch {
    return [];
  }
}

// ---------- helpers ----------

function getStreak(sessions: SessionLog[], logs: StudyLog[]): number {
  let streak = 0;
  const d = new Date();
  for (let i = 0; i < 365; i++) {
    const dateStr = d.toISOString().split("T")[0];
    const hasSession = sessions.some(
      (s) => s.date.startsWith(dateStr) && s.mode === "focus" && s.completed,
    );
    const hasLog = logs.some((l) => l.date.startsWith(dateStr));
    if (hasSession || hasLog) {
      streak++;
    } else if (i > 0) {
      break;
    }
    d.setDate(d.getDate() - 1);
  }
  return streak;
}

const SUBJECT_COLORS: Record<string, string> = {
  "数学": "#3B82F6",
  "英語": "#10B981",
  "理科": "#F59E0B",
  "国語": "#F43F5E",
  "社会": "#8B5CF6",
  "プログラミング": "#6366F1",
  "その他": "#6B7280",
};

const PIE_COLORS = ["#6366F1", "#3B82F6", "#10B981", "#F59E0B", "#F43F5E", "#8B5CF6", "#6B7280"];

// ---------- Custom Tooltip ----------

function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="glass rounded-lg px-3 py-2 text-xs border border-white/10">
      <p className="text-muted-foreground mb-1">{label}</p>
      {payload.map((entry: any, i: number) => (
        <p key={i} style={{ color: entry.color }} className="font-medium">
          {entry.name}: {entry.value}分
        </p>
      ))}
    </div>
  );
}

// ---------- Heatmap ----------

function StudyHeatmap({ sessions, logs }: { sessions: SessionLog[]; logs: StudyLog[] }) {
  const data = useMemo(() => {
    const cells = [];
    for (let i = 27; i >= 0; i--) {
      const d = new Date();
      d.setDate(d.getDate() - i);
      const dateStr = d.toISOString().split("T")[0];
      const pomMin = sessions
        .filter((s) => s.date.startsWith(dateStr) && s.mode === "focus" && s.completed)
        .reduce((sum, s) => sum + s.duration / 60, 0);
      const logMin = logs
        .filter((l) => l.date.startsWith(dateStr))
        .reduce((sum, l) => sum + l.minutes, 0);
      cells.push({
        date: dateStr,
        day: d.getDate(),
        dow: ["日", "月", "火", "水", "木", "金", "土"][d.getDay()],
        total: Math.round(pomMin + logMin),
      });
    }
    return cells;
  }, [sessions, logs]);

  const max = Math.max(...data.map((d) => d.total), 1);

  return (
    <div>
      <div className="grid grid-cols-7 gap-1.5">
        {data.map((cell) => {
          const intensity = cell.total / max;
          return (
            <div key={cell.date} className="relative group">
              <div
                className="aspect-square rounded-md transition-all duration-200 group-hover:scale-110"
                style={{
                  background:
                    cell.total === 0
                      ? "rgba(255,255,255,0.04)"
                      : `rgba(99, 102, 241, ${0.15 + intensity * 0.85})`,
                }}
              />
              <span className="absolute inset-0 flex items-center justify-center text-[9px] text-white/50">
                {cell.day}
              </span>
              {cell.total > 0 && (
                <div className="absolute -top-8 left-1/2 -translate-x-1/2 glass rounded px-2 py-0.5 text-[10px] whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity z-10">
                  {cell.total}分
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ---------- Hour Distribution ----------

function HourDistribution({ sessions, logs }: { sessions: SessionLog[]; logs: StudyLog[] }) {
  const data = useMemo(() => {
    const hours = Array(24).fill(0);
    sessions.forEach((s) => {
      if (s.mode === "focus" && s.completed) {
        const h = new Date(s.date).getHours();
        hours[h] += s.duration / 60;
      }
    });
    logs.forEach((l) => {
      const h = new Date(l.date).getHours();
      hours[h] += l.minutes;
    });
    // 6時～翌1時のみ表示
    return Array.from({ length: 20 }, (_, i) => {
      const h = (i + 6) % 24;
      return { hour: `${h}時`, minutes: Math.round(hours[h]) };
    });
  }, [sessions, logs]);

  const max = Math.max(...data.map((d) => d.minutes), 1);

  return (
    <div className="flex items-end gap-[3px] h-20">
      {data.map((d) => (
        <div key={d.hour} className="flex-1 flex flex-col items-center group relative">
          <div
            className="w-full rounded-t transition-all duration-300"
            style={{
              height: `${Math.max((d.minutes / max) * 100, d.minutes > 0 ? 8 : 0)}%`,
              background: d.minutes > 0
                ? `linear-gradient(to top, rgba(99,102,241,0.8), rgba(139,92,246,0.6))`
                : "rgba(255,255,255,0.04)",
            }}
          />
          {d.minutes > 0 && (
            <div className="absolute -top-6 left-1/2 -translate-x-1/2 glass rounded px-1.5 py-0.5 text-[9px] whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity z-10">
              {d.hour} {d.minutes}分
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// ---------- Main ----------

export default function GuestStatsPage() {
  const [sessions, setSessions] = useState<SessionLog[]>([]);
  const [logs, setLogs] = useState<StudyLog[]>([]);
  const [auth, setAuth] = useState(false);
  const [apiStreak, setApiStreak] = useState<number | null>(null);
  const [apiWeekly, setApiWeekly] = useState<number | null>(null);

  useEffect(() => {
    const authed = isAuthenticated();
    setAuth(authed);

    // Always load local data (for pomodoro sessions)
    setSessions(getTimerSessions());

    if (authed) {
      // Load study logs from API
      apiGetLogs(30)
        .then((items) => {
          setLogs(
            items.map((e) => ({
              id: String(e.id),
              subject: e.subject || "その他",
              minutes: e.duration_minutes,
              note: e.note,
              date: e.logged_at,
            })),
          );
        })
        .catch(() => setLogs(getStudyLogs()));

      // Load profile for streak
      getProfile()
        .then((p) => setApiStreak(p.streak_days))
        .catch(() => {});

      // Load weekly stats
      getStudyStats("weekly")
        .then((s) => setApiWeekly(s.total_minutes))
        .catch(() => {});
    } else {
      setLogs(getStudyLogs());
    }
  }, []);

  const today = new Date().toISOString().split("T")[0];

  // Today
  const todayPomodoro = sessions.filter(
    (s) => s.date.startsWith(today) && s.mode === "focus" && s.completed,
  );
  const todayPomodoroMin = todayPomodoro.reduce((sum, s) => sum + s.duration / 60, 0);
  const todayLogMin = logs
    .filter((l) => l.date.startsWith(today))
    .reduce((sum, l) => sum + l.minutes, 0);
  const todayTotalMin = Math.round(todayPomodoroMin + todayLogMin);

  // Weekly area chart data
  const weekData = useMemo(() => {
    return Array.from({ length: 14 }, (_, i) => {
      const d = new Date();
      d.setDate(d.getDate() - (13 - i));
      const dateStr = d.toISOString().split("T")[0];
      const pomMin = sessions
        .filter((s) => s.date.startsWith(dateStr) && s.mode === "focus" && s.completed)
        .reduce((sum, s) => sum + s.duration / 60, 0);
      const logMin = logs
        .filter((l) => l.date.startsWith(dateStr))
        .reduce((sum, l) => sum + l.minutes, 0);
      return {
        date: `${d.getMonth() + 1}/${d.getDate()}`,
        pomodoro: Math.round(pomMin),
        manual: Math.round(logMin),
        total: Math.round(pomMin + logMin),
      };
    });
  }, [sessions, logs]);

  const weekTotal = apiWeekly !== null ? apiWeekly : weekData.slice(-7).reduce((sum, d) => sum + d.total, 0);

  // Subject donut
  const subjectData = useMemo(() => {
    const map = new Map<string, number>();
    logs.forEach((l) => {
      map.set(l.subject, (map.get(l.subject) || 0) + l.minutes);
    });
    return Array.from(map.entries())
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 6);
  }, [logs]);

  const streak = apiStreak !== null ? apiStreak : getStreak(sessions, logs);

  // Total all time
  const allTimePom = sessions
    .filter((s) => s.mode === "focus" && s.completed)
    .reduce((sum, s) => sum + s.duration / 60, 0);
  const allTimeLog = logs.reduce((sum, l) => sum + l.minutes, 0);
  const allTimeTotal = Math.round(allTimePom + allTimeLog);
  const allTimeHours = (allTimeTotal / 60).toFixed(1);

  return (
    <div className="min-h-screen relative overflow-hidden pb-24">
      {/* Background */}
      <div className="fixed inset-0 -z-10">
        <div className="absolute inset-0 bg-gradient-to-br from-[#0a0f1e] via-[#0f1729] to-[#0a0f1e]" />
        <div className="absolute top-10 left-10 w-72 h-72 rounded-full bg-cyan-600/8 blur-[100px]" />
        <div className="absolute bottom-40 right-10 w-80 h-80 rounded-full bg-indigo-600/5 blur-[120px]" />
      </div>

      <div className="relative flex flex-col items-center px-4 pt-6">
        {/* Header */}
        <div className="w-full max-w-md mb-5 animate-fade-in-up">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold mb-0.5">統計</h1>
            {auth ? (
              <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 text-[10px] font-medium">
                <Cloud className="h-3 w-3" /> 同期中
              </span>
            ) : (
              <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-white/5 text-muted-foreground text-[10px]">
                <CloudOff className="h-3 w-3" /> ローカル
              </span>
            )}
          </div>
          <p className="text-xs text-muted-foreground">
            累計 {allTimeHours}時間 / {allTimeTotal}分
          </p>
        </div>

        {/* Highlight cards */}
        <div className="w-full max-w-md grid grid-cols-4 gap-2 mb-5 animate-fade-in-up animate-delay-100">
          {[
            { icon: Flame, value: streak, label: "連続", color: "text-orange-400" },
            { icon: Zap, value: todayTotalMin, label: "今日(分)", color: "text-yellow-400" },
            { icon: Target, value: todayPomodoro.length, label: "ポモドーロ", color: "text-indigo-400" },
            { icon: Clock, value: weekTotal, label: "週間(分)", color: "text-cyan-400" },
          ].map((item) => (
            <div key={item.label} className="glass rounded-2xl p-2.5 text-center">
              <item.icon className={`h-4 w-4 ${item.color} mx-auto mb-1`} />
              <p className="text-lg font-bold leading-none">{item.value}</p>
              <p className="text-[9px] text-muted-foreground mt-0.5">{item.label}</p>
            </div>
          ))}
        </div>

        {/* 14-day Area Chart */}
        <div className="w-full max-w-md glass rounded-2xl p-4 mb-4 animate-fade-in-up animate-delay-200">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-indigo-400" />
              <span className="text-xs font-medium">14日間の学習推移</span>
            </div>
            <div className="flex items-center gap-3 text-[10px]">
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-indigo-500" />
                ポモドーロ
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-purple-500" />
                手動記録
              </span>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={160}>
            <AreaChart data={weekData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="gradPom" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#6366F1" stopOpacity={0.4} />
                  <stop offset="100%" stopColor="#6366F1" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gradManual" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#A855F7" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#A855F7" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 10, fill: "rgba(255,255,255,0.4)" }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 10, fill: "rgba(255,255,255,0.4)" }}
                axisLine={false}
                tickLine={false}
                width={35}
              />
              <Tooltip content={<ChartTooltip />} />
              <Area
                type="monotone"
                dataKey="pomodoro"
                name="ポモドーロ"
                stroke="#6366F1"
                strokeWidth={2}
                fill="url(#gradPom)"
              />
              <Area
                type="monotone"
                dataKey="manual"
                name="手動記録"
                stroke="#A855F7"
                strokeWidth={2}
                fill="url(#gradManual)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Heatmap + Donut row */}
        <div className="w-full max-w-md grid grid-cols-2 gap-3 mb-4 animate-fade-in-up animate-delay-300">
          {/* 28-day heatmap */}
          <div className="glass rounded-2xl p-3">
            <div className="flex items-center gap-1.5 mb-2.5">
              <Calendar className="h-3.5 w-3.5 text-muted-foreground" />
              <span className="text-[10px] text-muted-foreground">28日間</span>
            </div>
            <StudyHeatmap sessions={sessions} logs={logs} />
          </div>

          {/* Subject donut */}
          <div className="glass rounded-2xl p-3">
            <div className="flex items-center gap-1.5 mb-1">
              <Award className="h-3.5 w-3.5 text-muted-foreground" />
              <span className="text-[10px] text-muted-foreground">科目別</span>
            </div>
            {subjectData.length > 0 ? (
              <div className="flex flex-col items-center">
                <ResponsiveContainer width="100%" height={100}>
                  <PieChart>
                    <Pie
                      data={subjectData}
                      cx="50%"
                      cy="50%"
                      innerRadius={28}
                      outerRadius={45}
                      paddingAngle={3}
                      dataKey="value"
                      stroke="none"
                    >
                      {subjectData.map((entry, i) => (
                        <Cell
                          key={entry.name}
                          fill={SUBJECT_COLORS[entry.name] || PIE_COLORS[i % PIE_COLORS.length]}
                        />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(value: number) => `${value}分`}
                      contentStyle={{
                        background: "rgba(15,23,42,0.9)",
                        border: "1px solid rgba(255,255,255,0.1)",
                        borderRadius: "8px",
                        fontSize: "11px",
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
                <div className="flex flex-wrap gap-x-2 gap-y-0.5 justify-center">
                  {subjectData.slice(0, 4).map((entry, i) => (
                    <span key={entry.name} className="flex items-center gap-1 text-[9px] text-muted-foreground">
                      <span
                        className="w-1.5 h-1.5 rounded-full"
                        style={{ background: SUBJECT_COLORS[entry.name] || PIE_COLORS[i] }}
                      />
                      {entry.name}
                    </span>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-[10px] text-muted-foreground text-center py-8">
                記録なし
              </p>
            )}
          </div>
        </div>

        {/* Hour distribution */}
        <div className="w-full max-w-md glass rounded-2xl p-4 mb-4 animate-fade-in-up">
          <div className="flex items-center gap-2 mb-3">
            <BarChart2 className="h-4 w-4 text-muted-foreground" />
            <span className="text-xs font-medium">時間帯別</span>
            <span className="text-[10px] text-muted-foreground ml-auto">6時〜翌1時</span>
          </div>
          <HourDistribution sessions={sessions} logs={logs} />
          <div className="flex justify-between mt-1.5">
            <span className="text-[9px] text-muted-foreground">6時</span>
            <span className="text-[9px] text-muted-foreground">12時</span>
            <span className="text-[9px] text-muted-foreground">18時</span>
            <span className="text-[9px] text-muted-foreground">1時</span>
          </div>
        </div>

        {/* Subject breakdown bars */}
        {subjectData.length > 0 && (
          <div className="w-full max-w-md glass rounded-2xl p-4 mb-4 animate-fade-in-up">
            <div className="flex items-center gap-2 mb-3">
              <Award className="h-4 w-4 text-muted-foreground" />
              <span className="text-xs font-medium">科目別ランキング</span>
            </div>
            <div className="space-y-2.5">
              {subjectData.map((entry, i) => {
                const total = subjectData.reduce((sum, e) => sum + e.value, 0);
                const pct = total > 0 ? (entry.value / total) * 100 : 0;
                const color = SUBJECT_COLORS[entry.name] || PIE_COLORS[i];
                return (
                  <div key={entry.name}>
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <span
                          className="w-2.5 h-2.5 rounded"
                          style={{ background: color }}
                        />
                        <span className="text-xs font-medium">{entry.name}</span>
                      </div>
                      <span className="text-[11px] text-muted-foreground">
                        {entry.value}分 ({Math.round(pct)}%)
                      </span>
                    </div>
                    <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-700"
                        style={{ width: `${pct}%`, background: color }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Empty state */}
        {sessions.length === 0 && logs.length === 0 && (
          <div className="text-center py-8">
            <TrendingUp className="h-12 w-12 text-muted-foreground/20 mx-auto mb-3" />
            <p className="text-sm text-muted-foreground">
              タイマーや学習記録を使うと
              <br />
              ここに統計が表示されます
            </p>
          </div>
        )}
      </div>

      <GuestBottomNav />
    </div>
  );
}
