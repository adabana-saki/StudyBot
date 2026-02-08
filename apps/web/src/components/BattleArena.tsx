"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { BattleDetailResponse } from "@/lib/api";
import ContributionChart from "@/components/ContributionChart";

interface BattleArenaProps {
  battle: BattleDetailResponse;
}

export default function BattleArena({ battle }: BattleArenaProps) {
  const totalScore = battle.team_a.score + battle.team_b.score;
  const aPercent = totalScore > 0 ? (battle.team_a.score / totalScore) * 100 : 50;

  const statusLabels: Record<string, string> = {
    pending: "承認待ち",
    active: "進行中",
    completed: "完了",
  };

  const goalLabels: Record<string, string> = {
    study_minutes: "学習時間（分）",
    pomodoro: "ポモドーロ回数",
    tasks: "タスク完了数",
  };

  const daysRemaining = () => {
    const end = new Date(battle.end_date);
    const now = new Date();
    return Math.max(0, Math.ceil((end.getTime() - now.getTime()) / (1000 * 60 * 60 * 24)));
  };

  return (
    <div className="space-y-6">
      {/* Score Header */}
      <Card>
        <CardContent className="py-6">
          <div className="flex items-center justify-between mb-4">
            <Badge variant={battle.status === "active" ? "default" : "secondary"}>
              {statusLabels[battle.status] || battle.status}
            </Badge>
            <span className="text-sm text-muted-foreground">
              {goalLabels[battle.goal_type] || battle.goal_type} | 残り {daysRemaining()}日
            </span>
          </div>

          <div className="flex items-center justify-between mb-3">
            <div className="text-center">
              <div className="text-3xl font-bold text-blue-400">{battle.team_a.score}</div>
              <div className="text-sm font-medium mt-1">{battle.team_a.name}</div>
              <div className="text-xs text-muted-foreground">{battle.team_a.member_count}人</div>
            </div>
            <div className="text-2xl font-bold text-muted-foreground">VS</div>
            <div className="text-center">
              <div className="text-3xl font-bold text-red-400">{battle.team_b.score}</div>
              <div className="text-sm font-medium mt-1">{battle.team_b.name}</div>
              <div className="text-xs text-muted-foreground">{battle.team_b.member_count}人</div>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="relative h-4 rounded-full overflow-hidden bg-red-500/30">
            <div
              className="absolute left-0 top-0 h-full bg-blue-500 transition-all duration-700 ease-in-out"
              style={{ width: `${aPercent}%` }}
            />
          </div>
        </CardContent>
      </Card>

      {/* Contributions */}
      {battle.contributions.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">貢献度ランキング</CardTitle>
          </CardHeader>
          <CardContent>
            <ContributionChart
              contributions={battle.contributions}
              teamAId={battle.team_a.team_id}
              teamBId={battle.team_b.team_id}
            />
          </CardContent>
        </Card>
      )}
    </div>
  );
}
