"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import { getBattleDetail, BattleDetailResponse } from "@/lib/api";
import { useEventStream } from "@/hooks/useEventStream";
import LoadingSpinner from "@/components/LoadingSpinner";
import PageHeader from "@/components/PageHeader";
import BattleArena from "@/components/BattleArena";

export default function BattleDetailPage() {
  const authenticated = useAuthGuard();
  const params = useParams();
  const battleId = Number(params.id);
  const [loading, setLoading] = useState(true);
  const [battle, setBattle] = useState<BattleDetailResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const guildId = typeof window !== "undefined"
    ? localStorage.getItem("guild_id") || "0"
    : "0";

  const { on } = useEventStream({ guildId, enabled: authenticated });

  const fetchData = useCallback(async () => {
    try {
      const data = await getBattleDetail(guildId, battleId);
      setBattle(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "データの取得に失敗しました");
    } finally {
      setLoading(false);
    }
  }, [guildId, battleId]);

  useEffect(() => {
    if (authenticated) fetchData();
  }, [authenticated, fetchData]);

  // Real-time score updates
  useEffect(() => {
    if (!authenticated) return;
    const unsub = on("battle_score_update", (event) => {
      const data = event.data as { battle_id?: number; team_a_score?: number; team_b_score?: number };
      if (data.battle_id === battleId && battle) {
        setBattle((prev) =>
          prev
            ? {
                ...prev,
                team_a: { ...prev.team_a, score: data.team_a_score ?? prev.team_a.score },
                team_b: { ...prev.team_b, score: data.team_b_score ?? prev.team_b.score },
              }
            : prev
        );
      }
    });
    return unsub;
  }, [authenticated, on, battleId, battle]);

  if (!authenticated || loading) return <LoadingSpinner />;

  if (error || !battle) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="text-center text-destructive py-12">
          {error || "バトルが見つかりません"}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <PageHeader
        title={`${battle.team_a.name} vs ${battle.team_b.name}`}
        description={`${battle.start_date} - ${battle.end_date}`}
      />
      <BattleArena battle={battle} />
    </div>
  );
}
