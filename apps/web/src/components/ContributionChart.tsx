"use client";

import { BattleContribution } from "@/lib/api";
import { cn } from "@/lib/utils";

interface ContributionChartProps {
  contributions: BattleContribution[];
  teamAId: number;
  teamBId: number;
}

export default function ContributionChart({
  contributions,
  teamAId,
  teamBId,
}: ContributionChartProps) {
  const maxContribution = Math.max(...contributions.map((c) => c.contribution), 1);

  return (
    <div className="space-y-2">
      {contributions.map((contrib, i) => {
        const isTeamA = contrib.team_id === teamAId;
        const width = (contrib.contribution / maxContribution) * 100;

        return (
          <div key={`${contrib.user_id}-${contrib.source}-${i}`} className="flex items-center gap-3">
            <span className="text-sm w-24 truncate">{contrib.username}</span>
            <div className="flex-1 h-6 bg-muted rounded-md overflow-hidden relative">
              <div
                className={cn(
                  "h-full rounded-md transition-all duration-500",
                  isTeamA ? "bg-blue-500/70" : "bg-red-500/70"
                )}
                style={{ width: `${width}%` }}
              />
              <span className="absolute right-2 top-0 h-full flex items-center text-xs font-medium">
                {contrib.contribution}
              </span>
            </div>
            <span className="text-xs text-muted-foreground w-12 text-right">
              {contrib.source}
            </span>
          </div>
        );
      })}
    </div>
  );
}
