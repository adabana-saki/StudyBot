"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { isAuthenticated } from "@/lib/auth";
import { getLeaderboard, LeaderboardEntry } from "@/lib/api";
import LeaderboardTable from "@/components/LeaderboardTable";
import PageHeader from "@/components/PageHeader";
import LoadingSpinner from "@/components/LoadingSpinner";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";

const categories = [
  { value: "xp", label: "XP" },
  { value: "study_time", label: "学習時間" },
  { value: "tasks", label: "タスク" },
];

const periods = [
  { value: "weekly", label: "週間" },
  { value: "monthly", label: "月間" },
  { value: "all_time", label: "全期間" },
];

function LeaderboardContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [entries, setEntries] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [category, setCategory] = useState(
    searchParams.get("category") || "xp"
  );
  const [period, setPeriod] = useState(
    searchParams.get("period") || "all_time"
  );

  // Use guild_id from query param or a placeholder
  const guildId = searchParams.get("guild_id") || "default";

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/");
      return;
    }

    async function fetchData() {
      setLoading(true);
      setError(null);
      try {
        const data = await getLeaderboard(guildId, category, period);
        setEntries(data);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "データの取得に失敗しました"
        );
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [router, guildId, category, period]);

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <PageHeader title="リーダーボード" />

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4 mb-6">
        {/* Category Tabs */}
        <Tabs value={category} onValueChange={setCategory}>
          <TabsList>
            {categories.map((cat) => (
              <TabsTrigger key={cat.value} value={cat.value}>
                {cat.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>

        {/* Period Selector */}
        <Tabs value={period} onValueChange={setPeriod}>
          <TabsList>
            {periods.map((p) => (
              <TabsTrigger key={p.value} value={p.value}>
                {p.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      </div>

      {/* Content */}
      {loading ? (
        <LoadingSpinner label="データを読み込み中..." />
      ) : error ? (
        <Card className="border-destructive/50">
          <CardContent className="p-8 text-center">
            <span className="text-4xl block mb-4">⚠️</span>
            <p className="text-muted-foreground">{error}</p>
          </CardContent>
        </Card>
      ) : (
        <LeaderboardTable entries={entries} />
      )}
    </div>
  );
}

export default function LeaderboardPage() {
  return (
    <Suspense fallback={<LoadingSpinner label="読み込み中..." />}>
      <LeaderboardContent />
    </Suspense>
  );
}
