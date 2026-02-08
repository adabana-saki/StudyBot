"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

interface StudyHeatmapProps {
  data: Array<{ day: string; total_minutes: number }>;
}

export default function StudyHeatmap({ data }: StudyHeatmapProps) {
  const maxMinutes = Math.max(...data.map((d) => d.total_minutes), 1);

  function getColor(minutes: number): string {
    if (minutes === 0) return "bg-muted";
    const ratio = minutes / maxMinutes;
    if (ratio > 0.75) return "bg-green-500";
    if (ratio > 0.5) return "bg-green-400";
    if (ratio > 0.25) return "bg-green-300";
    return "bg-green-200";
  }

  // Fill to 90 days
  const today = new Date();
  const cells: Array<{ date: string; minutes: number }> = [];
  const dataMap = new Map(data.map((d) => [d.day, d.total_minutes]));
  for (let i = 89; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(d.getDate() - i);
    const key = d.toISOString().split("T")[0];
    cells.push({ date: key, minutes: dataMap.get(key) || 0 });
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">学習ヒートマップ（90日間）</CardTitle>
      </CardHeader>
      <CardContent>
        <TooltipProvider>
          <div className="flex flex-wrap gap-1">
            {cells.map((cell) => (
              <Tooltip key={cell.date}>
                <TooltipTrigger>
                  <div
                    className={`w-3 h-3 rounded-sm ${getColor(cell.minutes)}`}
                  />
                </TooltipTrigger>
                <TooltipContent>
                  <p className="text-xs">
                    {cell.date}: {cell.minutes}分
                  </p>
                </TooltipContent>
              </Tooltip>
            ))}
          </div>
        </TooltipProvider>
      </CardContent>
    </Card>
  );
}
