"use client";

import { useEffect, useState, useCallback } from "react";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import {
  getCommunityHealth,
  getEngagement,
  getAtRiskMembers,
  getTopicAnalysis,
  getOptimalTimes,
  CommunityHealth,
  EngagementData,
  AtRiskMember,
  TopicAnalysis,
  OptimalTime,
} from "@/lib/api";
import LoadingSpinner from "@/components/LoadingSpinner";
import PageHeader from "@/components/PageHeader";
import CommunityHealthCard from "@/components/CommunityHealth";
import EngagementChart from "@/components/EngagementChart";
import AtRiskPanel from "@/components/AtRiskPanel";
import ActivityHeatmap from "@/components/ActivityHeatmap";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function ServerAnalyticsPage() {
  const authenticated = useAuthGuard();
  const [loading, setLoading] = useState(true);
  const [health, setHealth] = useState<CommunityHealth | null>(null);
  const [engagement, setEngagement] = useState<EngagementData[]>([]);
  const [atRisk, setAtRisk] = useState<AtRiskMember[]>([]);
  const [topics, setTopics] = useState<TopicAnalysis[]>([]);
  const [optimalTimes, setOptimalTimes] = useState<OptimalTime[]>([]);
  const [error, setError] = useState<string | null>(null);

  const guildId = typeof window !== "undefined"
    ? localStorage.getItem("guild_id") || "0"
    : "0";

  const fetchData = useCallback(async () => {
    try {
      const [h, e, r, t, o] = await Promise.all([
        getCommunityHealth(guildId),
        getEngagement(guildId),
        getAtRiskMembers(guildId),
        getTopicAnalysis(guildId),
        getOptimalTimes(guildId),
      ]);
      setHealth(h);
      setEngagement(e);
      setAtRisk(r);
      setTopics(t);
      setOptimalTimes(o);
    } catch (err) {
      setError(err instanceof Error ? err.message : "データの取得に失敗しました");
    } finally {
      setLoading(false);
    }
  }, [guildId]);

  useEffect(() => {
    if (authenticated) fetchData();
  }, [authenticated, fetchData]);

  if (!authenticated || loading) return <LoadingSpinner />;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <PageHeader
        title="コマンドセンター"
        description="サーバー分析とアクション管理"
      />

      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-3 mb-4 text-destructive text-sm">
          {error}
          <button onClick={() => setError(null)} className="ml-2 underline">閉じる</button>
        </div>
      )}

      <div className="space-y-6">
        {/* Community Health */}
        {health && <CommunityHealthCard health={health} />}

        {/* Engagement Chart */}
        <EngagementChart data={engagement} />

        {/* Topics */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">トピック分析</CardTitle>
          </CardHeader>
          <CardContent>
            {topics.length === 0 ? (
              <p className="text-sm text-muted-foreground">データがありません</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {topics.map((t) => {
                  const trend = t.this_week > t.last_week ? "up" : t.this_week < t.last_week ? "down" : "same";
                  return (
                    <Badge
                      key={t.topic}
                      variant="outline"
                      className="text-sm py-1 px-3"
                      style={{ fontSize: `${Math.min(1.2, 0.75 + t.count * 0.02)}rem` }}
                    >
                      {t.topic} ({t.count})
                      {trend === "up" && " ↑"}
                      {trend === "down" && " ↓"}
                    </Badge>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>

        {/* At-Risk Members */}
        <AtRiskPanel members={atRisk} guildId={guildId} />

        {/* Activity Heatmap */}
        <ActivityHeatmap data={optimalTimes} />
      </div>
    </div>
  );
}
