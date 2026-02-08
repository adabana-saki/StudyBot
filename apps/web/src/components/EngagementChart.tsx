"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EngagementData } from "@/lib/api";

interface EngagementChartProps {
  data: EngagementData[];
}

export default function EngagementChart({ data }: EngagementChartProps) {
  if (data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">エンゲージメント推移</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">データがありません</p>
        </CardContent>
      </Card>
    );
  }

  const maxMinutes = Math.max(...data.map((d) => d.total_minutes), 1);
  const maxUsers = Math.max(...data.map((d) => d.active_users), 1);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">エンゲージメント推移（30日間）</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-end gap-1 h-40">
          {data.map((d, i) => {
            const heightMinutes = (d.total_minutes / maxMinutes) * 100;
            const heightUsers = (d.active_users / maxUsers) * 100;

            return (
              <div key={d.date} className="flex-1 flex flex-col items-center gap-0.5" title={`${d.date}\n学習: ${d.total_minutes}分\nユーザー: ${d.active_users}人`}>
                <div className="w-full flex items-end gap-0.5" style={{ height: "100%" }}>
                  <div
                    className="flex-1 bg-blue-500/60 rounded-t-sm transition-all"
                    style={{ height: `${heightMinutes}%`, minHeight: d.total_minutes > 0 ? "2px" : "0" }}
                  />
                  <div
                    className="flex-1 bg-green-500/60 rounded-t-sm transition-all"
                    style={{ height: `${heightUsers}%`, minHeight: d.active_users > 0 ? "2px" : "0" }}
                  />
                </div>
              </div>
            );
          })}
        </div>

        <div className="flex items-center gap-4 mt-3 text-xs text-muted-foreground">
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded-sm bg-blue-500/60" />
            <span>学習時間</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded-sm bg-green-500/60" />
            <span>アクティブユーザー</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
