"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { AppGuardSummary } from "@/lib/api";
import { Shield, AlertTriangle, Clock, Smartphone } from "lucide-react";

interface AppDisciplineScoreProps {
  summary: AppGuardSummary;
}

function formatDuration(ms: number): string {
  const minutes = Math.floor(ms / 60000);
  if (minutes < 60) return `${minutes}分`;
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return remainingMinutes > 0 ? `${hours}h${remainingMinutes}m` : `${hours}h`;
}

function getModeLabel(mode: string): { label: string; color: string } {
  switch (mode) {
    case "soft":
      return { label: "ソフトブロック", color: "text-yellow-400" };
    case "hard":
      return { label: "ハードブロック", color: "text-red-400" };
    default:
      return { label: "OFF", color: "text-muted-foreground" };
  }
}

export default function AppDisciplineScore({
  summary,
}: AppDisciplineScoreProps) {
  const mode = getModeLabel(summary.native_block_mode);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Shield className="w-5 h-5" />
          AppGuard サマリー
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-4">
          <div className="flex items-center gap-3 p-3 rounded-lg bg-muted/50">
            <Clock className="w-5 h-5 text-blue-400" />
            <div>
              <p className="text-xs text-muted-foreground">総使用時間</p>
              <p className="text-lg font-bold">
                {formatDuration(summary.total_usage_ms)}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3 p-3 rounded-lg bg-muted/50">
            <AlertTriangle className="w-5 h-5 text-orange-400" />
            <div>
              <p className="text-xs text-muted-foreground">ブリーチ</p>
              <p className="text-lg font-bold">
                {summary.breach_count}
                <span className="text-sm font-normal text-muted-foreground ml-1">回</span>
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3 p-3 rounded-lg bg-muted/50">
            <Smartphone className="w-5 h-5 text-purple-400" />
            <div>
              <p className="text-xs text-muted-foreground">ブロックアプリ</p>
              <p className="text-lg font-bold">
                {summary.blocked_app_count}
                <span className="text-sm font-normal text-muted-foreground ml-1">個</span>
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3 p-3 rounded-lg bg-muted/50">
            <Shield className="w-5 h-5 text-green-400" />
            <div>
              <p className="text-xs text-muted-foreground">ブロックモード</p>
              <p className={`text-lg font-bold ${mode.color}`}>{mode.label}</p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
