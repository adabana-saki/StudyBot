"use client";

import { useState, useEffect, useCallback } from "react";
import GuestBottomNav from "@/components/GuestBottomNav";
import { isAuthenticated } from "@/lib/auth";
import {
  getStudyLogs as apiGetLogs,
  createStudyLog as apiCreateLog,
  StudyLogEntry,
} from "@/lib/api";
import {
  BookOpen,
  Plus,
  Clock,
  Tag,
  Trash2,
  Cloud,
  CloudOff,
} from "lucide-react";

// ---------- Types ----------

interface LocalStudyLog {
  id: string;
  subject: string;
  minutes: number;
  note: string;
  date: string;
}

interface UnifiedLog {
  id: string;
  subject: string;
  minutes: number;
  note: string;
  date: string;
  _apiId?: number;
}

// ---------- Constants ----------

const SUBJECTS = [
  { label: "数学", color: "from-blue-500/20 to-cyan-500/20", text: "text-blue-400" },
  { label: "英語", color: "from-emerald-500/20 to-teal-500/20", text: "text-emerald-400" },
  { label: "理科", color: "from-amber-500/20 to-orange-500/20", text: "text-amber-400" },
  { label: "国語", color: "from-rose-500/20 to-pink-500/20", text: "text-rose-400" },
  { label: "社会", color: "from-violet-500/20 to-purple-500/20", text: "text-violet-400" },
  { label: "プログラミング", color: "from-indigo-500/20 to-blue-500/20", text: "text-indigo-400" },
  { label: "その他", color: "from-gray-500/20 to-slate-500/20", text: "text-gray-400" },
];

const QUICK_MINUTES = [15, 30, 45, 60, 90, 120];

// ---------- localStorage ----------

function loadLocalLogs(): LocalStudyLog[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(localStorage.getItem("studybot_logs") || "[]");
  } catch {
    return [];
  }
}

function saveLocalLogs(logs: LocalStudyLog[]) {
  localStorage.setItem("studybot_logs", JSON.stringify(logs));
}

function apiToUnified(entry: StudyLogEntry): UnifiedLog {
  return {
    id: String(entry.id),
    subject: entry.subject || "その他",
    minutes: entry.duration_minutes,
    note: entry.note,
    date: entry.logged_at,
    _apiId: entry.id,
  };
}

function localToUnified(entry: LocalStudyLog): UnifiedLog {
  return { ...entry, _apiId: undefined };
}

// ---------- Component ----------

export default function GuestLogPage() {
  const [logs, setLogs] = useState<UnifiedLog[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [subject, setSubject] = useState("数学");
  const [minutes, setMinutes] = useState(30);
  const [note, setNote] = useState("");
  const [auth, setAuth] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const authed = isAuthenticated();
    setAuth(authed);

    if (authed) {
      apiGetLogs(30)
        .then((items) => setLogs(items.map(apiToUnified)))
        .catch(() => setLogs(loadLocalLogs().map(localToUnified)))
        .finally(() => setLoading(false));
    } else {
      setLogs(loadLocalLogs().map(localToUnified));
      setLoading(false);
    }
  }, []);

  const addLog = useCallback(async () => {
    if (minutes <= 0) return;

    if (auth) {
      try {
        const entry = await apiCreateLog({
          subject,
          duration_minutes: minutes,
          note: note.trim(),
        });
        setLogs((prev) => [apiToUnified(entry), ...prev]);
      } catch {
        // fallback
      }
    } else {
      const newLog: LocalStudyLog = {
        id: Date.now().toString(),
        subject,
        minutes,
        note: note.trim(),
        date: new Date().toISOString(),
      };
      const localLogs = loadLocalLogs();
      const updated = [newLog, ...localLogs];
      saveLocalLogs(updated);
      setLogs(updated.map(localToUnified));
    }

    setNote("");
    setShowForm(false);
  }, [subject, minutes, note, auth]);

  const deleteLog = useCallback(
    (id: string) => {
      if (!auth) {
        const localLogs = loadLocalLogs().filter((l) => l.id !== id);
        saveLocalLogs(localLogs);
      }
      // API doesn't have delete endpoint for study logs, just remove from display
      setLogs((prev) => prev.filter((l) => l.id !== id));
    },
    [auth],
  );

  // Today
  const today = new Date().toISOString().split("T")[0];
  const todayMinutes = logs
    .filter((l) => l.date.startsWith(today))
    .reduce((sum, l) => sum + l.minutes, 0);

  // Weekly chart
  const weekData = Array.from({ length: 7 }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (6 - i));
    const dateStr = d.toISOString().split("T")[0];
    const dayMinutes = logs
      .filter((l) => l.date.startsWith(dateStr))
      .reduce((sum, l) => sum + l.minutes, 0);
    return {
      day: ["日", "月", "火", "水", "木", "金", "土"][d.getDay()],
      date: dateStr,
      minutes: dayMinutes,
      isToday: dateStr === today,
    };
  });
  const maxMinutes = Math.max(...weekData.map((d) => d.minutes), 60);

  const subjectInfo = (name: string) =>
    SUBJECTS.find((s) => s.label === name) || SUBJECTS[SUBJECTS.length - 1];

  return (
    <div className="min-h-screen relative overflow-hidden pb-24">
      <div className="fixed inset-0 -z-10">
        <div className="absolute inset-0 bg-gradient-to-br from-[#0a0f1e] via-[#0f1729] to-[#0a0f1e]" />
        <div className="absolute top-32 left-5 w-72 h-72 rounded-full bg-emerald-600/8 blur-[100px]" />
        <div className="absolute bottom-32 right-5 w-80 h-80 rounded-full bg-blue-600/5 blur-[120px]" />
      </div>

      <div className="relative flex flex-col items-center px-4 pt-6">
        {/* Header */}
        <div className="w-full max-w-md mb-6 animate-fade-in-up">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-bold mb-1">学習記録</h1>
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
              <p className="text-xs text-muted-foreground">今日: {todayMinutes}分</p>
            </div>
            <button
              onClick={() => setShowForm(!showForm)}
              className="h-10 w-10 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 flex items-center justify-center hover:from-indigo-500 hover:to-purple-500 transition-all active:scale-95"
            >
              <Plus className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Weekly chart */}
        <div className="w-full max-w-md glass rounded-2xl p-4 mb-6 animate-fade-in-up animate-delay-100">
          <p className="text-xs text-muted-foreground mb-3">今週の学習時間</p>
          <div className="flex items-end justify-between gap-2 h-28">
            {weekData.map((d) => (
              <div key={d.date} className="flex-1 flex flex-col items-center gap-1">
                <span className="text-[10px] text-muted-foreground tabular-nums">
                  {d.minutes > 0 ? `${d.minutes}m` : ""}
                </span>
                <div className="w-full relative" style={{ height: "80px" }}>
                  <div
                    className={`absolute bottom-0 w-full rounded-lg transition-all duration-500 ${
                      d.isToday
                        ? "bg-gradient-to-t from-indigo-600 to-indigo-400"
                        : "bg-white/10"
                    }`}
                    style={{
                      height: `${Math.max((d.minutes / maxMinutes) * 100, d.minutes > 0 ? 8 : 0)}%`,
                    }}
                  />
                </div>
                <span className={`text-[10px] font-medium ${d.isToday ? "text-indigo-400" : "text-muted-foreground"}`}>
                  {d.day}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Add form */}
        {showForm && (
          <div className="w-full max-w-md glass rounded-2xl p-4 mb-6 space-y-4 animate-fade-in-up">
            <div>
              <label className="text-xs text-muted-foreground mb-2 block">
                <Tag className="h-3 w-3 inline mr-1" /> 科目
              </label>
              <div className="flex flex-wrap gap-2">
                {SUBJECTS.map((s) => (
                  <button
                    key={s.label}
                    onClick={() => setSubject(s.label)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                      subject === s.label
                        ? `bg-gradient-to-r ${s.color} ${s.text} border border-white/10`
                        : "bg-white/5 text-muted-foreground hover:bg-white/10"
                    }`}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="text-xs text-muted-foreground mb-2 block">
                <Clock className="h-3 w-3 inline mr-1" /> 学習時間
              </label>
              <div className="flex flex-wrap gap-2">
                {QUICK_MINUTES.map((m) => (
                  <button
                    key={m}
                    onClick={() => setMinutes(m)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                      minutes === m
                        ? "bg-indigo-500/20 text-indigo-400 border border-indigo-500/20"
                        : "bg-white/5 text-muted-foreground hover:bg-white/10"
                    }`}
                  >
                    {m}分
                  </button>
                ))}
              </div>
            </div>
            <div>
              <input
                type="text"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="メモ（任意）"
                className="w-full h-10 px-3 rounded-xl bg-white/5 border border-white/10 text-sm placeholder:text-muted-foreground/40 focus:outline-none focus:border-indigo-500/30"
              />
            </div>
            <button
              onClick={addLog}
              className="w-full h-11 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 text-sm font-semibold hover:from-indigo-500 hover:to-purple-500 transition-all active:scale-[0.98]"
            >
              記録する
            </button>
          </div>
        )}

        {/* Log list */}
        <div className="w-full max-w-md space-y-2 animate-fade-in-up animate-delay-200">
          {loading ? (
            <div className="text-sm text-muted-foreground text-center py-8">読み込み中...</div>
          ) : logs.length === 0 ? (
            <div className="text-center py-12">
              <BookOpen className="h-12 w-12 text-muted-foreground/20 mx-auto mb-3" />
              <p className="text-sm text-muted-foreground">学習を記録しましょう</p>
            </div>
          ) : (
            logs.slice(0, 30).map((log) => {
              const si = subjectInfo(log.subject);
              return (
                <div key={log.id} className="glass rounded-xl px-4 py-3 flex items-center gap-3 group">
                  <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${si.color} flex items-center justify-center flex-shrink-0`}>
                    <span className="text-xs font-bold">{log.subject.slice(0, 1)}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">{log.subject}</span>
                      <span className={`text-xs ${si.text}`}>{log.minutes}分</span>
                    </div>
                    {log.note && <p className="text-xs text-muted-foreground truncate">{log.note}</p>}
                    <p className="text-[10px] text-muted-foreground/60">
                      {new Date(log.date).toLocaleDateString("ja-JP", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                    </p>
                  </div>
                  {!auth && (
                    <button
                      onClick={() => deleteLog(log.id)}
                      className="flex-shrink-0 opacity-0 group-hover:opacity-100 transition-all active:scale-90 p-1"
                    >
                      <Trash2 className="h-4 w-4 text-muted-foreground/40 hover:text-red-400" />
                    </button>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>

      <GuestBottomNav />
    </div>
  );
}
