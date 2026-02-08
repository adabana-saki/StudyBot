"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CommunityHealth } from "@/lib/api";
import { cn } from "@/lib/utils";

interface CommunityHealthCardProps {
  health: CommunityHealth;
}

export default function CommunityHealthCard({ health }: CommunityHealthCardProps) {
  const getScoreColor = (score: number) => {
    if (score >= 70) return "text-green-400";
    if (score >= 40) return "text-yellow-400";
    return "text-red-400";
  };

  const getScoreBg = (score: number) => {
    if (score >= 70) return "border-green-500/50";
    if (score >= 40) return "border-yellow-500/50";
    return "border-red-500/50";
  };

  const stats = [
    { label: "DAU/MAU比率", value: `${(health.dau_mau_ratio * 100).toFixed(1)}%` },
    { label: "定着率", value: `${(health.retention_rate * 100).toFixed(1)}%` },
    { label: "平均ストリーク", value: `${health.avg_streak}日` },
    { label: "離脱率", value: `${(health.churn_rate * 100).toFixed(1)}%` },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">コミュニティ健全性</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-8">
          {/* Big Score Circle */}
          <div
            className={cn(
              "w-24 h-24 rounded-full border-4 flex items-center justify-center flex-shrink-0",
              getScoreBg(health.score)
            )}
          >
            <span className={cn("text-3xl font-bold", getScoreColor(health.score))}>
              {health.score}
            </span>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-2 gap-4 flex-1">
            {stats.map((stat) => (
              <div key={stat.label}>
                <div className="text-xs text-muted-foreground">{stat.label}</div>
                <div className="text-lg font-semibold">{stat.value}</div>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
