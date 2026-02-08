"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { OptimalTime } from "@/lib/api";
import { cn } from "@/lib/utils";

interface ActivityHeatmapProps {
  data: OptimalTime[];
}

const DAY_LABELS = ["日", "月", "火", "水", "木", "金", "土"];

export default function ActivityHeatmap({ data }: ActivityHeatmapProps) {
  // Build 7x24 grid
  const grid: Record<string, number> = {};
  let maxCount = 1;
  for (const d of data) {
    const key = `${d.day_of_week}-${d.hour}`;
    grid[key] = d.session_count;
    if (d.session_count > maxCount) maxCount = d.session_count;
  }

  const getIntensity = (count: number) => {
    if (count === 0) return "bg-muted";
    const ratio = count / maxCount;
    if (ratio > 0.75) return "bg-green-500";
    if (ratio > 0.5) return "bg-green-400/70";
    if (ratio > 0.25) return "bg-green-300/50";
    return "bg-green-200/30";
  };

  // Show only hours 6-24 for readability
  const hours = Array.from({ length: 18 }, (_, i) => i + 6);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">学習パターン（曜日×時間帯）</CardTitle>
      </CardHeader>
      <CardContent>
        {data.length === 0 ? (
          <p className="text-sm text-muted-foreground">データがありません</p>
        ) : (
          <div className="overflow-x-auto">
            <div className="min-w-[500px]">
              {/* Header */}
              <div className="flex gap-0.5 mb-1 ml-8">
                {hours.map((h) => (
                  <div key={h} className="flex-1 text-center text-xs text-muted-foreground">
                    {h % 3 === 0 ? `${h}` : ""}
                  </div>
                ))}
              </div>

              {/* Rows */}
              {DAY_LABELS.map((label, day) => (
                <div key={day} className="flex gap-0.5 mb-0.5 items-center">
                  <div className="w-7 text-xs text-muted-foreground text-right pr-1">{label}</div>
                  {hours.map((hour) => {
                    const count = grid[`${day}-${hour}`] || 0;
                    return (
                      <div
                        key={`${day}-${hour}`}
                        className={cn(
                          "flex-1 aspect-square rounded-sm",
                          getIntensity(count)
                        )}
                        title={`${label} ${hour}時: ${count}セッション`}
                      />
                    );
                  })}
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
