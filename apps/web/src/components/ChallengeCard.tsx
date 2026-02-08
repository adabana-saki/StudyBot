"use client";

import Link from "next/link";
import { Challenge } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Users, Calendar, Target } from "lucide-react";

function daysRemaining(endDate: string): number {
  const end = new Date(endDate);
  const now = new Date();
  const diff = end.getTime() - now.getTime();
  return Math.max(0, Math.ceil(diff / (1000 * 60 * 60 * 24)));
}

const STATUS_CONFIG: Record<string, { label: string; variant: "default" | "secondary" | "outline" }> = {
  active: { label: "進行中", variant: "default" },
  upcoming: { label: "予定", variant: "secondary" },
  completed: { label: "完了", variant: "outline" },
};

const GOAL_TYPE_LABELS: Record<string, string> = {
  study_minutes: "学習時間（分）",
  session_count: "セッション数",
  tasks_completed: "タスク完了数",
};

interface ChallengeCardProps {
  challenge: Challenge;
}

export default function ChallengeCard({ challenge }: ChallengeCardProps) {
  const remaining = daysRemaining(challenge.end_date);
  const statusConfig = STATUS_CONFIG[challenge.status] || STATUS_CONFIG.active;

  return (
    <Link href={`/challenges/${challenge.id}`}>
      <Card className="hover:shadow-md transition-shadow cursor-pointer h-full">
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between">
            <CardTitle className="text-lg leading-tight">
              {challenge.name}
            </CardTitle>
            <Badge variant={statusConfig.variant}>{statusConfig.label}</Badge>
          </div>
          {challenge.description && (
            <p className="text-sm text-muted-foreground line-clamp-2 mt-1">
              {challenge.description}
            </p>
          )}
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <span className="flex items-center gap-1">
              <Target className="h-4 w-4" />
              {challenge.goal_target} {GOAL_TYPE_LABELS[challenge.goal_type] || challenge.goal_type}
            </span>
          </div>
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <span className="flex items-center gap-1">
              <Users className="h-4 w-4" />
              {challenge.participant_count}人参加
            </span>
            <span className="flex items-center gap-1">
              <Calendar className="h-4 w-4" />
              {challenge.status === "active"
                ? `残り${remaining}日`
                : `${challenge.duration_days}日間`}
            </span>
          </div>
          {challenge.xp_multiplier > 1 && (
            <Badge variant="secondary" className="text-xs">
              XP {challenge.xp_multiplier}x ボーナス
            </Badge>
          )}
        </CardContent>
      </Card>
    </Link>
  );
}
