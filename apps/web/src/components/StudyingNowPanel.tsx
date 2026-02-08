"use client";

import type { ActiveStudier } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface StudyingNowPanelProps {
  studiers: ActiveStudier[];
}

export default function StudyingNowPanel({ studiers }: StudyingNowPanelProps) {
  if (studiers.length === 0) return null;

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500" />
          </span>
          今勉強中 ({studiers.length})
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {studiers.map((s) => (
          <div key={s.user_id} className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center text-sm font-bold">
              {s.username.charAt(0)}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{s.username}</p>
              {typeof s.event_data.topic === "string" && s.event_data.topic && (
                <p className="text-xs text-muted-foreground truncate">
                  {s.event_data.topic}
                </p>
              )}
            </div>
            <Badge variant="secondary" className="text-xs">
              {s.event_type === "focus_start" ? "フォーカス" : "学習中"}
            </Badge>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
