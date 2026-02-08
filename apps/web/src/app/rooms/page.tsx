"use client";

import { useEffect, useState, useCallback } from "react";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import { getRooms, StudyRoom } from "@/lib/api";
import { useEventStream } from "@/hooks/useEventStream";
import LoadingSpinner from "@/components/LoadingSpinner";
import PageHeader from "@/components/PageHeader";
import RoomCard from "@/components/RoomCard";

export default function RoomsPage() {
  const authenticated = useAuthGuard();
  const [loading, setLoading] = useState(true);
  const [rooms, setRooms] = useState<StudyRoom[]>([]);
  const [error, setError] = useState<string | null>(null);

  const guildId = typeof window !== "undefined"
    ? localStorage.getItem("guild_id") || "0"
    : "0";

  const { on } = useEventStream({ guildId, enabled: authenticated });

  const fetchData = useCallback(async () => {
    try {
      const data = await getRooms(guildId);
      setRooms(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "データの取得に失敗しました");
    } finally {
      setLoading(false);
    }
  }, [guildId]);

  useEffect(() => {
    if (authenticated) fetchData();
  }, [authenticated, fetchData]);

  // Real-time member count updates
  useEffect(() => {
    if (!authenticated) return;
    const unsubJoin = on("room_join", () => fetchData());
    const unsubLeave = on("room_leave", () => fetchData());
    return () => {
      unsubJoin();
      unsubLeave();
    };
  }, [authenticated, on, fetchData]);

  if (!authenticated || loading) return <LoadingSpinner />;

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <PageHeader
        title="スタディキャンパス"
        description="仲間と一緒に学習しよう"
      />

      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-3 mb-4 text-destructive text-sm">
          {error}
          <button onClick={() => setError(null)} className="ml-2 underline">閉じる</button>
        </div>
      )}

      {rooms.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          ルームがありません。Discordで /room create を使ってルームを作成しよう！
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {rooms.map((room) => (
            <RoomCard key={room.id} room={room} guildId={guildId} />
          ))}
        </div>
      )}
    </div>
  );
}
