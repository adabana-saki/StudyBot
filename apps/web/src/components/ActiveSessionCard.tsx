"use client";

import { useEffect, useState } from "react";
import type { ActiveSession } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";

interface ActiveSessionCardProps {
  session: ActiveSession;
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}

export default function ActiveSessionCard({ session }: ActiveSessionCardProps) {
  const [remaining, setRemaining] = useState(session.remaining_seconds);

  useEffect(() => {
    const interval = setInterval(() => {
      setRemaining((prev) => Math.max(0, prev - 1));
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const totalSeconds = session.duration_minutes * 60;
  const elapsed = totalSeconds - remaining;
  const progress = (elapsed / totalSeconds) * 100;

  const typeLabels: Record<string, string> = {
    pomodoro: "🍅 ポモドーロ",
    focus: "🎯 フォーカス",
    study: "📖 学習",
  };

  return (
    <Card className="border-primary/30 bg-primary/5">
      <CardContent className="py-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500" />
            </span>
            <span className="font-medium text-sm">
              {typeLabels[session.session_type] || session.session_type}
            </span>
          </div>
          <Badge variant="outline" className="text-xs">
            {session.source_platform === "discord" ? "Discord" : "Web"}
          </Badge>
        </div>

        {session.topic && (
          <p className="text-sm text-muted-foreground mb-2">{session.topic}</p>
        )}

        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span>残り {formatTime(remaining)}</span>
            <span>{session.username}</span>
          </div>
          <Progress value={progress} className="h-2" />
        </div>
      </CardContent>
    </Card>
  );
}
