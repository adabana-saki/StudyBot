"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { isAuthenticated } from "@/lib/auth";
import { getActivityFeed, getStudyingNow, ActivityEvent, ActiveStudier } from "@/lib/api";
import { useEventStream } from "@/hooks/useEventStream";
import ActivityFeed from "@/components/ActivityFeed";
import StudyingNowPanel from "@/components/StudyingNowPanel";
import LoadingSpinner from "@/components/LoadingSpinner";
import PageHeader from "@/components/PageHeader";

export default function ActivityPage() {
  const router = useRouter();
  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [studiers, setStudiers] = useState<ActiveStudier[]>([]);
  const [loading, setLoading] = useState(true);
  const [guildId] = useState<string>("0");

  const { on } = useEventStream({ guildId, enabled: !!guildId });

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/");
      return;
    }

    async function fetchData() {
      try {
        const [feedData, studyingData] = await Promise.all([
          getActivityFeed(guildId),
          getStudyingNow(guildId),
        ]);
        setEvents(feedData);
        setStudiers(studyingData);
      } catch {
        // ignore errors
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [router, guildId]);

  // Real-time updates via SSE
  useEffect(() => {
    const unsub = on("*", (event) => {
      const d = event.data as Record<string, unknown>;
      const newActivity: ActivityEvent = {
        id: Date.now(),
        user_id: (d.user_id as number) || 0,
        username: (d.username as string) || "",
        event_type: event.type,
        event_data: d,
        created_at: event.timestamp,
      };
      setEvents((prev) => [newActivity, ...prev].slice(0, 100));
    });
    return unsub;
  }, [on]);

  if (loading) return <LoadingSpinner label="読み込み中..." />;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <PageHeader title="アクティビティ" description="サーバーのリアルタイムアクティビティ" />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
        <div className="lg:col-span-2">
          <ActivityFeed events={events} />
        </div>
        <div>
          <StudyingNowPanel studiers={studiers} />
        </div>
      </div>
    </div>
  );
}
