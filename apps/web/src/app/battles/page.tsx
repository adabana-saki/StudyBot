"use client";

import { useEffect, useState, useCallback } from "react";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import { getBattles, BattleResponse } from "@/lib/api";
import LoadingSpinner from "@/components/LoadingSpinner";
import PageHeader from "@/components/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import Link from "next/link";

export default function BattlesPage() {
  const authenticated = useAuthGuard();
  const [loading, setLoading] = useState(true);
  const [battles, setBattles] = useState<BattleResponse[]>([]);
  const [error, setError] = useState<string | null>(null);

  const guildId = typeof window !== "undefined"
    ? localStorage.getItem("guild_id") || "0"
    : "0";

  const fetchData = useCallback(async () => {
    try {
      const data = await getBattles(guildId);
      setBattles(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "データの取得に失敗しました");
    } finally {
      setLoading(false);
    }
  }, [guildId]);

  useEffect(() => {
    if (authenticated) fetchData();
  }, [authenticated, fetchData]);

  if (!authenticated || loading) return <LoadingSpinner />;

  const getDaysRemaining = (endDate: string) => {
    const end = new Date(endDate);
    const now = new Date();
    const diff = Math.ceil((end.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
    return Math.max(0, diff);
  };

  const goalLabels: Record<string, string> = {
    study_minutes: "学習時間",
    pomodoro: "ポモドーロ",
    tasks: "タスク",
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <PageHeader
        title="チームバトル"
        description="チーム対抗の学習バトルで競い合おう"
      />

      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-3 mb-4 text-destructive text-sm">
          {error}
          <button onClick={() => setError(null)} className="ml-2 underline">閉じる</button>
        </div>
      )}

      {battles.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          アクティブなバトルはありません。Discordで /battle challenge を使ってバトルを開始しよう！
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {battles.map((battle) => {
            const totalScore = battle.team_a.score + battle.team_b.score;
            const aPercent = totalScore > 0 ? (battle.team_a.score / totalScore) * 100 : 50;
            const daysLeft = getDaysRemaining(battle.end_date);

            return (
              <Link key={battle.id} href={`/battles/${battle.id}`}>
                <Card className="hover:border-primary/50 transition-colors cursor-pointer">
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-base">
                        {battle.team_a.name} vs {battle.team_b.name}
                      </CardTitle>
                      <Badge variant={battle.status === "active" ? "default" : "secondary"}>
                        {battle.status === "active" ? "進行中" : "承認待ち"}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="flex justify-between text-sm mb-2">
                      <span className="font-medium text-blue-400">
                        {battle.team_a.name}: {battle.team_a.score}
                      </span>
                      <span className="font-medium text-red-400">
                        {battle.team_b.name}: {battle.team_b.score}
                      </span>
                    </div>

                    <div className="relative h-3 rounded-full overflow-hidden bg-red-500/30">
                      <div
                        className="absolute left-0 top-0 h-full bg-blue-500 transition-all duration-500"
                        style={{ width: `${aPercent}%` }}
                      />
                    </div>

                    <div className="flex justify-between mt-2 text-xs text-muted-foreground">
                      <span>{goalLabels[battle.goal_type] || battle.goal_type}</span>
                      <span>残り {daysLeft}日</span>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
