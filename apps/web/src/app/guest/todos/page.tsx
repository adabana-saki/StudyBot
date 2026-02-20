"use client";

import { useState, useEffect, useMemo, useCallback } from "react";
import GuestBottomNav from "@/components/GuestBottomNav";
import { isAuthenticated } from "@/lib/auth";
import {
  getTodos,
  createTodo as apiCreateTodo,
  completeTodo as apiCompleteTodo,
  deleteTodo as apiDeleteTodo,
  updateTodo as apiUpdateTodo,
  TodoItem as ApiTodoItem,
} from "@/lib/api";
import {
  Plus,
  Trash2,
  Check,
  Circle,
  Star,
  CheckSquare,
  CalendarClock,
  AlertTriangle,
  Clock,
  X,
  Cloud,
  CloudOff,
} from "lucide-react";

// ---------- Unified Todo type ----------

interface Todo {
  id: string;
  text: string;
  completed: boolean;
  priority: boolean;
  createdAt: string;
  deadline: string | null;
  _apiId?: number; // API ID for authenticated mode
}

// ---------- localStorage helpers ----------

function loadLocalTodos(): Todo[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(localStorage.getItem("studybot_todos") || "[]");
  } catch {
    return [];
  }
}

function saveLocalTodos(todos: Todo[]) {
  localStorage.setItem("studybot_todos", JSON.stringify(todos));
}

// ---------- API ↔ local conversion ----------

function apiToLocal(item: ApiTodoItem): Todo {
  return {
    id: String(item.id),
    text: item.title,
    completed: item.status === "completed",
    priority: item.priority === 3,
    createdAt: item.created_at,
    deadline: item.deadline,
    _apiId: item.id,
  };
}

// ---------- Deadline helpers ----------

function getDeadlineStatus(deadline: string | null) {
  if (!deadline) return { label: "", color: "", bgColor: "", urgent: false };
  const now = new Date();
  const dl = new Date(deadline);
  const diffMs = dl.getTime() - now.getTime();
  const diffMin = diffMs / (1000 * 60);
  const diffHours = diffMin / 60;
  const diffDays = diffHours / 24;

  if (diffMs < 0)
    return { label: "期限切れ", color: "text-red-400", bgColor: "bg-red-500/15", urgent: true };
  if (diffMin < 60)
    return { label: `あと${Math.max(1, Math.round(diffMin))}分`, color: "text-red-400", bgColor: "bg-red-500/15", urgent: true };
  if (diffHours < 3)
    return { label: `あと${Math.round(diffHours * 10) / 10}時間`, color: "text-orange-400", bgColor: "bg-orange-500/15", urgent: true };
  if (diffHours < 24)
    return { label: `今日 ${dl.toLocaleTimeString("ja-JP", { hour: "2-digit", minute: "2-digit" })}`, color: "text-amber-400", bgColor: "bg-amber-500/10", urgent: false };
  if (diffDays < 2)
    return { label: `明日 ${dl.toLocaleTimeString("ja-JP", { hour: "2-digit", minute: "2-digit" })}`, color: "text-yellow-300", bgColor: "bg-yellow-500/10", urgent: false };
  if (diffDays < 7)
    return { label: `${Math.ceil(diffDays)}日後`, color: "text-blue-400", bgColor: "bg-blue-500/10", urgent: false };
  return { label: dl.toLocaleDateString("ja-JP", { month: "short", day: "numeric" }), color: "text-muted-foreground", bgColor: "bg-white/5", urgent: false };
}

function formatDeadlineDisplay(deadline: string): string {
  return new Date(deadline).toLocaleDateString("ja-JP", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function getDefaultDeadline(): string {
  const d = new Date();
  d.setHours(d.getHours() + 1);
  d.setMinutes(Math.ceil(d.getMinutes() / 15) * 15, 0, 0);
  return d.toISOString().slice(0, 16);
}

// ---------- Component ----------

export default function GuestTodosPage() {
  const [todos, setTodos] = useState<Todo[]>([]);
  const [input, setInput] = useState("");
  const [filter, setFilter] = useState<"all" | "active" | "done">("all");
  const [showDeadlinePicker, setShowDeadlinePicker] = useState(false);
  const [deadlineValue, setDeadlineValue] = useState("");
  const [editingDeadline, setEditingDeadline] = useState<string | null>(null);
  const [swipedId, setSwipedId] = useState<string | null>(null);
  const [auth, setAuth] = useState(false);
  const [loading, setLoading] = useState(true);

  const [, setTick] = useState(0);
  useEffect(() => {
    const timer = setInterval(() => setTick((t) => t + 1), 60000);
    return () => clearInterval(timer);
  }, []);

  // Load data
  useEffect(() => {
    const authed = isAuthenticated();
    setAuth(authed);

    if (authed) {
      getTodos()
        .then((items) => setTodos(items.map(apiToLocal)))
        .catch(() => setTodos(loadLocalTodos()))
        .finally(() => setLoading(false));
    } else {
      setTodos(loadLocalTodos());
      setLoading(false);
    }
  }, []);

  const addTodo = useCallback(async () => {
    const text = input.trim();
    if (!text) return;

    const deadline =
      showDeadlinePicker && deadlineValue
        ? new Date(deadlineValue).toISOString()
        : null;

    if (auth) {
      try {
        const item = await apiCreateTodo({
          title: text,
          priority: 2,
          deadline: deadline || undefined,
        });
        setTodos((prev) => [apiToLocal(item), ...prev]);
      } catch {
        // fallback to local
      }
    } else {
      const newTodo: Todo = {
        id: Date.now().toString(),
        text,
        completed: false,
        priority: false,
        createdAt: new Date().toISOString(),
        deadline,
      };
      const updated = [newTodo, ...todos];
      setTodos(updated);
      saveLocalTodos(updated);
    }

    setInput("");
    setShowDeadlinePicker(false);
    setDeadlineValue("");
  }, [input, showDeadlinePicker, deadlineValue, auth, todos]);

  const toggleComplete = useCallback(async (id: string) => {
    const todo = todos.find((t) => t.id === id);
    if (!todo) return;

    if (auth && todo._apiId) {
      try {
        if (!todo.completed) {
          await apiCompleteTodo(todo._apiId);
        } else {
          await apiUpdateTodo(todo._apiId, { status: "pending" });
        }
      } catch {
        return;
      }
    }

    const updated = todos.map((t) =>
      t.id === id ? { ...t, completed: !t.completed } : t,
    );
    setTodos(updated);
    if (!auth) saveLocalTodos(updated);
  }, [todos, auth]);

  const togglePriority = useCallback(async (id: string) => {
    const todo = todos.find((t) => t.id === id);
    if (!todo) return;

    if (auth && todo._apiId) {
      try {
        await apiUpdateTodo(todo._apiId, { priority: todo.priority ? 2 : 3 });
      } catch {
        return;
      }
    }

    const updated = todos.map((t) =>
      t.id === id ? { ...t, priority: !t.priority } : t,
    );
    setTodos(updated);
    if (!auth) saveLocalTodos(updated);
  }, [todos, auth]);

  const deleteTodo = useCallback(async (id: string) => {
    const todo = todos.find((t) => t.id === id);
    if (auth && todo?._apiId) {
      try {
        await apiDeleteTodo(todo._apiId);
      } catch {
        return;
      }
    }

    const updated = todos.filter((t) => t.id !== id);
    setTodos(updated);
    if (!auth) saveLocalTodos(updated);
    setSwipedId(null);
  }, [todos, auth]);

  const updateDeadline = useCallback(async (id: string, deadline: string | null) => {
    const todo = todos.find((t) => t.id === id);
    if (auth && todo?._apiId) {
      try {
        await apiUpdateTodo(todo._apiId, { deadline });
      } catch {
        return;
      }
    }

    const updated = todos.map((t) => (t.id === id ? { ...t, deadline } : t));
    setTodos(updated);
    if (!auth) saveLocalTodos(updated);
    setEditingDeadline(null);
  }, [todos, auth]);

  const clearCompleted = useCallback(async () => {
    if (auth) {
      const completed = todos.filter((t) => t.completed && t._apiId);
      await Promise.allSettled(completed.map((t) => apiDeleteTodo(t._apiId!)));
    }
    const updated = todos.filter((t) => !t.completed);
    setTodos(updated);
    if (!auth) saveLocalTodos(updated);
  }, [todos, auth]);

  const filtered = useMemo(() => {
    return todos
      .filter((t) => {
        if (filter === "active") return !t.completed;
        if (filter === "done") return t.completed;
        return true;
      })
      .sort((a, b) => {
        if (a.priority !== b.priority) return a.priority ? -1 : 1;
        if (a.completed !== b.completed) return a.completed ? 1 : -1;
        if (a.deadline && b.deadline)
          return new Date(a.deadline).getTime() - new Date(b.deadline).getTime();
        if (a.deadline) return -1;
        if (b.deadline) return 1;
        return 0;
      });
  }, [todos, filter]);

  const activeCount = todos.filter((t) => !t.completed).length;
  const doneCount = todos.filter((t) => t.completed).length;
  const overdueCount = todos.filter(
    (t) => !t.completed && t.deadline && new Date(t.deadline) < new Date(),
  ).length;

  return (
    <div className="min-h-screen relative overflow-hidden pb-24">
      <div className="fixed inset-0 -z-10">
        <div className="absolute inset-0 bg-gradient-to-br from-[#0a0f1e] via-[#0f1729] to-[#0a0f1e]" />
        <div className="absolute top-20 right-10 w-72 h-72 rounded-full bg-indigo-600/8 blur-[100px]" />
        <div className="absolute bottom-40 left-10 w-80 h-80 rounded-full bg-purple-600/5 blur-[120px]" />
      </div>

      <div className="relative flex flex-col items-center px-4 pt-6">
        {/* Header */}
        <div className="w-full max-w-md mb-5 animate-fade-in-up">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold mb-1">TODO</h1>
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
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <span>{activeCount}件の未完了</span>
            <span>/</span>
            <span>{doneCount}件完了</span>
            {overdueCount > 0 && (
              <span className="flex items-center gap-1 text-red-400 font-medium">
                <AlertTriangle className="h-3 w-3" />
                {overdueCount}件期限切れ
              </span>
            )}
          </div>
        </div>

        {/* Input area */}
        <div className="w-full max-w-md mb-5 animate-fade-in-up" style={{ animationDelay: "50ms" }}>
          <div className="glass rounded-2xl p-3 space-y-2">
            <div className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && addTodo()}
                placeholder="新しいタスクを追加..."
                className="flex-1 h-11 px-4 rounded-xl bg-white/5 border border-white/10 text-sm placeholder:text-muted-foreground/50 focus:outline-none focus:border-indigo-500/30 transition-colors"
              />
              <button
                onClick={addTodo}
                disabled={!input.trim()}
                className="h-11 w-11 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 flex items-center justify-center hover:from-indigo-500 hover:to-purple-500 transition-all disabled:opacity-40 active:scale-95"
              >
                <Plus className="h-5 w-5" />
              </button>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => {
                  setShowDeadlinePicker(!showDeadlinePicker);
                  if (!showDeadlinePicker && !deadlineValue) setDeadlineValue(getDefaultDeadline());
                }}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  showDeadlinePicker
                    ? "bg-indigo-500/20 text-indigo-300 border border-indigo-500/20"
                    : "bg-white/5 text-muted-foreground hover:bg-white/10"
                }`}
              >
                <CalendarClock className="h-3.5 w-3.5" />
                期限設定
              </button>
              {showDeadlinePicker && (
                <div className="flex items-center gap-1.5 flex-1">
                  <input
                    type="datetime-local"
                    value={deadlineValue}
                    onChange={(e) => setDeadlineValue(e.target.value)}
                    className="flex-1 h-8 px-2 rounded-lg bg-white/5 border border-white/10 text-xs text-foreground focus:outline-none focus:border-indigo-500/30 [color-scheme:dark]"
                  />
                  <button onClick={() => { setShowDeadlinePicker(false); setDeadlineValue(""); }} className="p-1 rounded-md hover:bg-white/10 transition-colors">
                    <X className="h-3.5 w-3.5 text-muted-foreground" />
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Filter tabs */}
        <div className="w-full max-w-md mb-4 animate-fade-in-up" style={{ animationDelay: "100ms" }}>
          <div className="glass rounded-full p-1 flex gap-1 w-fit">
            {(["all", "active", "done"] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-4 py-1.5 rounded-full text-xs font-medium transition-all ${
                  filter === f ? "bg-white/10 text-foreground" : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {f === "all" ? "すべて" : f === "active" ? "未完了" : "完了"}
              </button>
            ))}
          </div>
        </div>

        {/* Loading */}
        {loading && (
          <div className="text-sm text-muted-foreground py-8">読み込み中...</div>
        )}

        {/* Todo list */}
        {!loading && (
          <div className="w-full max-w-md space-y-2 animate-fade-in-up" style={{ animationDelay: "150ms" }}>
            {filtered.length === 0 ? (
              <div className="text-center py-12">
                <CheckSquare className="h-12 w-12 text-muted-foreground/20 mx-auto mb-3" />
                <p className="text-sm text-muted-foreground">
                  {filter === "done" ? "完了したタスクはありません" : "タスクを追加しましょう"}
                </p>
              </div>
            ) : (
              filtered.map((todo) => {
                const dlStatus = getDeadlineStatus(todo.completed ? null : todo.deadline);
                const isSwiped = swipedId === todo.id;

                return (
                  <div key={todo.id} className="relative overflow-hidden rounded-xl">
                    <div className="absolute inset-y-0 right-0 w-20 bg-red-500/20 flex items-center justify-center rounded-r-xl">
                      <Trash2 className="h-5 w-5 text-red-400" />
                    </div>
                    <div
                      className={`relative glass rounded-xl px-4 py-3 transition-all duration-200 ${
                        todo.completed ? "opacity-50" : ""
                      } ${dlStatus.urgent && !todo.completed ? "border-l-2 border-l-red-400/50" : ""} ${
                        isSwiped ? "-translate-x-20" : "translate-x-0"
                      }`}
                      onClick={() => { if (isSwiped) deleteTodo(todo.id); }}
                      onTouchStart={(e) => {
                        const startX = e.touches[0].clientX;
                        const el = e.currentTarget;
                        const handleMove = (ev: TouchEvent) => {
                          const diff = startX - ev.touches[0].clientX;
                          if (diff > 60) setSwipedId(todo.id);
                          else if (diff < -20) setSwipedId(null);
                        };
                        const handleEnd = () => {
                          el.removeEventListener("touchmove", handleMove);
                          el.removeEventListener("touchend", handleEnd);
                        };
                        el.addEventListener("touchmove", handleMove);
                        el.addEventListener("touchend", handleEnd);
                      }}
                    >
                      <div className="flex items-start gap-3">
                        <button
                          onClick={(e) => { e.stopPropagation(); toggleComplete(todo.id); }}
                          className="flex-shrink-0 mt-0.5 transition-all active:scale-90"
                        >
                          {todo.completed ? (
                            <div className="w-6 h-6 rounded-full bg-emerald-500/20 flex items-center justify-center">
                              <Check className="h-3.5 w-3.5 text-emerald-400" />
                            </div>
                          ) : (
                            <Circle className="h-6 w-6 text-muted-foreground/40 hover:text-indigo-400 transition-colors" />
                          )}
                        </button>

                        <div className="flex-1 min-w-0">
                          <span className={`text-sm leading-snug ${todo.completed ? "line-through text-muted-foreground" : ""}`}>
                            {todo.text}
                          </span>

                          {todo.deadline && !todo.completed && (
                            <button
                              onClick={(e) => { e.stopPropagation(); setEditingDeadline(editingDeadline === todo.id ? null : todo.id); }}
                              className={`flex items-center gap-1 mt-1 px-2 py-0.5 rounded-md ${dlStatus.bgColor} transition-colors`}
                            >
                              <Clock className={`h-3 w-3 ${dlStatus.color}`} />
                              <span className={`text-[10px] font-medium ${dlStatus.color}`}>{dlStatus.label}</span>
                              <span className="text-[9px] text-muted-foreground ml-1">{formatDeadlineDisplay(todo.deadline)}</span>
                            </button>
                          )}

                          {todo.deadline && todo.completed && (
                            <span className="text-[10px] text-muted-foreground mt-0.5 block">
                              期限: {formatDeadlineDisplay(todo.deadline)}
                            </span>
                          )}

                          {editingDeadline === todo.id && (
                            <div className="flex items-center gap-1.5 mt-2 animate-fade-in-up">
                              <input
                                type="datetime-local"
                                defaultValue={
                                  todo.deadline
                                    ? new Date(new Date(todo.deadline).getTime() - new Date(todo.deadline).getTimezoneOffset() * 60000).toISOString().slice(0, 16)
                                    : getDefaultDeadline()
                                }
                                onChange={(e) => { if (e.target.value) updateDeadline(todo.id, new Date(e.target.value).toISOString()); }}
                                className="h-7 px-2 rounded-md bg-white/5 border border-white/10 text-[11px] text-foreground focus:outline-none focus:border-indigo-500/30 [color-scheme:dark]"
                                onClick={(e) => e.stopPropagation()}
                              />
                              <button
                                onClick={(e) => { e.stopPropagation(); updateDeadline(todo.id, null); }}
                                className="p-1 rounded-md hover:bg-red-500/10 transition-colors"
                              >
                                <X className="h-3.5 w-3.5 text-red-400" />
                              </button>
                            </div>
                          )}

                          {!todo.deadline && !todo.completed && editingDeadline !== todo.id && (
                            <button
                              onClick={(e) => { e.stopPropagation(); setEditingDeadline(todo.id); }}
                              className="flex items-center gap-1 mt-1 text-[10px] text-muted-foreground/50 hover:text-muted-foreground transition-colors"
                            >
                              <CalendarClock className="h-3 w-3" /> 期限を追加
                            </button>
                          )}

                          {!todo.deadline && editingDeadline === todo.id && (
                            <div className="flex items-center gap-1.5 mt-2 animate-fade-in-up">
                              <input
                                type="datetime-local"
                                defaultValue={getDefaultDeadline()}
                                onChange={(e) => { if (e.target.value) updateDeadline(todo.id, new Date(e.target.value).toISOString()); }}
                                className="h-7 px-2 rounded-md bg-white/5 border border-white/10 text-[11px] text-foreground focus:outline-none focus:border-indigo-500/30 [color-scheme:dark]"
                                onClick={(e) => e.stopPropagation()}
                              />
                              <button onClick={(e) => { e.stopPropagation(); setEditingDeadline(null); }} className="p-1 rounded-md hover:bg-white/10 transition-colors">
                                <X className="h-3.5 w-3.5 text-muted-foreground" />
                              </button>
                            </div>
                          )}
                        </div>

                        <button onClick={(e) => { e.stopPropagation(); togglePriority(todo.id); }} className="flex-shrink-0 transition-all active:scale-90">
                          <Star className={`h-4 w-4 transition-colors ${todo.priority ? "text-amber-400 fill-amber-400" : "text-muted-foreground/30 hover:text-amber-400/50"}`} />
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        )}

        {doneCount > 0 && (
          <button onClick={clearCompleted} className="mt-4 text-xs text-muted-foreground hover:text-red-400 transition-colors">
            完了済みを削除（{doneCount}件）
          </button>
        )}
      </div>

      <GuestBottomNav />
    </div>
  );
}
