"use client";

import { useEffect, useState, useCallback } from "react";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import { getChallenges, Challenge } from "@/lib/api";
import LoadingSpinner from "@/components/LoadingSpinner";
import PageHeader from "@/components/PageHeader";
import ChallengeCard from "@/components/ChallengeCard";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function ChallengesPage() {
  const authenticated = useAuthGuard();
  const [loading, setLoading] = useState(true);
  const [challenges, setChallenges] = useState<Challenge[]>([]);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const data = await getChallenges();
      setChallenges(data);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "データの取得に失敗しました"
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (authenticated) fetchData();
  }, [authenticated, fetchData]);

  if (!authenticated || loading) return <LoadingSpinner />;

  const activeChallenges = challenges.filter((c) => c.status === "active");
  const upcomingChallenges = challenges.filter((c) => c.status === "upcoming");
  const completedChallenges = challenges.filter(
    (c) => c.status === "completed"
  );

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <PageHeader
        title="コホートチャレンジ"
        description="仲間と一緒に目標を達成しよう"
      />

      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-3 mb-4 text-destructive text-sm">
          {error}
          <button onClick={() => setError(null)} className="ml-2 underline">
            閉じる
          </button>
        </div>
      )}

      <Tabs defaultValue="active" className="w-full">
        <TabsList className="mb-6">
          <TabsTrigger value="active">
            進行中 ({activeChallenges.length})
          </TabsTrigger>
          <TabsTrigger value="upcoming">
            予定 ({upcomingChallenges.length})
          </TabsTrigger>
          <TabsTrigger value="completed">
            完了 ({completedChallenges.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="active">
          {activeChallenges.length === 0 ? (
            <div className="text-center py-16 text-muted-foreground">
              <p className="text-lg mb-2">進行中のチャレンジはありません</p>
              <p className="text-sm">
                Discordで <code>/challenge create</code>{" "}
                を使ってチャレンジを作成しましょう！
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {activeChallenges.map((c) => (
                <ChallengeCard key={c.id} challenge={c} />
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="upcoming">
          {upcomingChallenges.length === 0 ? (
            <div className="text-center py-16 text-muted-foreground">
              <p>予定されているチャレンジはありません</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {upcomingChallenges.map((c) => (
                <ChallengeCard key={c.id} challenge={c} />
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="completed">
          {completedChallenges.length === 0 ? (
            <div className="text-center py-16 text-muted-foreground">
              <p>完了したチャレンジはありません</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {completedChallenges.map((c) => (
                <ChallengeCard key={c.id} challenge={c} />
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
