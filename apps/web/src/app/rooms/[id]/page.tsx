"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import { useEventStream } from "@/hooks/useEventStream";
import {
  getRoomDetail,
  joinRoom,
  leaveRoom,
  RoomDetail,
} from "@/lib/api";
import LoadingSpinner from "@/components/LoadingSpinner";
import PageHeader from "@/components/PageHeader";
import RoomMemberGrid from "@/components/RoomMemberGrid";
import RoomTimer from "@/components/RoomTimer";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Users, Target, DoorOpen, DoorClosed } from "lucide-react";

const THEME_ICONS: Record<string, string> = {
  general: "\u{1F4DA}",
  math: "\u{1F4D0}",
  english: "\u{1F524}",
  science: "\u{1F52C}",
  programming: "\u{1F4BB}",
};

export default function RoomDetailPage() {
  const authenticated = useAuthGuard();
  const params = useParams();
  const roomId = Number(params.id);

  const [loading, setLoading] = useState(true);
  const [room, setRoom] = useState<RoomDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [joined, setJoined] = useState(false);
  const [topic, setTopic] = useState("");

  const guildId =
    typeof window !== "undefined"
      ? localStorage.getItem("guild_id") || "0"
      : "0";

  const { on } = useEventStream({ guildId, enabled: authenticated });

  const fetchData = useCallback(async () => {
    try {
      const data = await getRoomDetail(guildId, roomId);
      setRoom(data);

      // Check if current user is in the room
      const userId = typeof window !== "undefined"
        ? localStorage.getItem("user_id")
        : null;
      if (userId) {
        const inRoom = data.members.some(
          (m) => String(m.user_id) === userId
        );
        setJoined(inRoom);
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "データの取得に失敗しました"
      );
    } finally {
      setLoading(false);
    }
  }, [guildId, roomId]);

  useEffect(() => {
    if (authenticated && roomId) fetchData();
  }, [authenticated, roomId, fetchData]);

  // Real-time updates
  useEffect(() => {
    if (!authenticated) return;
    const unsubJoin = on("room_join", () => fetchData());
    const unsubLeave = on("room_leave", () => fetchData());
    const unsubGoal = on("room_goal_reached", () => fetchData());
    return () => {
      unsubJoin();
      unsubLeave();
      unsubGoal();
    };
  }, [authenticated, on, fetchData]);

  const handleJoin = async () => {
    setActionLoading(true);
    setError(null);
    try {
      await joinRoom(guildId, roomId, topic || undefined);
      setJoined(true);
      setTopic("");
      await fetchData();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "参加に失敗しました"
      );
    } finally {
      setActionLoading(false);
    }
  };

  const handleLeave = async () => {
    setActionLoading(true);
    setError(null);
    try {
      await leaveRoom(guildId, roomId);
      setJoined(false);
      await fetchData();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "退出に失敗しました"
      );
    } finally {
      setActionLoading(false);
    }
  };

  if (!authenticated || loading) return <LoadingSpinner />;
  if (!room) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8 text-center text-muted-foreground">
        ルームが見つかりません
      </div>
    );
  }

  const icon = THEME_ICONS[room.theme] || THEME_ICONS.general;
  const hasGoal = room.collective_goal_minutes > 0;
  const goalPercent = hasGoal
    ? Math.min(
        100,
        Math.round(
          (room.collective_progress_minutes / room.collective_goal_minutes) * 100
        )
      )
    : 0;
  const isFull = room.member_count >= room.max_occupants;

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <PageHeader
        title={`${icon} ${room.name}`}
        description={room.description}
        action={
          <Badge variant="secondary" className="text-sm">
            {room.theme}
          </Badge>
        }
      />

      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-3 mb-4 text-destructive text-sm">
          {error}
          <button onClick={() => setError(null)} className="ml-2 underline">
            閉じる
          </button>
        </div>
      )}

      {/* Stats Row */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <Card>
          <CardContent className="p-4 text-center">
            <Users className="h-5 w-5 mx-auto mb-1 text-muted-foreground" />
            <div className="text-2xl font-bold">
              {room.member_count}/{room.max_occupants}
            </div>
            <div className="text-xs text-muted-foreground">参加者</div>
          </CardContent>
        </Card>
        {hasGoal && (
          <Card>
            <CardContent className="p-4 text-center">
              <Target className="h-5 w-5 mx-auto mb-1 text-muted-foreground" />
              <div className="text-2xl font-bold">{goalPercent}%</div>
              <div className="text-xs text-muted-foreground">共同目標達成率</div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Collective Goal Progress */}
      {hasGoal && (
        <Card className="mb-6">
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <Target className="h-4 w-4" />
              共同目標
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex items-center justify-between text-sm text-muted-foreground">
              <span>{room.collective_progress_minutes}分</span>
              <span>{room.collective_goal_minutes}分</span>
            </div>
            <div className="h-3 bg-muted rounded-full overflow-hidden">
              <div
                className="h-full bg-primary rounded-full transition-all duration-700 ease-in-out"
                style={{ width: `${goalPercent}%` }}
              />
            </div>
            {goalPercent >= 100 && (
              <p className="text-sm text-center text-green-600 font-medium">
                目標達成！おめでとうございます！
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Join / Leave Action */}
      {!joined ? (
        <Card className="mb-6">
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <DoorOpen className="h-4 w-4" />
              ルームに参加
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <Input
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="学習トピック（任意）"
              />
            </div>
            <Button
              onClick={handleJoin}
              disabled={actionLoading || isFull}
              className="w-full"
            >
              {isFull ? "満室です" : "参加する"}
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="mb-6">
          <RoomTimer onLeave={handleLeave} />
        </div>
      )}

      {/* Members */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <DoorClosed className="h-4 w-4" />
            ルームメンバー ({room.members.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          <RoomMemberGrid members={room.members} />
        </CardContent>
      </Card>
    </div>
  );
}
