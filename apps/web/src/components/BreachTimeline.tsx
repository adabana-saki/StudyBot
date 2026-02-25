"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { AppBreachEvent } from "@/lib/api";
import { AlertTriangle } from "lucide-react";

interface BreachTimelineProps {
  breaches: AppBreachEvent[];
}

function formatDuration(ms: number): string {
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) return `${seconds}秒`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return remainingSeconds > 0 ? `${minutes}分${remainingSeconds}秒` : `${minutes}分`;
}

function formatTime(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleString("ja-JP", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getSeverity(durationMs: number): { color: string; label: string } {
  if (durationMs < 5000) return { color: "bg-yellow-500/20 text-yellow-400", label: "軽微" };
  if (durationMs < 30000) return { color: "bg-orange-500/20 text-orange-400", label: "注意" };
  return { color: "bg-red-500/20 text-red-400", label: "重大" };
}

export default function BreachTimeline({ breaches }: BreachTimelineProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-orange-400" />
          ブリーチ履歴
        </CardTitle>
      </CardHeader>
      <CardContent>
        {breaches.length === 0 ? (
          <p className="text-center text-muted-foreground py-8">
            ブリーチ記録はありません
          </p>
        ) : (
          <div className="space-y-3">
            {breaches.map((breach) => {
              const severity = getSeverity(breach.breach_duration_ms);
              return (
                <div
                  key={breach.id}
                  className="flex items-center justify-between p-3 rounded-lg border"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-2 h-2 rounded-full bg-orange-400" />
                    <div>
                      <p className="font-medium text-sm">
                        {breach.app_name || breach.package_name}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {formatTime(breach.occurred_at)}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-mono">
                      {formatDuration(breach.breach_duration_ms)}
                    </span>
                    <Badge variant="secondary" className={severity.color}>
                      {severity.label}
                    </Badge>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
