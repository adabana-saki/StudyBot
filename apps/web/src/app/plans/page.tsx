"use client";

import { useEffect, useState } from "react";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import LoadingSpinner from "@/components/LoadingSpinner";
import ErrorBanner from "@/components/ErrorBanner";
import PageHeader from "@/components/PageHeader";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";
import {
  getPlans,
  getPlanDetail,
  StudyPlanItem,
  StudyPlanDetail,
} from "@/lib/api";

const STATUS_BADGE_STYLES: Record<string, string> = {
  active: "text-green-400 bg-green-400/10 border-transparent",
  completed: "text-blue-400 bg-blue-400/10 border-transparent",
  paused: "text-yellow-400 bg-yellow-400/10 border-transparent",
  cancelled: "text-muted-foreground bg-secondary border-transparent",
};

const STATUS_LABELS: Record<string, string> = {
  active: "進行中",
  completed: "完了",
  paused: "一時停止",
  cancelled: "キャンセル",
};

/** 学習プランページ - プラン一覧・進捗・タスクチェックリスト */
export default function PlansPage() {
  const authenticated = useAuthGuard();
  const [plans, setPlans] = useState<StudyPlanItem[]>([]);
  const [selectedPlan, setSelectedPlan] = useState<StudyPlanDetail | null>(
    null
  );
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (authenticated) fetchPlans();
  }, [authenticated]);

  async function fetchPlans() {
    try {
      const data = await getPlans();
      setPlans(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "取得に失敗しました");
    } finally {
      setLoading(false);
    }
  }

  async function handleSelectPlan(id: number) {
    if (selectedPlan?.id === id) {
      setSelectedPlan(null);
      return;
    }
    setDetailLoading(true);
    try {
      const detail = await getPlanDetail(id);
      setSelectedPlan(detail);
    } catch (err) {
      setError(err instanceof Error ? err.message : "詳細取得に失敗しました");
    } finally {
      setDetailLoading(false);
    }
  }

  function getProgress(plan: StudyPlanDetail): number {
    if (!plan.tasks.length) return 0;
    const completed = plan.tasks.filter(
      (t) => t.status === "completed"
    ).length;
    return Math.round((completed / plan.tasks.length) * 100);
  }

  if (loading) return <LoadingSpinner />;

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <PageHeader title="学習プラン" />

      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}

      {plans.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-muted-foreground">
            学習プランがありません。Discordで /plan create
            コマンドを使ってプランを作成できます。
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {plans.map((plan) => {
            const isSelected = selectedPlan?.id === plan.id;
            const statusBadgeStyle =
              STATUS_BADGE_STYLES[plan.status] || STATUS_BADGE_STYLES.active;
            const statusLabel =
              STATUS_LABELS[plan.status] || plan.status;
            return (
              <div key={plan.id}>
                {/* Plan Card */}
                <Card
                  className={cn(
                    "cursor-pointer transition-colors",
                    isSelected ? "border-primary" : "hover:border-accent"
                  )}
                  onClick={() => handleSelectPlan(plan.id)}
                >
                  <CardContent className="p-5">
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2 mb-1">
                          <h3 className="font-semibold truncate">
                            {plan.subject}
                          </h3>
                          <Badge
                            variant="outline"
                            className={statusBadgeStyle}
                          >
                            {statusLabel}
                          </Badge>
                        </div>
                        <p className="text-muted-foreground text-sm truncate">
                          {plan.goal}
                        </p>
                        {plan.deadline && (
                          <p className="text-muted-foreground text-xs mt-1">
                            期限:{" "}
                            {new Date(plan.deadline).toLocaleDateString("ja-JP")}
                          </p>
                        )}
                      </div>
                      <svg
                        className={cn(
                          "w-5 h-5 text-muted-foreground flex-shrink-0 ml-2 transition-transform",
                          isSelected && "rotate-180"
                        )}
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M19 9l-7 7-7-7"
                        />
                      </svg>
                    </div>

                    {/* Progress Bar (visible when detail loaded) */}
                    {isSelected && selectedPlan && (
                      <div className="mt-3">
                        <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
                          <span>進捗</span>
                          <span>{getProgress(selectedPlan)}%</span>
                        </div>
                        <Progress value={getProgress(selectedPlan)} className="h-2" />
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Plan Detail */}
                {isSelected && (
                  <Card className="mt-2 opacity-90">
                    <CardContent className="p-5">
                      {detailLoading ? (
                        <div className="flex justify-center py-4">
                          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary"></div>
                        </div>
                      ) : selectedPlan ? (
                        <>
                          {selectedPlan.ai_feedback && (
                            <div className="bg-primary/10 border border-primary/30 rounded-lg p-3 mb-4">
                              <p className="text-sm">
                                <span className="text-primary font-medium">
                                  AI フィードバック:
                                </span>{" "}
                                {selectedPlan.ai_feedback}
                              </p>
                            </div>
                          )}

                          <h4 className="font-medium mb-3">
                            タスク ({selectedPlan.tasks.length})
                          </h4>
                          <div className="space-y-2">
                            {selectedPlan.tasks
                              .sort((a, b) => a.order_index - b.order_index)
                              .map((task) => {
                                const isCompleted = task.status === "completed";
                                return (
                                  <div
                                    key={task.id}
                                    className={cn(
                                      "flex items-start space-x-3 p-3 rounded-lg",
                                      isCompleted
                                        ? "bg-secondary/30"
                                        : "bg-secondary/50"
                                    )}
                                  >
                                    <div
                                      className={cn(
                                        "w-5 h-5 rounded flex-shrink-0 mt-0.5 flex items-center justify-center",
                                        isCompleted
                                          ? "bg-green-500"
                                          : "border-2 border-muted-foreground"
                                      )}
                                    >
                                      {isCompleted && (
                                        <svg
                                          className="w-3 h-3 text-white"
                                          fill="none"
                                          viewBox="0 0 24 24"
                                          stroke="currentColor"
                                        >
                                          <path
                                            strokeLinecap="round"
                                            strokeLinejoin="round"
                                            strokeWidth={3}
                                            d="M5 13l4 4L19 7"
                                          />
                                        </svg>
                                      )}
                                    </div>
                                    <div className="min-w-0">
                                      <p
                                        className={cn(
                                          isCompleted
                                            ? "text-muted-foreground line-through"
                                            : ""
                                        )}
                                      >
                                        {task.title}
                                      </p>
                                      {task.description && (
                                        <p className="text-muted-foreground text-sm mt-0.5">
                                          {task.description}
                                        </p>
                                      )}
                                    </div>
                                  </div>
                                );
                              })}
                          </div>
                        </>
                      ) : null}
                    </CardContent>
                  </Card>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
