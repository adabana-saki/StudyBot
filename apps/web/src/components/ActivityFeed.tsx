"use client";

import { EVENT_LABELS } from "@/lib/events";
import type { ActivityEvent } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";

interface ActivityFeedProps {
  events: ActivityEvent[];
}

function formatTimeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "たった今";
  if (minutes < 60) return `${minutes}分前`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}時間前`;
  return `${Math.floor(hours / 24)}日前`;
}

export default function ActivityFeed({ events }: ActivityFeedProps) {
  return (
    <div className="space-y-2">
      {events.map((event) => {
        const meta = EVENT_LABELS[event.event_type] || {
          label: event.event_type,
          icon: "📌",
          color: "text-gray-400",
        };
        return (
          <Card key={event.id} className="border-l-4 border-l-primary/30">
            <CardContent className="py-3 px-4 flex items-center gap-3">
              <span className="text-xl">{meta.icon}</span>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">
                  <span className="font-semibold">{event.username}</span>{" "}
                  <span className={meta.color}>{meta.label}</span>
                </p>
                {typeof event.event_data.topic === "string" && event.event_data.topic && (
                  <p className="text-xs text-muted-foreground truncate">
                    {event.event_data.topic}
                  </p>
                )}
              </div>
              <span className="text-xs text-muted-foreground whitespace-nowrap">
                {formatTimeAgo(event.created_at)}
              </span>
            </CardContent>
          </Card>
        );
      })}
      {events.length === 0 && (
        <p className="text-center text-muted-foreground py-8">
          まだアクティビティがありません
        </p>
      )}
    </div>
  );
}
