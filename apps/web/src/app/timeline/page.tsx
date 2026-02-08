"use client";

import { useEffect, useState, useCallback } from "react";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import { getTimeline, TimelineEvent, PaginatedResponse } from "@/lib/api";
import LoadingSpinner from "@/components/LoadingSpinner";
import PageHeader from "@/components/PageHeader";
import TimelineCard from "@/components/TimelineCard";
import { Button } from "@/components/ui/button";

export default function TimelinePage() {
  const authenticated = useAuthGuard();
  const [loading, setLoading] = useState(true);
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const guildId = typeof window !== "undefined"
    ? localStorage.getItem("guild_id") || "0"
    : "0";

  const fetchData = useCallback(async (off: number) => {
    try {
      setLoading(true);
      const data = await getTimeline(guildId, off, 30);
      if (off === 0) {
        setEvents(data.items);
      } else {
        setEvents((prev) => [...prev, ...data.items]);
      }
      setTotal(data.total);
      setOffset(off);
    } catch (err) {
      setError(err instanceof Error ? err.message : "データの取得に失敗しました");
    } finally {
      setLoading(false);
    }
  }, [guildId]);

  useEffect(() => {
    if (authenticated) fetchData(0);
  }, [authenticated, fetchData]);

  if (!authenticated) return <LoadingSpinner />;

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <PageHeader
        title="タイムライン"
        description="仲間のアクティビティに応援を送ろう"
      />

      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-3 mb-4 text-destructive text-sm">
          {error}
          <button onClick={() => setError(null)} className="ml-2 underline">閉じる</button>
        </div>
      )}

      {loading && events.length === 0 ? (
        <LoadingSpinner />
      ) : events.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          まだアクティビティがありません
        </div>
      ) : (
        <div className="space-y-4">
          {events.map((event) => (
            <TimelineCard key={event.id} event={event} />
          ))}

          {events.length < total && (
            <div className="text-center py-4">
              <Button
                variant="outline"
                onClick={() => fetchData(offset + 30)}
                disabled={loading}
              >
                {loading ? "読み込み中..." : "もっと見る"}
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
