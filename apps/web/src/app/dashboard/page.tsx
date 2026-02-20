"use client";

import { useEffect, useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { isAuthenticated } from "@/lib/auth";
import {
  getProfile,
  getStudyStats,
  getDailyStudy,
  getActiveSessions,
  UserProfile,
  StudyStats,
  DailyStudy,
  ActiveSession,
} from "@/lib/api";
import ActiveSessionCard from "@/components/ActiveSessionCard";
import LoadingSpinner from "@/components/LoadingSpinner";
import {
  Flame,
  Zap,
  Target,
  TrendingUp,
  Clock,
  Trophy,
  Layers,
  Award,
  Calendar,
  BarChart2,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

// ---------- Chart Tooltip ----------

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

// ---------- Study Heatmap ----------

function StudyHeatmap({ data }: { data: DailyStudy[] }) {
  const cells = useMemo(() => {
    const dailyMap = new Map(
      data.map((d) => [d.day, d.total_minutes]),
    );
    const result = [];
    for (let i = 27; i >= 0; i--) {
      const d = new Date();
      d.setDate(d.getDate() - i);
      const dateStr = d.toISOString().split("T")[0];
      result.push({
        date: dateStr,
        day: d.getDate(),
        dow: ["日", "月", "火", "水", "木", "金", "土"][d.getDay()],
        total: dailyMap.get(dateStr) || 0,
      });
    }
    return result;
  }, [data]);

  const max = Math.max(...cells.map((d) => d.total), 1);

  return (
    <div className="grid grid-cols-7 gap-1.5">
      {cells.map((cell) => {
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
  );
}

// ---------- XP Ring ----------

function XPRing({ xp, level }: { xp: number; level: number }) {
  const xpInLevel = xp % 1000;
  const progress = xpInLevel / 1000;
  const circumference = 2 * Math.PI * 54;
  const strokeDashoffset = circumference * (1 - progress);

  return (
    <div className="relative w-32 h-32">
      <svg className="w-full h-full -rotate-90" viewBox="0 0 120 120">
        <circle
          cx="60"
          cy="60"
          r="54"
          fill="none"
          stroke="rgba(255,255,255,0.06)"
          strokeWidth="8"
        />
        <circle
          cx="60"
          cy="60"
          r="54"
          fill="none"
          stroke="url(#xpGradient)"
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          className="transition-all duration-1000"
        />
        <defs>
          <linearGradient id="xpGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#6366F1" />
            <stop offset="100%" stopColor="#A855F7" />
          </linearGradient>
        </defs>
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
          Lv.{level}
        </span>
        <span className="text-[10px] text-muted-foreground">
          {xpInLevel}/1000 XP
        </span>
      </div>
    </div>
  );
}

// ---------- Day of Week Chart ----------

function DayOfWeekChart({ data }: { data: DailyStudy[] }) {
  const dowData = useMemo(() => {
    const dowMap = [0, 0, 0, 0, 0, 0, 0]; // Sun-Sat
    const dowCount = [0, 0, 0, 0, 0, 0, 0];
    const labels = ["日", "月", "火", "水", "木", "金", "土"];

    data.forEach((d) => {
      const date = new Date(d.day);
      const dow = date.getDay();
      dowMap[dow] += d.total_minutes;
      dowCount[dow]++;
    });

    return labels.map((label, i) => ({
      day: label,
      avg: dowCount[i] > 0 ? Math.round(dowMap[i] / dowCount[i]) : 0,
      total: dowMap[i],
    }));
  }, [data]);

  const max = Math.max(...dowData.map((d) => d.avg), 1);

  return (
    <div className="flex items-end gap-2 h-20">
      {dowData.map((d) => (
        <div key={d.day} className="flex-1 flex flex-col items-center group relative">
          <div
            className="w-full rounded-t transition-all duration-300"
            style={{
              height: `${Math.max((d.avg / max) * 100, d.avg > 0 ? 8 : 0)}%`,
              background:
                d.avg > 0
                  ? "linear-gradient(to top, rgba(99,102,241,0.8), rgba(139,92,246,0.6))"
                  : "rgba(255,255,255,0.04)",
            }}
          />
          <span className="text-[9px] text-muted-foreground mt-1">{d.day}</span>
          {d.avg > 0 && (
            <div className="absolute -top-6 left-1/2 -translate-x-1/2 glass rounded px-1.5 py-0.5 text-[9px] whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity z-10">
              平均{d.avg}分
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// ---------- Trend Indicator ----------

function TrendBadge({ current, previous }: { current: number; previous: number }) {
  if (previous === 0 && current === 0)
    return <Minus className="h-3 w-3 text-muted-foreground" />;
  if (previous === 0)
    return <ArrowUpRight className="h-3 w-3 text-emerald-400" />;

  const pct = ((current - previous) / previous) * 100;
  if (Math.abs(pct) < 5) return <Minus className="h-3 w-3 text-muted-foreground" />;

  return pct > 0 ? (
    <span className="flex items-center gap-0.5 text-[10px] text-emerald-400">
      <ArrowUpRight className="h-3 w-3" />
      {Math.round(pct)}%
    </span>
  ) : (
    <span className="flex items-center gap-0.5 text-[10px] text-rose-400">
      <ArrowDownRight className="h-3 w-3" />
      {Math.abs(Math.round(pct))}%
    </span>
  );
}

// ---------- Main ----------

export default function DashboardPage() {
  const router = useRouter();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [weeklyStats, setWeeklyStats] = useState<StudyStats | null>(null);
  const [monthlyStats, setMonthlyStats] = useState<StudyStats | null>(null);
  const [dailyStudy, setDailyStudy] = useState<DailyStudy[]>([]);
  const [activeSessions, setActiveSessions] = useState<ActiveSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/");
      return;
    }

    async function fetchData() {
      try {
        const [profileRes, weekRes, monthRes, dailyRes] =
          await Promise.allSettled([
            getProfile(),
            getStudyStats("weekly"),
            getStudyStats("monthly"),
            getDailyStudy(28),
          ]);
        if (profileRes.status === "fulfilled") setProfile(profileRes.value);
        if (weekRes.status === "fulfilled") setWeeklyStats(weekRes.value);
        if (monthRes.status === "fulfilled") setMonthlyStats(monthRes.value);
        if (dailyRes.status === "fulfilled") setDailyStudy(dailyRes.value);

        if (
          profileRes.status === "rejected" &&
          weekRes.status === "rejected" &&
          monthRes.status === "rejected" &&
          dailyRes.status === "rejected"
        ) {
          const err = profileRes.reason;
          setError(
            err instanceof Error ? err.message : "データの取得に失敗しました",
          );
        }
        const sessionsData = await getActiveSessions().catch(() => []);
        setActiveSessions(sessionsData);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "データの取得に失敗しました",
        );
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [router]);

  // Chart data
  const chartData = useMemo(() => {
    return dailyStudy.map((item) => {
      const date = new Date(item.day);
      return {
        date: `${date.getMonth() + 1}/${date.getDate()}`,
        学習時間: item.total_minutes,
      };
    });
  }, [dailyStudy]);

  // This week vs last week
  const thisWeekMin = useMemo(() => {
    const now = new Date();
    const weekAgo = new Date();
    weekAgo.setDate(now.getDate() - 7);
    return dailyStudy
      .filter((d) => new Date(d.day) >= weekAgo)
      .reduce((sum, d) => sum + d.total_minutes, 0);
  }, [dailyStudy]);

  const lastWeekMin = useMemo(() => {
    const weekAgo = new Date();
    weekAgo.setDate(weekAgo.getDate() - 7);
    const twoWeeksAgo = new Date();
    twoWeeksAgo.setDate(twoWeeksAgo.getDate() - 14);
    return dailyStudy
      .filter((d) => {
        const date = new Date(d.day);
        return date >= twoWeeksAgo && date < weekAgo;
      })
      .reduce((sum, d) => sum + d.total_minutes, 0);
  }, [dailyStudy]);

  // Today
  const today = new Date().toISOString().split("T")[0];
  const todayMin =
    dailyStudy.find((d) => d.day === today)?.total_minutes || 0;

  if (loading) {
    return <LoadingSpinner label="読み込み中..." />;
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <div className="glass rounded-2xl p-8 max-w-md w-full text-center">
          <span className="text-4xl block mb-4">⚠️</span>
          <h1 className="text-xl font-bold mb-2">エラー</h1>
          <p className="text-muted-foreground">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen relative overflow-hidden pb-8">
      {/* Background */}
      <div className="fixed inset-0 -z-10">
        <div className="absolute inset-0 bg-gradient-to-br from-[#0a0f1e] via-[#0f1729] to-[#0a0f1e]" />
        <div className="absolute top-10 left-10 w-72 h-72 rounded-full bg-indigo-600/8 blur-[100px]" />
        <div className="absolute bottom-40 right-10 w-80 h-80 rounded-full bg-purple-600/5 blur-[120px]" />
      </div>

      <div className="relative max-w-3xl mx-auto px-4 pt-6">
        {/* Header with profile */}
        {profile && (
          <div className="glass rounded-2xl p-5 mb-5 animate-fade-in-up">
            <div className="flex items-center gap-5">
              {/* Avatar + XP Ring */}
              <div className="relative flex-shrink-0">
                {profile.avatar_url ? (
                  <div className="relative">
                    <XPRing xp={profile.xp} level={profile.level} />
                    <img
                      src={profile.avatar_url}
                      alt={profile.display_name || profile.username}
                      className="absolute inset-0 m-auto w-20 h-20 rounded-full border-2 border-indigo-500/30"
                    />
                  </div>
                ) : (
                  <XPRing xp={profile.xp} level={profile.level} />
                )}
              </div>

              {/* User info */}
              <div className="min-w-0 flex-1">
                <h1 className="text-xl font-bold truncate">
                  おかえり、{profile.display_name || profile.username}さん
                </h1>
                <div className="flex items-center gap-3 mt-1.5">
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 text-xs font-medium">
                    <Trophy className="h-3 w-3" />#{profile.rank}
                  </span>
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-yellow-500/20 text-yellow-300 text-xs font-medium">
                    🪙 {profile.coins.toLocaleString()}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground mt-1.5">
                  {profile.xp.toLocaleString()} XP 累計
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Active Sessions */}
        {activeSessions.length > 0 && (
          <div className="mb-5 space-y-3 animate-fade-in-up">
            <h3 className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
              アクティブセッション
            </h3>
            {activeSessions.map((s) => (
              <ActiveSessionCard key={s.id} session={s} />
            ))}
          </div>
        )}

        {/* Stats highlight cards */}
        <div className="grid grid-cols-4 gap-2 mb-5 animate-fade-in-up" style={{ animationDelay: "100ms" }}>
          {[
            {
              icon: Flame,
              value: profile?.streak_days ?? 0,
              label: "連続日数",
              color: "text-orange-400",
            },
            {
              icon: Zap,
              value: todayMin,
              label: "今日(分)",
              color: "text-yellow-400",
            },
            {
              icon: Target,
              value: weeklyStats?.session_count ?? 0,
              label: "週セッション",
              color: "text-indigo-400",
            },
            {
              icon: Clock,
              value: weeklyStats?.total_minutes ?? 0,
              label: "週間(分)",
              color: "text-cyan-400",
              trend: { current: thisWeekMin, previous: lastWeekMin },
            },
          ].map((item) => (
            <div key={item.label} className="glass rounded-2xl p-2.5 text-center">
              <item.icon className={`h-4 w-4 ${item.color} mx-auto mb-1`} />
              <p className="text-lg font-bold leading-none">{item.value}</p>
              <p className="text-[9px] text-muted-foreground mt-0.5">
                {item.label}
              </p>
              {"trend" in item && item.trend && (
                <div className="mt-0.5 flex justify-center">
                  <TrendBadge
                    current={item.trend.current}
                    previous={item.trend.previous}
                  />
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Weekly comparison banner */}
        <div
          className="glass rounded-2xl p-4 mb-5 flex items-center justify-between animate-fade-in-up"
          style={{ animationDelay: "150ms" }}
        >
          <div>
            <p className="text-xs text-muted-foreground">今週 vs 先週</p>
            <p className="text-lg font-bold">
              {Math.floor(thisWeekMin / 60)}時間{thisWeekMin % 60}分
              <span className="text-xs text-muted-foreground font-normal ml-2">
                / {Math.floor(lastWeekMin / 60)}時間{lastWeekMin % 60}分
              </span>
            </p>
          </div>
          <TrendBadge current={thisWeekMin} previous={lastWeekMin} />
        </div>

        {/* 28-day Area Chart */}
        {chartData.length > 0 && (
          <div
            className="glass rounded-2xl p-4 mb-5 animate-fade-in-up"
            style={{ animationDelay: "200ms" }}
          >
            <div className="flex items-center gap-2 mb-3">
              <TrendingUp className="h-4 w-4 text-indigo-400" />
              <span className="text-xs font-medium">学習推移（28日間）</span>
            </div>
            <ResponsiveContainer width="100%" height={180}>
              <AreaChart
                data={chartData}
                margin={{ top: 5, right: 5, left: -20, bottom: 0 }}
              >
                <defs>
                  <linearGradient id="gradStudy" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#6366F1" stopOpacity={0.4} />
                    <stop offset="100%" stopColor="#6366F1" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="rgba(255,255,255,0.06)"
                />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 10, fill: "rgba(255,255,255,0.4)" }}
                  axisLine={false}
                  tickLine={false}
                  interval="preserveStartEnd"
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
                  dataKey="学習時間"
                  name="学習時間"
                  stroke="#6366F1"
                  strokeWidth={2}
                  fill="url(#gradStudy)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Heatmap + DOW row */}
        <div
          className="grid grid-cols-2 gap-3 mb-5 animate-fade-in-up"
          style={{ animationDelay: "300ms" }}
        >
          {/* 28-day heatmap */}
          <div className="glass rounded-2xl p-3">
            <div className="flex items-center gap-1.5 mb-2.5">
              <Calendar className="h-3.5 w-3.5 text-muted-foreground" />
              <span className="text-[10px] text-muted-foreground">
                28日間ヒートマップ
              </span>
            </div>
            <StudyHeatmap data={dailyStudy} />
          </div>

          {/* Day of week chart */}
          <div className="glass rounded-2xl p-3">
            <div className="flex items-center gap-1.5 mb-2.5">
              <BarChart2 className="h-3.5 w-3.5 text-muted-foreground" />
              <span className="text-[10px] text-muted-foreground">
                曜日別平均
              </span>
            </div>
            <DayOfWeekChart data={dailyStudy} />
          </div>
        </div>

        {/* Monthly stats summary */}
        {monthlyStats && (
          <div
            className="glass rounded-2xl p-4 mb-5 animate-fade-in-up"
            style={{ animationDelay: "350ms" }}
          >
            <div className="flex items-center gap-2 mb-3">
              <Award className="h-4 w-4 text-purple-400" />
              <span className="text-xs font-medium">月間サマリー</span>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div className="text-center">
                <p className="text-2xl font-bold text-indigo-400">
                  {Math.floor(monthlyStats.total_minutes / 60)}
                  <span className="text-sm font-normal text-muted-foreground">
                    h
                  </span>
                  {monthlyStats.total_minutes % 60}
                  <span className="text-sm font-normal text-muted-foreground">
                    m
                  </span>
                </p>
                <p className="text-[10px] text-muted-foreground">
                  総学習時間
                </p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-purple-400">
                  {monthlyStats.session_count}
                </p>
                <p className="text-[10px] text-muted-foreground">
                  セッション数
                </p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-cyan-400">
                  {Math.round(monthlyStats.avg_minutes)}
                  <span className="text-sm font-normal text-muted-foreground">
                    分
                  </span>
                </p>
                <p className="text-[10px] text-muted-foreground">
                  平均セッション
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Quick Links */}
        <div
          className="grid grid-cols-3 gap-3 animate-fade-in-up"
          style={{ animationDelay: "400ms" }}
        >
          {[
            {
              href: "/leaderboard",
              icon: Trophy,
              label: "ランキング",
              color: "text-yellow-400",
            },
            {
              href: "/achievements",
              icon: Award,
              label: "実績",
              color: "text-purple-400",
            },
            {
              href: "/flashcards",
              icon: Layers,
              label: "フラッシュカード",
              color: "text-cyan-400",
            },
          ].map((link) => (
            <Link key={link.href} href={link.href}>
              <div className="glass rounded-2xl p-4 text-center hover:bg-white/5 transition-colors group">
                <link.icon
                  className={`h-6 w-6 ${link.color} mx-auto mb-2 group-hover:scale-110 transition-transform`}
                />
                <p className="text-xs font-medium">{link.label}</p>
              </div>
            </Link>
          ))}
        </div>

        {/* Empty state */}
        {dailyStudy.length === 0 && !weeklyStats && (
          <div className="text-center py-12">
            <TrendingUp className="h-12 w-12 text-muted-foreground/20 mx-auto mb-3" />
            <p className="text-sm text-muted-foreground">
              学習を記録すると
              <br />
              ここに統計が表示されます
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
