"use client";

import { useEffect, useState } from "react";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import LoadingSpinner from "@/components/LoadingSpinner";
import ErrorBanner from "@/components/ErrorBanner";
import Modal from "@/components/Modal";
import PageHeader from "@/components/PageHeader";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import {
  getTodos,
  createTodo,
  completeTodo,
  deleteTodo,
  TodoItem,
} from "@/lib/api";

const PRIORITY_LABELS: Record<number, { label: string; color: string }> = {
  1: { label: "低", color: "text-muted-foreground bg-secondary" },
  2: { label: "中", color: "text-yellow-400 bg-yellow-400/10" },
  3: { label: "高", color: "text-red-400 bg-red-400/10" },
};

/** タスク管理ページ - 作成・完了・削除・フィルター */
export default function TodosPage() {
  const authenticated = useAuthGuard();
  const [todos, setTodos] = useState<TodoItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>("");
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newPriority, setNewPriority] = useState(2);
  const [newDeadline, setNewDeadline] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (authenticated) fetchTodos();
  }, [authenticated]);

  useEffect(() => {
    if (!authenticated) return;
    getTodos(filter || undefined)
      .then(setTodos)
      .catch((err) =>
        setError(err instanceof Error ? err.message : "フィルター取得に失敗しました")
      );
  }, [filter, authenticated]);

  async function fetchTodos() {
    try {
      const data = await getTodos();
      setTodos(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "取得に失敗しました");
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate() {
    if (!newTitle.trim()) return;
    setCreating(true);
    try {
      const todo = await createTodo({
        title: newTitle.trim(),
        priority: newPriority,
        deadline: newDeadline || undefined,
      });
      setTodos((prev) => [todo, ...prev]);
      setShowCreateModal(false);
      setNewTitle("");
      setNewPriority(2);
      setNewDeadline("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "作成に失敗しました");
    } finally {
      setCreating(false);
    }
  }

  async function handleComplete(id: number) {
    try {
      const updated = await completeTodo(id);
      setTodos((prev) => prev.map((t) => (t.id === id ? updated : t)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "完了処理に失敗しました");
    }
  }

  async function handleDelete(id: number) {
    try {
      await deleteTodo(id);
      setTodos((prev) => prev.filter((t) => t.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "削除に失敗しました");
    }
  }

  if (loading) return <LoadingSpinner />;

  const pendingTodos = todos.filter((t) => t.status === "pending");
  const completedTodos = todos.filter((t) => t.status === "completed");

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Header */}
      <PageHeader
        title="タスク"
        action={
          <Button onClick={() => setShowCreateModal(true)} size="sm">
            + 新規タスク
          </Button>
        }
      />

      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}

      {/* Filter */}
      <div className="flex space-x-2 mb-6">
        {[
          { value: "", label: "すべて" },
          { value: "pending", label: "未完了" },
          { value: "completed", label: "完了済み" },
        ].map((f) => (
          <Button
            key={f.value}
            onClick={() => setFilter(f.value)}
            variant={filter === f.value ? "default" : "outline"}
            size="sm"
            className="rounded-full"
          >
            {f.label}
          </Button>
        ))}
      </div>

      {/* Pending Tasks */}
      {pendingTodos.length > 0 && (
        <div className="mb-8">
          <h2 className="text-lg font-semibold mb-3">
            未完了 ({pendingTodos.length})
          </h2>
          <div className="space-y-2">
            {pendingTodos.map((todo) => {
              const pri = PRIORITY_LABELS[todo.priority] || PRIORITY_LABELS[2];
              return (
                <Card key={todo.id} className="group">
                  <CardContent className="p-4 flex items-center justify-between">
                    <div className="flex items-center space-x-3 flex-1 min-w-0">
                      <button
                        onClick={() => handleComplete(todo.id)}
                        className="w-5 h-5 rounded border-2 border-muted-foreground hover:border-green-400 hover:bg-green-400/20 flex-shrink-0 transition-colors"
                      />
                      <div className="min-w-0">
                        <p className="truncate">{todo.title}</p>
                        <div className="flex items-center space-x-2 mt-1">
                          <Badge
                            variant="outline"
                            className={cn("border-transparent", pri.color)}
                          >
                            {pri.label}
                          </Badge>
                          {todo.deadline && (
                            <span className="text-xs text-muted-foreground">
                              期限: {new Date(todo.deadline).toLocaleDateString("ja-JP")}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleDelete(todo.id)}
                      className="text-muted-foreground hover:text-destructive opacity-0 group-hover:opacity-100 transition-all ml-2"
                    >
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </Button>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>
      )}

      {/* Completed Tasks */}
      {completedTodos.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-muted-foreground mb-3">
            完了済み ({completedTodos.length})
          </h2>
          <div className="space-y-2">
            {completedTodos.map((todo) => (
              <Card key={todo.id} className="opacity-60 group">
                <CardContent className="p-4 flex items-center justify-between">
                  <div className="flex items-center space-x-3 flex-1 min-w-0">
                    <div className="w-5 h-5 rounded bg-green-500 flex items-center justify-center flex-shrink-0">
                      <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                    <p className="text-muted-foreground line-through truncate">
                      {todo.title}
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handleDelete(todo.id)}
                    className="text-muted-foreground hover:text-destructive opacity-0 group-hover:opacity-100 transition-all ml-2"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {todos.length === 0 && (
        <div className="text-center py-16">
          <p className="text-muted-foreground mb-4">タスクがありません</p>
          <Button onClick={() => setShowCreateModal(true)} size="sm">
            最初のタスクを作成
          </Button>
        </div>
      )}

      {/* Create Modal */}
      <Modal isOpen={showCreateModal} title="新規タスク" maxWidth="max-w-md" onClose={() => setShowCreateModal(false)}>
            <div className="space-y-4">
              <div>
                <Label className="mb-1 block">
                  タイトル
                </Label>
                <Input
                  type="text"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  placeholder="タスクの内容..."
                  maxLength={200}
                  autoFocus
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="mb-1 block">
                    優先度
                  </Label>
                  <select
                    value={newPriority}
                    onChange={(e) => setNewPriority(Number(e.target.value))}
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                  >
                    <option value={1}>低</option>
                    <option value={2}>中</option>
                    <option value={3}>高</option>
                  </select>
                </div>
                <div>
                  <Label className="mb-1 block">
                    期限
                  </Label>
                  <Input
                    type="date"
                    value={newDeadline}
                    onChange={(e) => setNewDeadline(e.target.value)}
                  />
                </div>
              </div>
              <div className="flex space-x-3">
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={() => setShowCreateModal(false)}
                >
                  キャンセル
                </Button>
                <Button
                  className="flex-1"
                  onClick={handleCreate}
                  disabled={creating || !newTitle.trim()}
                >
                  {creating ? "作成中..." : "作成"}
                </Button>
              </div>
            </div>
      </Modal>
    </div>
  );
}
