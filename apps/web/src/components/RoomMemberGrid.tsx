"use client";

import { useEffect, useState } from "react";
import { RoomMember } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const PLATFORM_STYLES: Record<string, { label: string; className: string }> = {
  discord: { label: "Discord", className: "bg-purple-500/10 text-purple-600" },
  web: { label: "Web", className: "bg-blue-500/10 text-blue-600" },
};

function formatElapsed(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;

  if (h > 0) {
    return `${h}h ${m}m`;
  }
  return `${m}m ${s}s`;
}

function ElapsedTime({ joinedAt }: { joinedAt: string }) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const joinedTime = new Date(joinedAt).getTime();

    function update() {
      const now = Date.now();
      setElapsed(Math.max(0, Math.floor((now - joinedTime) / 1000)));
    }

    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, [joinedAt]);

  return (
    <span className="text-xs font-mono text-muted-foreground">
      {formatElapsed(elapsed)}
    </span>
  );
}

interface RoomMemberGridProps {
  members: RoomMember[];
}

export default function RoomMemberGrid({ members }: RoomMemberGridProps) {
  if (members.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground text-sm">
        まだ誰もいません。最初の参加者になろう！
      </div>
    );
  }

  return (
    <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {members.map((member) => {
        const platform = PLATFORM_STYLES[member.platform] || PLATFORM_STYLES.web;

        return (
          <Card key={member.user_id} className="overflow-hidden">
            <CardContent className="p-4 space-y-2">
              {/* Username + platform */}
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium text-sm truncate">
                  {member.username}
                </span>
                <Badge variant="secondary" className={platform.className}>
                  {platform.label}
                </Badge>
              </div>

              {/* Topic */}
              {member.topic && (
                <p className="text-xs text-muted-foreground truncate">
                  {member.topic}
                </p>
              )}

              {/* Elapsed time */}
              <div className="flex items-center gap-1.5">
                <span className="text-xs text-muted-foreground">経過:</span>
                <ElapsedTime joinedAt={member.joined_at} />
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
