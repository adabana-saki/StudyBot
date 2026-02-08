"use client";

import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { TimelineEvent } from "@/lib/api";
import { EVENT_LABELS } from "@/lib/events";
import ReactionBar from "@/components/ReactionBar";
import CommentThread from "@/components/CommentThread";
import { cn } from "@/lib/utils";

interface TimelineCardProps {
  event: TimelineEvent;
}

export default function TimelineCard({ event }: TimelineCardProps) {
  const [showComments, setShowComments] = useState(false);
  const [reactionCounts, setReactionCounts] = useState(event.reaction_counts);
  const [myReactions, setMyReactions] = useState(event.my_reactions);
  const [commentCount, setCommentCount] = useState(event.comment_count);

  const label = EVENT_LABELS[event.event_type] || {
    label: event.event_type,
    icon: "📌",
    color: "text-gray-400",
  };

  const timeAgo = (dateStr: string) => {
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "たった今";
    if (mins < 60) return `${mins}分前`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}時間前`;
    const days = Math.floor(hours / 24);
    return `${days}日前`;
  };

  const getEventDescription = () => {
    const data = event.event_data;
    switch (event.event_type) {
      case "study_end":
        return `${data.duration_minutes || 0}分間の学習を完了`;
      case "pomodoro_complete":
        return `ポモドーロ${data.work_minutes || 25}分を完了`;
      case "study_log":
        return `${data.topic || "学習"}を${data.duration_minutes || 0}分間記録`;
      case "level_up":
        return `レベル${data.new_level || "?"}に到達！`;
      case "achievement_unlock":
        return `実績「${data.achievement_name || ""}」${data.achievement_emoji || ""} を解除！`;
      case "todo_complete":
        return `タスク「${data.title || ""}」を完了`;
      case "raid_complete":
        return `レイド「${data.raid_topic || ""}」を完了`;
      default:
        return label.label;
    }
  };

  const handleReactionChange = (
    newCounts: Record<string, number>,
    newMyReactions: string[]
  ) => {
    setReactionCounts(newCounts);
    setMyReactions(newMyReactions);
  };

  return (
    <Card>
      <CardContent className="pt-4 pb-3">
        <div className="flex items-start gap-3">
          <div className="text-2xl">{label.icon}</div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="font-medium text-sm">{event.username}</span>
              <Badge variant="outline" className={cn("text-xs", label.color)}>
                {label.label}
              </Badge>
              <span className="text-xs text-muted-foreground ml-auto">
                {timeAgo(event.created_at)}
              </span>
            </div>
            <p className="text-sm text-muted-foreground">{getEventDescription()}</p>

            <div className="mt-3">
              <ReactionBar
                eventId={event.id}
                reactionCounts={reactionCounts}
                myReactions={myReactions}
                onReactionChange={handleReactionChange}
              />
            </div>

            <button
              onClick={() => setShowComments(!showComments)}
              className="mt-2 text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              💬 コメント {commentCount > 0 ? `(${commentCount})` : ""}
            </button>

            {showComments && (
              <div className="mt-2">
                <CommentThread
                  eventId={event.id}
                  onCommentCountChange={setCommentCount}
                />
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
