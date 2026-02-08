"use client";

import Link from "next/link";
import { StudyRoom } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Users } from "lucide-react";
import { cn } from "@/lib/utils";

const THEME_ICONS: Record<string, string> = {
  general: "\u{1F4DA}",
  math: "\u{1F4D0}",
  english: "\u{1F524}",
  science: "\u{1F52C}",
  programming: "\u{1F4BB}",
};

const THEME_COLORS: Record<string, string> = {
  general: "border-l-blue-500",
  math: "border-l-amber-500",
  english: "border-l-green-500",
  science: "border-l-purple-500",
  programming: "border-l-cyan-500",
};

const THEME_BADGE_COLORS: Record<string, string> = {
  general: "bg-blue-500/10 text-blue-600",
  math: "bg-amber-500/10 text-amber-600",
  english: "bg-green-500/10 text-green-600",
  science: "bg-purple-500/10 text-purple-600",
  programming: "bg-cyan-500/10 text-cyan-600",
};

interface RoomCardProps {
  room: StudyRoom;
  guildId: string;
}

export default function RoomCard({ room, guildId }: RoomCardProps) {
  const icon = THEME_ICONS[room.theme] || THEME_ICONS.general;
  const borderColor = THEME_COLORS[room.theme] || THEME_COLORS.general;
  const badgeColor = THEME_BADGE_COLORS[room.theme] || THEME_BADGE_COLORS.general;

  const isFull = room.member_count >= room.max_occupants;
  const hasGoal = room.collective_goal_minutes > 0;
  const goalPercent = hasGoal
    ? Math.min(100, Math.round((room.collective_progress_minutes / room.collective_goal_minutes) * 100))
    : 0;

  return (
    <Link href={`/rooms/${room.id}`}>
      <Card
        className={cn(
          "border-l-4 hover:shadow-md transition-shadow cursor-pointer h-full",
          borderColor
        )}
      >
        <CardContent className="p-4 space-y-3">
          {/* Header: icon + name + theme badge */}
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-2 min-w-0">
              <span className="text-xl flex-shrink-0">{icon}</span>
              <h3 className="font-semibold text-base truncate">{room.name}</h3>
            </div>
            <Badge variant="secondary" className={cn("text-xs flex-shrink-0", badgeColor)}>
              {room.theme}
            </Badge>
          </div>

          {/* Description */}
          {room.description && (
            <p className="text-sm text-muted-foreground line-clamp-2">
              {room.description}
            </p>
          )}

          {/* Member count */}
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-sm text-muted-foreground">
              <Users className="h-4 w-4" />
              <span>
                {room.member_count}/{room.max_occupants}
              </span>
            </span>
            {isFull && (
              <Badge variant="destructive" className="text-xs">
                満室
              </Badge>
            )}
            {room.state === "active" && !isFull && room.member_count > 0 && (
              <Badge variant="default" className="text-xs">
                学習中
              </Badge>
            )}
          </div>

          {/* Collective goal progress bar */}
          {hasGoal && (
            <div className="space-y-1">
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>共同目標</span>
                <span>
                  {room.collective_progress_minutes}/{room.collective_goal_minutes}分 ({goalPercent}%)
                </span>
              </div>
              <div className="h-2 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary rounded-full transition-all duration-500"
                  style={{ width: `${goalPercent}%` }}
                />
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </Link>
  );
}
