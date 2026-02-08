"use client";

import { Achievement } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";

interface AchievementCardProps {
  achievement: Achievement;
  progress: number;
  unlocked: boolean;
}

export default function AchievementCard({
  achievement,
  progress,
  unlocked,
}: AchievementCardProps) {
  const progressPercent = Math.min(
    (progress / achievement.threshold) * 100,
    100
  );
  const isInProgress = !unlocked && progress > 0;

  return (
    <Card
      className={cn(
        "transition-all",
        unlocked
          ? "bg-yellow-900/20 border-yellow-600/50 shadow-lg shadow-yellow-900/10"
          : isInProgress
            ? "border-border"
            : "opacity-60"
      )}
    >
      <CardContent className="p-5">
        <div className="flex items-start space-x-3">
          <span
            className={cn("text-3xl", !unlocked && "grayscale")}
          >
            {achievement.emoji}
          </span>
          <div className="flex-1 min-w-0">
            <h3
              className={cn(
                "font-semibold text-sm",
                unlocked ? "text-yellow-400" : "text-card-foreground"
              )}
            >
              {achievement.name}
            </h3>
            <p className="text-xs text-muted-foreground mt-1">
              {achievement.description}
            </p>
          </div>
        </div>

        {/* Progress bar */}
        {!unlocked && (
          <div className="mt-3">
            <div className="flex justify-between text-xs text-muted-foreground mb-1">
              <span>
                {progress} / {achievement.threshold}
              </span>
              <span>{Math.round(progressPercent)}%</span>
            </div>
            <Progress
              value={progressPercent}
              className={cn("h-1.5", !isInProgress && "[&>div]:bg-muted-foreground/30")}
            />
          </div>
        )}

        {unlocked && (
          <div className="mt-3">
            <Badge className="bg-yellow-900/30 text-yellow-400 border-yellow-600/30 hover:bg-yellow-900/40">
              解除済み
            </Badge>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
